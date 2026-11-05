import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User
from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument, DataroomFolder
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import PERM_VIEW, ROLE_SLUG_VIEWER
from permissions_rbac.models import DataroomFolderRoleRule, DataroomRole
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.services import has_perm, hidden_folder_ids_for_user


@pytest.fixture
def viewer_user(db, organization):
    return User.objects.create_user(
        username='viewer@test.com',
        email='viewer@test.com',
        password='password123',
        organization=organization,
    )


@pytest.fixture
def rbac_dataroom(user, viewer_user, organization):
    ensure_default_roles_for_organization(organization)
    room = Dataroom.objects.create(name='RBAC Room', organization=organization, created_by=user)
    viewer_role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_VIEWER)
    DataroomCollaborator.objects.create(
        dataroom=room,
        user=viewer_user,
        invited_by=user,
        dataroom_role=viewer_role,
    )
    return room


def _doc(name, creator, organization):
    doc = Document.objects.create(
        name=name,
        created_by=creator,
        organization=organization,
        status='ready',
        file_size=100,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        original_storage_key=f'org/{name}',
        file_size=100,
    )
    return doc


@pytest.mark.django_db
class TestHasPermRoles:
    def test_viewer_cannot_delete_owner_document(self, rbac_dataroom, user, viewer_user, organization):
        doc = _doc('owner.pdf', user, organization)
        dd = DataroomDocument.objects.create(dataroom=rbac_dataroom, document=doc, name=doc.name)
        assert has_perm(viewer_user, 'delete', rbac_dataroom, dd, 'document') is False
        assert has_perm(user, 'delete', rbac_dataroom, dd, 'document') is True

    def test_manager_role_granted_via_api_matrix(self, admin_api_client, organization):
        ensure_default_roles_for_organization(organization)
        res = admin_api_client.get('/api/v1/admin/rbac/roles/matrix/')
        assert res.status_code == status.HTTP_200_OK
        assert any(r['slug'] == 'editor' for r in res.data['roles'])


@pytest.mark.django_db
class TestHiddenFolderRules:
    def test_hidden_folder_excluded_from_listing(
        self, rbac_dataroom, user, viewer_user, organization
    ):
        ensure_default_roles_for_organization(organization)
        viewer_role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_VIEWER)
        visible = DataroomFolder.objects.create(
            dataroom=rbac_dataroom, name='Visible', created_by=user
        )
        hidden = DataroomFolder.objects.create(
            dataroom=rbac_dataroom, name='Secret', created_by=user
        )
        DataroomFolderRoleRule.objects.create(
            dataroom_folder=hidden,
            dataroom_role=viewer_role,
            rule=DataroomFolderRoleRule.RULE_HIDDEN,
        )
        hidden_ids = hidden_folder_ids_for_user(viewer_user, rbac_dataroom)
        assert str(hidden.id) in hidden_ids
        assert str(visible.id) not in hidden_ids

        client = APIClient()
        client.force_authenticate(user=viewer_user)
        res = client.get(f'/api/v1/dataroom-folders/?dataroom_id={rbac_dataroom.id}')
        assert res.status_code == status.HTTP_200_OK
        returned_ids = {row['id'] for row in res.data}
        assert str(hidden.id) not in returned_ids
        assert str(visible.id) in returned_ids

    def test_viewer_cannot_download_from_view_only_folder(
        self, rbac_dataroom, user, viewer_user, organization
    ):
        ensure_default_roles_for_organization(organization)
        viewer_role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_VIEWER)
        folder = DataroomFolder.objects.create(
            dataroom=rbac_dataroom, name='ReadOnly', created_by=user
        )
        DataroomFolderRoleRule.objects.create(
            dataroom_folder=folder,
            dataroom_role=viewer_role,
            rule=DataroomFolderRoleRule.RULE_VIEW_ONLY,
        )
        doc = _doc('locked.pdf', user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=rbac_dataroom, document=doc, name=doc.name, folder=folder
        )
        assert has_perm(viewer_user, PERM_VIEW, rbac_dataroom, dd, 'document') is True
        assert has_perm(viewer_user, 'delete', rbac_dataroom, dd, 'document') is False
