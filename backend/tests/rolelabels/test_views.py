from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status

from core.models import AppConfiguration, Organization
from permissions_rbac.catalogue import ROLE_SLUG_MANAGER
from permissions_rbac.models import DataroomRole
from permissions_rbac.seed import ensure_default_roles_for_organization
from rolelabels.models import RoleLabel, UserRoleLabel

User = get_user_model()

pytestmark = pytest.mark.django_db


def _set_user_invite_enabled(enabled: bool):
    AppConfiguration.objects.update_or_create(
        key='USER_INVITE_EMAIL_ENABLED',
        defaults={
            'value': 'true' if enabled else 'false',
            'description': 'User invite email toggle',
        },
    )
    cache.delete('app_config:USER_INVITE_EMAIL_ENABLED')


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
    def test_member_with_organization_role(self, admin_api_client, user, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        manager = DataroomRole.objects.get(organization=admin_user.organization, slug=ROLE_SLUG_MANAGER)
        response = admin_api_client.patch(
            f'/api/v1/admin/users/{user.id}/',
            {'role': 'member', 'organization_role_id': str(manager.id)},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.role == 'member'
        assert user.organization_role_id == manager.id
        assert response.data['organization_role']['id'] == str(manager.id)

    def test_admin_role_clears_organization_role(self, admin_api_client, user, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        manager = DataroomRole.objects.get(organization=admin_user.organization, slug=ROLE_SLUG_MANAGER)
        user.organization_role = manager
        user.save(update_fields=['organization_role'])
        response = admin_api_client.patch(
            f'/api/v1/admin/users/{user.id}/',
            {'role': 'admin', 'organization_role_id': None},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.role == 'admin'
        assert user.organization_role_id is None


class TestAdminUserCreateRoleLabel:
    def _create_payload(self, **overrides):
        payload = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'role': 'member',
            'password': 'ValidPassword123!',
        }
        payload.update(overrides)
        return payload

    def test_create_member_with_organization_role(self, admin_api_client, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        custom = DataroomRole.objects.create(
            organization=admin_user.organization,
            slug='custom-analyst',
            name='Analyst',
            is_system=False,
        )
        payload = self._create_payload(
            email='labeled@example.com',
            role='member',
            organization_role_id=str(custom.id),
        )
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='labeled@example.com')
        assert user.role == 'member'
        assert user.organization_role_id == custom.id
        assert response.data['organization_role']['id'] == str(custom.id)

    def test_create_admin_without_label(self, admin_api_client):
        payload = self._create_payload(email='newadmin@example.com', role='admin')
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='newadmin@example.com')
        assert user.role == 'admin'
        assert not UserRoleLabel.objects.filter(user=user).exists()

    def test_create_member_without_label(self, admin_api_client):
        payload = self._create_payload(email='plainmember@example.com', role='member')
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='plainmember@example.com')
        assert user.role == 'member'
        assert not UserRoleLabel.objects.filter(user=user).exists()

    def test_create_rejects_foreign_org_role(self, admin_api_client, other_org, admin_user):
        ensure_default_roles_for_organization(other_org)
        foreign = DataroomRole.objects.create(
            organization=other_org,
            slug='foreign-role',
            name='Foreign',
            is_system=False,
        )
        payload = self._create_payload(
            email='foreignlabel@example.com',
            organization_role_id=str(foreign.id),
        )
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'organization_role_id' in response.data


class TestAdminUserCreateInviteRoleLabel:
    @staticmethod
    def _enable_invite():
        _set_user_invite_enabled(True)

    @staticmethod
    def _disable_invite():
        _set_user_invite_enabled(False)

    def setup_method(self):
        self._enable_invite()

    def teardown_method(self):
        self._disable_invite()

    @staticmethod
    def _invite_payload(**overrides):
        payload = {
            'email': 'invited-label@example.com',
            'name': 'Invited Label User',
            'role': 'member',
            'send_invite': True,
        }
        payload.update(overrides)
        return payload

    @patch('django.db.transaction.on_commit', side_effect=lambda func: func())
    @patch('onboarding.services.send_user_invite_email_task.delay')
    def test_create_with_invite_and_organization_role(self, mock_delay, _on_commit, admin_api_client, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        custom = DataroomRole.objects.create(
            organization=admin_user.organization,
            slug='invite-custom',
            name='Invite Custom',
            is_system=False,
        )
        response = admin_api_client.post(
            '/api/v1/admin/users/',
            self._invite_payload(organization_role_id=str(custom.id)),
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='invited-label@example.com')
        assert user.role == 'member'
        assert user.has_usable_password() is False
        assert user.organization_role_id == custom.id
        assert response.data['organization_role']['id'] == str(custom.id)
        mock_delay.assert_called_once()

    @patch('django.db.transaction.on_commit', side_effect=lambda func: func())
    @patch('onboarding.services.send_user_invite_email_task.delay')
    def test_create_with_invite_without_role_label(self, mock_delay, _on_commit, admin_api_client):
        response = admin_api_client.post(
            '/api/v1/admin/users/',
            self._invite_payload(email='invited-plain@example.com'),
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='invited-plain@example.com')
        assert user.role == 'member'
        assert not UserRoleLabel.objects.filter(user=user).exists()
        mock_delay.assert_called_once()
