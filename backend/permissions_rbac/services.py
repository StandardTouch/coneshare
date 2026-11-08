"""
Permission evaluation for system, dataroom, and site actions.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple

from django.core.cache import cache
from django.db.models import Q

from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument, DataroomFolder
from permissions_rbac.catalogue import (
    ALL_SYSTEM_PERMISSIONS,
    MODIFY_PERMISSIONS,
    PERM_CREATE_DATAROOM,
    PERM_CREATE_FOLDER,
    PERM_DATAROOM_CREATE,
    PERM_DATAROOM_DELETE,
    PERM_DATAROOM_EDIT,
    PERM_DATAROOM_QNA_TAB,
    PERM_DATAROOM_SETTINGS_TAB,
    PERM_DELETE,
    PERM_DELETE_DATAROOM,
    PERM_DOWNLOAD,
    PERM_EDIT_DATAROOM_SETTINGS,
    PERM_FILE_CREATE_SHARE_LINK,
    PERM_FILE_DOWNLOAD,
    PERM_FILE_RENAME,
    PERM_FILE_VIEW,
    PERM_FOLDER_CREATE,
    PERM_FOLDER_DELETE,
    PERM_FOLDER_RENAME,
    PERM_MANAGE_SHARE_SETTINGS,
    PERM_MOVE,
    PERM_RENAME,
    PERM_REORDER,
    PERM_UPLOAD,
    PERM_UPLOAD_ADD_FROM_CONTENT,
    PERM_UPLOAD_FILES,
    PERM_UPLOAD_FOLDER,
    PERM_VIEW,
    ROLE_SLUG_ADMIN,
    SCOPE_ANY,
    SCOPE_OWN,
)
from permissions_rbac.models import (
    DataroomRole,
    DataroomRolePermission,
    SiteRolePermission,
)
from permissions_rbac.request_context import rbac_request_state
from permissions_rbac.safety import user_has_full_access

CACHE_TIMEOUT = 3600


def _role_cache_key(organization_id: str, role_id: str) -> str:
    return f'rbac:role_grants:{organization_id}:{role_id}'


def _site_cache_key(organization_id: str, site_role: str) -> str:
    return f'rbac:site_grants:{organization_id}:{site_role}'


def invalidate_organization_rbac_cache(organization_id: str) -> None:
    if not organization_id:
        return
    role_ids = DataroomRole.objects.filter(organization_id=organization_id).values_list('id', flat=True)
    keys = [_site_cache_key(organization_id, 'admin'), _site_cache_key(organization_id, 'member')]
    keys.extend(_role_cache_key(organization_id, str(rid)) for rid in role_ids)
    cache.delete_many(keys)


def invalidate_role_cache(role: DataroomRole) -> None:
    cache.delete(_role_cache_key(str(role.organization_id), str(role.id)))


def invalidate_folder_rule_cache(role: DataroomRole) -> None:
    """No-op after folder rule removal; kept for model compatibility."""
    return None


def _load_role_grants(role: DataroomRole) -> Dict[str, str]:
    cache_key = _role_cache_key(str(role.organization_id), str(role.id))
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    grants = {
        row.permission: (row.scope or SCOPE_ANY)
        for row in DataroomRolePermission.objects.filter(role=role)
    }
    cache.set(cache_key, grants, CACHE_TIMEOUT)
    return grants


def _load_site_grants(organization_id: str, site_role: str) -> Set[str]:
    cache_key = _site_cache_key(organization_id, site_role)
    cached = cache.get(cache_key)
    if cached is not None:
        return set(cached)
    perms = set(
        SiteRolePermission.objects.filter(
            organization_id=organization_id,
            site_role=site_role,
        ).values_list('permission', flat=True)
    )
    cache.set(cache_key, list(perms), CACHE_TIMEOUT)
    return perms


def resolve_organization_role(user) -> Optional[DataroomRole]:
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    org_role = getattr(user, 'organization_role', None)
    if org_role is None and getattr(user, 'organization_role_id', None):
        org_role = (
            DataroomRole.objects.filter(id=user.organization_role_id)
            .only('id', 'organization_id', 'slug')
            .first()
        )
    if org_role is not None:
        return org_role
    if getattr(user, 'role', '') == 'admin' and getattr(user, 'organization_id', None):
        return DataroomRole.objects.filter(
            organization_id=user.organization_id,
            slug=ROLE_SLUG_ADMIN,
        ).first()
    return None


def get_collaborator_dataroom_role(user, dataroom: Dataroom) -> Optional[DataroomRole]:
    if user is None or not user.is_authenticated:
        return None
    if dataroom.created_by_id == user.id:
        return None
    if not DataroomCollaborator.objects.filter(dataroom=dataroom, user=user).exists():
        return None
    return resolve_organization_role(user)


def _item_created_by_user(user, dataroom: Dataroom, item_type: str, item) -> bool:
    if item_type == 'folder':
        folder = item
        if folder.created_by_id != user.id:
            return False
        all_folder_ids = _expand_dataroom_folder_ids(dataroom, [folder.id])
        if (
            DataroomFolder.objects.filter(id__in=all_folder_ids, dataroom=dataroom)
            .exclude(created_by_id=user.id)
            .exists()
        ):
            return False
        foreign_doc = DataroomDocument.objects.filter(
            dataroom=dataroom,
            folder_id__in=all_folder_ids,
        ).exclude(document__created_by_id=user.id).exists()
        return not foreign_doc
    if item_type == 'document':
        ddoc = item
        doc = getattr(ddoc, 'document', None)
        return doc is not None and doc.created_by_id == user.id
    return False


def _expand_dataroom_folder_ids(dataroom: Dataroom, dataroom_folder_ids: list) -> set:
    all_folder_ids = set(dataroom_folder_ids or [])
    if not all_folder_ids:
        return all_folder_ids
    folders_to_check = list(
        DataroomFolder.objects.filter(id__in=all_folder_ids, dataroom=dataroom)
    )
    stack = list(folders_to_check)
    while stack:
        folder = stack.pop()
        for child in folder.children.all():
            if child.id not in all_folder_ids:
                all_folder_ids.add(child.id)
                stack.append(child)
    return all_folder_ids


def _effective_scope(stored_scope: str, permission: str) -> str:
    return stored_scope or SCOPE_ANY


def _resolve_action_codename(action: str, item_type: Optional[str] = None) -> str:
    legacy_actions = {
        'view': PERM_FILE_VIEW,
        'download': PERM_FILE_DOWNLOAD,
        'upload': PERM_UPLOAD_FILES,
        'create_folder': PERM_FOLDER_CREATE,
        'delete': PERM_FOLDER_DELETE,
        'rename': PERM_RENAME,
        'move': PERM_MOVE,
        'reorder': PERM_REORDER,
        'create_dataroom': PERM_DATAROOM_CREATE,
        'delete_dataroom': PERM_DATAROOM_DELETE,
        'edit_dataroom_settings': PERM_EDIT_DATAROOM_SETTINGS,
        'manage_share_settings': PERM_MANAGE_SHARE_SETTINGS,
    }
    if action in legacy_actions and action not in (
        PERM_RENAME,
        PERM_MOVE,
        PERM_REORDER,
        PERM_DELETE,
    ):
        return legacy_actions[action]
    if action == PERM_VIEW:
        return PERM_FILE_VIEW
    if action == PERM_DOWNLOAD:
        return PERM_FILE_DOWNLOAD
    if action == PERM_UPLOAD:
        return PERM_UPLOAD_FILES
    if action == PERM_CREATE_FOLDER:
        return PERM_FOLDER_CREATE
    if action == PERM_DELETE_DATAROOM:
        return PERM_DATAROOM_DELETE
    if action == PERM_CREATE_DATAROOM:
        return PERM_DATAROOM_CREATE
    if action == PERM_EDIT_DATAROOM_SETTINGS:
        return PERM_DATAROOM_SETTINGS_TAB
    if action == PERM_MANAGE_SHARE_SETTINGS:
        return PERM_FILE_CREATE_SHARE_LINK
    if action in (PERM_RENAME, PERM_MOVE, PERM_REORDER):
        if item_type == 'folder':
            return PERM_FOLDER_RENAME
        if item_type == 'document':
            return PERM_FILE_RENAME
        return PERM_FOLDER_RENAME
    if action in (PERM_DELETE, 'delete'):
        return PERM_FOLDER_DELETE
    return action


def has_system_perm(user, permission: str) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if user_has_full_access(user):
        return True
    if permission not in ALL_SYSTEM_PERMISSIONS:
        return False
    role = resolve_organization_role(user)
    if role is None:
        return False
    grants = _load_role_grants(role)
    return permission in grants


def has_site_perm(user, permission: str) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if user_has_full_access(user):
        return True
    if permission == PERM_CREATE_DATAROOM or permission == PERM_DATAROOM_CREATE:
        role = resolve_organization_role(user)
        if role is None:
            return False
        grants = _load_role_grants(role)
        return PERM_DATAROOM_CREATE in grants
    site_role = getattr(user, 'role', '') or 'member'
    grants = _load_site_grants(str(user.organization_id), site_role)
    return permission in grants


def has_perm(
    user,
    action: str,
    dataroom: Optional[Dataroom] = None,
    item=None,
    item_type: Optional[str] = None,
) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False

    if user_has_full_access(user):
        if action in (PERM_CREATE_DATAROOM, PERM_DATAROOM_CREATE):
            return True
        if dataroom is not None:
            return True
        return has_system_perm(user, action) or action in ALL_SYSTEM_PERMISSIONS

    if action in (PERM_CREATE_DATAROOM, PERM_DATAROOM_CREATE, 'create_dataroom'):
        return has_site_perm(user, PERM_DATAROOM_CREATE)

    if action in ALL_SYSTEM_PERMISSIONS:
        return has_system_perm(user, action)

    if dataroom is None:
        return False

    if getattr(dataroom, 'created_by_id', None) == user.id:
        return True

    role = get_collaborator_dataroom_role(user, dataroom)
    if role is None:
        return False

    resolved_type = item_type
    if resolved_type is None and item is not None:
        if isinstance(item, DataroomFolder):
            resolved_type = 'folder'
        elif isinstance(item, DataroomDocument):
            resolved_type = 'document'

    codename = _resolve_action_codename(action, resolved_type)
    grants = _load_role_grants(role)
    if codename not in grants:
        return False

    stored_scope = grants[codename]
    scope = _effective_scope(stored_scope, codename)

    if scope == SCOPE_ANY:
        return True
    if scope == SCOPE_OWN:
        if item is None:
            return False
        return _item_created_by_user(user, dataroom, resolved_type or '', item)
    return False


def resolved_folder_for_item(item, item_type: Optional[str] = None):
    if item_type == 'folder' or isinstance(item, DataroomFolder):
        return item
    if item_type == 'document' or isinstance(item, DataroomDocument):
        return getattr(item, 'folder', None)
    return None


def hidden_folder_ids_for_user(user, dataroom: Dataroom) -> Set[str]:
    return set()


def is_folder_hidden_for_role(folder: DataroomFolder, role: DataroomRole) -> bool:
    return False


def is_folder_view_only_for_role(folder: DataroomFolder, role: DataroomRole) -> bool:
    return False


def filter_dataroom_documents_for_user(qs, user, dataroom: Dataroom):
    from datarooms.utils import is_dataroom_owner_or_admin

    if is_dataroom_owner_or_admin(user, dataroom):
        return qs
    role = get_collaborator_dataroom_role(user, dataroom)
    if role is None:
        return qs.none()
    grants = _load_role_grants(role)
    if PERM_FILE_VIEW not in grants:
        return qs.none()
    scope = _effective_scope(grants[PERM_FILE_VIEW], PERM_FILE_VIEW)
    hidden = hidden_folder_ids_for_user(user, dataroom)
    if hidden:
        qs = qs.exclude(folder_id__in=hidden)
    if scope == SCOPE_OWN:
        qs = qs.filter(document__created_by=user)
    return qs


def filter_dataroom_folders_for_user(qs, user, dataroom: Dataroom):
    return qs


def assert_dataroom_perm(user, action: str, dataroom: Dataroom, item=None, item_type: Optional[str] = None) -> None:
    from rest_framework.exceptions import PermissionDenied

    from datarooms.collaborator_delete_permissions import COLLABORATOR_MODIFY_DENIED_DETAIL

    if has_perm(user, action, dataroom, item=item, item_type=item_type):
        return
    if action in MODIFY_PERMISSIONS or action in (PERM_DELETE, PERM_RENAME, PERM_MOVE, PERM_REORDER):
        raise PermissionDenied(COLLABORATOR_MODIFY_DENIED_DETAIL)
    raise PermissionDenied('You do not have permission to perform this action.')


def item_permissions_for_user(user, dataroom: Dataroom, item_type: str, item) -> Dict[str, bool]:
    if getattr(dataroom, 'created_by_id', None) == user.id or user_has_full_access(user):
        return {
            'can_view': True,
            'can_download': True,
            'can_modify': True,
            'can_delete': True,
            'can_rename': True,
            'can_move': True,
            'can_reorder': True,
            'can_manage_share_settings': True,
            'can_upload_files': True,
            'can_upload_folder': True,
            'can_upload_add_from_content': True,
            'can_create_folder': True,
            'can_upload': True,
        }
    return {
        'can_view': has_perm(user, PERM_VIEW, dataroom, item, item_type),
        'can_download': has_perm(user, PERM_DOWNLOAD, dataroom, item, item_type),
        'can_modify': has_perm(user, PERM_RENAME, dataroom, item, item_type),
        'can_delete': has_perm(user, PERM_DELETE, dataroom, item, item_type),
        'can_rename': has_perm(user, PERM_RENAME, dataroom, item, item_type),
        'can_move': has_perm(user, PERM_MOVE, dataroom, item, item_type),
        'can_reorder': has_perm(user, PERM_REORDER, dataroom, item, item_type),
        'can_manage_share_settings': has_perm(
            user, PERM_MANAGE_SHARE_SETTINGS, dataroom, item, item_type
        ),
        'can_upload_files': has_perm(user, PERM_UPLOAD_FILES, dataroom, item, item_type),
        'can_upload_folder': has_perm(user, PERM_UPLOAD_FOLDER, dataroom, item, item_type),
        'can_upload_add_from_content': has_perm(
            user, PERM_UPLOAD_ADD_FROM_CONTENT, dataroom, item, item_type
        ),
        'can_create_folder': has_perm(user, PERM_FOLDER_CREATE, dataroom, item, item_type),
        'can_upload': has_perm(user, PERM_UPLOAD_FILES, dataroom, item, item_type),
    }


MODIFY_ACTIONS = (
    PERM_RENAME,
    PERM_MOVE,
    PERM_REORDER,
    PERM_DELETE,
    PERM_MANAGE_SHARE_SETTINGS,
)


def assert_user_may_modify_dataroom_content(
    user,
    dataroom: Dataroom,
    dataroom_doc_ids=None,
    dataroom_folder_ids=None,
) -> None:
    dataroom_doc_ids = list(dataroom_doc_ids or [])
    dataroom_folder_ids = list(dataroom_folder_ids or [])
    all_folder_ids = _expand_dataroom_folder_ids(dataroom, dataroom_folder_ids)

    if all_folder_ids:
        for folder in DataroomFolder.objects.filter(id__in=all_folder_ids, dataroom=dataroom):
            assert_dataroom_perm(user, PERM_RENAME, dataroom, folder, 'folder')

    ddocs_qs = DataroomDocument.objects.filter(
        Q(id__in=dataroom_doc_ids)
        | Q(document_id__in=dataroom_doc_ids)
        | Q(folder_id__in=all_folder_ids),
        dataroom=dataroom,
    ).select_related('document')

    for ddoc in ddocs_qs:
        assert_dataroom_perm(user, PERM_RENAME, dataroom, ddoc, 'document')


def assert_user_may_remove_dataroom_content(
    user,
    dataroom: Dataroom,
    dataroom_doc_ids=None,
    dataroom_folder_ids=None,
) -> None:
    dataroom_doc_ids = list(dataroom_doc_ids or [])
    dataroom_folder_ids = list(dataroom_folder_ids or [])
    all_folder_ids = _expand_dataroom_folder_ids(dataroom, dataroom_folder_ids)

    if all_folder_ids:
        for folder in DataroomFolder.objects.filter(id__in=all_folder_ids, dataroom=dataroom):
            assert_dataroom_perm(user, PERM_DELETE, dataroom, folder, 'folder')

    ddocs_qs = DataroomDocument.objects.filter(
        Q(id__in=dataroom_doc_ids)
        | Q(document_id__in=dataroom_doc_ids)
        | Q(folder_id__in=all_folder_ids),
        dataroom=dataroom,
    ).select_related('document')

    for ddoc in ddocs_qs:
        assert_dataroom_perm(user, PERM_DELETE, dataroom, ddoc, 'document')


def assert_user_may_modify_dataroom_document(user, dataroom_document: DataroomDocument) -> None:
    assert_dataroom_perm(user, PERM_RENAME, dataroom_document.dataroom, dataroom_document, 'document')


def assert_user_may_modify_dataroom_folder(user, dataroom_folder: DataroomFolder) -> None:
    assert_dataroom_perm(user, PERM_RENAME, dataroom_folder.dataroom, dataroom_folder, 'folder')


def assert_user_may_reorder_dataroom_items(user, dataroom: Dataroom, ordered_items) -> None:
    folder_ids = [item['id'] for item in ordered_items if item.get('type') == 'folder']
    doc_ids = [item['id'] for item in ordered_items if item.get('type') == 'document']
    assert_user_may_modify_dataroom_content(
        user,
        dataroom,
        dataroom_doc_ids=doc_ids,
        dataroom_folder_ids=folder_ids,
    )


def user_can_modify_dataroom_item(user, dataroom: Dataroom, item_type: str, item) -> bool:
    return has_perm(user, PERM_RENAME, dataroom, item, item_type)


def user_can_delete_dataroom_item(user, dataroom: Dataroom, item_type: str, item) -> bool:
    return has_perm(user, PERM_DELETE, dataroom, item, item_type)


def assert_user_may_create_dataroom(user) -> None:
    from rest_framework.exceptions import PermissionDenied

    from datarooms.dataroom_create_policy import DATAROOM_CREATE_DENIED_DETAIL

    if has_site_perm(user, PERM_DATAROOM_CREATE):
        return
    raise PermissionDenied(DATAROOM_CREATE_DENIED_DETAIL)


def collaborator_viewable_document_ids(user) -> Set[str]:
    """Document IDs a collaborator may open via dataroom file_view (incl. own/any scope)."""
    from datarooms.views import get_dataroom_queryset_for_user

    doc_ids: Set[str] = set()
    rooms = (
        get_dataroom_queryset_for_user(user)
        .filter(collaborators__user=user)
        .distinct()
    )
    for room in rooms:
        dd_qs = DataroomDocument.objects.filter(dataroom=room)
        dd_qs = filter_dataroom_documents_for_user(dd_qs, user, room)
        doc_ids.update(str(doc_id) for doc_id in dd_qs.values_list('document_id', flat=True))
    return doc_ids


def user_can_view_document_via_dataroom(user, document_id: str) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    viewable = collaborator_viewable_document_ids(user)
    if str(document_id) in viewable:
        return True
    return DataroomDocument.objects.filter(
        document_id=document_id,
        dataroom__created_by_id=user.id,
        dataroom__organization_id=user.organization_id,
    ).exists()


def user_dataroom_capabilities(user, dataroom: Dataroom) -> Dict[str, bool]:
    owner = getattr(dataroom, 'created_by_id', None) == getattr(user, 'id', None)
    full = owner or user_has_full_access(user)
    can_upload_files = full or has_perm(user, PERM_UPLOAD_FILES, dataroom)
    can_upload_folder = full or has_perm(user, PERM_UPLOAD_FOLDER, dataroom)
    return {
        'can_upload_files': can_upload_files,
        'can_upload_folder': can_upload_folder,
        'can_upload_add_from_content': full or has_perm(
            user, PERM_UPLOAD_ADD_FROM_CONTENT, dataroom
        ),
        'can_create_folder': full or has_perm(user, PERM_FOLDER_CREATE, dataroom),
        'can_upload': can_upload_files or can_upload_folder,
        'can_edit_dataroom_settings': full or has_perm(user, PERM_EDIT_DATAROOM_SETTINGS, dataroom),
        'can_delete_dataroom': full or has_perm(user, PERM_DELETE_DATAROOM, dataroom),
        'can_edit_dataroom': full or has_perm(user, PERM_DATAROOM_EDIT, dataroom),
        'can_see_qna_tab': full or has_perm(user, PERM_DATAROOM_QNA_TAB, dataroom),
        'can_see_settings_tab': full or has_perm(user, PERM_DATAROOM_SETTINGS_TAB, dataroom),
    }
