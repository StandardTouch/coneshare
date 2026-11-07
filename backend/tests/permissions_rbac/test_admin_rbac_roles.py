"""Admin dataroom role create/list API (matches frontend payloads)."""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from permissions_rbac.models import DataroomRole
from permissions_rbac.seed import ensure_default_roles_for_organization

User = get_user_model()

# Exact body AdminRolesPage sends via api.createAdminRbacRole(createForm).
FRONTEND_CREATE_ROLE_PAYLOAD = {'name': 'Deal Analyst', 'description': 'Custom analysts for diligence.'}


@pytest.mark.django_db
class TestAdminRbacRoleCreate:
    def test_post_frontend_payload_creates_role_with_generated_slug(self, admin_api_client, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        before = DataroomRole.objects.filter(organization=admin_user.organization).count()

        response = admin_api_client.post(
            '/api/v1/admin/rbac/roles/',
            FRONTEND_CREATE_ROLE_PAYLOAD,
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['name'] == FRONTEND_CREATE_ROLE_PAYLOAD['name']
        assert response.data['description'] == FRONTEND_CREATE_ROLE_PAYLOAD['description']
        assert response.data['slug'] == 'deal-analyst'
        assert response.data['is_system'] is False

        after = DataroomRole.objects.filter(organization=admin_user.organization).count()
        assert after == before + 1

    def test_created_role_appears_in_roles_list_for_user_pickers(self, admin_api_client, admin_user):
        create = admin_api_client.post(
            '/api/v1/admin/rbac/roles/',
            {'name': 'Picker Role', 'description': ''},
            format='json',
        )
        assert create.status_code == status.HTTP_201_CREATED
        role_id = create.data['id']

        list_res = admin_api_client.get('/api/v1/admin/rbac/roles/', {'page_size': 100})
        assert list_res.status_code == status.HTTP_200_OK
        ids = {row['id'] for row in list_res.data['results']}
        assert role_id in ids

    def test_duplicate_name_returns_400_with_message(self, admin_api_client, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        first = admin_api_client.post(
            '/api/v1/admin/rbac/roles/',
            {'name': 'Unique Custom', 'description': ''},
            format='json',
        )
        assert first.status_code == status.HTTP_201_CREATED

        duplicate = admin_api_client.post(
            '/api/v1/admin/rbac/roles/',
            {'name': 'unique custom', 'description': ''},
            format='json',
        )
        assert duplicate.status_code == status.HTTP_400_BAD_REQUEST
        assert 'name' in duplicate.data
