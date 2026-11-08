import { describe, it, expect } from 'vitest';
import {
  canAddContentToDataroom,
  canCreateFolderInDataroom,
  canShowDataroomUploadDropdown,
  canUploadFilesToDataroom,
  canUploadFolderToDataroom,
} from '../../utils/dataroomItemPermissions';

const user = { id: 'u1', role: 'member' };

const dataroomWithPerms = (permissions) => ({
  id: 'dr1',
  created_by: { id: 'owner' },
  current_user_permissions: permissions,
});

describe('dataroomItemPermissions granular upload', () => {
  it('maps each UI action to its own permission flag', () => {
    const dataroom = dataroomWithPerms({
      can_upload_files: true,
      can_upload_folder: false,
      can_upload_add_from_content: false,
      can_create_folder: false,
    });
    const ctx = { dataroom, user, folderItem: null };

    expect(canUploadFilesToDataroom(ctx)).toBe(true);
    expect(canUploadFolderToDataroom(ctx)).toBe(false);
    expect(canAddContentToDataroom(ctx)).toBe(false);
    expect(canCreateFolderInDataroom(ctx)).toBe(false);
    expect(canShowDataroomUploadDropdown(ctx)).toBe(true);
  });

  it('hides upload dropdown when both file and folder upload are denied', () => {
    const dataroom = dataroomWithPerms({
      can_upload_files: false,
      can_upload_folder: false,
      can_upload_add_from_content: true,
      can_create_folder: true,
    });
    const ctx = { dataroom, user, folderItem: null };

    expect(canShowDataroomUploadDropdown(ctx)).toBe(false);
    expect(canAddContentToDataroom(ctx)).toBe(true);
    expect(canCreateFolderInDataroom(ctx)).toBe(true);
  });

  it('shows folder upload option only when upload_folder is granted', () => {
    const dataroom = dataroomWithPerms({
      can_upload_files: false,
      can_upload_folder: true,
      can_upload_add_from_content: false,
      can_create_folder: false,
    });
    const ctx = { dataroom, user, folderItem: null };

    expect(canUploadFilesToDataroom(ctx)).toBe(false);
    expect(canUploadFolderToDataroom(ctx)).toBe(true);
    expect(canShowDataroomUploadDropdown(ctx)).toBe(true);
  });
});
