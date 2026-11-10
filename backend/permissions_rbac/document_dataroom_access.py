"""Dataroom-scoped access to document workspace APIs (without system_documents)."""
from __future__ import annotations

from typing import Optional

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, PermissionDenied

from datarooms.models import Dataroom, DataroomDocument
from documents.models import Document
from permissions_rbac.catalogue import (
    PERM_DATAROOM_QNA_TAB,
    PERM_FILE_CREATE_SHARE_LINK,
    PERM_FILE_DOWNLOAD,
    PERM_FILE_RENAME,
    PERM_FILE_VIEW,
)
from permissions_rbac.services import has_perm, item_permissions_for_user

# DocumentViewSet actions allowed via dataroom grants when system_documents is off.
_DATAROOM_DOCUMENT_VIEWSET_ACTIONS = {
    'retrieve': PERM_FILE_VIEW,
    'status': PERM_FILE_VIEW,
    'stats': PERM_FILE_VIEW,
    'versions': PERM_FILE_VIEW,
    'view_sessions': PERM_FILE_VIEW,
}


def _accessible_dataroom_document_pairs(user, document_id: str):
    from datarooms.views import get_dataroom_queryset_for_user

    accessible_rooms = get_dataroom_queryset_for_user(user)
    return (
        DataroomDocument.objects.filter(
            document_id=document_id,
            dataroom_id__in=accessible_rooms.values('id'),
        )
        .select_related('dataroom', 'document', 'folder')
    )


def user_has_dataroom_document_permission(user, document_id: str, permission: str) -> bool:
    for ddoc in _accessible_dataroom_document_pairs(user, document_id):
        if has_perm(user, permission, ddoc.dataroom, ddoc, 'document'):
            return True
    return False


def user_can_access_document_viewset_action(user, action: str, document_id: str) -> bool:
    permission = _DATAROOM_DOCUMENT_VIEWSET_ACTIONS.get(action)
    if not permission:
        return False
    return user_has_dataroom_document_permission(user, document_id, permission)


def ensure_document_viewset_dataroom_access(view, user) -> None:
    from featuregates.services import documents_enabled_for_user

    if documents_enabled_for_user(user):
        return
    action = getattr(view, 'action', None)
    if action == 'list':
        raise PermissionDenied('You do not have permission to perform this action.')
    lookup_url_kwarg = getattr(view, 'lookup_url_kwarg', None) or view.lookup_field
    document_id = view.kwargs.get(lookup_url_kwarg or 'pk')
    if document_id and user_can_access_document_viewset_action(user, action, document_id):
        return
    if action in _DATAROOM_DOCUMENT_VIEWSET_ACTIONS:
        raise NotFound()
    raise PermissionDenied('You do not have permission to perform this action.')


def user_can_view_document_analytics(user, document: Document) -> bool:
    from featuregates.services import documents_enabled_for_user

    if getattr(user, 'role', '') == 'admin' and document.organization_id == user.organization_id:
        return True
    if document.created_by_id == user.id and documents_enabled_for_user(user):
        return True
    return user_has_dataroom_document_permission(user, str(document.id), PERM_FILE_VIEW)


def user_can_manage_document_share_links(user, document: Document) -> bool:
    from featuregates.services import documents_enabled_for_user

    if getattr(user, 'role', '') == 'admin' and document.organization_id == user.organization_id:
        return True
    if document.created_by_id == user.id and documents_enabled_for_user(user):
        return True
    return user_has_dataroom_document_permission(
        user, str(document.id), PERM_FILE_CREATE_SHARE_LINK
    )


def user_can_access_dataroom_qna_for_document(user, document: Document, dataroom_id: Optional[str] = None) -> bool:
    from featuregates.services import documents_enabled_for_user

    if getattr(user, 'role', '') == 'admin' and document.organization_id == user.organization_id:
        return True
    if document.created_by_id == user.id and documents_enabled_for_user(user):
        return True

    pairs = _accessible_dataroom_document_pairs(user, str(document.id))
    if dataroom_id:
        pairs = pairs.filter(dataroom_id=dataroom_id)
    for ddoc in pairs:
        if has_perm(user, PERM_DATAROOM_QNA_TAB, ddoc.dataroom):
            return True
    return False


def document_dataroom_page_permissions(user, document: Document, dataroom_id: str) -> dict:
    dataroom = get_object_or_404(Dataroom, id=dataroom_id, organization_id=user.organization_id)
    ddoc = (
        DataroomDocument.objects.filter(dataroom=dataroom, document_id=document.id)
        .select_related('document', 'folder')
        .first()
    )
    if ddoc is None:
        return {}
    item = item_permissions_for_user(user, dataroom, 'document', ddoc)
    return {
        'dataroom_id': str(dataroom.id),
        'can_view': item.get('can_view', False),
        'can_download': item.get('can_download', False),
        'can_print': item.get('can_print', False),
        'can_rename': item.get('can_rename', False),
        'can_create_share_link': item.get('can_manage_share_settings', False),
        'can_see_qna_tab': has_perm(user, PERM_DATAROOM_QNA_TAB, dataroom),
        'can_see_analytics': item.get('can_view', False),
    }


def user_can_preview_document(user, document_id: str) -> bool:
    from featuregates.services import documents_enabled_for_user

    if documents_enabled_for_user(user):
        return True
    return user_has_dataroom_document_permission(user, document_id, PERM_FILE_VIEW)


def user_can_download_document_dataroom(user, document_id: str) -> bool:
    return user_has_dataroom_document_permission(user, document_id, PERM_FILE_DOWNLOAD)


def user_can_rename_document_dataroom(user, document_id: str) -> bool:
    return user_has_dataroom_document_permission(user, document_id, PERM_FILE_RENAME)
