from automations.views import (
    AutomationAssignmentViewSet,
    AutomationDeliveryViewSet,
    AutomationDestinationViewSet,
    AutomationRuleViewSet,
)
from core.views import APIKeyViewSet, PublicSettingsView

from .services import ensure_admin_user, swagger_enabled


def _wrap_admin_only(viewset_cls):
    original_initial = viewset_cls.initial

    def patched_initial(self, request, *args, **kwargs):
        ensure_admin_user(request.user)
        return original_initial(self, request, *args, **kwargs)

    viewset_cls.initial = patched_initial


_wrap_admin_only(APIKeyViewSet)

for _automation_viewset in (
    AutomationRuleViewSet,
    AutomationDestinationViewSet,
    AutomationDeliveryViewSet,
    AutomationAssignmentViewSet,
):
    _wrap_admin_only(_automation_viewset)


_original_public_settings_get = PublicSettingsView.get


def _patched_public_settings_get(self, request):
    response = _original_public_settings_get(self, request)
    response.data['swagger_enabled'] = swagger_enabled()
    return response


PublicSettingsView.get = _patched_public_settings_get
