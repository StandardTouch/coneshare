import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../i18n';
import SigningPage from '../../pages/SigningPage';
import * as esign from '../../services/esign';

vi.mock('../../services/esign', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getSigningData: vi.fn(),
    requestOTP: vi.fn(),
    verifyOTP: vi.fn(),
    submitSignature: vi.fn(),
    getSignerDocumentPdfUrl: vi.fn(() => '/pdf'),
  };
});

vi.mock('../../components/esign/EsignPdfViewer', () => ({
  EsignPdfViewer: () => <div data-testid="pdf-viewer">PDF</div>,
}));

vi.mock('../../components/esign/SignatureDrawModal', () => ({
  SignatureDrawModal: ({ isOpen, onSave }) =>
    isOpen ? (
      <button type="button" onClick={() => onSave('data:image/png;base64,abc')}>
        Mock Save Signature
      </button>
    ) : null,
}));

vi.mock('../../components/esign/TypedSignatureModal', () => ({
  TypedSignatureModal: () => null,
}));

vi.mock('../../contexts/UserProvider', () => ({
  useUser: () => ({ user: { name: 'Signer' } }),
}));

const TOKEN = 'signer-token-test';
const FIELD_SIG = '01M6BBPMBM7QFDG413TWMECWQH';
const FIELD_DATE = '01M6BBPMBM7QFDG413TWMECWQI';

function signingPayload({ can_sign, can_sign_reason, otp_verified_at = null }) {
  return {
    id: '01SIGNER000000000000000001',
    otp_verified_at,
    can_sign,
    can_sign_reason,
    signature_request: {
      id: '01REQ00000000000000000001',
      title: 'Test Doc',
      message: '',
      document: { id: '01DOC00000000000000000001', name: 'a.pdf', num_pages: 1 },
    },
    fields: [
      { id: FIELD_SIG, field_type: 'signature', page_number: 1, required: true },
      { id: FIELD_DATE, field_type: 'date_signed', page_number: 1, required: true },
    ],
    all_fields: [],
  };
}

function renderPage() {
  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter initialEntries={[`/sign/${TOKEN}`]}>
        <Routes>
          <Route path="/sign/:token" element={<SigningPage />} />
        </Routes>
      </MemoryRouter>
    </I18nextProvider>
  );
}

describe('SigningPage submit after OTP', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    esign.verifyOTP.mockResolvedValue({ verified: true });
    esign.requestOTP.mockResolvedValue({});
    esign.submitSignature.mockResolvedValue({ status: 'signed' });
  });

  it('enables Submit after OTP verify refetch and required fields filled', async () => {
    esign.getSigningData
      .mockResolvedValueOnce(
        signingPayload({
          can_sign: false,
          can_sign_reason: 'OTP verification required',
        })
      )
      .mockResolvedValueOnce(
        signingPayload({
          can_sign: true,
          can_sign_reason: 'OK',
          otp_verified_at: new Date().toISOString(),
        })
      );

    renderPage();

    await screen.findByText('Test Doc');
    fireEvent.click(screen.getByRole('button', { name: /Request Verification Code/i }));
    await waitFor(() => expect(esign.requestOTP).toHaveBeenCalled());

    fireEvent.change(await screen.findByPlaceholderText(/6-digit/i), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /^Verify$/i }));

    await waitFor(() => expect(esign.getSigningData).toHaveBeenCalledTimes(2));

    const submitBtn = screen.getByRole('button', { name: /Submit Signature/i });
    expect(submitBtn).toBeDisabled();

    const fieldRows = [...document.querySelectorAll('[class*="cursor-pointer"]')];
    const signatureRow = fieldRows.find((el) => /Signature/i.test(el.textContent) && /Page/i.test(el.textContent));
    const dateRow = fieldRows.find((el) => /Date Signed/i.test(el.textContent));
    fireEvent.click(signatureRow);
    fireEvent.click(await screen.findByRole('button', { name: /Mock Save Signature/i }));
    fireEvent.click(dateRow);

    await waitFor(() => expect(submitBtn).not.toBeDisabled());

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(esign.submitSignature).toHaveBeenCalledTimes(1);
      const [, payload] = esign.submitSignature.mock.calls[0];
      expect(payload).toEqual(
        expect.arrayContaining([
          { field_id: FIELD_SIG, value: 'data:image/png;base64,abc' },
          expect.objectContaining({ field_id: FIELD_DATE }),
        ])
      );
    });
  });
});
