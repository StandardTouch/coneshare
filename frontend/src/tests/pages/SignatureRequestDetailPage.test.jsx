import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import SignatureRequestDetailPage from '../../pages/SignatureRequestDetailPage';
import * as esign from '../../services/esign';

vi.mock('../../services/esign', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getSignatureRequest: vi.fn(),
    downloadSignedDocument: vi.fn(),
    downloadCertificate: vi.fn(),
  };
});

vi.mock('../../components/layout/BreadcrumbProvider', () => ({
  useBreadcrumb: () => ({ setBreadcrumbs: vi.fn() }),
}));

const SAMPLE_ID = '01M6GKKBFYR5KJ0J947ZBDKQT8';

describe('SignatureRequestDetailPage audit view', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows signers, hashes, and event log in English', async () => {
    esign.getSignatureRequest.mockResolvedValue({
      id: SAMPLE_ID,
      title: 'NDA Pack',
      status: 'completed',
      completed_at: '2026-01-15T12:00:00Z',
      original_document_hash: 'sha256:aaa',
      signed_document_hash: 'sha256:bbb',
      certificate_storage_key: 'signatures/x/certificate.pdf',
      signers: [
        {
          id: 'signer1',
          signed_at: '2026-01-15T12:05:00Z',
          otp_verified_at: '2026-01-15T12:04:00Z',
          ip_address: '203.0.113.50',
          user_agent: 'Mozilla/5.0 Test',
          user: { name: 'Jane Signer', email: 'jane@example.com' },
          actions: [
            {
              id: 'act1',
              action: 'signed',
              timestamp: '2026-01-15T12:05:00Z',
              ip_address: '203.0.113.50',
              user_agent: 'Mozilla/5.0 Test',
            },
          ],
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={[`/signatures/${SAMPLE_ID}`]}>
        <Routes>
          <Route path="/signatures/:requestId" element={<SignatureRequestDetailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => expect(screen.getByText('Document integrity')).toBeInTheDocument());
    expect(screen.getByText('sha256:aaa')).toBeInTheDocument();
    expect(screen.getByText('sha256:bbb')).toBeInTheDocument();
    expect(screen.getByText('jane@example.com')).toBeInTheDocument();
    expect(screen.getAllByText('203.0.113.50').length).toBeGreaterThan(0);
    expect(screen.getByText('Event log')).toBeInTheDocument();
    expect(screen.getByText('signed')).toBeInTheDocument();
  });
});
