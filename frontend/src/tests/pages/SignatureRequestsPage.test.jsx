import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import SignatureRequestsPage from '../../pages/SignatureRequestsPage';
import * as esign from '../../services/esign';

vi.mock('../../services/esign', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    listSignatureRequests: vi.fn(),
    cancelSignatureRequest: vi.fn(),
    sendReminder: vi.fn(),
  };
});

const REQUEST_ULID = '01M6DR9ZF681SZEKXA8CJBX7F6';
const TOKEN = 'signer-token-ulid-flow';

describe('SignatureRequestsPage awaiting tab', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('shows View & Sign when awaiting list includes signer_token', async () => {
    esign.listSignatureRequests.mockImplementation((view) => {
      if (view === 'awaiting') {
        return Promise.resolve([
          {
            id: REQUEST_ULID,
            title: 'Sign me',
            status: 'sent',
            document: { name: 'doc.pdf' },
            signer_status: 'sent',
            signer_token: TOKEN,
            can_sign: true,
            created_at: new Date().toISOString(),
          },
        ]);
      }
      return Promise.resolve([]);
    });

    render(
      <I18nextProvider i18n={i18n}>
        <MemoryRouter>
          <SignatureRequestsPage />
        </MemoryRouter>
      </I18nextProvider>
    );

    const awaitingTab = screen.getByRole('button', { name: /Awaiting My Signature/i });
    awaitingTab.click();

    expect(await screen.findByRole('button', { name: /View & Sign/i })).toBeInTheDocument();
  });
});
