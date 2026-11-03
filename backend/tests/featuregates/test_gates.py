import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from core.authentication import generate_raw_api_key
from core.models import AppConfiguration, APIKey


def _set_toggle(key: str, enabled: bool):
    AppConfiguration.objects.update_or_create(
        key=key,
        defaults={
            'value': 'true' if enabled else 'false',
            'description': f'Toggle {key}',
        },
    )
    cache.delete(f'app_config:{key}')


@pytest.fixture(autouse=True)
def enable_all_feature_gates():
    for key in ('MCP_ENABLED', 'API_KEYS_ENABLED', 'AUTOMATION_ENABLED', 'SWAGGER_ENABLED'):
        _set_toggle(key, True)
    yield
    for key in ('MCP_ENABLED', 'API_KEYS_ENABLED', 'AUTOMATION_ENABLED', 'SWAGGER_ENABLED'):
        cache.delete(f'app_config:{key}')


@pytest.mark.django_db
class TestPublicSettingsFeatureFlags:
    def test_public_settings_includes_feature_flags(self, public_client):
        response = public_client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        for field in ('mcp_enabled', 'api_keys_enabled', 'automation_enabled'):
            assert field in response.data
            assert response.data[field] is True

    def test_public_settings_reflects_disabled_mcp(self, public_client):
        _set_toggle('MCP_ENABLED', False)
        response = public_client.get('/api/v1/public/settings/')
        assert response.data['mcp_enabled'] is False


@pytest.mark.django_db
class TestApiKeyAdminAndToggle:
    def test_member_cannot_list_api_keys_when_enabled(self, api_client):
        url = reverse('api-key-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_list_api_keys_when_enabled(self, admin_api_client):
        url = reverse('api-key-list')
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_api_keys_endpoints_return_404_when_disabled(self, admin_api_client):
        _set_toggle('API_KEYS_ENABLED', False)
        url = reverse('api-key-list')
        response = admin_api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_existing_member_api_key_still_authenticates_when_feature_enabled(
        self, public_client, user
    ):
        raw_key, prefix, hashed_key = generate_raw_api_key()
        APIKey.objects.create(
            user=user,
            name='Legacy member key',
            prefix=prefix,
            hashed_key=hashed_key,
            tier='read_only',
        )
        public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
        url = reverse('api-key-list')
        response = public_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_api_key_auth_rejected_when_feature_disabled(self, public_client, user):
        raw_key, prefix, hashed_key = generate_raw_api_key()
        APIKey.objects.create(
            user=user,
            name='Blocked key',
            prefix=prefix,
            hashed_key=hashed_key,
            tier='read_only',
        )
        _set_toggle('API_KEYS_ENABLED', False)
        public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
        response = public_client.get('/api/v1/documents/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_health_and_public_settings_work_when_api_keys_disabled(self, public_client):
        _set_toggle('API_KEYS_ENABLED', False)
        assert public_client.get(reverse('health-check')).status_code == status.HTTP_200_OK
        assert public_client.get('/api/v1/public/settings/').status_code == status.HTTP_200_OK


TOGGLE_KEYS = (
    'MCP_ENABLED',
    'API_KEYS_ENABLED',
    'AUTOMATION_ENABLED',
    'SWAGGER_ENABLED',
)


@pytest.mark.django_db
class TestCriticalPathsWhenSingleToggleOff:
    @pytest.mark.parametrize('toggle_key', TOGGLE_KEYS)
    def test_health_public_settings_login_and_jwt_when_toggle_off(
        self, public_client, api_client, user, toggle_key
    ):
        _set_toggle(toggle_key, False)

        health = public_client.get(reverse('health-check'))
        assert health.status_code == status.HTTP_200_OK

        settings_resp = public_client.get('/api/v1/public/settings/')
        assert settings_resp.status_code == status.HTTP_200_OK

        login_resp = public_client.post(
            reverse('token_obtain_pair'),
            {'email': user.email, 'password': 'password'},
            format='json',
        )
        assert login_resp.status_code == status.HTTP_200_OK
        assert 'access' in login_resp.data

        jwt_resp = api_client.get('/api/v1/documents/')
        assert jwt_resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAutomationAdminAndToggle:
    def test_member_cannot_list_automations(self, api_client):
        response = api_client.get('/api/v1/automations/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_list_automations(self, admin_api_client):
        response = admin_api_client.get('/api/v1/automations/')
        assert response.status_code == status.HTTP_200_OK

    def test_automation_returns_404_when_disabled(self, admin_api_client):
        _set_toggle('AUTOMATION_ENABLED', False)
        response = admin_api_client.get('/api/v1/automations/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestSwaggerToggle:
    def test_schema_available_when_enabled(self, public_client):
        response = public_client.get('/api/schema/')
        assert response.status_code == status.HTTP_200_OK

    def test_swagger_ui_available_when_enabled(self, public_client):
        response = public_client.get('/api/schema/swagger/')
        assert response.status_code == status.HTTP_200_OK

    def test_redoc_available_when_enabled(self, public_client):
        response = public_client.get('/api/schema/redoc/')
        assert response.status_code == status.HTTP_200_OK

    def test_schema_returns_404_when_disabled(self, public_client):
        _set_toggle('SWAGGER_ENABLED', False)
        assert public_client.get('/api/schema/').status_code == status.HTTP_404_NOT_FOUND
        assert public_client.get('/api/schema/swagger/').status_code == status.HTTP_404_NOT_FOUND
        assert public_client.get('/api/schema/redoc/').status_code == status.HTTP_404_NOT_FOUND
