import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import { AdminRolesPage } from '../../pages/AdminRolesPage';
import * as api from '../../services/api';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock('../../utils/errorTranslator', () => ({
  getLocalizedErrorMessage: () => null,
}));

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
    mockNavigate.mockReset();
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

  it('creates a role and navigates to edit page', async () => {
    const user = userEvent.setup();
    api.createAdminRbacRole.mockResolvedValue({
      data: { id: 'role-new', name: 'Analyst', slug: 'analyst', is_system: false },
    });

    render(
      <MemoryRouter>
        <AdminRolesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Create role' }));
    await user.type(screen.getByPlaceholderText('Name'), 'Analyst');
    await user.type(screen.getByPlaceholderText('Description'), 'Read-only analysts');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => {
      expect(api.createAdminRbacRole).toHaveBeenCalledWith({
        name: 'Analyst',
        description: 'Read-only analysts',
      });
    });
    expect(mockNavigate).toHaveBeenCalledWith('/admin/roles/role-new');
  });

  it('shows inline validation error from API', async () => {
    const user = userEvent.setup();
    api.createAdminRbacRole.mockRejectedValue({
      response: { data: { name: ['A role with this name already exists.'] } },
    });

    render(
      <MemoryRouter>
        <AdminRolesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Create role' }));
    await user.type(screen.getByPlaceholderText('Name'), 'Duplicate');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('A role with this name already exists.');
    });
  });

  it('does not show stale Member-role subtitle copy', async () => {
    render(
      <MemoryRouter>
        <AdminRolesPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
    });

    expect(screen.queryByText(/display labels only/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Manage organization roles and permissions/i)).toBeInTheDocument();
  });
});
