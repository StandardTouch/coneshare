import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import SidebarFooter from '../../components/layout/SidebarFooter';

vi.mock('../../contexts/UserProvider', () => ({
  useUser: vi.fn(),
}));

vi.mock('../../featuregates/useFeatureGates', () => ({
  useFeatureGates: vi.fn(),
}));

vi.mock('../../components/layout/SidebarProvider', () => ({
  useSidebar: () => ({ isCollapsed: false }),
}));

vi.mock('../../components/layout/NavUser', () => ({
  default: () => <div data-testid="nav-user" />,
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key) => (key === 'nav.apiDocs' ? 'API Docs (Swagger)' : key) }),
}));

import { useUser } from '../../contexts/UserProvider';
import { useFeatureGates } from '../../featuregates/useFeatureGates';

describe('SidebarFooter API docs link', () => {
  beforeEach(() => {
    useUser.mockReturnValue({
      user: { role: 'admin', file_size_quota_mb: 0, total_document_size: 0 },
    });
  });

  it('shows link for admin when swagger enabled', () => {
    useFeatureGates.mockReturnValue({ canAccessApiDocs: true });
    render(
      <MemoryRouter>
        <SidebarFooter />
      </MemoryRouter>
    );
    expect(screen.getByText('API Docs (Swagger)')).toBeInTheDocument();
  });

  it('hides link when swagger disabled', () => {
    useFeatureGates.mockReturnValue({ canAccessApiDocs: false });
    render(
      <MemoryRouter>
        <SidebarFooter />
      </MemoryRouter>
    );
    expect(screen.queryByText('API Docs (Swagger)')).not.toBeInTheDocument();
  });
});
