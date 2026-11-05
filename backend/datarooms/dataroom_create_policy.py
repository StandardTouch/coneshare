"""
Dataroom creation policy messages and RBAC assertion entry points.
"""
from permissions_rbac.services import assert_user_may_create_dataroom  # noqa: F401

DATAROOM_CREATE_DENIED_DETAIL = "Only organization admins can create datarooms."
