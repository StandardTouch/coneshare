"""
Dataroom collaborator delete policy (Allure / configurable via admin settings).

When COLLABORATORS_OWN_DELETE_ONLY is enabled (default), dataroom collaborators may
remove only documents and folders they created or uploaded. Owners and org admins
retain full delete access within the dataroom.
"""
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from core.services import get_dynamic_setting
from datarooms.models import Dataroom, DataroomDocument, DataroomFolder
from datarooms.utils import is_dataroom_owner_or_admin

COLLABORATOR_DELETE_DENIED_DETAIL = (
    "Collaborators can only delete files and folders they uploaded or created."
)


def collaborators_own_delete_only_enabled() -> bool:
    return bool(get_dynamic_setting('COLLABORATORS_OWN_DELETE_ONLY'))


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


def assert_user_may_remove_dataroom_content(
    user,
    dataroom: Dataroom,
    dataroom_doc_ids=None,
    dataroom_folder_ids=None,
) -> None:
    """
    Raises PermissionDenied (403) when a collaborator attempts to remove content
    they did not create. Folder deletes are blocked if the folder or any nested
    folder/document in the removal scope was created by someone else.
    """
    if not collaborators_own_delete_only_enabled():
        return
    if is_dataroom_owner_or_admin(user, dataroom):
        return

    dataroom_doc_ids = list(dataroom_doc_ids or [])
    dataroom_folder_ids = list(dataroom_folder_ids or [])
    all_folder_ids = _expand_dataroom_folder_ids(dataroom, dataroom_folder_ids)

    if all_folder_ids:
        foreign_folder = (
            DataroomFolder.objects.filter(id__in=all_folder_ids, dataroom=dataroom)
            .exclude(created_by_id=user.id)
            .exists()
        )
        if foreign_folder:
            raise PermissionDenied(COLLABORATOR_DELETE_DENIED_DETAIL)

    ddocs_qs = DataroomDocument.objects.filter(
        Q(id__in=dataroom_doc_ids)
        | Q(document_id__in=dataroom_doc_ids)
        | Q(folder_id__in=all_folder_ids),
        dataroom=dataroom,
    ).select_related('document')

    for ddoc in ddocs_qs:
        doc = ddoc.document
        if doc is None or doc.created_by_id != user.id:
            raise PermissionDenied(COLLABORATOR_DELETE_DENIED_DETAIL)


def user_can_delete_dataroom_item(user, dataroom: Dataroom, item_type: str, item) -> bool:
    """Read-model helper for serializers and UI hints."""
    if not collaborators_own_delete_only_enabled():
        return True
    if is_dataroom_owner_or_admin(user, dataroom):
        return True

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
