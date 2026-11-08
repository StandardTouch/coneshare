"""Queryset and object-level enforcement for dataroom folder RBAC rules."""
from __future__ import annotations

from typing import Iterable, Optional, Set

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import NotFound, PermissionDenied

from datarooms.models import Dataroom, DataroomDocument, DataroomFolder
from datarooms.utils import is_dataroom_owner_or_admin
from permissions_rbac.catalogue import (
    PERM_CREATE_FOLDER,
    PERM_DOWNLOAD,
    PERM_UPLOAD,
    PERM_VIEW,
)
from permissions_rbac.services import (
    filter_dataroom_documents_for_user,
    filter_dataroom_folders_for_user,
    get_collaborator_dataroom_role,
    has_perm,
    hidden_folder_ids_for_user,
    is_folder_hidden_for_role,
)


def _accessible_datarooms_for_user(user) -> QuerySet:
    from datarooms.views import get_dataroom_queryset_for_user

    return get_dataroom_queryset_for_user(user)


def hidden_folder_ids_for_dataroom(user, dataroom: Dataroom) -> Set[str]:
    return hidden_folder_ids_for_user(user, dataroom)


def apply_folder_hidden_exclusions(qs: QuerySet, user, dataroom: Optional[Dataroom] = None) -> QuerySet:
    if dataroom is not None:
        return filter_dataroom_folders_for_user(qs, user, dataroom)
    exclusion = Q()
    for room in _accessible_datarooms_for_user(user):
        hidden = hidden_folder_ids_for_user(user, room)
        if hidden:
            exclusion |= Q(dataroom=room, id__in=hidden)
    if exclusion:
        return qs.exclude(exclusion)
    return qs


def apply_document_hidden_exclusions(qs: QuerySet, user, dataroom: Optional[Dataroom] = None) -> QuerySet:
    if dataroom is not None:
        return filter_dataroom_documents_for_user(qs, user, dataroom)
    exclusion = Q()
    for room in _accessible_datarooms_for_user(user):
        hidden = hidden_folder_ids_for_user(user, room)
        if hidden:
            exclusion |= Q(dataroom=room, folder_id__in=hidden)
    if exclusion:
        return qs.exclude(exclusion)
    return qs


def exclude_vault_documents_in_hidden_folders(document_qs: QuerySet, user) -> QuerySet:
    """Remove Document rows linked to dataroom items in hidden folders."""
    hidden_doc_ids = []
    for room in _accessible_datarooms_for_user(user):
        if is_dataroom_owner_or_admin(user, room):
            continue
        hidden = hidden_folder_ids_for_user(user, room)
        if not hidden:
            continue
        hidden_doc_ids.extend(
            DataroomDocument.objects.filter(
                dataroom=room,
                folder_id__in=hidden,
            ).values_list('document_id', flat=True)
        )
    if hidden_doc_ids:
        return document_qs.exclude(id__in=hidden_doc_ids)
    return document_qs


def get_visible_dataroom_folder_or_404(user, folder_id: str) -> DataroomFolder:
    folder = get_object_or_404(
        DataroomFolder.objects.select_related('dataroom'),
        id=folder_id,
    )
    if not _accessible_datarooms_for_user(user).filter(id=folder.dataroom_id).exists():
        raise NotFound()
    visible_qs = apply_folder_hidden_exclusions(
        DataroomFolder.objects.filter(id=folder.id),
        user,
        folder.dataroom,
    )
    if not visible_qs.exists():
        raise NotFound()
    if not has_perm(user, PERM_VIEW, folder.dataroom, folder, 'folder'):
        raise NotFound()
    return folder


def get_visible_dataroom_document_or_404(user, dataroom_document_id: str) -> DataroomDocument:
    ddoc = get_object_or_404(
        DataroomDocument.objects.select_related('dataroom', 'document', 'folder'),
        id=dataroom_document_id,
    )
    if not _accessible_datarooms_for_user(user).filter(id=ddoc.dataroom_id).exists():
        raise NotFound()
    visible_qs = apply_document_hidden_exclusions(
        DataroomDocument.objects.filter(id=ddoc.id),
        user,
        ddoc.dataroom,
    )
    if not visible_qs.exists():
        raise NotFound()
    if not has_perm(user, PERM_VIEW, ddoc.dataroom, ddoc, 'document'):
        raise NotFound()
    return ddoc


def assert_destination_folder_allowed(
    user,
    dataroom: Dataroom,
    folder: Optional[DataroomFolder],
    *,
    for_upload: bool = False,
    upload_mode: str = 'files',
) -> None:
    from permissions_rbac.catalogue import (
        PERM_FOLDER_CREATE,
        PERM_UPLOAD_ADD_FROM_CONTENT,
        PERM_UPLOAD_FILES,
        PERM_UPLOAD_FOLDER,
    )

    if for_upload:
        if upload_mode == 'content':
            action = PERM_UPLOAD_ADD_FROM_CONTENT
        elif upload_mode == 'folder':
            action = PERM_UPLOAD_FOLDER
        else:
            action = PERM_UPLOAD_FILES
    else:
        action = PERM_FOLDER_CREATE
    if folder is None:
        if for_upload and upload_mode == 'folder' and not has_perm(user, PERM_FOLDER_CREATE, dataroom):
            raise PermissionDenied('You do not have permission to perform this action.')
        if not has_perm(user, action, dataroom):
            raise PermissionDenied('You do not have permission to perform this action.')
        return
    try:
        get_visible_dataroom_folder_or_404(user, folder.id)
    except NotFound:
        raise PermissionDenied('You do not have permission to perform this action in this folder.')
    if not has_perm(user, action, dataroom, folder, 'folder'):
        raise PermissionDenied('You do not have permission to perform this action in this folder.')


