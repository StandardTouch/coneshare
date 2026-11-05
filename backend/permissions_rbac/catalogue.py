"""
Central catalogue of dataroom and site permissions.

Scoped permissions use ``any`` (all items in the dataroom) or ``own`` (items the user
created or uploaded). Non-scoped permissions ignore scope.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set


SCOPE_ANY = 'any'
SCOPE_OWN = 'own'
SCOPE_CHOICES = (SCOPE_ANY, SCOPE_OWN)

SITE_ROLE_ADMIN = 'admin'
SITE_ROLE_MEMBER = 'member'

# Dataroom-level permission codenames
PERM_VIEW = 'view'
PERM_DOWNLOAD = 'download'
PERM_UPLOAD = 'upload'
PERM_CREATE_FOLDER = 'create_folder'
PERM_RENAME = 'rename'
PERM_MOVE = 'move'
PERM_REORDER = 'reorder'
PERM_DELETE = 'delete'
PERM_MANAGE_SHARE_SETTINGS = 'manage_share_settings'
PERM_INVITE_COLLABORATORS = 'invite_collaborators'
PERM_MANAGE_COLLABORATORS = 'manage_collaborators'
PERM_EDIT_DATAROOM_SETTINGS = 'edit_dataroom_settings'
PERM_DELETE_DATAROOM = 'delete_dataroom'

# Site-level (organization membership)
PERM_CREATE_DATAROOM = 'create_dataroom'

MODIFY_PERMISSIONS: Set[str] = {
    PERM_RENAME,
    PERM_MOVE,
    PERM_REORDER,
    PERM_DELETE,
    PERM_MANAGE_SHARE_SETTINGS,
}

ALL_DATAROOM_PERMISSIONS: List[str] = [
    PERM_VIEW,
    PERM_DOWNLOAD,
    PERM_UPLOAD,
    PERM_CREATE_FOLDER,
    PERM_RENAME,
    PERM_MOVE,
    PERM_REORDER,
    PERM_DELETE,
    PERM_MANAGE_SHARE_SETTINGS,
    PERM_INVITE_COLLABORATORS,
    PERM_MANAGE_COLLABORATORS,
    PERM_EDIT_DATAROOM_SETTINGS,
    PERM_DELETE_DATAROOM,
]

ALL_SITE_PERMISSIONS: List[str] = [PERM_CREATE_DATAROOM]

ROLE_SLUG_VIEWER = 'viewer'
ROLE_SLUG_CONTRIBUTOR = 'contributor'
ROLE_SLUG_EDITOR = 'editor'
ROLE_SLUG_MANAGER = 'manager'

SYSTEM_ROLE_SLUGS = (
    ROLE_SLUG_VIEWER,
    ROLE_SLUG_CONTRIBUTOR,
    ROLE_SLUG_EDITOR,
    ROLE_SLUG_MANAGER,
)


@dataclass(frozen=True)
class PermissionDefinition:
    codename: str
    label: str
    supports_scope: bool
    category: str  # 'content' | 'collaboration' | 'dataroom' | 'site'


PERMISSION_DEFINITIONS: Dict[str, PermissionDefinition] = {
    PERM_VIEW: PermissionDefinition(PERM_VIEW, 'View content', False, 'content'),
    PERM_DOWNLOAD: PermissionDefinition(PERM_DOWNLOAD, 'Download files and folders', False, 'content'),
    PERM_UPLOAD: PermissionDefinition(PERM_UPLOAD, 'Upload files', False, 'content'),
    PERM_CREATE_FOLDER: PermissionDefinition(PERM_CREATE_FOLDER, 'Create folders', False, 'content'),
    PERM_RENAME: PermissionDefinition(PERM_RENAME, 'Rename items', True, 'content'),
    PERM_MOVE: PermissionDefinition(PERM_MOVE, 'Move items', True, 'content'),
    PERM_REORDER: PermissionDefinition(PERM_REORDER, 'Reorder items', True, 'content'),
    PERM_DELETE: PermissionDefinition(PERM_DELETE, 'Delete or remove items', True, 'content'),
    PERM_MANAGE_SHARE_SETTINGS: PermissionDefinition(
        PERM_MANAGE_SHARE_SETTINGS, 'Manage share link item settings', True, 'content'
    ),
    PERM_INVITE_COLLABORATORS: PermissionDefinition(
        PERM_INVITE_COLLABORATORS, 'Invite collaborators', False, 'collaboration'
    ),
    PERM_MANAGE_COLLABORATORS: PermissionDefinition(
        PERM_MANAGE_COLLABORATORS, 'Manage collaborators', False, 'collaboration'
    ),
    PERM_EDIT_DATAROOM_SETTINGS: PermissionDefinition(
        PERM_EDIT_DATAROOM_SETTINGS, 'Edit dataroom settings', False, 'dataroom'
    ),
    PERM_DELETE_DATAROOM: PermissionDefinition(
        PERM_DELETE_DATAROOM, 'Delete dataroom', False, 'dataroom'
    ),
    PERM_CREATE_DATAROOM: PermissionDefinition(
        PERM_CREATE_DATAROOM, 'Create datarooms', False, 'site'
    ),
}


def iter_dataroom_permission_definitions() -> Iterable[PermissionDefinition]:
    for codename in ALL_DATAROOM_PERMISSIONS:
        yield PERMISSION_DEFINITIONS[codename]


def default_grants_for_role_slug(slug: str) -> Dict[str, Optional[str]]:
    """
    Default permission matrix for seeded system roles.
    Values are scope (any/own) or None for non-scoped grants; missing key = denied.
    """
    if slug == ROLE_SLUG_VIEWER:
        return {PERM_VIEW: None, PERM_DOWNLOAD: None}
    if slug == ROLE_SLUG_CONTRIBUTOR:
        base = default_grants_for_role_slug(ROLE_SLUG_VIEWER)
        base.update({PERM_UPLOAD: None, PERM_CREATE_FOLDER: None})
        return base
    if slug == ROLE_SLUG_EDITOR:
        base = default_grants_for_role_slug(ROLE_SLUG_CONTRIBUTOR)
        for perm in MODIFY_PERMISSIONS:
            base[perm] = SCOPE_OWN
        return base
    if slug == ROLE_SLUG_MANAGER:
        grants = {perm: SCOPE_ANY for perm in ALL_DATAROOM_PERMISSIONS if perm != PERM_DELETE_DATAROOM}
        return grants
    return {}


DEFAULT_SITE_ROLE_GRANTS = {
    SITE_ROLE_ADMIN: {PERM_CREATE_DATAROOM: None},
    SITE_ROLE_MEMBER: {},
}
