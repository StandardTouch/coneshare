import { isDataroomCollaborator, isDataroomOwner } from './formatters';

export {
  canRemoveDataroomItem,
  selectionIncludesNonDeletableItems,
} from './dataroomDeletePermissions';

export function resolveItemCreatorId(item) {
  if (!item) return null;
  if (item.created_by && typeof item.created_by === 'object') {
    return item.created_by.id ?? null;
  }
  if (typeof item.created_by === 'string') {
    return item.created_by;
  }
  return null;
}

function perm(item, key) {
  if (item?.permissions && typeof item.permissions[key] === 'boolean') {
    return item.permissions[key];
  }
  return undefined;
}

function roomPerm(dataroom, key) {
  if (dataroom?.current_user_permissions && typeof dataroom.current_user_permissions[key] === 'boolean') {
    return dataroom.current_user_permissions[key];
  }
  return undefined;
}

function roomHasGranularUploadPerms(dataroom) {
  const perms = dataroom?.current_user_permissions;
  if (!perms || typeof perms !== 'object') {
    return false;
  }
  return (
    'can_upload_files' in perms
    || 'can_upload_folder' in perms
    || 'can_upload_add_from_content' in perms
    || 'can_create_folder' in perms
  );
}

function legacyCollaboratorUploadAccess({ dataroom, user }) {
  return (
    isDataroomOwner(dataroom, user)
    || user.role === 'admin'
    || isDataroomCollaborator(dataroom, user)
  );
}

function resolveDataroomPerm({ dataroom, user, folderItem, key }) {
  if (!user || !dataroom) return false;
  const fromFolder = folderItem ? perm(folderItem, key) : undefined;
  if (typeof fromFolder === 'boolean') {
    return fromFolder;
  }
  const fromRoom = roomPerm(dataroom, key);
  if (typeof fromRoom === 'boolean') {
    return fromRoom;
  }

  const granularMode = roomHasGranularUploadPerms(dataroom);
  if (granularMode) {
    return false;
  }

  const legacyUpload = folderItem ? perm(folderItem, 'can_upload') : roomPerm(dataroom, 'can_upload');
  if (typeof legacyUpload === 'boolean') {
    if (
      key === 'can_upload_files'
      || key === 'can_upload_folder'
      || key === 'can_upload_add_from_content'
    ) {
      return legacyUpload;
    }
    if (key === 'can_create_folder') {
      return legacyUpload;
    }
  }

  return legacyCollaboratorUploadAccess({ dataroom, user });
}

export function canModifyDataroomItem({ item, user, dataroom }) {
  if (!item || !user || !dataroom) {
    return false;
  }
  const fromPermissions = perm(item, 'can_modify') ?? perm(item, 'can_rename');
  if (typeof fromPermissions === 'boolean') {
    return fromPermissions;
  }
  if (typeof item.can_modify === 'boolean') {
    return item.can_modify;
  }
  if (typeof item.can_delete === 'boolean') {
    return item.can_delete;
  }
  if (isDataroomOwner(dataroom, user) || user.role === 'admin') {
    return true;
  }
  if (!isDataroomCollaborator(dataroom, user)) {
    return false;
  }
  return resolveItemCreatorId(item) === user.id;
}

/** @deprecated Use canUploadFilesToDataroom or specific upload helpers. */
export function canUploadToDataroom({ dataroom, user, folderItem }) {
  return canUploadFilesToDataroom({ dataroom, user, folderItem });
}

export function canUploadFilesToDataroom({ dataroom, user, folderItem }) {
  return resolveDataroomPerm({ dataroom, user, folderItem, key: 'can_upload_files' });
}

export function canUploadFolderToDataroom({ dataroom, user, folderItem }) {
  return resolveDataroomPerm({ dataroom, user, folderItem, key: 'can_upload_folder' });
}

export function canAddContentToDataroom({ dataroom, user, folderItem }) {
  return resolveDataroomPerm({ dataroom, user, folderItem, key: 'can_upload_add_from_content' });
}

export function canCreateFolderInDataroom({ dataroom, user, folderItem }) {
  return resolveDataroomPerm({ dataroom, user, folderItem, key: 'can_create_folder' });
}

export function canShowDataroomUploadDropdown({ dataroom, user, folderItem }) {
  return (
    canUploadFilesToDataroom({ dataroom, user, folderItem })
    || canUploadFolderToDataroom({ dataroom, user, folderItem })
  );
}

export function canShowDataroomDocumentsToolbar({ dataroom, user, folderItem }) {
  return (
    canShowDataroomUploadDropdown({ dataroom, user, folderItem })
    || canAddContentToDataroom({ dataroom, user, folderItem })
    || canCreateFolderInDataroom({ dataroom, user, folderItem })
  );
}

export function selectionIncludesNonModifiableItems({
  allItems,
  selectedDocuments,
  selectedFolders,
  user,
  dataroom,
}) {
  const selectedKeys = new Set([
    ...selectedDocuments.map((id) => `document:${id}`),
    ...selectedFolders.map((id) => `folder:${id}`),
  ]);
  return allItems.some((item) => {
    const key = `${item.type}:${item.id}`;
    if (!selectedKeys.has(key)) return false;
    return !canModifyDataroomItem({
      item,
      user,
      dataroom,
    });
  });
}

export function scopeIncludesNonModifiableItems({ allItems, user, dataroom }) {
  return allItems.some(
    (item) =>
      !canModifyDataroomItem({
        item,
        user,
        dataroom,
      })
  );
}
