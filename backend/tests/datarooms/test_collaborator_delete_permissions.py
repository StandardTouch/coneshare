import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User
from datarooms.collaborator_delete_permissions import COLLABORATOR_DELETE_DENIED_DETAIL
from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument, DataroomFolder
from documents.models import Document, DocumentVersion


@pytest.fixture
def collab_user(db, organization):
    return User.objects.create_user(
        username="collab_del@test.com",
        email="collab_del@test.com",
        password="password123",
        organization=organization,
    )


@pytest.fixture
def other_collab(db, organization):
    return User.objects.create_user(
        username="collab2_del@test.com",
        email="collab2_del@test.com",
        password="password123",
        organization=organization,
    )


@pytest.fixture
def shared_dataroom(user, collab_user, organization):
    room = Dataroom.objects.create(
        name="Delete Policy Room",
        organization=organization,
        created_by=user,
    )
    DataroomCollaborator.objects.create(dataroom=room, user=collab_user, invited_by=user)
    return room


def _make_document(name, creator, organization):
    doc = Document.objects.create(
        name=name,
        created_by=creator,
        organization=organization,
        status="ready",
        file_size=512,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        original_storage_key=f"org/{name}.pdf",
        file_size=512,
    )
    return doc


@pytest.mark.django_db
class TestCollaboratorDeletePermissions:
    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_owner_can_remove_any_content(self, _mock_setting, api_client, user, shared_dataroom, collab_user, organization):
        owner_doc = _make_document("owner.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        url = f'/api/v1/datarooms/{shared_dataroom.id}/remove-content/'
        response = api_client.post(url, {'dataroom_document_ids': [str(dd.id)]})
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not DataroomDocument.objects.filter(id=dd.id).exists()

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_can_remove_own_document(
        self, _mock_setting, shared_dataroom, collab_user, organization
    ):
        own_doc = _make_document("collab.pdf", collab_user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=own_doc, name=own_doc.name, is_direct_upload=True
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/remove-content/'
        response = client.post(url, {'dataroom_document_ids': [str(dd.id)]})
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_blocked_on_owner_document(
        self, _mock_setting, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("owner_only.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/remove-content/'
        response = client.post(url, {'dataroom_document_ids': [str(dd.id)]})
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert COLLABORATOR_DELETE_DENIED_DETAIL in response.data['detail']
        assert DataroomDocument.objects.filter(id=dd.id).exists()

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_blocked_on_peer_document(
        self, _mock_setting, shared_dataroom, collab_user, other_collab, organization
    ):
        DataroomCollaborator.objects.create(
            dataroom=shared_dataroom, user=other_collab, invited_by=shared_dataroom.created_by
        )
        peer_doc = _make_document("peer.pdf", other_collab, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=peer_doc, name=peer_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/remove-content/'
        response = client.post(url, {'dataroom_document_ids': [str(dd.id)]})
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_bulk_remove_blocked_when_selection_includes_foreign_document(
        self, _mock_setting, shared_dataroom, user, collab_user, organization
    ):
        own_doc = _make_document("mine.pdf", collab_user, organization)
        owner_doc = _make_document("theirs.pdf", user, organization)
        dd_own = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=own_doc, name=own_doc.name
        )
        dd_owner = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/remove-content/'
        response = client.post(
            url,
            {'dataroom_document_ids': [str(dd_own.id), str(dd_owner.id)]},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DataroomDocument.objects.filter(id__in=[dd_own.id, dd_owner.id]).count() == 2

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_folder_delete_blocked_when_folder_contains_others_files(
        self, _mock_setting, shared_dataroom, user, collab_user, organization
    ):
        folder = DataroomFolder.objects.create(
            dataroom=shared_dataroom,
            name="Collab Folder",
            created_by=collab_user,
        )
        owner_doc = _make_document("inside.pdf", user, organization)
        DataroomDocument.objects.create(
            dataroom=shared_dataroom,
            document=owner_doc,
            name=owner_doc.name,
            folder=folder,
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.delete(f'/api/v1/dataroom-folders/{folder.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DataroomFolder.objects.filter(id=folder.id).exists()

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_folder_delete_blocked_for_owner_created_folder(
        self, _mock_setting, shared_dataroom, user, collab_user
    ):
        folder = DataroomFolder.objects.create(
            dataroom=shared_dataroom,
            name="Owner Folder",
            created_by=user,
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.delete(f'/api/v1/dataroom-folders/{folder.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_org_admin_can_remove_any_content(
        self, _mock_setting, shared_dataroom, user, organization
    ):
        admin = User.objects.create_user(
            username="admin_del@test.com",
            email="admin_del@test.com",
            password="password123",
            organization=organization,
            role='admin',
        )
        owner_doc = _make_document("admin_target.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/remove-content/'
        response = client.post(url, {'dataroom_document_ids': [str(dd.id)]})
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=False)
    def test_toggle_off_allows_collaborator_to_remove_owner_document(
        self, _mock_setting, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("legacy.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/remove-content/'
        response = client.post(url, {'dataroom_document_ids': [str(dd.id)]})
        assert response.status_code == status.HTTP_204_NO_CONTENT

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_can_soft_delete_own_document_via_documents_api(
        self, _mock_setting, shared_dataroom, collab_user, organization
    ):
        own_doc = _make_document("soft_own.pdf", collab_user, organization)
        DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=own_doc, name=own_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.delete(f'/api/v1/documents/{own_doc.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        own_doc.refresh_from_db()
        assert own_doc.deleted_at is not None

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_serializer_exposes_can_delete_flags(
        self, _mock_setting, api_client, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("flag_owner.pdf", user, organization)
        own_doc = _make_document("flag_own.pdf", collab_user, organization)
        dd_owner = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        dd_own = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=own_doc, name=own_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        owner_resp = client.get(f'/api/v1/dataroom-documents/{dd_owner.id}/')
        own_resp = client.get(f'/api/v1/dataroom-documents/{dd_own.id}/')
        assert owner_resp.data['can_delete'] is False
        assert own_resp.data['can_delete'] is True
