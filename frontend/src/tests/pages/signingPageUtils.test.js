import { describe, it, expect } from 'vitest';
import {
  areAllRequiredSignerFieldsFilled,
  buildSubmitFieldsPayload,
  getApiErrorDetail,
  isSubmitDisabled,
  signingActionErrorMessage,
} from '../../pages/signingPageUtils';

const FIELD_A = '01M6BBPMBM7QFDG413TWMECWQH';
const FIELD_B = '01M6BBPMBM7QFDG413TWMECWQI';

describe('signingPageUtils', () => {
  it('extracts backend detail from axios errors', () => {
    const error = {
      response: { data: { detail: 'Verification code has expired. Please request a new one.' } },
    };
    expect(getApiErrorDetail(error)).toBe(
      'Verification code has expired. Please request a new one.'
    );
  });

  it('falls back to i18n key when detail is missing', () => {
    const t = (key) => (key === 'esign.otp.verifyFailed' ? 'Invalid verification code' : key);
    expect(signingActionErrorMessage(new Error('network'), 'esign.otp.verifyFailed', t)).toBe(
      'Invalid verification code'
    );
  });

  it('prefers backend detail over fallback', () => {
    const t = () => 'generic';
    const error = { response: { data: { detail: 'Too many failed attempts. Please request a new code.' } } };
    expect(signingActionErrorMessage(error, 'esign.otp.verifyFailed', t)).toBe(
      'Too many failed attempts. Please request a new code.'
    );
  });
  const signerFields = [
    { id: FIELD_A, required: true, field_type: 'signature' },
    { id: FIELD_B, required: true, field_type: 'date_signed' },
  ];

  it('requires every required signer field to be filled', () => {
    expect(
      areAllRequiredSignerFieldsFilled(signerFields, {
        [FIELD_A]: 'data:image/png;base64,abc',
      })
    ).toBe(false);
    expect(
      areAllRequiredSignerFieldsFilled(signerFields, {
        [FIELD_A]: 'data:image/png;base64,abc',
        [FIELD_B]: '11/3/2026',
      })
    ).toBe(true);
  });

  it('builds submit payload with string ULID field ids', () => {
    const payload = buildSubmitFieldsPayload(signerFields, {
      [FIELD_A]: 'data:image/png;base64,abc',
      [FIELD_B]: '11/3/2026',
      extra: 'ignored',
    });
    expect(payload).toEqual([
      { field_id: FIELD_A, value: 'data:image/png;base64,abc' },
      { field_id: FIELD_B, value: '11/3/2026' },
    ]);
  });

  it('submit stays disabled when can_sign is false even if fields are filled', () => {
    expect(
      isSubmitDisabled({
        canSign: false,
        signerFields,
        fieldValues: { [FIELD_A]: 'x', [FIELD_B]: 'y' },
      })
    ).toBe(true);
  });

  it('submit enables when can_sign is true and required fields filled', () => {
    expect(
      isSubmitDisabled({
        canSign: true,
        signerFields,
        fieldValues: { [FIELD_A]: 'data:image/png;base64,x', [FIELD_B]: 'today' },
      })
    ).toBe(false);
  });
});
