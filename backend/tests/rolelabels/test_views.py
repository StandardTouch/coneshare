import pytest
from django.core.cache import cache
from rest_framework import status
from core.models import AppConfiguration, Organization
from rolelabels.models import RoleLabel, UserRoleLabel

pytestmark = pytest.mark.django_db


def _set_role_labels_enabled(enabled: bool):
    AppConfiguration.objects.update_or_create(
        key='ROLE_LABELS_ENABLED',
        defaults={
            'value': 'true' if enabled else 'false',
            'description': 'Enable custom display role labels.',
        },
    )
    cache.delete('app_config:ROLE_LABELS_ENABLED')
    cache.clear()


@pytest.fixture(autouse=True)
def local_cache(settings):
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }


@pytest.fixture(autouse=True)
def role_labels_on(local_cache):
    _set_role_labels_enabled(True)
    yield
    _set_role_labels_enabled(False)


@pytest.fixture
def other_org(db):
    return Organization.objects.create(name='Other Org')


@pytest.fixture
def custom_role(admin_user):
    return RoleLabel.objects.create(
        organization=admin_user.organization,
        name='L1-member',
        description='Level 1 member label',
    )


class TestRoleLabelToggle:
    def test_list_returns_404_when_disabled(self, admin_api_client):
        _set_role_labels_enabled(False)
        response = admin_api_client.get('/api/v1/admin/role-labels/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRoleLabelCRUD:
    def test_admin_can_create_list_update(self, admin_api_client, admin_user):
        create_resp = admin_api_client.post(
            '/api/v1/admin/role-labels/',
            {'name': 'Analyst', 'description': 'Read-only analyst label'},
            format='json',
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        role_id = create_resp.data['id']

        list_resp = admin_api_client.get('/api/v1/admin/role-labels/')
        assert list_resp.status_code == status.HTTP_200_OK
        assert len(list_resp.data['system_roles']) == 2
        assert any(r['is_system'] for r in list_resp.data['system_roles'])
        assert list_resp.data['custom_roles'][0]['name'] == 'Analyst'

        patch_resp = admin_api_client.patch(
            f'/api/v1/admin/role-labels/{role_id}/',
            {'name': 'Senior Analyst'},
            format='json',
        )
        assert patch_resp.status_code == status.HTTP_200_OK
        assert patch_resp.data['name'] == 'Senior Analyst'

    def test_name_unique_case_insensitive(self, admin_api_client, custom_role):
        response = admin_api_client.post(
            '/api/v1/admin/role-labels/',
            {'name': 'l1-MEMBER', 'description': ''},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_blocked_when_in_use(self, admin_api_client, user, custom_role):
        UserRoleLabel.objects.create(user=user, role_label=custom_role)
        response = admin_api_client.delete(f'/api/v1/admin/role-labels/{custom_role.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'reassign them first' in response.data['detail']

    def test_delete_allowed_when_unused(self, admin_api_client, custom_role):
        response = admin_api_client.delete(f'/api/v1/admin/role-labels/{custom_role.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestRoleLabelOrgScoping:
    def test_admin_cannot_access_other_org_role(self, admin_api_client, other_org):
        foreign = RoleLabel.objects.create(organization=other_org, name='Foreign')
        response = admin_api_client.get(f'/api/v1/admin/role-labels/{foreign.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_member_forbidden(self, api_client, user, custom_role):
        api_client.force_authenticate(user=user)
        response = api_client.get('/api/v1/admin/role-labels/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAdminUserRoleLabel:
    def test_labeled_user_has_member_role(self, admin_api_client, user, custom_role):
        response = admin_api_client.patch(
            f'/api/v1/admin/users/{user.id}/',
            {'role': 'member', 'role_label_id': custom_role.id},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.role == 'member'
        assert response.data['role_label']['id'] == custom_role.id
        assert response.data['role_label']['name'] == custom_role.name

    def test_admin_role_clears_label(self, admin_api_client, user, custom_role):
        UserRoleLabel.objects.create(user=user, role_label=custom_role)
        response = admin_api_client.patch(
            f'/api/v1/admin/users/{user.id}/',
            {'role': 'admin', 'role_label_id': None},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.role == 'admin'
        assert not UserRoleLabel.objects.filter(user=user).exists()
