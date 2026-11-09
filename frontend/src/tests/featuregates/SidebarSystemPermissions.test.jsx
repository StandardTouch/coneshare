import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { useNavItems } from '../../components/layout/SidebarContent';

vi.mock('../../featuregates/useFeatureGates', () => ({
  useFeatureGates: vi.fn(),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => {
      const labels = {
        'nav.dashboard': 'Dashboard',
        'nav.documents': 'Documents',
        'nav.datarooms': 'Datarooms',
        'nav.fileRequests': 'File Requests',
        'nav.signatures': 'Signatures',
        'nav.automations': 'Automations',
        'nav.trash': 'Trash',
      };
      return labels[key] || key;
    },
  }),
}));

import { useFeatureGates } from '../../featuregates/useFeatureGates';

function NavProbe() {
  const items = useNavItems();
  return (
    <ul>
      {items.map((item) => (
        <li key={item.href}>{item.label}</li>
      ))}
    </ul>
  );
}

describe('Sidebar system permission visibility', () => {
  beforeEach(() => {
    useFeatureGates.mockReturnValue({
      canAccessFileRequests: false,
      canAccessAutomations: false,
      canAccessDocuments: false,
      canAccessTrash: false,
      canAccessSignatures: false,
    });
  });

  it('hides gated nav items when all system permissions are off', () => {
    render(
      <MemoryRouter>
        <NavProbe />
      </MemoryRouter>
    );
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Datarooms')).toBeInTheDocument();
    expect(screen.queryByText('Documents')).not.toBeInTheDocument();
    expect(screen.queryByText('Trash')).not.toBeInTheDocument();
    expect(screen.queryByText('File Requests')).not.toBeInTheDocument();
    expect(screen.queryByText('Automations')).not.toBeInTheDocument();
    expect(screen.queryByText('Signatures')).not.toBeInTheDocument();
  });

  it('shows documents and trash only when those gates are on', () => {
    useFeatureGates.mockReturnValue({
      canAccessFileRequests: false,
      canAccessAutomations: false,
      canAccessDocuments: true,
      canAccessTrash: true,
      canAccessSignatures: false,
    });
    render(
      <MemoryRouter>
        <NavProbe />
      </MemoryRouter>
    );
    expect(screen.getByText('Documents')).toBeInTheDocument();
    expect(screen.getByText('Trash')).toBeInTheDocument();
  });
});
