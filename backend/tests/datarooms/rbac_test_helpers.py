"""Shared helpers for dataroom RBAC tests."""

import pytest

from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import (
    PERM_DATAROOM_CREATE,
    PERM_FILE_DELETE,
    PERM_FILE_RENAME,
    PERM_FILE_VIEW,
    PERM_FOLDER_CREATE,
    PERM_FOLDER_DELETE,
    PERM_UPLOAD_FILES,
    ROLE_SLUG_MANAGER,
    SCOPE_OWN,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization


def _legacy_editor_grants():
    return {
        PERM_FILE_VIEW: '',
        'file_download': '',
        PERM_UPLOAD_FILES: '',
        PERM_FOLDER_CREATE: '',
        PERM_FILE_RENAME: SCOPE_OWN,
        PERM_FILE_DELETE: SCOPE_OWN,
        'folder_rename': SCOPE_OWN,
        PERM_FOLDER_DELETE: SCOPE_OWN,
    }


@pytest.fixture
def editor_role_fixture(organization):
    ensure_default_roles_for_organization(organization)
    role, _ = DataroomRole.objects.get_or_create(
        organization=organization,
        slug='legacy-editor',
        defaults={'name': 'Editor', 'is_system': False, 'description': 'Test editor grants'},
    )
    DataroomRolePermission.objects.filter(role=role).delete()
    DataroomRolePermission.objects.bulk_create(
        [
            DataroomRolePermission(role=role, permission=p, scope=s if s != 'any' else '')
            for p, s in _legacy_editor_grants().items()
        ]
    )
    return role


def editor_role(organization):
    ensure_default_roles_for_organization(organization)
    role, _ = DataroomRole.objects.get_or_create(
        organization=organization,
        slug='legacy-editor',
        defaults={'name': 'Editor', 'is_system': False},
    )
    DataroomRolePermission.objects.filter(role=role).delete()
    DataroomRolePermission.objects.bulk_create(
        [
            DataroomRolePermission(role=role, permission=p, scope=s if s != 'any' else '')
            for p, s in _legacy_editor_grants().items()
        ]
    )
    return role


def add_editor_collaborator(dataroom, user, invited_by, editor_rbac_role):
    user.organization_role = editor_rbac_role
    user.save(update_fields=['organization_role'])
    return DataroomCollaborator.objects.create(
        dataroom=dataroom,
        user=user,
        invited_by=invited_by,
        dataroom_role=None,
    )


def _document(name, creator, organization):
    doc = Document.objects.create(
        name=name,
        created_by=creator,
        organization=organization,
        status='ready',
        file_size=256,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        original_storage_key=f'org/{name}',
        file_size=256,
    )
    return doc


def make_shared_dataroom(owner, editor, other_user=None, *, name='RBAC Shared Room'):
    organization = owner.organization
    editor_rbac = editor_role(organization)
    dataroom = Dataroom.objects.create(
        name=name,
        organization=organization,
        created_by=owner,
    )
    add_editor_collaborator(dataroom, editor, owner, editor_rbac)

    owner_doc = _document('owner_item.pdf', owner, organization)
    editor_doc = _document('editor_item.pdf', editor, organization)
    dd_owner = DataroomDocument.objects.create(
        dataroom=dataroom,
        document=owner_doc,
        name=owner_doc.name,
    )
    dd_editor = DataroomDocument.objects.create(
        dataroom=dataroom,
        document=editor_doc,
        name=editor_doc.name,
    )
    dd_other = None
    if other_user is not None:
        other_doc = _document('other_item.pdf', other_user, organization)
        dd_other = DataroomDocument.objects.create(
            dataroom=dataroom,
            document=other_doc,
            name=other_doc.name,
        )
    return dataroom, dd_owner, dd_editor, dd_other


def manager_role(organization):
    ensure_default_roles_for_organization(organization)
    return DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_MANAGER)


def grant_create_dataroom_on_role(role):
    DataroomRolePermission.objects.get_or_create(
        role=role,
        permission=PERM_DATAROOM_CREATE,
        defaults={'scope': ''},
    )