def assert_document_view_allowed(user, document) -> None:
    if not document:
        raise NotFound()
    personal_only = not DataroomDocument.objects.filter(document=document).exists()
    if personal_only:
        return
    ddocs = DataroomDocument.objects.filter(document=document).select_related('dataroom', 'folder')
    accessible = _accessible_datarooms_for_user(user)
    relevant = [d for d in ddocs if accessible.filter(id=d.dataroom_id).exists()]
    if not relevant:
        raise NotFound()
    for ddoc in relevant:
        if is_dataroom_owner_or_admin(user, ddoc.dataroom):
            if has_perm(user, PERM_VIEW, ddoc.dataroom, ddoc, 'document'):
                return
            continue
        try:
            get_visible_dataroom_document_or_404(user, str(ddoc.id))
        except NotFound:
            continue
        if has_perm(user, PERM_VIEW, ddoc.dataroom, ddoc, 'document'):
            return
    raise NotFound()


def assert_document_download_allowed(user, document) -> None:
    ddocs = DataroomDocument.objects.filter(document=document).select_related('dataroom', 'folder')
    accessible = _accessible_datarooms_for_user(user)
    relevant = [d for d in ddocs if accessible.filter(id=d.dataroom_id).exists()]
    if not relevant:
        return
    for ddoc in relevant:
        if is_dataroom_owner_or_admin(user, ddoc.dataroom):
            if has_perm(user, PERM_DOWNLOAD, ddoc.dataroom, ddoc, 'document'):
                return
            continue
        try:
            get_visible_dataroom_document_or_404(user, str(ddoc.id))
        except NotFound:
            continue
        if has_perm(user, PERM_DOWNLOAD, ddoc.dataroom, ddoc, 'document'):
            return
    raise NotFound()


def filter_public_dataroom_folders_for_user(user, dataroom: Dataroom, folders: Iterable[DataroomFolder]):
    if not user or not user.is_authenticated or is_dataroom_owner_or_admin(user, dataroom):
        return list(folders)
    hidden = hidden_folder_ids_for_user(user, dataroom)
    if not hidden:
        return list(folders)
    return [f for f in folders if str(f.id) not in hidden]


def filter_public_dataroom_documents_for_user(user, dataroom: Dataroom, documents: Iterable[DataroomDocument]):
    if not user or not user.is_authenticated or is_dataroom_owner_or_admin(user, dataroom):
        return list(documents)
    hidden = hidden_folder_ids_for_user(user, dataroom)
    if not hidden:
        return list(documents)
    return [d for d in documents if not d.folder_id or str(d.folder_id) not in hidden]


def assert_share_link_dataroom_document_visible(user, dataroom_document: DataroomDocument) -> None:
    if not user or not user.is_authenticated:
        return
    dataroom = dataroom_document.dataroom
    if is_dataroom_owner_or_admin(user, dataroom):
        return
    role = get_collaborator_dataroom_role(user, dataroom)
    if role is None:
        return
    folder = dataroom_document.folder
    if folder and is_folder_hidden_for_role(folder, role):
        raise NotFound()
    if folder and not has_perm(user, PERM_VIEW, dataroom, dataroom_document, 'document'):
        raise NotFound()


def filter_ancestor_chain_for_user(user, dataroom: Dataroom, ancestors: list) -> list:
    if is_dataroom_owner_or_admin(user, dataroom):
        return ancestors
    hidden = hidden_folder_ids_for_user(user, dataroom)
    if not hidden:
        return ancestors
    return [a for a in ancestors if str(a.get('id')) not in hidden]


def filter_dataroom_visits_queryset(qs: QuerySet, user, dataroom: Dataroom) -> QuerySet:
    if is_dataroom_owner_or_admin(user, dataroom):
        return qs
    hidden = hidden_folder_ids_for_user(user, dataroom)
    if not hidden:
        return qs
    return qs.exclude(
        Q(dataroom_folder_id__in=hidden) | Q(dataroom_document__folder_id__in=hidden)
    )


def filter_dashboard_view_sessions_queryset(qs: QuerySet, user) -> QuerySet:
    from documents.views import get_document_queryset_for_user

    if getattr(user, 'role', '') == 'admin':
        return qs
    accessible = get_document_queryset_for_user(user).values('id')
    return qs.filter(Q(share_link__document__isnull=True) | Q(share_link__document_id__in=accessible))
