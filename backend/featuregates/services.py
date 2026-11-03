from core.services import get_dynamic_setting
from rest_framework.exceptions import PermissionDenied


def swagger_enabled() -> bool:
    return bool(get_dynamic_setting('SWAGGER_ENABLED'))


def ensure_admin_user(user):
    if getattr(user, 'role', '') != 'admin':
        raise PermissionDenied('Admin role required.')
