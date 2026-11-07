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
from permissions_rbac.services import has_system_perm, resolve_organization_role
from permissions_rbac.catalogue import PERM_SYSTEM_API_KEYS
from rest_framework.exceptions import PermissionDenied

from .services import (
    api_keys_enabled_for_user,
    automation_enabled_for_user,
    ensure_admin_user,
    ensure_api_keys_enabled_for_user,
    ensure_automation_enabled_for_user,
    ensure_file_requests_enabled_for_user,
    file_requests_enabled_for_user,
    swagger_enabled_for_user,
)


def _wrap_admin_only(viewset_cls, feature_check=None):
    original_initial = viewset_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        ensure_admin_user(request.user)
        if feature_check is not None:
            feature_check(request.user)
        return original_initial(self, request, *args, **kwargs)

    viewset_cls.initial = patched_initial


def _wrap_feature_only(viewset_cls, feature_check):
    original_initial = viewset_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        feature_check(request.user)
        return original_initial(self, request, *args, **kwargs)

    viewset_cls.initial = patched_initial


def _wrap_api_view_feature(view_cls, feature_check):
    original_initial = view_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        feature_check(request.user)
        return original_initial(self, request, *args, **kwargs)

    view_cls.initial = patched_initial


_wrap_admin_only(APIKeyViewSet, ensure_api_keys_enabled_for_user)

for _automation_viewset in (
    AutomationRuleViewSet,
    AutomationDestinationViewSet,
    AutomationDeliveryViewSet,
    AutomationAssignmentViewSet,
):
    _wrap_admin_only(_automation_viewset, ensure_automation_enabled_for_user)

_wrap_feature_only(FileRequestViewSet, ensure_file_requests_enabled_for_user)


_original_api_key_authenticate = APIKeyAuthentication.authenticate


def _patched_api_key_authenticate(self, request):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        parts = auth_header.split()
        if len(parts) == 2 and parts[0].lower() == 'bearer' and parts[1].startswith('cs_live_'):
            result = _original_api_key_authenticate(self, request)
            if result is None:
                return None
            user, api_key = result
            owner = getattr(api_key, 'user', None) or user
            if not has_system_perm(owner, PERM_SYSTEM_API_KEYS):
                raise PermissionDenied('API key authentication is not enabled for this account.')
            return user, api_key
    return _original_api_key_authenticate(self, request)


APIKeyAuthentication.authenticate = _patched_api_key_authenticate


_original_public_settings_get = PublicSettingsView.get


def _patched_public_settings_get(self, request):
    response = _original_public_settings_get(self, request)
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        response.data['swagger_enabled'] = swagger_enabled_for_user(user)
        response.data['automation_enabled'] = automation_enabled_for_user(user)
        response.data['api_keys_enabled'] = api_keys_enabled_for_user(user)
        response.data['file_requests_enabled'] = file_requests_enabled_for_user(user)
    else:
        response.data['swagger_enabled'] = False
        response.data['automation_enabled'] = False
        response.data['api_keys_enabled'] = False
        response.data['file_requests_enabled'] = False
    response.data['role_labels_enabled'] = True
    return response


PublicSettingsView.get = _patched_public_settings_get

from documents.views import DocumentViewSet, TrashViewSet

from .services import ensure_documents_enabled_for_user, ensure_trash_enabled_for_user

_wrap_feature_only(DocumentViewSet, ensure_documents_enabled_for_user)
_wrap_feature_only(TrashViewSet, ensure_trash_enabled_for_user)
