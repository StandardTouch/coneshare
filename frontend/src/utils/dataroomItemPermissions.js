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

export function canUploadToDataroom({ dataroom, user, folderItem }) {
  if (!user || !dataroom) return false;
  if (folderItem?.permissions && typeof folderItem.permissions.can_upload === 'boolean') {
    return folderItem.permissions.can_upload;
  }
  if (dataroom.current_user_permissions && typeof dataroom.current_user_permissions.can_upload === 'boolean') {
    return dataroom.current_user_permissions.can_upload;
  }
  return isDataroomOwner(dataroom, user) || user.role === 'admin' || isDataroomCollaborator(dataroom, user);
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
