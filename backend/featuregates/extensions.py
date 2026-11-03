from automations.views import (
    AutomationAssignmentViewSet,
    AutomationDeliveryViewSet,
    AutomationDestinationViewSet,
    AutomationRuleViewSet,
)
from core.authentication import APIKeyAuthentication
from core.views import APIKeyViewSet, PublicSettingsView
from filerequests.views import (
    FileRequestUploadFinalizeView,
    FileRequestUploadRequestView,
    FileRequestViewSet,
    PublicFileRequestView,
)
from rest_framework.exceptions import PermissionDenied

from .services import (
    api_keys_enabled,
    automation_enabled,
    ensure_admin_user,
    ensure_api_keys_enabled,
    ensure_automation_enabled,
    ensure_file_requests_enabled,
    file_requests_enabled,
    swagger_enabled,
)


def _wrap_admin_only(viewset_cls, feature_check=None):
    original_initial = viewset_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        ensure_admin_user(request.user)
        if feature_check is not None:
            feature_check()
        return original_initial(self, request, *args, **kwargs)

    viewset_cls.initial = patched_initial


def _wrap_feature_only(viewset_cls, feature_check):
    original_initial = viewset_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        feature_check()
        return original_initial(self, request, *args, **kwargs)

    viewset_cls.initial = patched_initial


def _wrap_api_view_feature(view_cls, feature_check):
    original_initial = view_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        feature_check()
        return original_initial(self, request, *args, **kwargs)

    view_cls.initial = patched_initial


_wrap_admin_only(APIKeyViewSet, ensure_api_keys_enabled)

for _automation_viewset in (
    AutomationRuleViewSet,
    AutomationDestinationViewSet,
    AutomationDeliveryViewSet,
    AutomationAssignmentViewSet,
):
    _wrap_admin_only(_automation_viewset, ensure_automation_enabled)

_wrap_feature_only(FileRequestViewSet, ensure_file_requests_enabled)

for _public_file_request_view in (
    PublicFileRequestView,
    FileRequestUploadRequestView,
    FileRequestUploadFinalizeView,
):
    _wrap_api_view_feature(_public_file_request_view, ensure_file_requests_enabled)


_original_api_key_authenticate = APIKeyAuthentication.authenticate


def _patched_api_key_authenticate(self, request):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer' and parts[1].startswith('cs_live_'):
            if not api_keys_enabled():
                raise PermissionDenied('API key authentication is not enabled.')
    return _original_api_key_authenticate(self, request)


APIKeyAuthentication.authenticate = _patched_api_key_authenticate


_original_public_settings_get = PublicSettingsView.get


def _patched_public_settings_get(self, request):
    response = _original_public_settings_get(self, request)
    response.data['swagger_enabled'] = swagger_enabled()
    response.data['automation_enabled'] = automation_enabled()
    response.data['api_keys_enabled'] = api_keys_enabled()
    response.data['file_requests_enabled'] = file_requests_enabled()
    return response


PublicSettingsView.get = _patched_public_settings_get
