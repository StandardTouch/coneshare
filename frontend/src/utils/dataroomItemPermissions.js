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

/**
 * Whether the current user may modify this dataroom list item (rename, move, star, link settings, etc.).
 * Prefer API-provided can_modify when present; otherwise derive from policy flags.
 */
export function canModifyDataroomItem({
  item,
  user,
  dataroom,
  collaboratorsOwnDeleteOnly = true,
}) {
  if (!item || !user || !dataroom) {
    return false;
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
  if (!collaboratorsOwnDeleteOnly) {
    return true;
  }
  return resolveItemCreatorId(item) === user.id;
}

export function selectionIncludesNonModifiableItems({
  allItems,
  selectedDocuments,
  selectedFolders,
  user,
  dataroom,
  collaboratorsOwnDeleteOnly,
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
      collaboratorsOwnDeleteOnly,
    });
  });
}

export function scopeIncludesNonModifiableItems({
  allItems,
  user,
  dataroom,
  collaboratorsOwnDeleteOnly,
}) {
  return allItems.some(
    (item) =>
      !canModifyDataroomItem({
        item,
        user,
        dataroom,
        collaboratorsOwnDeleteOnly,
      })
  );
}
