import pytest
from rest_framework import status

from permissions_rbac.models import DataroomRole


@pytest.mark.django_db
class TestAdminRbacRoleCreate:
    """Matches AdminRolesPage create modal payload (name + description only)."""

    def test_create_custom_role_frontend_payload(self, admin_api_client):
        payload = {'name': 'Deal Desk', 'description': 'Negotiation team'}
        response = admin_api_client.post('/api/v1/admin/rbac/roles/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert response.data['name'] == 'Deal Desk'
        assert response.data['description'] == 'Negotiation team'
        assert response.data['slug']
        assert response.data['is_system'] is False
        role = DataroomRole.objects.get(id=response.data['id'])
        assert role.slug == response.data['slug']

    def test_create_rejects_missing_name(self, admin_api_client):
        response = admin_api_client.post(
            '/api/v1/admin/rbac/roles/',
            {'name': '', 'description': 'x'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'name' in response.data

    def test_create_rejects_duplicate_name(self, admin_api_client, organization):
        DataroomRole.objects.create(
            organization=organization,
            slug='deal-desk',
            name='Deal Desk',
            is_system=False,
        )
        response = admin_api_client.post(
            '/api/v1/admin/rbac/roles/',
            {'name': 'deal desk', 'description': ''},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['name'] == ['A role with this name already exists.']
