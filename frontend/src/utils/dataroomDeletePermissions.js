import { isDataroomCollaborator, isDataroomOwner } from './formatters';

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

export function canRemoveDataroomItem({
  item,
  user,
  dataroom,
  collaboratorsOwnDeleteOnly = true,
}) {
  if (!item || !user || !dataroom) {
    return false;
  }
  if (item.permissions && typeof item.permissions.can_delete === 'boolean') {
    return item.permissions.can_delete;
  }
  if (typeof item.can_delete === 'boolean') {
    return item.can_delete;
  }
  if (typeof item.can_modify === 'boolean') {
    return item.can_modify;
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

export function selectionIncludesNonDeletableItems({
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
    return !canRemoveDataroomItem({
      item,
      user,
      dataroom,
      collaboratorsOwnDeleteOnly,
    });
  });
}
