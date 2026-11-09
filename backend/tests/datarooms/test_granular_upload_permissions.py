"""Granular dataroom upload RBAC: capabilities payload and endpoint enforcement."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status

from datarooms.models import DataroomCollaborator
from permissions_rbac.catalogue import (
    PERM_FOLDER_CREATE,
    PERM_UPLOAD_ADD_FROM_CONTENT,
    PERM_UPLOAD_FILES,
    PERM_UPLOAD_FOLDER,
    PERM_UPLOAD_FROM_DRIVE,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.services import invalidate_organization_rbac_cache, user_dataroom_capabilities


def _role_with_grants(organization, grants):
    ensure_default_roles_for_organization(organization)
    role, _ = DataroomRole.objects.get_or_create(
        organization=organization,
        slug='upload-granular-test',
        defaults={'name': 'Upload Granular Test', 'is_system': False},
    )
    DataroomRolePermission.objects.filter(role=role).delete()
    DataroomRolePermission.objects.bulk_create(
        [
            DataroomRolePermission(role=role, permission=perm, scope='')
            for perm in grants
        ]
    )
    invalidate_organization_rbac_cache(str(organization.id))
    return role


def _add_collaborator(dataroom, user, role, invited_by):
    user.organization_role = role
    user.save(update_fields=['organization_role'])
    DataroomCollaborator.objects.create(
        dataroom=dataroom,
        user=user,
        invited_by=invited_by,
        dataroom_role=None,
    )


@pytest.fixture
def upload_only_files_role(organization):
    return _role_with_grants(organization, [PERM_UPLOAD_FILES])


@pytest.fixture
def upload_files_and_folder_role(organization):
    return _role_with_grants(organization, [PERM_UPLOAD_FILES, PERM_UPLOAD_FOLDER])


@pytest.mark.django_db
class TestGranularUploadCapabilities:
    def test_capabilities_reflect_individual_grants(
        self, user, user2, organization, dataroom, upload_only_files_role
    ):
        _add_collaborator(dataroom, user2, upload_only_files_role, user)
        caps = user_dataroom_capabilities(user2, dataroom)
        assert caps['can_upload_files'] is True
        assert caps['can_upload_folder'] is False
        assert caps['can_upload_add_from_content'] is False
        assert caps['can_upload_from_drive'] is False
        assert caps['can_create_folder'] is False
        assert caps['can_upload'] is True

    def test_upload_dropdown_flag_requires_files_or_folder(
        self, user, user2, organization, dataroom, upload_files_and_folder_role
    ):
        _add_collaborator(dataroom, user2, upload_files_and_folder_role, user)
        caps = user_dataroom_capabilities(user2, dataroom)
        assert caps['can_upload'] is True

    def test_detail_serializer_exposes_granular_flags(
        self, api_client, user, user2, organization, dataroom, upload_only_files_role
    ):
        _add_collaborator(dataroom, user2, upload_only_files_role, user)
        api_client.force_authenticate(user=user2)
        response = api_client.get(reverse('dataroom-detail', kwargs={'pk': dataroom.id}))
        assert response.status_code == status.HTTP_200_OK
        perms = response.data['current_user_permissions']
        assert perms['can_upload_files'] is True
        assert perms['can_upload_folder'] is False
        assert perms['can_upload_add_from_content'] is False
        assert perms['can_upload_from_drive'] is False
        assert perms['can_create_folder'] is False


@pytest.mark.django_db
class TestGranularUploadEndpointEnforcement:
    def test_folder_upload_paths_denied_without_upload_folder(
        self, api_client, user, user2, organization, dataroom, upload_only_files_role
    ):
        _add_collaborator(dataroom, user2, upload_only_files_role, user)
        api_client.force_authenticate(user=user2)
        url = f'/api/v1/datarooms/{dataroom.id}/ensure-paths/'
        response = api_client.post(url, {'paths': ['NestedDir/file.txt']}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_add_content_denied_without_add_from_content(
        self, api_client, user, user2, organization, dataroom, upload_only_files_role
    ):
        _add_collaborator(dataroom, user2, upload_only_files_role, user)
        api_client.force_authenticate(user=user2)
        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        response = api_client.post(
            url,
            {'document_ids': [], 'folder_ids': []},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @patch('datarooms.views.fileserver_client.generate_upload_url', return_value='http://mocked/upload')
    def test_file_upload_request_allowed_with_upload_files_only(
        self, _mock_url, api_client, user, user2, organization, dataroom, upload_only_files_role
    ):
        _add_collaborator(dataroom, user2, upload_only_files_role, user)
        api_client.force_authenticate(user=user2)
        url = f'/api/v1/datarooms/{dataroom.id}/uploads/request/'
        response = api_client.post(
            url,
            {'file_name': 'test.pdf', 'file_size': 1024},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    @patch('datarooms.views.fileserver_client.generate_upload_url', return_value='http://mocked/upload')
    def test_file_upload_request_denied_without_upload_files(
        self, _mock_url, api_client, user, user2, organization, dataroom
    ):
        role = _role_with_grants(organization, [PERM_UPLOAD_FOLDER])
        _add_collaborator(dataroom, user2, role, user)
        api_client.force_authenticate(user=user2)
        url = f'/api/v1/datarooms/{dataroom.id}/uploads/request/'
        response = api_client.post(
            url,
            {'file_name': 'test.pdf', 'file_size': 1024},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_folder_denied_without_folder_create(
        self, api_client, user, user2, organization, dataroom, upload_only_files_role
    ):
        _add_collaborator(dataroom, user2, upload_only_files_role, user)
        api_client.force_authenticate(user=user2)
        response = api_client.post(
            '/api/v1/dataroom-folders/',
            {'name': 'New Folder', 'dataroom': str(dataroom.id)},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_folder_allowed_with_folder_create(
        self, api_client, user, user2, organization, dataroom
    ):
        role = _role_with_grants(organization, [PERM_FOLDER_CREATE])
        _add_collaborator(dataroom, user2, role, user)
        api_client.force_authenticate(user=user2)
        response = api_client.post(
            '/api/v1/dataroom-folders/',
            {'name': 'New Folder', 'dataroom': str(dataroom.id)},
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_add_content_allowed_with_grant(
        self, api_client, user, user2, organization, dataroom, document
    ):
        role = _role_with_grants(organization, [PERM_UPLOAD_ADD_FROM_CONTENT])
        _add_collaborator(dataroom, user2, role, user)
        document.created_by = user2
        document.save(update_fields=['created_by'])
        api_client.force_authenticate(user=user2)
        url = f'/api/v1/datarooms/{dataroom.id}/add-content/'
        response = api_client.post(
            url,
            {'document_ids': [str(document.id)], 'folder_ids': []},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_upload_from_drive_requires_grant(
        self, api_client, user, user2, organization, dataroom, document
    ):
        role = _role_with_grants(organization, [PERM_UPLOAD_FILES])
        _add_collaborator(dataroom, user2, role, user)
        document.created_by = user2
        document.save(update_fields=['created_by'])
        version = document.versions.get(is_primary=True)
        version.metadata = {'cloud_import': {'provider': 'google_drive', 'file_id': 'file-1'}}
        version.save(update_fields=['metadata'])
        api_client.force_authenticate(user=user2)
        url = f'/api/v1/datarooms/{dataroom.id}/attach-cloud-import/'
        denied = api_client.post(url, {'document_id': str(document.id)}, format='json')
        assert denied.status_code == status.HTTP_403_FORBIDDEN

        drive_role = _role_with_grants(organization, [PERM_UPLOAD_FROM_DRIVE])
        user2.organization_role = drive_role
        user2.save(update_fields=['organization_role'])
        invalidate_organization_rbac_cache(str(organization.id))
        allowed = api_client.post(url, {'document_id': str(document.id)}, format='json')
        assert allowed.status_code == status.HTTP_201_CREATED
        assert dataroom.documents.filter(document=document).exists()
