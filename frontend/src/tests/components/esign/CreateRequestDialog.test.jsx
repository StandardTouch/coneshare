import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

import '../../../i18n';
import { CreateRequestDialog } from '../../../components/esign/CreateRequestDialog';
import * as esign from '../../../services/esign';

vi.mock('../../../services/esign', () => ({
  createSignatureRequest: vi.fn(),
  getSignatureRequest: vi.fn(),
  updateSignatureFields: vi.fn(),
  sendSignatureRequest: vi.fn(),
}));

vi.mock('../../../components/esign/FieldPlacementEditor', () => ({
  FieldPlacementEditor: () => <div data-testid="field-placement-editor">Field editor</div>,
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const ULID_A = '01JBEEF00000000000000000001';
const ULID_B = '01JBEEF00000000000000000002';

describe('CreateRequestDialog', () => {
  const document = { id: 42, name: 'Contract.pdf' };
  const users = [
    { id: ULID_A, name: 'Alice', email: 'alice@example.com' },
    { id: ULID_B, name: 'Bob', email: 'bob@example.com' },
  ];

  beforeEach(() => {
    vi.resetAllMocks();
    esign.createSignatureRequest.mockResolvedValue({ id: 99 });
    esign.getSignatureRequest.mockResolvedValue({
      id: 99,
      signers: [
        { id: 1, user: { id: ULID_A }, signing_order: 1 },
        { id: 2, user: { id: ULID_B }, signing_order: 1 },
      ],
    });
  });

  it('submits ULID user_id strings unchanged when creating a request', async () => {
    render(
      <MemoryRouter>
        <CreateRequestDialog
          isOpen
          onOpenChange={vi.fn()}
          document={document}
          users={users}
        />
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /add signer/i }));
    const selects = screen.getAllByRole('combobox');
    const signerSelect = selects[0];
    fireEvent.change(signerSelect, { target: { value: ULID_A } });
    expect(signerSelect.value).toBe(ULID_A);

    fireEvent.click(screen.getByRole('button', { name: /^next$/i }));

    await waitFor(() => {
      expect(esign.createSignatureRequest).toHaveBeenCalledTimes(1);
    });

    const payload = esign.createSignatureRequest.mock.calls[0][0];
    expect(payload.signers).toEqual([{ user_id: ULID_A, signing_order: 1 }]);
    expect(typeof payload.signers[0].user_id).toBe('string');
    expect(payload.signers[0].user_id).toBe(ULID_A);
  });
});
