import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from core.authentication import generate_raw_api_key
from core.models import AppConfiguration


def _set_setting(key: str, enabled: bool):
    AppConfiguration.objects.update_or_create(
        key=key,
        defaults={
            'value': 'true' if enabled else 'false',
            'description': f'{key} toggle',
        },
    )
    cache.delete(f'app_config:{key}')


def _set_swagger(enabled: bool):
    _set_setting('SWAGGER_ENABLED', enabled)


def _set_all_feature_toggles(enabled: bool):
    for key in (
        'SWAGGER_ENABLED',
        'AUTOMATION_ENABLED',
        'API_KEYS_ENABLED',
        'FILE_REQUESTS_ENABLED',
    ):
        _set_setting(key, enabled)


@pytest.fixture(autouse=True)
def feature_toggles_on():
    _set_all_feature_toggles(True)
    yield
    for key in (
        'SWAGGER_ENABLED',
        'AUTOMATION_ENABLED',
        'API_KEYS_ENABLED',
        'FILE_REQUESTS_ENABLED',
    ):
        cache.delete(f'app_config:{key}')


RETIRED_TOGGLE_KEYS = ('MCP_ENABLED',)


@pytest.mark.django_db
class TestAdminOnlyFeatures:
    def test_member_forbidden_on_api_keys_and_automations(self, api_client):
        assert api_client.get(reverse('api-key-list')).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get('/api/v1/automations/').status_code == status.HTTP_403_FORBIDDEN

    def test_admin_allowed_on_api_keys_and_automations(self, admin_api_client):
        assert admin_api_client.get(reverse('api-key-list')).status_code == status.HTTP_200_OK
        assert admin_api_client.get('/api/v1/automations/').status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFeatureTogglesInAdminSettings:
    def test_admin_settings_list_includes_feature_toggles(self, admin_api_client):
        response = admin_api_client.get('/api/v1/admin/settings/')
        assert response.status_code == status.HTTP_200_OK
        keys = {item['key'] for item in response.data}
        assert 'AUTOMATION_ENABLED' in keys
        assert 'API_KEYS_ENABLED' in keys
        assert 'FILE_REQUESTS_ENABLED' in keys
        assert 'SWAGGER_ENABLED' in keys
        for retired in RETIRED_TOGGLE_KEYS:
            assert retired not in keys

    def test_retired_toggle_keys_not_in_registry(self):
        from core.settings_registry import DEFAULT_SETTINGS

        for retired in RETIRED_TOGGLE_KEYS:
            assert retired not in DEFAULT_SETTINGS


@pytest.mark.django_db
class TestAutomationToggle:
    def test_automation_403_when_disabled(self, admin_api_client):
        _set_setting('AUTOMATION_ENABLED', False)
        assert admin_api_client.get('/api/v1/automations/').status_code == status.HTTP_403_FORBIDDEN

    def test_automation_200_when_re_enabled_via_db_without_stale_cache(self, admin_api_client):
        _set_setting('AUTOMATION_ENABLED', False)
        assert admin_api_client.get('/api/v1/automations/').status_code == status.HTTP_403_FORBIDDEN
        _set_setting('AUTOMATION_ENABLED', True)
        assert admin_api_client.get('/api/v1/automations/').status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestApiKeysToggle:
    def test_api_key_management_403_when_disabled(self, admin_api_client):
        _set_setting('API_KEYS_ENABLED', False)
        assert admin_api_client.get(reverse('api-key-list')).status_code == status.HTTP_403_FORBIDDEN

    def test_jwt_session_still_works_when_api_keys_disabled(self, api_client):
        _set_setting('API_KEYS_ENABLED', False)
        assert api_client.get('/api/v1/documents/').status_code == status.HTTP_200_OK

    def test_health_and_public_settings_when_api_keys_disabled(self, public_client):
        _set_setting('API_KEYS_ENABLED', False)
        assert public_client.get(reverse('health-check')).status_code == status.HTTP_200_OK
        response = public_client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('api_keys_enabled') is False

    def test_bearer_api_key_rejected_when_disabled(self, public_client, user):
        _set_setting('API_KEYS_ENABLED', False)
        raw_key, prefix, hashed_key = generate_raw_api_key()
        from core.models import APIKey

        APIKey.objects.create(
            user=user,
            name='test',
            prefix=prefix,
            hashed_key=hashed_key,
            tier='read_only',
        )
        public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
        assert public_client.get('/api/v1/documents/').status_code == status.HTTP_403_FORBIDDEN

    def test_non_api_bearer_does_not_trigger_api_keys_off_rejection(self, public_client, user):
        _set_setting('API_KEYS_ENABLED', False)
        login = public_client.post(
            reverse('token_obtain_pair'),
            {'email': user.email, 'password': 'password'},
            format='json',
        )
        assert login.status_code == status.HTTP_200_OK
        token = login.data['access']
        public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        assert public_client.get('/api/v1/documents/').status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestFileRequestsToggle:
    def test_file_requests_403_when_disabled(self, api_client):
        _set_setting('FILE_REQUESTS_ENABLED', False)
        assert api_client.get('/api/v1/file-requests/').status_code == status.HTTP_403_FORBIDDEN

    def test_public_file_request_403_when_disabled(self, public_client, file_request):
        _set_setting('FILE_REQUESTS_ENABLED', False)
        url = reverse('public-file-request-detail', kwargs={'slug': file_request.slug})
        assert public_client.get(url).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestPublicSettingsFeatureFlags:
    def test_public_settings_exposes_feature_flags(self, public_client):
        response = public_client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('automation_enabled') is True
        assert response.data.get('api_keys_enabled') is True
        assert response.data.get('file_requests_enabled') is True
        assert response.data.get('swagger_enabled') is True
        assert 'mcp_enabled' not in response.data


@pytest.mark.django_db
class TestSwaggerToggle:
    def test_schema_404_when_swagger_off(self, public_client):
        _set_swagger(False)
        assert public_client.get('/api/schema/').status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCriticalPathsUnaffected:
    def test_health_login_jwt_with_all_feature_toggles_off(self, public_client, api_client, user):
        _set_all_feature_toggles(False)
        assert public_client.get(reverse('health-check')).status_code == status.HTTP_200_OK
        login = public_client.post(
            reverse('token_obtain_pair'),
            {'email': user.email, 'password': 'password'},
            format='json',
        )
        assert login.status_code == status.HTTP_200_OK
        assert api_client.get('/api/v1/documents/').status_code == status.HTTP_200_OK
        settings_response = public_client.get('/api/v1/public/settings/')
        assert settings_response.status_code == status.HTTP_200_OK
