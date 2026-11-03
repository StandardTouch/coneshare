import { describe, it, expect } from 'vitest';
import {
  canRemoveDataroomItem,
  selectionIncludesNonDeletableItems,
} from '../../utils/dataroomDeletePermissions';

const dataroom = { id: 'dr1', created_by: { id: 'owner1' } };
const owner = { id: 'owner1', role: 'member' };
const collab = { id: 'collab1', role: 'member' };
const admin = { id: 'admin1', role: 'admin' };

describe('dataroomDeletePermissions', () => {
  it('respects API can_delete when provided', () => {
    expect(
      canRemoveDataroomItem({
        item: { id: '1', type: 'document', can_delete: false },
        user: collab,
        dataroom: { ...dataroom, current_user_role: 'collaborator' },
      })
    ).toBe(false);
  });

  it('allows owner to remove any item when policy is on', () => {
    expect(
      canRemoveDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'collab1' } },
        user: owner,
        dataroom,
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(true);
  });

  it('blocks collaborator from removing owner item when policy is on', () => {
    expect(
      canRemoveDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'owner1' } },
        user: collab,
        dataroom: { ...dataroom, collaborators: [{ user: { id: 'collab1' } }] },
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(false);
  });

  it('allows collaborator to remove own item when policy is on', () => {
    expect(
      canRemoveDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'collab1' } },
        user: collab,
        dataroom: { ...dataroom, collaborators: [{ user: { id: 'collab1' } }] },
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(true);
  });

  it('allows org admin regardless of uploader', () => {
    expect(
      canRemoveDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'owner1' } },
        user: admin,
        dataroom,
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(true);
  });

  it('restores permissive behaviour for collaborators when policy is off', () => {
    expect(
      canRemoveDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'owner1' } },
        user: collab,
        dataroom: { ...dataroom, collaborators: [{ user: { id: 'collab1' } }] },
        collaboratorsOwnDeleteOnly: false,
      })
    ).toBe(true);
  });

  it('detects mixed bulk selection with a non-deletable item', () => {
    const allItems = [
      { id: 'd1', type: 'document', can_delete: true },
      { id: 'd2', type: 'document', can_delete: false },
    ];
    expect(
      selectionIncludesNonDeletableItems({
        allItems,
        selectedDocuments: ['d1', 'd2'],
        selectedFolders: [],
        user: collab,
        dataroom,
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(true);
  });
});
