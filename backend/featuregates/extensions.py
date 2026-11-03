from rest_framework.exceptions import AuthenticationFailed

from automations.views import (
    AutomationAssignmentViewSet,
    AutomationDeliveryViewSet,
    AutomationDestinationViewSet,
    AutomationRuleViewSet,
)
from core.authentication import APIKeyAuthentication
from core.views import APIKeyViewSet, PublicSettingsView

from .services import (
    ensure_admin_user,
    ensure_api_keys_feature_enabled,
    ensure_automation_enabled,
    api_keys_enabled,
    automation_enabled,
    mcp_enabled,
)


def _wrap_initial(viewset_cls, feature_check, require_admin=True):
    original_initial = viewset_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        feature_check()
        if require_admin:
            ensure_admin_user(request.user)
        return original_initial(self, request, *args, **kwargs)

    viewset_cls.initial = patched_initial


_wrap_initial(APIKeyViewSet, ensure_api_keys_feature_enabled, require_admin=True)

for _automation_viewset in (
    AutomationRuleViewSet,
    AutomationDestinationViewSet,
    AutomationDeliveryViewSet,
    AutomationAssignmentViewSet,
):
    _wrap_initial(_automation_viewset, ensure_automation_enabled, require_admin=True)


_original_api_key_authenticate = APIKeyAuthentication.authenticate


def _patched_api_key_authenticate(self, request):
    if not api_keys_enabled():
        raise AuthenticationFailed('API key authentication is disabled.')
    return _original_api_key_authenticate(self, request)


APIKeyAuthentication.authenticate = _patched_api_key_authenticate


_original_public_settings_get = PublicSettingsView.get


def _patched_public_settings_get(self, request):
    response = _original_public_settings_get(self, request)
    response.data['mcp_enabled'] = mcp_enabled()
    response.data['api_keys_enabled'] = api_keys_enabled()
    response.data['automation_enabled'] = automation_enabled()
    return response


PublicSettingsView.get = _patched_public_settings_get
