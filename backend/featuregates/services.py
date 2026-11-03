from core.services import get_dynamic_setting
from rest_framework.exceptions import NotFound, PermissionDenied


def mcp_enabled() -> bool:
    return bool(get_dynamic_setting('MCP_ENABLED'))


def api_keys_enabled() -> bool:
    return bool(get_dynamic_setting('API_KEYS_ENABLED'))


def automation_enabled() -> bool:
    return bool(get_dynamic_setting('AUTOMATION_ENABLED'))


def swagger_enabled() -> bool:
    return bool(get_dynamic_setting('SWAGGER_ENABLED'))


def ensure_mcp_enabled():
    if not mcp_enabled():
        raise NotFound()


def ensure_api_keys_feature_enabled():
    if not api_keys_enabled():
        raise NotFound()


def ensure_automation_enabled():
    if not automation_enabled():
        raise NotFound()


def ensure_swagger_enabled():
    if not swagger_enabled():
        raise NotFound()


def ensure_admin_user(user):
    if getattr(user, 'role', '') != 'admin':
        raise PermissionDenied('Admin role required.')
