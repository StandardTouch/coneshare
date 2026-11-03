from core.services import get_dynamic_setting
from rest_framework.exceptions import PermissionDenied


def swagger_enabled() -> bool:
    return bool(get_dynamic_setting('SWAGGER_ENABLED'))


def automation_enabled() -> bool:
    return bool(get_dynamic_setting('AUTOMATION_ENABLED'))


def api_keys_enabled() -> bool:
    return bool(get_dynamic_setting('API_KEYS_ENABLED'))


def file_requests_enabled() -> bool:
    return bool(get_dynamic_setting('FILE_REQUESTS_ENABLED'))


def ensure_admin_user(user):
    if getattr(user, 'role', '') != 'admin':
        raise PermissionDenied('Admin role required.')


def ensure_automation_enabled():
    if not automation_enabled():
        raise PermissionDenied('Automation feature is not enabled.')


def ensure_api_keys_enabled():
    if not api_keys_enabled():
        raise PermissionDenied('API keys and MCP integration are not enabled.')


def ensure_file_requests_enabled():
    if not file_requests_enabled():
        raise PermissionDenied('File requests feature is not enabled.')
