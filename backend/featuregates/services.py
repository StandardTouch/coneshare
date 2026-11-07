from rest_framework.exceptions import PermissionDenied

from permissions_rbac.catalogue import (
    PERM_SYSTEM_API_KEYS,
    PERM_SYSTEM_AUTOMATION,
    PERM_SYSTEM_DOCUMENTS,
    PERM_SYSTEM_FILE_REQUESTS,
    PERM_SYSTEM_SIGNATURE,
    PERM_SYSTEM_SWAGGER,
    PERM_SYSTEM_TRASH,
)
from permissions_rbac.services import has_system_perm


def swagger_enabled_for_user(user) -> bool:
    return has_system_perm(user, PERM_SYSTEM_SWAGGER)


def automation_enabled_for_user(user) -> bool:
    return has_system_perm(user, PERM_SYSTEM_AUTOMATION)


def api_keys_enabled_for_user(user) -> bool:
    return has_system_perm(user, PERM_SYSTEM_API_KEYS)


def file_requests_enabled_for_user(user) -> bool:
    return has_system_perm(user, PERM_SYSTEM_FILE_REQUESTS)


def documents_enabled_for_user(user) -> bool:
    return has_system_perm(user, PERM_SYSTEM_DOCUMENTS)


def trash_enabled_for_user(user) -> bool:
    return has_system_perm(user, PERM_SYSTEM_TRASH)


def signature_enabled_for_user(user) -> bool:
    return has_system_perm(user, PERM_SYSTEM_SIGNATURE)


def ensure_admin_user(user):
    if getattr(user, 'role', '') != 'admin':
        raise PermissionDenied('Admin role required.')


def _require_perm(user, checker):
    if not checker(user):
        raise PermissionDenied('You do not have permission to perform this action.')


def ensure_automation_enabled_for_user(user):
    _require_perm(user, automation_enabled_for_user)


def ensure_api_keys_enabled_for_user(user):
    _require_perm(user, api_keys_enabled_for_user)


def ensure_file_requests_enabled_for_user(user):
    _require_perm(user, file_requests_enabled_for_user)


def ensure_documents_enabled_for_user(user):
    _require_perm(user, documents_enabled_for_user)


def ensure_trash_enabled_for_user(user):
    _require_perm(user, trash_enabled_for_user)


def ensure_signature_enabled_for_user(user):
    _require_perm(user, signature_enabled_for_user)


def ensure_swagger_for_user(user):
    _require_perm(user, swagger_enabled_for_user)


# Backwards-compatible aliases used in extensions/tests
def swagger_enabled() -> bool:
    return True


def automation_enabled() -> bool:
    return True


def api_keys_enabled() -> bool:
    return True


def file_requests_enabled() -> bool:
    return True


def ensure_automation_enabled():
    raise PermissionDenied('Use per-user RBAC checks.')


def ensure_api_keys_enabled():
    raise PermissionDenied('Use per-user RBAC checks.')


def ensure_file_requests_enabled():
    raise PermissionDenied('Use per-user RBAC checks.')
