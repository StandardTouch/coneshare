import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { AdminRolesPage } from '../../pages/AdminRolesPage';
import * as api from '../../services/api';

vi.mock('../../services/api', () => ({
  getAdminRbacRoles: vi.fn(),
  getAdminRbacAuditLog: vi.fn(),
  resetAdminRbacDefaults: vi.fn(),
  createAdminRbacRole: vi.fn(),
  deleteAdminRbacRole: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key, opts) => opts?.defaultValue || key }),
}));

vi.mock('../../contexts/BrandingProvider', () => ({
  useBranding: () => ({ roleLabelsEnabled: true }),
}));

describe('AdminRolesPage', () => {
  beforeEach(() => {
    api.getAdminRbacAuditLog.mockResolvedValue({ data: [] });
    api.getAdminRbacRoles.mockResolvedValue({
      data: {
        count: 2,
        current_page: 1,
        total_pages: 1,
        results: [
          {
            id: 'role-admin',
            name: 'Admin',
            slug: 'admin',
            description: 'Full access',
            is_system: true,
            user_count: 1,
            permission_grants: [],
          },
          {
            id: 'role-manager',
            name: 'Manager',
            slug: 'manager',
            description: '',
            is_system: true,
            user_count: 2,
            permission_grants: [],
          },
        ],
      },
    });
  });

  it('renders unified roles list', async () => {
    render(
      <MemoryRouter>
        <AdminRolesPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(api.getAdminRbacRoles).toHaveBeenCalled();
    });
    expect(screen.getByRole('heading', { name: 'Roles' })).toBeInTheDocument();
    expect(screen.getByText('Admin')).toBeInTheDocument();
    expect(screen.getByText('Manager')).toBeInTheDocument();
  });

  it('shows edit control for system roles', async () => {
    render(
      <MemoryRouter>
        <AdminRolesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });

    const adminRow = screen.getByText('Admin').closest('tr');
    expect(adminRow.querySelector('a[href="/admin/roles/role-admin"]')).toBeTruthy();

    const managerRow = screen.getByText('Manager').closest('tr');
    expect(managerRow.querySelector('a[href="/admin/roles/role-manager"]')).toBeTruthy();
  });
});
