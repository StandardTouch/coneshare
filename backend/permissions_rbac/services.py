"""
Permission evaluation for dataroom and site actions.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple

from django.core.cache import cache
from django.db.models import Q

from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument, DataroomFolder
from datarooms.utils import is_dataroom_owner_or_admin
from permissions_rbac.catalogue import (
    MODIFY_PERMISSIONS,
    PERM_CREATE_DATAROOM,
    PERM_CREATE_FOLDER,
    PERM_DELETE,
    PERM_DELETE_DATAROOM,
    PERM_DOWNLOAD,
    PERM_EDIT_DATAROOM_SETTINGS,
    PERM_INVITE_COLLABORATORS,
    PERM_MANAGE_COLLABORATORS,
    PERM_MANAGE_SHARE_SETTINGS,
    PERM_MOVE,
    PERM_RENAME,
    PERM_REORDER,
    PERM_UPLOAD,
    PERM_VIEW,
    ROLE_SLUG_EDITOR,
    SCOPE_ANY,
    SCOPE_OWN,
)
from permissions_rbac.models import (
    DataroomFolderRoleRule,
    DataroomRole,
    DataroomRolePermission,
    SiteRolePermission,
)
from permissions_rbac.request_context import rbac_request_state

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


def get_collaborator_dataroom_role(user, dataroom: Dataroom) -> Optional[DataroomRole]:
    if user is None or not user.is_authenticated:
        return None
    if dataroom.created_by_id == user.id:
        return None
    collab = (
        DataroomCollaborator.objects.filter(dataroom=dataroom, user=user)
        .select_related('dataroom_role')
        .first()
    )
    if not collab:
        return None
    if collab.dataroom_role_id:
        return collab.dataroom_role
    # Fallback for rows not yet migrated
    return DataroomRole.objects.filter(
        organization=dataroom.organization,
        slug=ROLE_SLUG_EDITOR,
    ).first()


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


def has_site_perm(user, permission: str) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    site_role = getattr(user, 'role', '') or 'member'
    if site_role == 'admin':
        org_id = str(user.organization_id)
        grants = _load_site_grants(org_id, site_role)
        return permission in grants

    org_role = getattr(user, 'organization_role', None)
    if org_role is None and getattr(user, 'organization_role_id', None):
        org_role = (
            DataroomRole.objects.filter(id=user.organization_role_id)
            .only('id', 'organization_id')
            .first()
        )
    if org_role is not None:
        role_grants = _load_role_grants(org_role)
        return permission in role_grants

    org_id = str(user.organization_id)
    grants = _load_site_grants(org_id, 'member')
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

    if action == PERM_CREATE_DATAROOM:
        return has_site_perm(user, PERM_CREATE_DATAROOM)

    if dataroom is None:
        return False

    if is_dataroom_owner_or_admin(user, dataroom):
        return True

    role = get_collaborator_dataroom_role(user, dataroom)
    if role is None:
        return False

    grants = _load_role_grants(role)
    if action not in grants:
        return False

    stored_scope = grants[action]
    scope = _effective_scope(stored_scope, action)

    if scope == SCOPE_ANY:
        allowed = True
    elif scope == SCOPE_OWN:
        if item is None:
            allowed = False
        else:
            resolved_type = item_type
            if resolved_type is None:
                if isinstance(item, DataroomFolder):
                    resolved_type = 'folder'
                elif isinstance(item, DataroomDocument):
                    resolved_type = 'document'
            allowed = _item_created_by_user(user, dataroom, resolved_type or '', item)
    else:
        allowed = False

    if not allowed:
        return False

    if item is not None:
        folder = resolved_folder_for_item(item, item_type)
        if folder and is_folder_hidden_for_role(folder, role):
            return False
        if folder and is_folder_view_only_for_role(folder, role):
            if action not in (PERM_VIEW, PERM_DOWNLOAD):
                return False

    return True


def resolved_folder_for_item(item, item_type: Optional[str] = None):
    if item_type == 'folder' or isinstance(item, DataroomFolder):
        return item
    if item_type == 'document' or isinstance(item, DataroomDocument):
        return getattr(item, 'folder', None)
    return None


def _folder_rule_map_for_role(role: DataroomRole) -> Dict[str, str]:
    cache_key = f'rbac:folder_rules:{role.organization_id}:{role.id}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    rules = {
        str(row.dataroom_folder_id): row.rule
        for row in DataroomFolderRoleRule.objects.filter(dataroom_role=role).select_related('dataroom_folder')
    }
    cache.set(cache_key, rules, CACHE_TIMEOUT)
    return rules


def invalidate_folder_rule_cache(role: DataroomRole) -> None:
    cache.delete(f'rbac:folder_rules:{role.organization_id}:{role.id}')


def _effective_folder_rule_from_maps(
    folder_id: str,
    rule_map: Dict[str, str],
    parent_by_id: Dict[str, Optional[str]],
) -> str:
    current = folder_id
    visited = set()
    while current and current not in visited:
        visited.add(current)
        rule = rule_map.get(current)
        if rule and rule != DataroomFolderRoleRule.RULE_INHERIT:
            return rule
        current = parent_by_id.get(current)
    return DataroomFolderRoleRule.RULE_INHERIT


def _effective_folder_rule(folder: DataroomFolder, role: DataroomRole) -> str:
    rules = _folder_rule_map_for_role(role)
    parent_by_id = rbac_request_state().get(f'folder_parents:{folder.dataroom_id}')
    if parent_by_id is None:
        parent_by_id = {
            str(row['id']): str(row['parent_id']) if row['parent_id'] else None
            for row in DataroomFolder.objects.filter(dataroom_id=folder.dataroom_id).values('id', 'parent_id')
        }
        rbac_request_state()[f'folder_parents:{folder.dataroom_id}'] = parent_by_id
    return _effective_folder_rule_from_maps(str(folder.id), rules, parent_by_id)


def _compute_hidden_folder_ids(user, dataroom: Dataroom) -> Set[str]:
    if is_dataroom_owner_or_admin(user, dataroom):
        return set()
    role = get_collaborator_dataroom_role(user, dataroom)
    if role is None:
        return set()
    state = rbac_request_state()
    parent_key = f'folder_parents:{dataroom.id}'
    parent_by_id = state.get(parent_key)
    if parent_by_id is None:
        parent_by_id = {
            str(row['id']): str(row['parent_id']) if row['parent_id'] else None
            for row in DataroomFolder.objects.filter(dataroom=dataroom).values('id', 'parent_id')
        }
        state[parent_key] = parent_by_id
    rule_map = _folder_rule_map_for_role(role)
    hidden = set()
    for folder_id in parent_by_id.keys():
        if _effective_folder_rule_from_maps(folder_id, rule_map, parent_by_id) == DataroomFolderRoleRule.RULE_HIDDEN:
            hidden.add(folder_id)
    return hidden


def hidden_folder_ids_for_user(user, dataroom: Dataroom) -> Set[str]:
    cache_key = f'hidden_folder_ids:{user.id}:{dataroom.id}'
    state = rbac_request_state()
    if cache_key in state:
        return state[cache_key]
    hidden = _compute_hidden_folder_ids(user, dataroom)
    state[cache_key] = hidden
    return hidden


def is_folder_hidden_for_role(folder: DataroomFolder, role: DataroomRole) -> bool:
    return _effective_folder_rule(folder, role) == DataroomFolderRoleRule.RULE_HIDDEN


def is_folder_view_only_for_role(folder: DataroomFolder, role: DataroomRole) -> bool:
    return _effective_folder_rule(folder, role) == DataroomFolderRoleRule.RULE_VIEW_ONLY


def filter_dataroom_documents_for_user(qs, user, dataroom: Dataroom):
    hidden = hidden_folder_ids_for_user(user, dataroom)
    if not hidden:
        return qs
    return qs.exclude(folder_id__in=hidden)


def filter_dataroom_folders_for_user(qs, user, dataroom: Dataroom):
    hidden = hidden_folder_ids_for_user(user, dataroom)
    if not hidden:
        return qs
    return qs.exclude(id__in=hidden)


def assert_dataroom_perm(user, action: str, dataroom: Dataroom, item=None, item_type: Optional[str] = None) -> None:
    from rest_framework.exceptions import PermissionDenied

    from datarooms.collaborator_delete_permissions import COLLABORATOR_MODIFY_DENIED_DETAIL

    if has_perm(user, action, dataroom, item=item, item_type=item_type):
        return
    if action in MODIFY_PERMISSIONS or action == PERM_DELETE:
        raise PermissionDenied(COLLABORATOR_MODIFY_DENIED_DETAIL)
    raise PermissionDenied('You do not have permission to perform this action.')


def item_permissions_for_user(user, dataroom: Dataroom, item_type: str, item) -> Dict[str, bool]:
    if is_dataroom_owner_or_admin(user, dataroom):
        return {
            'can_view': True,
            'can_download': True,
            'can_modify': True,
            'can_delete': True,
            'can_rename': True,
            'can_move': True,
            'can_reorder': True,
            'can_manage_share_settings': True,
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
        'can_upload': has_perm(user, PERM_UPLOAD, dataroom, item, item_type),
    }


# Map legacy modify checks to RBAC actions
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

    if has_site_perm(user, PERM_CREATE_DATAROOM):
        return
    raise PermissionDenied(DATAROOM_CREATE_DENIED_DETAIL)
