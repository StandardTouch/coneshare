import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User
from datarooms.collaborator_delete_permissions import COLLABORATOR_MODIFY_DENIED_DETAIL
from datarooms.dataroom_create_policy import DATAROOM_CREATE_DENIED_DETAIL
from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument, DataroomFolder
from documents.models import Document, DocumentVersion
from sharelinks.models import ShareLink, ShareLinkDataroomSetting


@pytest.fixture
def collab_user(db, organization):
    return User.objects.create_user(
        username="collab_mod@test.com",
        email="collab_mod@test.com",
        password="password123",
        organization=organization,
    )


@pytest.fixture
def member_user(db, organization):
    return User.objects.create_user(
        username="member_mod@test.com",
        email="member_mod@test.com",
        password="password123",
        organization=organization,
    )


@pytest.fixture
def shared_dataroom(user, collab_user, organization):
    room = Dataroom.objects.create(
        name="Modify Policy Room",
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
class TestCollaboratorModifyPermissions:
    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_blocked_on_rename_owner_document(
        self, _mock, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("owner_rename.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.patch(
            f'/api/v1/dataroom-documents/{dd.id}/',
            {'name': 'Renamed.pdf'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert COLLABORATOR_MODIFY_DENIED_DETAIL in response.data['detail']
        dd.refresh_from_db()
        assert dd.name == owner_doc.name

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_can_rename_own_document(
        self, _mock, shared_dataroom, collab_user, organization
    ):
        own_doc = _make_document("own_rename.pdf", collab_user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=own_doc, name=own_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.patch(
            f'/api/v1/dataroom-documents/{dd.id}/',
            {'name': 'My Renamed.pdf'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        dd.refresh_from_db()
        assert dd.name == 'My Renamed.pdf'

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_blocked_on_move_owner_document(
        self, _mock, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("move_me.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        dest = DataroomFolder.objects.create(
            dataroom=shared_dataroom, name="Dest", created_by=collab_user
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/move-content/'
        response = client.post(
            url,
            {
                'dataroom_document_ids': [str(dd.id)],
                'destination_folder_id': str(dest.id),
            },
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_blocked_on_reorder_when_scope_has_foreign_item(
        self, _mock, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("order_owner.pdf", user, organization)
        own_doc = _make_document("order_own.pdf", collab_user, organization)
        dd_owner = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        dd_own = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=own_doc, name=own_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        url = f'/api/v1/datarooms/{shared_dataroom.id}/reorder-items/'
        response = client.post(
            url,
            {
                'ordered_items': [
                    {'type': 'document', 'id': str(dd_own.id)},
                    {'type': 'document', 'id': str(dd_owner.id)},
                ],
            },
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_blocked_on_star_owner_document(
        self, _mock, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("star_owner.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name, is_starred=False
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.patch(
            f'/api/v1/dataroom-documents/{dd.id}/',
            {'is_starred': True},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_collaborator_blocked_on_share_link_item_settings_for_owner_document(
        self, _mock, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("settings_owner.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        link = ShareLink.objects.create(
            dataroom=shared_dataroom,
            created_by=collab_user,
            name="Collab Link",
        )
        setting = ShareLinkDataroomSetting.objects.get(
            share_link=link, dataroom_document=dd
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.patch(
            f'/api/v1/share-links/{link.id}/dataroom-settings/',
            [{'id': str(setting.id), 'is_visible': False}],
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=False)
    def test_toggle_off_allows_collaborator_rename_owner_document(
        self, _mock, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("legacy_rename.pdf", user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=shared_dataroom, document=owner_doc, name=owner_doc.name
        )
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.patch(
            f'/api/v1/dataroom-documents/{dd.id}/',
            {'name': 'Allowed.pdf'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    def test_serializer_exposes_can_modify_flags(
        self, _mock, shared_dataroom, user, collab_user, organization
    ):
        owner_doc = _make_document("flag_mod_owner.pdf", user, organization)
        own_doc = _make_document("flag_mod_own.pdf", collab_user, organization)
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
        assert owner_resp.data['can_modify'] is False
        assert owner_resp.data['can_delete'] is False
        assert own_resp.data['can_modify'] is True
        assert own_resp.data['can_delete'] is True


@pytest.mark.django_db
class TestDataroomCreateAdminOnly:
    @patch('datarooms.dataroom_create_policy.get_dynamic_setting', return_value=True)
    def test_member_cannot_create_dataroom(self, _mock, member_user):
        client = APIClient()
        client.force_authenticate(user=member_user)
        response = client.post('/api/v1/datarooms/', {'name': 'Member Room'}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert DATAROOM_CREATE_DENIED_DETAIL in response.data['detail']

    @patch('datarooms.dataroom_create_policy.get_dynamic_setting', return_value=True)
    def test_admin_can_create_dataroom(self, _mock, admin_user):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.post('/api/v1/datarooms/', {'name': 'Admin Room'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    @patch('datarooms.dataroom_create_policy.get_dynamic_setting', return_value=False)
    def test_toggle_off_allows_member_create(self, _mock, member_user):
        client = APIClient()
        client.force_authenticate(user=member_user)
        response = client.post('/api/v1/datarooms/', {'name': 'Open Room'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    @patch('datarooms.dataroom_create_policy.get_dynamic_setting', return_value=True)
    def test_owner_role_member_with_collaboration_can_still_use_existing_room(
        self, _mock, user, collab_user, organization
    ):
        room = Dataroom.objects.create(
            name="Existing",
            organization=organization,
            created_by=user,
        )
        DataroomCollaborator.objects.create(dataroom=room, user=collab_user, invited_by=user)
        client = APIClient()
        client.force_authenticate(user=collab_user)
        response = client.get(f'/api/v1/datarooms/{room.id}/')
        assert response.status_code == status.HTTP_200_OK
