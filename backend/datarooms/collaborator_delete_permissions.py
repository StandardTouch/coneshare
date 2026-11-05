"""
Dataroom collaborator content policy messages and RBAC assertion entry points.
"""
from permissions_rbac.services import (  # noqa: F401
    assert_user_may_modify_dataroom_content,
    assert_user_may_modify_dataroom_document,
    assert_user_may_modify_dataroom_folder,
    assert_user_may_remove_dataroom_content,
    assert_user_may_reorder_dataroom_items,
    user_can_delete_dataroom_item,
    user_can_modify_dataroom_item,
)

COLLABORATOR_DELETE_DENIED_DETAIL = (
    "Collaborators can only modify or delete files and folders they uploaded or created."
)
COLLABORATOR_MODIFY_DENIED_DETAIL = COLLABORATOR_DELETE_DENIED_DETAIL
