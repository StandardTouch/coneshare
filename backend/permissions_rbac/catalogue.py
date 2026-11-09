"""
Central catalogue of system and dataroom permissions.

Scoped permissions use ``any`` (all items in the dataroom) or ``own`` (items the user
created or uploaded). Non-scoped permissions ignore scope.

**File delete / move / reorder:** enforced with ``folder_delete`` and scoped rename
permissions — documents use ``file_rename`` / ``folder_delete`` (file delete does not
get a separate codename).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

SCOPE_ANY = 'any'
SCOPE_OWN = 'own'
SCOPE_CHOICES = (SCOPE_ANY, SCOPE_OWN)

SITE_ROLE_ADMIN = 'admin'
SITE_ROLE_MEMBER = 'member'

# --- System (per-role only; no site-wide toggle) ---
PERM_SYSTEM_API_KEYS = 'system_api_keys'
PERM_SYSTEM_FILE_REQUESTS = 'system_file_requests'
PERM_SYSTEM_DOCUMENTS = 'system_documents'
PERM_SYSTEM_SWAGGER = 'system_swagger'
PERM_SYSTEM_AUTOMATION = 'system_automation'
PERM_SYSTEM_TRASH = 'system_trash'
PERM_SYSTEM_SIGNATURE = 'system_signature'

ALL_SYSTEM_PERMISSIONS: List[str] = [
    PERM_SYSTEM_API_KEYS,
    PERM_SYSTEM_FILE_REQUESTS,
    PERM_SYSTEM_DOCUMENTS,
    PERM_SYSTEM_SWAGGER,
    PERM_SYSTEM_AUTOMATION,
    PERM_SYSTEM_TRASH,
    PERM_SYSTEM_SIGNATURE,
]

# --- Dataroom: global settings ---
PERM_DATAROOM_CREATE = 'dataroom_create'
PERM_DATAROOM_EDIT = 'dataroom_edit'
PERM_DATAROOM_DELETE = 'dataroom_delete'
PERM_DATAROOM_QNA_TAB = 'dataroom_qna_tab'
PERM_DATAROOM_SETTINGS_TAB = 'dataroom_settings_tab'
PERM_DATAROOM_SHARE = 'dataroom_share'

# --- Dataroom: folder ---
PERM_FOLDER_CREATE = 'folder_create'
PERM_FOLDER_RENAME = 'folder_rename'
PERM_FOLDER_DELETE = 'folder_delete'

# --- Dataroom: upload ---
PERM_UPLOAD_FILES = 'upload_files'
PERM_UPLOAD_FOLDER = 'upload_folder'
PERM_UPLOAD_ADD_FROM_CONTENT = 'upload_add_from_content'

# --- Dataroom: file ---
PERM_FILE_VIEW = 'file_view'
PERM_FILE_DOWNLOAD = 'file_download'
PERM_FILE_RENAME = 'file_rename'
PERM_FILE_CREATE_SHARE_LINK = 'file_create_share_link'

# Legacy aliases (runtime action names used across the codebase)
PERM_VIEW = PERM_FILE_VIEW
PERM_DOWNLOAD = PERM_FILE_DOWNLOAD
PERM_UPLOAD = PERM_UPLOAD_FILES
PERM_CREATE_FOLDER = PERM_FOLDER_CREATE
PERM_RENAME = 'rename'  # resolved to file/folder rename in services
PERM_MOVE = 'move'
PERM_REORDER = 'reorder'
PERM_DELETE = 'delete'  # resolved to folder_delete in services
PERM_MANAGE_SHARE_SETTINGS = PERM_FILE_CREATE_SHARE_LINK
PERM_EDIT_DATAROOM_SETTINGS = PERM_DATAROOM_SETTINGS_TAB
PERM_DELETE_DATAROOM = PERM_DATAROOM_DELETE
PERM_CREATE_DATAROOM = PERM_DATAROOM_CREATE
PERM_INVITE_COLLABORATORS = '_removed_invite_collaborators'
PERM_MANAGE_COLLABORATORS = '_removed_manage_collaborators'

ALL_DATAROOM_PERMISSIONS: List[str] = [
    PERM_DATAROOM_CREATE,
    PERM_DATAROOM_EDIT,
    PERM_DATAROOM_DELETE,
    PERM_DATAROOM_QNA_TAB,
    PERM_DATAROOM_SETTINGS_TAB,
    PERM_DATAROOM_SHARE,
    PERM_FOLDER_CREATE,
    PERM_FOLDER_RENAME,
    PERM_FOLDER_DELETE,
    PERM_UPLOAD_FILES,
    PERM_UPLOAD_FOLDER,
    PERM_UPLOAD_ADD_FROM_CONTENT,
    PERM_FILE_VIEW,
    PERM_FILE_DOWNLOAD,
    PERM_FILE_RENAME,
    PERM_FILE_CREATE_SHARE_LINK,
]

ALL_ROLE_GRANT_PERMISSIONS: List[str] = ALL_SYSTEM_PERMISSIONS + ALL_DATAROOM_PERMISSIONS

ROLE_SLUG_ADMIN = 'admin'
ROLE_SLUG_MANAGER = 'manager'

# Deprecated slugs removed in migration
ROLE_SLUG_VIEWER = 'viewer'
ROLE_SLUG_CONTRIBUTOR = 'contributor'
ROLE_SLUG_EDITOR = 'editor'

SYSTEM_ROLE_SLUGS = (
    ROLE_SLUG_ADMIN,
    ROLE_SLUG_MANAGER,
)

SCOPED_DATAROOM_PERMISSIONS: Set[str] = {
    PERM_DATAROOM_EDIT,
    PERM_DATAROOM_DELETE,
    PERM_FOLDER_RENAME,
    PERM_FOLDER_DELETE,
    PERM_FILE_RENAME,
    PERM_FILE_VIEW,
}

MODIFY_PERMISSIONS: Set[str] = {
    PERM_FOLDER_RENAME,
    PERM_FOLDER_DELETE,
    PERM_FILE_RENAME,
    PERM_FILE_CREATE_SHARE_LINK,
}

# AppConfiguration / feature-toggle keys retired (enforced per-role instead)
RETIRED_GLOBAL_FEATURE_KEYS = (
    'AUTOMATION_ENABLED',
    'API_KEYS_ENABLED',
    'FILE_REQUESTS_ENABLED',
    'SWAGGER_ENABLED',
    'ESIGN_ENABLED',
    'ROLE_LABELS_ENABLED',
    'MCP_ENABLED',
)

# Old codename -> new codename(s) for data migration
LEGACY_PERMISSION_MAP: Dict[str, List[str]] = {
    'view': [PERM_FILE_VIEW],
    'download': [PERM_FILE_DOWNLOAD],
    'upload': [PERM_UPLOAD_FILES, PERM_UPLOAD_FOLDER, PERM_UPLOAD_ADD_FROM_CONTENT],
    'create_folder': [PERM_FOLDER_CREATE],
    'rename': [PERM_FOLDER_RENAME, PERM_FILE_RENAME],
    'move': [PERM_FOLDER_RENAME, PERM_FILE_RENAME],
    'reorder': [PERM_FOLDER_RENAME, PERM_FILE_RENAME],
    'delete': [PERM_FOLDER_DELETE],
    'manage_share_settings': [PERM_FILE_CREATE_SHARE_LINK],
    'edit_dataroom_settings': [PERM_DATAROOM_SETTINGS_TAB, PERM_DATAROOM_EDIT],
    'delete_dataroom': [PERM_DATAROOM_DELETE],
    'create_dataroom': [PERM_DATAROOM_CREATE],
    'invite_collaborators': [],
    'manage_collaborators': [],
}


@dataclass(frozen=True)
class PermissionDefinition:
    codename: str
    label: str
    supports_scope: bool
    category: str
    group: str


PERMISSION_DEFINITIONS: Dict[str, PermissionDefinition] = {
    PERM_SYSTEM_API_KEYS: PermissionDefinition(
        PERM_SYSTEM_API_KEYS, 'API Keys (incl. MCP)', False, 'system', 'System'
    ),
    PERM_SYSTEM_FILE_REQUESTS: PermissionDefinition(
        PERM_SYSTEM_FILE_REQUESTS, 'File Requests (incl. public upload links)', False, 'system', 'System'
    ),
    PERM_SYSTEM_DOCUMENTS: PermissionDefinition(PERM_SYSTEM_DOCUMENTS, 'Documents', False, 'system', 'System'),
    PERM_SYSTEM_SWAGGER: PermissionDefinition(
        PERM_SYSTEM_SWAGGER, 'Swagger Documentation', False, 'system', 'System'
    ),
    PERM_SYSTEM_AUTOMATION: PermissionDefinition(PERM_SYSTEM_AUTOMATION, 'Automation', False, 'system', 'System'),
    PERM_SYSTEM_TRASH: PermissionDefinition(PERM_SYSTEM_TRASH, 'Trash', False, 'system', 'System'),
    PERM_SYSTEM_SIGNATURE: PermissionDefinition(PERM_SYSTEM_SIGNATURE, 'Signature', False, 'system', 'System'),
    PERM_DATAROOM_CREATE: PermissionDefinition(
        PERM_DATAROOM_CREATE, 'Create', False, 'dataroom_global', 'Datarooms — Global Settings'
    ),
    PERM_DATAROOM_EDIT: PermissionDefinition(
        PERM_DATAROOM_EDIT, 'Edit', True, 'dataroom_global', 'Datarooms — Global Settings'
    ),
    PERM_DATAROOM_DELETE: PermissionDefinition(
        PERM_DATAROOM_DELETE, 'Delete', True, 'dataroom_global', 'Datarooms — Global Settings'
    ),
    PERM_DATAROOM_QNA_TAB: PermissionDefinition(
        PERM_DATAROOM_QNA_TAB, 'Q&A Tab', False, 'dataroom_global', 'Datarooms — Global Settings'
    ),
    PERM_DATAROOM_SETTINGS_TAB: PermissionDefinition(
        PERM_DATAROOM_SETTINGS_TAB, 'Settings Tab', False, 'dataroom_global', 'Datarooms — Global Settings'
    ),
    PERM_DATAROOM_SHARE: PermissionDefinition(
        PERM_DATAROOM_SHARE, 'Share', False, 'dataroom_global', 'Datarooms — Global Settings'
    ),
    PERM_FOLDER_CREATE: PermissionDefinition(
        PERM_FOLDER_CREATE, 'Create', False, 'dataroom_folder', 'Datarooms — Folder'
    ),
    PERM_FOLDER_RENAME: PermissionDefinition(
        PERM_FOLDER_RENAME, 'Rename', True, 'dataroom_folder', 'Datarooms — Folder'
    ),
    PERM_FOLDER_DELETE: PermissionDefinition(
        PERM_FOLDER_DELETE, 'Delete', True, 'dataroom_folder', 'Datarooms — Folder'
    ),
    PERM_UPLOAD_FILES: PermissionDefinition(
        PERM_UPLOAD_FILES, 'Files', False, 'dataroom_upload', 'Datarooms — Upload'
    ),
    PERM_UPLOAD_FOLDER: PermissionDefinition(
        PERM_UPLOAD_FOLDER, 'Folder', False, 'dataroom_upload', 'Datarooms — Upload'
    ),
    PERM_UPLOAD_ADD_FROM_CONTENT: PermissionDefinition(
        PERM_UPLOAD_ADD_FROM_CONTENT, 'Add From Content', False, 'dataroom_upload', 'Datarooms — Upload'
    ),
    PERM_FILE_VIEW: PermissionDefinition(PERM_FILE_VIEW, 'View', True, 'dataroom_file', 'Datarooms — File Permission'),
    PERM_FILE_DOWNLOAD: PermissionDefinition(
        PERM_FILE_DOWNLOAD, 'Download', False, 'dataroom_file', 'Datarooms — File Permission'
    ),
    PERM_FILE_RENAME: PermissionDefinition(
        PERM_FILE_RENAME, 'Rename', True, 'dataroom_file', 'Datarooms — File Permission'
    ),
    PERM_FILE_CREATE_SHARE_LINK: PermissionDefinition(
        PERM_FILE_CREATE_SHARE_LINK, 'Create Share Link', False, 'dataroom_file', 'Datarooms — File Permission'
    ),
}


def iter_role_grant_permission_definitions() -> Iterable[PermissionDefinition]:
    for codename in ALL_ROLE_GRANT_PERMISSIONS:
        yield PERMISSION_DEFINITIONS[codename]


def iter_dataroom_permission_definitions() -> Iterable[PermissionDefinition]:
    for codename in ALL_DATAROOM_PERMISSIONS:
        yield PERMISSION_DEFINITIONS[codename]


def _all_grants_any() -> Dict[str, Optional[str]]:
    grants: Dict[str, Optional[str]] = {}
    for perm in ALL_ROLE_GRANT_PERMISSIONS:
        if perm in SCOPED_DATAROOM_PERMISSIONS:
            grants[perm] = SCOPE_ANY
        else:
            grants[perm] = None
    return grants


def default_grants_for_role_slug(slug: str) -> Dict[str, Optional[str]]:
    if slug == ROLE_SLUG_ADMIN:
        return _all_grants_any()
    if slug == ROLE_SLUG_MANAGER:
        grants = _all_grants_any()
        # Manager defaults: full dataroom access but no system administration unless granted
        for perm in ALL_SYSTEM_PERMISSIONS:
            grants.pop(perm, None)
        return grants
    return {}


# Legacy site-role table (unused; creation is granted on org roles).
ALL_SITE_PERMISSIONS: List[str] = []

DEFAULT_SITE_ROLE_GRANTS = {
    SITE_ROLE_ADMIN: {},
    SITE_ROLE_MEMBER: {},
}
