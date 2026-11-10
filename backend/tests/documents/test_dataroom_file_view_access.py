"""Dataroom file_view without system_documents and own/any scope."""
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import (
    PERM_FILE_CREATE_SHARE_LINK,
    PERM_FILE_DOWNLOAD,
    PERM_FILE_PRINT,
    PERM_FILE_VIEW,
    PERM_UPLOAD_FILES,
    SCOPE_ANY,
    SCOPE_OWN,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.services import invalidate_organization_rbac_cache

User = get_user_model()


def _role_with_grants(organization, grants):
    role = DataroomRole.objects.create(
        organization=organization,
        slug='dataroom-viewer-role',
        name='Dataroom Viewer',
        is_system=False,
    )
    rows = [
        DataroomRolePermission(role=role, permission=perm, scope=scope or '')
        for perm, scope in grants.items()
    ]
    DataroomRolePermission.objects.bulk_create(rows)
    invalidate_organization_rbac_cache(str(organization.id))
    return role


def _ready_doc(name, creator, organization):
    doc = Document.objects.create(
        name=name,
        created_by=creator,
        organization=organization,
        status='ready',
        file_size=100,
        type='pdf',
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        original_storage_key=f'org/{name}',
        file_size=100,
        content_type='application/pdf',
        type='pdf',
    )
    return doc


@pytest.fixture
def dataroom_viewer(db, organization):
    return User.objects.create_user(
        username='dr-viewer@test.com',
        email='dr-viewer@test.com',
        password='password123',
        organization=organization,
    )


@pytest.fixture
def viewer_client(dataroom_viewer):
    client = APIClient()
    client.force_authenticate(user=dataroom_viewer)
    return client


@pytest.mark.django_db
class TestDataroomFileViewWithoutSystemDocuments:
    def test_collaborator_can_retrieve_own_upload_without_system_documents(
        self, user, organization, dataroom_viewer, viewer_client
    ):
        role = _role_with_grants(
            organization,
            {
                PERM_FILE_VIEW: SCOPE_ANY,
                PERM_UPLOAD_FILES: '',
            },
        )
        dataroom_viewer.organization_role = role
        dataroom_viewer.save(update_fields=['organization_role'])

        room = Dataroom.objects.create(name='Deal', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
        own_doc = _ready_doc('own-upload.pdf', dataroom_viewer, organization)
        DataroomDocument.objects.create(dataroom=room, document=own_doc, name=own_doc.name)

        assert viewer_client.get('/api/v1/documents/').status_code == status.HTTP_403_FORBIDDEN

        resp = viewer_client.get(f'/api/v1/documents/{own_doc.id}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['id'] == str(own_doc.id)

    @patch('documents.views.prepare_pages_data')
    def test_preview_allowed_with_view_not_download(
        self, mock_pages, user, organization, dataroom_viewer, viewer_client
    ):
        mock_pages.return_value = []
        role = _role_with_grants(organization, {PERM_FILE_VIEW: SCOPE_ANY})
        dataroom_viewer.organization_role = role
        dataroom_viewer.save(update_fields=['organization_role'])

        room = Dataroom.objects.create(name='Preview Room', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
        owner_doc = _ready_doc('owner.pdf', user, organization)
        DataroomDocument.objects.create(dataroom=room, document=owner_doc, name=owner_doc.name)

        resp = viewer_client.get(f'/api/v1/documents/{owner_doc.id}/preview-data/')
        assert resp.status_code == status.HTTP_200_OK
        assert not resp.data.get('download_url')

        dl = viewer_client.get(f'/api/v1/documents/{owner_doc.id}/download/')
        assert dl.status_code == status.HTTP_404_NOT_FOUND

    @patch('documents.renderers.base.fileserver.fileserver_client.generate_download_url')
    def test_preview_includes_download_url_when_file_download_granted(
        self, mock_download_url, user, organization, dataroom_viewer, viewer_client
    ):
        mock_download_url.return_value = 'https://files.example/owner.pdf'
        role = _role_with_grants(
            organization,
            {PERM_FILE_VIEW: SCOPE_ANY, PERM_FILE_DOWNLOAD: ''},
        )
        dataroom_viewer.organization_role = role
        dataroom_viewer.save(update_fields=['organization_role'])

        room = Dataroom.objects.create(name='Download Room', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
        owner_doc = _ready_doc('owner.pdf', user, organization)
        DataroomDocument.objects.create(dataroom=room, document=owner_doc, name=owner_doc.name)

        resp = viewer_client.get(f'/api/v1/documents/{owner_doc.id}/preview-data/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data.get('download_url') == 'https://files.example/owner.pdf'

    def test_own_scope_hides_other_users_files(self, user, organization, dataroom_viewer, viewer_client):
        role = _role_with_grants(organization, {PERM_FILE_VIEW: SCOPE_OWN})
        dataroom_viewer.organization_role = role
        dataroom_viewer.save(update_fields=['organization_role'])

        room = Dataroom.objects.create(name='Scoped', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
        owner_doc = _ready_doc('other.pdf', user, organization)
        own_doc = _ready_doc('mine.pdf', dataroom_viewer, organization)
        DataroomDocument.objects.create(dataroom=room, document=owner_doc, name=owner_doc.name)
        DataroomDocument.objects.create(dataroom=room, document=own_doc, name=own_doc.name)

        assert viewer_client.get(f'/api/v1/documents/{own_doc.id}/').status_code == status.HTTP_200_OK
        assert viewer_client.get(f'/api/v1/documents/{owner_doc.id}/').status_code == status.HTTP_404_NOT_FOUND

        list_resp = viewer_client.get(f'/api/v1/datarooms/{room.id}/')
        assert list_resp.status_code == status.HTTP_200_OK
        doc_ids = {item['document_id'] for item in list_resp.data.get('items', []) if item.get('type') == 'document'}
        assert str(own_doc.id) in doc_ids
        assert str(owner_doc.id) not in doc_ids

    def test_view_sessions_and_stats_without_system_documents(
        self, user, organization, dataroom_viewer, viewer_client
    ):
        role = _role_with_grants(
            organization,
            {
                PERM_FILE_VIEW: SCOPE_ANY,
                PERM_FILE_CREATE_SHARE_LINK: '',
            },
        )
        dataroom_viewer.organization_role = role
        dataroom_viewer.save(update_fields=['organization_role'])

        room = Dataroom.objects.create(name='Analytics', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
        own_doc = _ready_doc('stats.pdf', dataroom_viewer, organization)
        DataroomDocument.objects.create(dataroom=room, document=own_doc, name=own_doc.name)

        stats = viewer_client.get(f'/api/v1/documents/{own_doc.id}/stats/')
        assert stats.status_code == status.HTTP_200_OK

        sessions = viewer_client.get(f'/api/v1/documents/{own_doc.id}/view-sessions/')
        assert sessions.status_code == status.HTTP_200_OK

    def test_retrieve_includes_dataroom_context_permissions(
        self, user, organization, dataroom_viewer, viewer_client
    ):
        role = _role_with_grants(
            organization,
            {
                PERM_FILE_VIEW: SCOPE_ANY,
                PERM_FILE_CREATE_SHARE_LINK: '',
            },
        )
        dataroom_viewer.organization_role = role
        dataroom_viewer.save(update_fields=['organization_role'])

        room = Dataroom.objects.create(name='Ctx', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
        own_doc = _ready_doc('ctx.pdf', dataroom_viewer, organization)
        DataroomDocument.objects.create(dataroom=room, document=own_doc, name=own_doc.name)

        resp = viewer_client.get(
            f'/api/v1/documents/{own_doc.id}/',
            {'dataroom_id': str(room.id)},
        )
        assert resp.status_code == status.HTTP_200_OK
        perms = resp.data.get('dataroom_context_permissions') or {}
        assert perms.get('can_view') is True
        assert perms.get('can_create_share_link') is True
        assert perms.get('can_download') is False
        assert perms.get('can_print') is False


@pytest.mark.django_db
def test_file_print_grant_allows_printing_and_owner_always_can(
    api_client, user, organization, dataroom_viewer, viewer_client
):
    room = Dataroom.objects.create(name='Print Room', organization=organization, created_by=user)
    DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
    doc = _ready_doc('printable.pdf', user, organization)
    DataroomDocument.objects.create(dataroom=room, document=doc, name=doc.name)
    role = _role_with_grants(organization, {PERM_FILE_VIEW: SCOPE_ANY})
    dataroom_viewer.organization_role = role
    dataroom_viewer.save(update_fields=['organization_role'])

    denied = viewer_client.get(f'/api/v1/documents/{doc.id}/', {'dataroom_id': str(room.id)})
    assert denied.status_code == status.HTTP_200_OK
    assert denied.data['dataroom_context_permissions']['can_print'] is False

    DataroomRolePermission.objects.create(role=role, permission=PERM_FILE_PRINT, scope='')
    invalidate_organization_rbac_cache(str(organization.id))

    allowed = viewer_client.get(f'/api/v1/documents/{doc.id}/', {'dataroom_id': str(room.id)})
    assert allowed.data['dataroom_context_permissions']['can_print'] is True

    owner = api_client.get(f'/api/v1/documents/{doc.id}/', {'dataroom_id': str(room.id)})
    assert owner.data['dataroom_context_permissions']['can_print'] is True


@pytest.mark.django_db
def test_file_share_link_scope_own_any_and_owner(api_client, user, organization, dataroom_viewer):
    room = Dataroom.objects.create(name='Share Scope', organization=organization, created_by=user)
    DataroomCollaborator.objects.create(dataroom=room, user=dataroom_viewer, invited_by=user)
    owner_doc = _ready_doc('owner-file.pdf', user, organization)
    own_doc = _ready_doc('viewer-file.pdf', dataroom_viewer, organization)
    DataroomDocument.objects.create(dataroom=room, document=owner_doc, name=owner_doc.name)
    DataroomDocument.objects.create(dataroom=room, document=own_doc, name=own_doc.name)

    role = _role_with_grants(organization, {PERM_FILE_CREATE_SHARE_LINK: SCOPE_OWN, PERM_FILE_VIEW: SCOPE_ANY})
    dataroom_viewer.organization_role = role
    dataroom_viewer.save(update_fields=['organization_role'])
    api_client.force_authenticate(user=dataroom_viewer)

    listed = api_client.get(f'/api/v1/datarooms/{room.id}/')
    items = {item['document_id']: item for item in listed.data['items'] if item.get('type') == 'document'}
    assert items[str(own_doc.id)]['permissions']['can_manage_share_settings'] is True
    assert items[str(owner_doc.id)]['permissions']['can_manage_share_settings'] is False

    own_link = api_client.post('/api/v1/share-links/', {'document': str(own_doc.id), 'name': 'Mine'}, format='json')
    assert own_link.status_code == status.HTTP_201_CREATED
    other_link = api_client.post('/api/v1/share-links/', {'document': str(owner_doc.id), 'name': 'Theirs'}, format='json')
    assert other_link.status_code == status.HTTP_400_BAD_REQUEST

    grant = DataroomRolePermission.objects.get(role=role, permission=PERM_FILE_CREATE_SHARE_LINK)
    grant.scope = ''
    grant.save(update_fields=['scope'])
    invalidate_organization_rbac_cache(str(organization.id))

    any_link = api_client.post('/api/v1/share-links/', {'document': str(owner_doc.id), 'name': 'Any Scope'}, format='json')
    assert any_link.status_code == status.HTTP_201_CREATED

    api_client.force_authenticate(user=user)
    owner_link = api_client.post('/api/v1/share-links/', {'document': str(own_doc.id), 'name': 'Owner Link'}, format='json')
    assert owner_link.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_migration_file_view_scope_defaults_to_any(organization):
    role = DataroomRole.objects.create(
        organization=organization, slug='legacy-view', name='Legacy', is_system=False
    )
    DataroomRolePermission.objects.create(role=role, permission=PERM_FILE_VIEW, scope='')
    import importlib

    from django.apps import apps

    migration = importlib.import_module('permissions_rbac.migrations.0006_file_view_scope')
    migration.forwards(apps, None)

    assert (
        DataroomRolePermission.objects.get(role=role, permission=PERM_FILE_VIEW).scope == SCOPE_ANY
    )
