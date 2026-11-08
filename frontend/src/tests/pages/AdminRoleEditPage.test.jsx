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
          {
            codename: 'system_documents',
            label: 'Documents',
            supports_scope: false,
            category: 'system',
            group: 'System',
          },
          {
            codename: 'dataroom_create',
            label: 'Create',
            supports_scope: false,
            category: 'dataroom_global',
            group: 'Datarooms — Global Settings',
          },
          {
            codename: 'legacy_view',
            label: 'Legacy view',
            supports_scope: false,
            category: 'content',
          },
          {
            codename: 'file_view',
            label: 'View',
            supports_scope: true,
            category: 'dataroom_file',
            group: 'Datarooms — File Permission',
          },
          {
            codename: 'file_rename',
            label: 'Rename',
            supports_scope: true,
            category: 'dataroom_file',
            group: 'Datarooms — File Permission',
          },
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
    expect(screen.getByText('Documents')).toBeInTheDocument();
  });

  it('groups permissions by catalogue group with category fallback', async () => {
    render(
      <MemoryRouter initialEntries={['/admin/roles/role-1']}>
        <Routes>
          <Route path="/admin/roles/:roleId" element={<AdminRoleEditPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'System' })).toBeInTheDocument();
    });
    expect(screen.getByRole('heading', { name: 'Datarooms — Global Settings' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'content' })).toBeInTheDocument();
  });

  it('shows own/any scope selector for file_view when enabled', async () => {
    api.getAdminRbacRole.mockResolvedValue({
      data: {
        id: 'role-1',
        name: 'Contributor',
        slug: 'contributor',
        is_system: true,
        permission_grants: [{ permission: 'file_view', scope: 'any' }],
      },
    });

    render(
      <MemoryRouter initialEntries={['/admin/roles/role-1']}>
        <Routes>
          <Route path="/admin/roles/:roleId" element={<AdminRoleEditPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('file_view')).toBeInTheDocument();
    });

    const scopeSelect = screen.getByDisplayValue('Any');
    expect(scopeSelect).toBeInTheDocument();
    expect(scopeSelect.querySelectorAll('option').length).toBeGreaterThanOrEqual(2);
  });
});
