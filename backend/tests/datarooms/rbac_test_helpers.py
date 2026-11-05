"""Shared helpers for dataroom RBAC tests."""

import pytest

from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import ROLE_SLUG_EDITOR
from permissions_rbac.models import DataroomRole
from permissions_rbac.seed import ensure_default_roles_for_organization


@pytest.fixture
def editor_role_fixture(organization):
    ensure_default_roles_for_organization(organization)
    return DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_EDITOR)


def editor_role(organization):
    roles = ensure_default_roles_for_organization(organization)
    return roles[ROLE_SLUG_EDITOR]


def add_editor_collaborator(dataroom, user, invited_by, editor_rbac_role):
    return DataroomCollaborator.objects.create(
        dataroom=dataroom,
        user=user,
        invited_by=invited_by,
        dataroom_role=editor_rbac_role,
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
