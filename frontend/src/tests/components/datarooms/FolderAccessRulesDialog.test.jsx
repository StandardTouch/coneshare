import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import { FolderAccessRulesDialog } from '../../../components/datarooms/FolderAccessRulesDialog';
import * as api from '../../../services/api';

vi.mock('../../../services/api', () => ({
  getDataroomRoleOptions: vi.fn(),
  getFolderAccessRules: vi.fn(),
  setFolderAccessRule: vi.fn(),
}));

describe('FolderAccessRulesDialog', () => {
  const folder = { id: 'folder-1', name: 'Finance' };

  beforeEach(() => {
    api.getDataroomRoleOptions.mockResolvedValue({
      data: [{ id: 'role-viewer', name: 'Viewer', slug: 'viewer' }],
    });
    api.getFolderAccessRules.mockResolvedValue({
      data: [{ dataroom_role: 'role-viewer', rule: 'hidden' }],
    });
    api.setFolderAccessRule.mockResolvedValue({ data: {} });
  });

  it('loads roles and rules when opened', async () => {
    render(
      <FolderAccessRulesDialog
        isOpen
        onOpenChange={vi.fn()}
        dataroomId="room-1"
        folder={folder}
      />
    );

    await waitFor(() => {
      expect(api.getDataroomRoleOptions).toHaveBeenCalledWith('room-1');
      expect(api.getFolderAccessRules).toHaveBeenCalled();
    });

    expect(screen.getByText(/Folder access rules/i)).toBeInTheDocument();
    expect(screen.getByText('Viewer')).toBeInTheDocument();
  });

  it('saves rule changes', async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <FolderAccessRulesDialog
        isOpen
        onOpenChange={onOpenChange}
        dataroomId="room-1"
        folder={folder}
      />
    );

    await waitFor(() => expect(screen.getByText('Viewer')).toBeInTheDocument());

    await user.click(screen.getByRole('button', { name: /save/i }));

    await waitFor(() => {
      expect(api.setFolderAccessRule).toHaveBeenCalled();
    });
  });
});
