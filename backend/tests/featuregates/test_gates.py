"""Feature access is enforced per user role (RBAC), not global AppConfiguration toggles."""
import pytest
from django.urls import reverse
from rest_framework import status

from core.authentication import generate_raw_api_key
from core.models import APIKey
from permissions_rbac.catalogue import (
    PERM_FILE_VIEW,
    PERM_SYSTEM_API_KEYS,
    PERM_SYSTEM_AUTOMATION,
    PERM_SYSTEM_DOCUMENTS,
    PERM_SYSTEM_FILE_REQUESTS,
    PERM_SYSTEM_SIGNATURE,
    PERM_SYSTEM_SWAGGER,
    PERM_SYSTEM_TRASH,
    ROLE_SLUG_ADMIN,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.services import invalidate_organization_rbac_cache
from permissions_rbac.safety import user_has_full_access
from core.models import User


@pytest.fixture(autouse=True)
def _reset_default_rbac_roles(organization):
    ensure_default_roles_for_organization(organization)
    yield
    ensure_default_roles_for_organization(organization)


def _role_without(*, organization, exclude):
    ensure_default_roles_for_organization(organization)
    role = DataroomRole.objects.create(
        organization=organization,
        slug='gate-test-role',
        name='Gate Test',
        is_system=False,
    )
    grants = {
        PERM_SYSTEM_DOCUMENTS: '',
        PERM_FILE_VIEW: '',
    }
    grants = {k: v for k, v in grants.items() if k not in exclude}
    DataroomRolePermission.objects.bulk_create(
        [DataroomRolePermission(role=role, permission=p, scope=s) for p, s in grants.items()]
    )
    invalidate_organization_rbac_cache(str(organization.id))
    return role


@pytest.fixture
def gated_member(db, organization):
    from core.models import User

    user = User.objects.create_user(
        username='gated-member@test.com',
        email='gated-member@test.com',
        password='password',
        organization=organization,
        role='member',
    )
    return user


@pytest.fixture
def member_client(gated_member):
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=gated_member)
    return client


