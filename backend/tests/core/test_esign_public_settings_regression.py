"""E-sign access follows per-role Signature permission (not global toggles)."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import PERM_SYSTEM_SIGNATURE
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization


@pytest.mark.django_db
class TestEsignRbacEnforcement:
    def test_list_403_without_signature_permission(self, organization, user):
        ensure_default_roles_for_organization(organization)
        role = DataroomRole.objects.create(
            organization=organization, slug='no-sign', name='No Sign', is_system=False
        )
        user.organization_role = role
        user.save(update_fields=['organization_role'])
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/esign/requests/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_200_with_signature_permission(self, organization, user):
        ensure_default_roles_for_organization(organization)
        role = DataroomRole.objects.create(
            organization=organization, slug='signer', name='Signer', is_system=False
        )
        DataroomRolePermission.objects.create(role=role, permission=PERM_SYSTEM_SIGNATURE, scope='')
        user.organization_role = role
        user.save(update_fields=['organization_role'])
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get('/api/v1/esign/requests/')
        assert response.status_code == status.HTTP_200_OK

    def test_public_settings_does_not_use_esign_toggle(self, public_client):
        response = public_client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        assert 'esign_enabled' in response.data
