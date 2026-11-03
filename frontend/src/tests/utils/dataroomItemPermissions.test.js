import { describe, it, expect } from 'vitest';
import {
  canModifyDataroomItem,
  selectionIncludesNonModifiableItems,
  scopeIncludesNonModifiableItems,
} from '../../utils/dataroomItemPermissions';

const dataroom = { id: 'dr1', created_by: { id: 'owner1' } };
const owner = { id: 'owner1', role: 'member' };
const collab = { id: 'collab1', role: 'member' };
const admin = { id: 'admin1', role: 'admin' };

describe('dataroomItemPermissions', () => {
  it('respects API can_modify when provided', () => {
    expect(
      canModifyDataroomItem({
        item: { id: '1', type: 'document', can_modify: false },
        user: collab,
        dataroom: { ...dataroom, collaborators: [{ user: collab }] },
      })
    ).toBe(false);
  });

  it('allows owner to modify any item', () => {
    expect(
      canModifyDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'other' } },
        user: owner,
        dataroom,
      })
    ).toBe(true);
  });

  it('blocks collaborator from modifying others items when policy is on', () => {
    expect(
      canModifyDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'owner1' } },
        user: collab,
        dataroom: { ...dataroom, collaborators: [{ user: collab }] },
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(false);
  });

  it('allows collaborator to modify own items', () => {
    expect(
      canModifyDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'collab1' } },
        user: collab,
        dataroom: { ...dataroom, collaborators: [{ user: collab }] },
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(true);
  });

  it('allows admin to modify any item', () => {
    expect(
      canModifyDataroomItem({
        item: { id: '1', type: 'document', created_by: { id: 'owner1' } },
        user: admin,
        dataroom,
      })
    ).toBe(true);
  });

  it('detects bulk selection with non-modifiable items', () => {
    const allItems = [
      { id: 'd1', type: 'document', can_modify: true },
      { id: 'd2', type: 'document', can_modify: false },
    ];
    expect(
      selectionIncludesNonModifiableItems({
        allItems,
        selectedDocuments: ['d1', 'd2'],
        selectedFolders: [],
        user: collab,
        dataroom,
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(true);
  });

  it('detects reorder scope with foreign items', () => {
    const allItems = [
      { id: 'd1', type: 'document', can_modify: true },
      { id: 'd2', type: 'document', can_modify: false },
    ];
    expect(
      scopeIncludesNonModifiableItems({
        allItems,
        user: collab,
        dataroom,
        collaboratorsOwnDeleteOnly: true,
      })
    ).toBe(true);
  });
});
