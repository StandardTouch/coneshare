"""Regression matrix: system permissions vs public settings and API gates."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from datarooms.models import DataroomCollaborator, DataroomDocument
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import (
    ALL_SYSTEM_PERMISSIONS,
    PERM_FILE_VIEW,
    PERM_SYSTEM_API_KEYS,
    PERM_SYSTEM_AUTOMATION,
    PERM_SYSTEM_DOCUMENTS,
    PERM_SYSTEM_FILE_REQUESTS,
    PERM_SYSTEM_SIGNATURE,
    PERM_SYSTEM_SWAGGER,
    PERM_SYSTEM_TRASH,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.services import invalidate_organization_rbac_cache


SYSTEM_SETTINGS_KEYS = {
    PERM_SYSTEM_API_KEYS: 'api_keys_enabled',
    PERM_SYSTEM_FILE_REQUESTS: 'file_requests_enabled',
    PERM_SYSTEM_DOCUMENTS: 'documents_enabled',
    PERM_SYSTEM_SWAGGER: 'swagger_enabled',
    PERM_SYSTEM_AUTOMATION: 'automation_enabled',
    PERM_SYSTEM_TRASH: 'trash_enabled',
    PERM_SYSTEM_SIGNATURE: 'signature_enabled',
}


SYSTEM_ENDPOINT_CHECKS = {
    PERM_SYSTEM_DOCUMENTS: ('GET', '/api/v1/documents/'),
    PERM_SYSTEM_TRASH: ('GET', '/api/v1/trash/'),
    PERM_SYSTEM_FILE_REQUESTS: ('GET', '/api/v1/file-requests/'),
    PERM_SYSTEM_SIGNATURE: ('GET', '/api/v1/esign/requests/'),
}


def _role_with_only(organization, granted):
    ensure_default_roles_for_organization(organization)
    role = DataroomRole.objects.create(
        organization=organization,
        slug=f'matrix-{granted or "none"}',
        name='Matrix Role',
        is_system=False,
    )
    if granted:
        DataroomRolePermission.objects.create(role=role, permission=granted, scope='')
    invalidate_organization_rbac_cache(str(organization.id))
    return role


def _role_reviewer(organization):
    """Role with file_view only — mirrors production Reviewer misconfiguration."""
    ensure_default_roles_for_organization(organization)
    role = DataroomRole.objects.create(
        organization=organization,
        slug='reviewer-matrix',
        name='Reviewer',
        is_system=False,
    )
    DataroomRolePermission.objects.create(role=role, permission=PERM_FILE_VIEW, scope='any')
    invalidate_organization_rbac_cache(str(organization.id))
    return role


@pytest.mark.django_db
class TestPublicSettingsSystemFlags:
    @pytest.mark.parametrize('permission', ALL_SYSTEM_PERMISSIONS)
    def test_public_settings_reflects_single_grant(self, organization, user, permission):
        role = _role_with_only(organization, permission)
        user.organization_role = role
        user.save(update_fields=['organization_role'])
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        settings_key = SYSTEM_SETTINGS_KEYS[permission]
        assert response.data[settings_key] is True
        for other_perm, key in SYSTEM_SETTINGS_KEYS.items():
            if other_perm != permission:
                assert response.data[key] is False, (other_perm, key)

    def test_reviewer_public_settings_hides_documents_and_trash(self, organization, user):
        role = _role_reviewer(organization)
        user.organization_role = role
        user.save(update_fields=['organization_role'])
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['documents_enabled'] is False
        assert response.data['trash_enabled'] is False


@pytest.mark.django_db
class TestSystemPermissionApiGates:
    @pytest.mark.parametrize('permission,method,url', [
        (perm, *SYSTEM_ENDPOINT_CHECKS[perm])
        for perm in SYSTEM_ENDPOINT_CHECKS
    ])
    def test_endpoint_403_without_grant(self, organization, user, permission, method, url):
        role = _role_reviewer(organization)
        user.organization_role = role
        user.save(update_fields=['organization_role'])
        client = APIClient()
        client.force_authenticate(user=user)
        response = getattr(client, method.lower())(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_dashboard_analytics_403_without_documents(self, organization, user):
        role = _role_reviewer(organization)
        user.organization_role = role
        user.save(update_fields=['organization_role'])
        client = APIClient()
        client.force_authenticate(user=user)
        assert client.get('/api/v1/analytics/dashboard/').status_code == status.HTTP_403_FORBIDDEN
        assert client.get('/api/v1/analytics/daily-visits/').status_code == status.HTTP_403_FORBIDDEN

    def test_document_retrieve_allowed_via_dataroom_file_view_without_system_documents(
        self, organization, user, user2, dataroom
    ):
        doc = Document.objects.create(
            name='vault.pdf',
            created_by=user,
            organization=organization,
            status='ready',
            file_size=100,
        )
        DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            is_primary=True,
            original_storage_key='org/vault.pdf',
            file_size=100,
        )
        DataroomDocument.objects.create(dataroom=dataroom, document=doc)
        role = _role_reviewer(organization)
        user2.organization_role = role
        user2.save(update_fields=['organization_role'])
        DataroomCollaborator.objects.create(dataroom=dataroom, user=user2, invited_by=user)
        client = APIClient()
        client.force_authenticate(user=user2)
        list_resp = client.get('/api/v1/documents/')
        assert list_resp.status_code == status.HTTP_403_FORBIDDEN
        detail_resp = client.get(reverse('document-detail', kwargs={'pk': doc.id}))
        assert detail_resp.status_code == status.HTTP_200_OK
