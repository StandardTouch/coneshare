import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { toast } from 'sonner';

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

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('../../utils/errorTranslator', () => ({
  getLocalizedErrorMessage: (err, fallback) =>
    err?.response?.data?.name?.[0] || fallback || 'error',
}));

describe('AdminRolesPage', () => {
  beforeEach(() => {
    api.getAdminRbacAuditLog.mockResolvedValue({ data: [] });
    api.getAdminRbacRoles.mockResolvedValue({
      data: {
        count: 1,
        current_page: 1,
        total_pages: 1,
        results: [
          {
            id: 'role-1',
            name: 'Viewer',
            slug: 'viewer',
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
    expect(screen.getByText('Viewer')).toBeInTheDocument();
  });

  it('shows API validation when create role fails', async () => {
    const user = userEvent.setup();
    api.createAdminRbacRole.mockRejectedValue({
      response: { data: { name: ['A role with this name already exists in your organization.'] } },
    });

    render(
      <MemoryRouter>
        <AdminRolesPage />
      </MemoryRouter>
    );
    await waitFor(() => expect(api.getAdminRbacRoles).toHaveBeenCalled());

    await user.click(screen.getByRole('button', { name: 'Create role' }));
    await user.type(screen.getByPlaceholderText(/name/i), 'Deal Analyst');
    await user.click(screen.getByRole('button', { name: /^Create$/i }));

    await waitFor(() => {
      expect(api.createAdminRbacRole).toHaveBeenCalledWith({
        name: 'Deal Analyst',
        description: '',
      });
    });
    expect(toast.error).toHaveBeenCalledWith(
      expect.stringMatching(/name already exists/i)
    );
  });
});
