import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { vi } from 'vitest';

import { AdminRbacPage } from '../../pages/AdminRbacPage';

describe('AdminRbacPage', () => {
  it('redirects legacy /admin/rbac to /admin/roles', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/admin/rbac']}>
        <Routes>
          <Route path="/admin/rbac" element={<AdminRbacPage />} />
          <Route path="/admin/roles" element={<div data-testid="roles-target" />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(container.querySelector('[data-testid="roles-target"]')).toBeTruthy();
    });
  });
});
