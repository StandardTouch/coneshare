"""
Dataroom creation policy (configurable via admin settings).

When DATAROOM_CREATE_ADMIN_ONLY is enabled (default), only organization admins
may create new datarooms. Members may still participate in rooms they are added to.
"""
from rest_framework.exceptions import PermissionDenied

from core.services import get_dynamic_setting

DATAROOM_CREATE_DENIED_DETAIL = "Only organization admins can create datarooms."


def dataroom_create_admin_only_enabled() -> bool:
    return bool(get_dynamic_setting('DATAROOM_CREATE_ADMIN_ONLY'))


def assert_user_may_create_dataroom(user) -> None:
    if not dataroom_create_admin_only_enabled():
        return
    if getattr(user, 'role', '') == 'admin':
        return
    raise PermissionDenied(DATAROOM_CREATE_DENIED_DETAIL)
