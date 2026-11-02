import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../i18n';
import { FieldPlacementEditor } from '../../../components/esign/FieldPlacementEditor';

vi.mock('../../../components/esign/EsignPdfViewer', () => ({
  EsignPdfViewer: () => <div data-testid="mock-pdf-viewer" />,
}));

const SIGNER_ULID = '01M6DR9ZF681SZEKXA8CJBX7F6';
const USER_ULID = '01M6BBPMBM7QFDG413TWMECWQH';

describe('FieldPlacementEditor', () => {
  it('lists signers by displayName from detail payload', () => {
    render(
      <I18nextProvider i18n={i18n}>
        <FieldPlacementEditor
          documentId={USER_ULID}
          signers={[
            {
              id: SIGNER_ULID,
              user_id: USER_ULID,
              displayName: 'Production Signer',
              signing_order: 1,
            },
          ]}
          users={[]}
          onSave={vi.fn()}
          onCancel={vi.fn()}
        />
      </I18nextProvider>
    );

    expect(screen.getByRole('combobox')).toHaveTextContent('Production Signer');
  });
});
