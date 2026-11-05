"""
Dataroom creation policy (configurable via admin settings).

Legacy import path; evaluation is implemented in ``permissions_rbac.services``.
"""
from core.services import get_dynamic_setting  # re-export for tests and legacy patches
from permissions_rbac.services import assert_user_may_create_dataroom  # noqa: F401

DATAROOM_CREATE_DENIED_DETAIL = "Only organization admins can create datarooms."


def dataroom_create_admin_only_enabled() -> bool:
    return bool(get_dynamic_setting('DATAROOM_CREATE_ADMIN_ONLY'))
