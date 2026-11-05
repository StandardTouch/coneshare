import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import { AdminRbacPage } from '../../pages/AdminRbacPage';
import * as api from '../../services/api';
import '../../i18n';

vi.mock('../../services/api', () => ({
  getAdminRbacMatrix: vi.fn(),
  updateAdminRbacRolePermissions: vi.fn(),
  resetAdminRbacDefaults: vi.fn(),
  getAdminRbacAuditLog: vi.fn(),
  updateAdminSitePermissions: vi.fn(),
}));

vi.mock('../../contexts/BrandingProvider', () => ({
  useBranding: () => ({ roleLabelsEnabled: false }),
}));

describe('AdminRbacPage', () => {
  beforeEach(() => {
    api.getAdminRbacAuditLog.mockResolvedValue({ data: [] });
    api.getAdminRbacMatrix.mockResolvedValue({
      data: {
        permissions: [{ codename: 'view', label: 'View content', supports_scope: false, category: 'content' }],
        roles: [
          {
            id: 'role-1',
            slug: 'editor',
            name: 'Editor',
            is_system: true,
            permission_grants: [{ permission: 'view', scope: '' }],
          },
        ],
        site_permissions: { admin: ['create_dataroom'], member: [] },
        role_labels_note: 'Labels are display-only.',
      },
    });
  });

  it('renders permission matrix from admin API', async () => {
    render(
      <MemoryRouter>
        <AdminRbacPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(api.getAdminRbacMatrix).toHaveBeenCalled();
    });

    expect(screen.getByRole('heading', { name: 'Roles & Permissions' })).toBeInTheDocument();
    expect(screen.getByText('Editor')).toBeInTheDocument();
    expect(screen.getByText('View content')).toBeInTheDocument();
    expect(screen.getByText('Audit log')).toBeInTheDocument();
  });
});
