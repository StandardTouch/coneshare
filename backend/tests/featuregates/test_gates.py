import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from core.models import AppConfiguration


def _set_swagger(enabled: bool):
    AppConfiguration.objects.update_or_create(
        key='SWAGGER_ENABLED',
        defaults={
            'value': 'true' if enabled else 'false',
            'description': 'Swagger toggle',
        },
    )
    cache.delete('app_config:SWAGGER_ENABLED')


@pytest.fixture(autouse=True)
def swagger_on():
    _set_swagger(True)
    yield
    cache.delete('app_config:SWAGGER_ENABLED')


RETIRED_TOGGLE_KEYS = ('MCP_ENABLED', 'API_KEYS_ENABLED', 'AUTOMATION_ENABLED')


@pytest.mark.django_db
class TestAdminOnlyFeatures:
    def test_member_forbidden_on_api_keys_and_automations(self, api_client):
        assert api_client.get(reverse('api-key-list')).status_code == status.HTTP_403_FORBIDDEN
        assert api_client.get('/api/v1/automations/').status_code == status.HTTP_403_FORBIDDEN

    def test_admin_allowed_on_api_keys_and_automations(self, admin_api_client):
        assert admin_api_client.get(reverse('api-key-list')).status_code == status.HTTP_200_OK
        assert admin_api_client.get('/api/v1/automations/').status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRetiredTogglesNotInAdminSettings:
    def test_admin_settings_list_excludes_retired_toggles(self, admin_api_client):
        for key in RETIRED_TOGGLE_KEYS:
            AppConfiguration.objects.update_or_create(
                key=key,
                defaults={'value': 'false', 'description': 'legacy'},
            )
        response = admin_api_client.get('/api/v1/admin/settings/')
        assert response.status_code == status.HTTP_200_OK
        keys = {item['key'] for item in response.data}
        for retired in RETIRED_TOGGLE_KEYS:
            assert retired not in keys
        assert 'SWAGGER_ENABLED' in keys

    def test_retired_toggle_keys_not_in_registry(self):
        from core.settings_registry import DEFAULT_SETTINGS

        for retired in RETIRED_TOGGLE_KEYS:
            assert retired not in DEFAULT_SETTINGS


@pytest.mark.django_db
class TestSwaggerToggle:
    def test_public_settings_exposes_swagger_enabled(self, public_client):
        response = public_client.get('/api/v1/public/settings/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('swagger_enabled') is True
        assert 'mcp_enabled' not in response.data
        assert 'api_keys_enabled' not in response.data

    def test_schema_public_when_swagger_on(self, public_client):
        assert public_client.get('/api/schema/').status_code == status.HTTP_200_OK
        assert public_client.get('/api/schema/swagger/').status_code == status.HTTP_200_OK
        assert public_client.get('/api/schema/redoc/').status_code == status.HTTP_200_OK

    def test_schema_404_when_swagger_off(self, public_client):
        _set_swagger(False)
        assert public_client.get('/api/schema/').status_code == status.HTTP_404_NOT_FOUND
        assert public_client.get('/api/schema/swagger/').status_code == status.HTTP_404_NOT_FOUND
        assert public_client.get('/api/schema/redoc/').status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCriticalPathsUnaffected:
    def test_health_login_jwt_with_swagger_off(self, public_client, api_client, user):
        _set_swagger(False)
        assert public_client.get(reverse('health-check')).status_code == status.HTTP_200_OK
        login = public_client.post(
            reverse('token_obtain_pair'),
            {'email': user.email, 'password': 'password'},
            format='json',
        )
        assert login.status_code == status.HTTP_200_OK
        assert api_client.get('/api/v1/documents/').status_code == status.HTTP_200_OK
