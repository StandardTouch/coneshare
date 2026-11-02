import { describe, it, expect } from 'vitest';
import {
  getEsignDocumentPdfUrl,
  getEsignRequestPdfUrl,
  getSignatureRequestDocumentId,
} from '../../services/esign';

const SAMPLE_ULID = '01M6BBPMBM7QFDG413TWMECWQH';

describe('esign PDF URLs with ULIDs', () => {
  it('embeds document ULID without coercion', () => {
    expect(getEsignDocumentPdfUrl(SAMPLE_ULID)).toBe(
      `/api/v1/esign/documents/${SAMPLE_ULID}/pdf/`
    );
  });

  it('embeds request ULID without coercion', () => {
    expect(getEsignRequestPdfUrl(SAMPLE_ULID)).toBe(
      `/api/v1/esign/requests/${SAMPLE_ULID}/pdf/`
    );
  });

  it('reads document id from nested document on list payloads', () => {
    expect(getSignatureRequestDocumentId({ document: { id: SAMPLE_ULID } })).toBe(SAMPLE_ULID);
    expect(getSignatureRequestDocumentId({ document_id: SAMPLE_ULID })).toBe(SAMPLE_ULID);
    expect(getSignatureRequestDocumentId({ document: { name: 'x.pdf' } })).toBeUndefined();
  });
});
