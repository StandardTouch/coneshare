import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { SetPasswordPage } from '../../pages/SetPasswordPage';
import * as api from '../../services/api';
import '../../i18n';

vi.mock('../../services/api', () => ({
  validateInviteToken: vi.fn(),
  completeInviteSetPassword: vi.fn(),
}));

vi.mock('../../contexts/BrandingProvider', () => ({
  useBranding: () => ({
    brandName: 'Allure Clinic',
    brandLogoUrl: null,
    brandWebsiteUrl: null,
    termsUrl: '/terms',
    privacyPolicyUrl: '/privacy',
  }),
}));

describe('SetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders password form when invite token is valid', async () => {
    api.validateInviteToken.mockResolvedValue({ valid: true, email: 'user@example.com' });

    render(
      <MemoryRouter initialEntries={['/set-password/uid123/token456']}>
        <Routes>
          <Route path="/set-password/:uid/:token" element={<SetPasswordPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('New Password')).toBeInTheDocument();
    });
    expect(screen.getByText(/user@example.com/i)).toBeInTheDocument();
  });

  it('renders password form when validate returns an axios response body', async () => {
    api.validateInviteToken.mockResolvedValue({
      data: { valid: true, email: 'user@example.com' },
      status: 200,
    });

    render(
      <MemoryRouter initialEntries={['/set-password/uid123/token456']}>
        <Routes>
          <Route path="/set-password/:uid/:token" element={<SetPasswordPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('New Password')).toBeInTheDocument();
    });
    expect(screen.queryByText('This invite link is invalid.')).not.toBeInTheDocument();
    expect(screen.getByText(/user@example.com/i)).toBeInTheDocument();
  });

  it('shows expired message when validate returns expired code', async () => {
    api.validateInviteToken.mockRejectedValue({
      response: {
        data: {
          valid: false,
          code: 'expired',
          detail: 'This invite link has expired.',
        },
      },
    });

    render(
      <MemoryRouter initialEntries={['/set-password/uid123/token456']}>
        <Routes>
          <Route path="/set-password/:uid/:token" element={<SetPasswordPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('This invite link has expired.')).toBeInTheDocument();
    });
  });

  it('shows already-used message when validate returns used code', async () => {
    api.validateInviteToken.mockRejectedValue({
      response: {
        data: {
          valid: false,
          code: 'used',
          detail: 'This invite link has already been used.',
        },
      },
    });

    render(
      <MemoryRouter initialEntries={['/set-password/uid123/token456']}>
        <Routes>
          <Route path="/set-password/:uid/:token" element={<SetPasswordPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('This invite link has already been used.')).toBeInTheDocument();
    });
  });

  it('submits new password via invite API', async () => {
    api.validateInviteToken.mockResolvedValue({ valid: true, email: 'user@example.com' });
    api.completeInviteSetPassword.mockResolvedValue({ detail: 'ok' });
    const user = userEvent.setup();

    render(
      <MemoryRouter initialEntries={['/set-password/uid123/token456']}>
        <Routes>
          <Route path="/set-password/:uid/:token" element={<SetPasswordPage />} />
        </Routes>
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByPlaceholderText('New Password')).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText('New Password'), 'StrongPass123!');
    await user.type(screen.getByPlaceholderText('Confirm New Password'), 'StrongPass123!');
    await user.click(screen.getByRole('button', { name: 'Set password and continue' }));

    await waitFor(() => {
      expect(api.completeInviteSetPassword).toHaveBeenCalledWith({
        uid: 'uid123',
        token: 'token456',
        password1: 'StrongPass123!',
        password2: 'StrongPass123!',
      });
    });
  });
});
