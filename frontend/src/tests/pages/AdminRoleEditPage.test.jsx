import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { AdminRoleEditPage } from '../../pages/AdminRoleEditPage';
import * as api from '../../services/api';

vi.mock('../../services/api', () => ({
  getAdminRbacRole: vi.fn(),
  getAdminRbacPermissionCatalog: vi.fn(),
  updateAdminRbacRole: vi.fn(),
  updateAdminRbacRolePermissions: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key, opts) => opts?.defaultValue || key }),
}));

describe('AdminRoleEditPage', () => {
  beforeEach(() => {
    api.getAdminRbacRole.mockResolvedValue({
      data: {
        id: 'role-1',
        name: 'Contributor',
        slug: 'contributor',
        is_system: true,
        permission_grants: [{ permission: 'view', scope: '' }],
      },
    });
    api.getAdminRbacPermissionCatalog.mockResolvedValue({
      data: {
        permissions: [
          { codename: 'view', label: 'View content', supports_scope: false, category: 'content' },
        ],
      },
    });
  });

  it('loads role edit view', async () => {
    render(
      <MemoryRouter initialEntries={['/admin/roles/role-1']}>
        <Routes>
          <Route path="/admin/roles/:roleId" element={<AdminRoleEditPage />} />
        </Routes>
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(api.getAdminRbacRole).toHaveBeenCalledWith('role-1');
    });
    expect(screen.getByRole('heading', { name: 'Contributor' })).toBeInTheDocument();
    expect(screen.getByText('View content')).toBeInTheDocument();
  });
});