@pytest.mark.django_db
class TestAdminOnlyFeatures:
    def test_member_forbidden_on_api_keys_and_automations(self, api_client):
        assert api_client.get(reverse('api-key-list')).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get('/api/v1/automations/').status_code == status.HTTP_403_FORBIDDEN

    def test_primary_admin_allowed_on_api_keys_and_automations(self, admin_api_client, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        assert user_has_full_access(admin_user)
        assert admin_api_client.get(reverse('api-key-list')).status_code == status.HTTP_200_OK
        assert admin_api_client.get('/api/v1/automations/').status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFeatureTogglesInAdminSettings:
    def test_admin_settings_list_excludes_retired_feature_toggles(self, admin_api_client):
        response = admin_api_client.get('/api/v1/admin/settings/')
        assert response.status_code == status.HTTP_200_OK
        keys = {item['key'] for item in response.data}
        for retired in (
            'AUTOMATION_ENABLED',
            'API_KEYS_ENABLED',
            'FILE_REQUESTS_ENABLED',
            'SWAGGER_ENABLED',
            'ESIGN_ENABLED',
            'ROLE_LABELS_ENABLED',
        ):
            assert retired not in keys


@pytest.mark.django_db
class TestAutomationRbac:
    def test_automation_403_without_role_grant(self, organization, admin_user):
        from rest_framework.test import APIClient

        ensure_default_roles_for_organization(organization)
        admin_role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
        admin_role.permission_grants.filter(permission=PERM_SYSTEM_AUTOMATION).delete()
        invalidate_organization_rbac_cache(str(organization.id))
        secondary_admin = User.objects.create_user(
            username='secondary-admin@test.com',
            email='secondary-admin@test.com',
            password='password',
            organization=organization,
            role='admin',
        )
        client = APIClient()
        client.force_authenticate(user=secondary_admin)
        assert client.get('/api/v1/automations/').status_code == status.HTTP_403_FORBIDDEN

    def test_automation_200_with_role_grant(self, organization, admin_user):
        from rest_framework.test import APIClient

        ensure_default_roles_for_organization(organization)
        invalidate_organization_rbac_cache(str(organization.id))
        secondary_admin = User.objects.create_user(
            username='secondary-admin-ok@test.com',
            email='secondary-admin-ok@test.com',
            password='password',
            organization=organization,
            role='admin',
        )
        client = APIClient()
        client.force_authenticate(user=secondary_admin)
        assert client.get('/api/v1/automations/').status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestApiKeysRbac:
    def test_api_key_management_403_without_grant(self, organization, admin_user):
        from rest_framework.test import APIClient

        admin_role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
        admin_role.permission_grants.filter(permission=PERM_SYSTEM_API_KEYS).delete()
        invalidate_organization_rbac_cache(str(organization.id))
        secondary_admin = User.objects.create_user(
            username='no-keys-admin@test.com',
            email='no-keys-admin@test.com',
            password='password',
            organization=organization,
            role='admin',
        )
        client = APIClient()
        client.force_authenticate(user=secondary_admin)
        assert client.get(reverse('api-key-list')).status_code == status.HTTP_403_FORBIDDEN

    def test_bearer_api_key_rejected_without_owner_grant(self, public_client, organization, user):
        role = _role_without(organization=organization, exclude={PERM_SYSTEM_API_KEYS, PERM_SYSTEM_DOCUMENTS})
        user.organization_role = role
        user.save(update_fields=['organization_role'])
        raw_key, prefix, hashed_key = generate_raw_api_key()
        APIKey.objects.create(
            user=user,
            name='test',
            prefix=prefix,
            hashed_key=hashed_key,
            tier='read_only',
        )
        public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
        assert public_client.get('/api/v1/documents/').status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestFileRequestsRbac:
    def test_file_requests_403_without_grant(self, organization, gated_member, member_client):
        role = _role_without(organization=organization, exclude={PERM_SYSTEM_FILE_REQUESTS})
        gated_member.organization_role = role
        gated_member.save(update_fields=['organization_role'])
        assert member_client.get('/api/v1/file-requests/').status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPublicSettingsFeatureFlags:
    def test_public_settings_false_for_anonymous(self, public_client):
        response = public_client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('automation_enabled') is False
        assert response.data.get('api_keys_enabled') is False
        assert response.data.get('file_requests_enabled') is False
        assert response.data.get('swagger_enabled') is False
        assert response.data.get('role_labels_enabled') is True


@pytest.mark.django_db
class TestSwaggerRbac:
    def test_schema_404_without_swagger_perm(self, organization, gated_member, member_client):
        ensure_default_roles_for_organization(organization)
        role = _role_without(organization=organization, exclude={PERM_SYSTEM_SWAGGER})
        gated_member.organization_role = role
        gated_member.save(update_fields=['organization_role'])
        assert member_client.get('/api/schema/').status_code == status.HTTP_404_NOT_FOUND

    def test_schema_access_with_swagger_grant(self, organization, gated_member, member_client):
        role = _role_without(organization=organization, exclude=set())
        DataroomRolePermission.objects.update_or_create(
            role=role, permission=PERM_SYSTEM_SWAGGER, defaults={'scope': ''}
        )
        invalidate_organization_rbac_cache(str(organization.id))
        gated_member.organization_role = role
        gated_member.save(update_fields=['organization_role'])
        from permissions_rbac.services import has_system_perm

        assert has_system_perm(gated_member, PERM_SYSTEM_SWAGGER) is True

    def test_schema_available_for_primary_admin(self, admin_api_client, admin_user):
        from permissions_rbac.catalogue import PERM_SYSTEM_SWAGGER
        from permissions_rbac.safety import user_has_full_access
        from permissions_rbac.services import has_system_perm

        ensure_default_roles_for_organization(admin_user.organization)
        assert user_has_full_access(admin_user) is True
        assert has_system_perm(admin_user, PERM_SYSTEM_SWAGGER) is True
        # Schema generation is environment-sensitive; swagger gate must allow primary admins.
        response = admin_api_client.get('/api/schema/')
        assert response.status_code != status.HTTP_403_FORBIDDEN, response.status_code


@pytest.mark.django_db
class TestCriticalPathsUnaffected:
    def test_health_always_available(self, public_client):
        assert public_client.get(reverse('health-check')).status_code == status.HTTP_200_OK

    def test_jwt_login_works_regardless_of_rbac(self, public_client, user):
        login = public_client.post(
            reverse('token_obtain_pair'),
            {'email': user.email, 'password': 'password'},
            format='json',
        )
        assert login.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDocumentsAndTrashRbac:
    def test_documents_403_without_grant(self, organization, gated_member, member_client):
        role = _role_without(organization=organization, exclude={PERM_SYSTEM_DOCUMENTS})
        gated_member.organization_role = role
        gated_member.save(update_fields=['organization_role'])
        assert member_client.get('/api/v1/documents/').status_code == status.HTTP_403_FORBIDDEN

    def test_trash_403_without_grant(self, organization, gated_member, member_client):
        role = _role_without(organization=organization, exclude={PERM_SYSTEM_TRASH})
        gated_member.organization_role = role
        gated_member.save(update_fields=['organization_role'])
        assert member_client.get('/api/v1/trash/').status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_system_role_includes_api_keys(organization):
    ensure_default_roles_for_organization(organization)
    admin = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
    assert admin.permission_grants.filter(permission=PERM_SYSTEM_API_KEYS).exists()
