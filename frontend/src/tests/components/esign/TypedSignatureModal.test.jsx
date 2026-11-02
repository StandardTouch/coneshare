import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

import '../../../i18n';
import { TypedSignatureModal } from '../../../components/esign/TypedSignatureModal';

describe('TypedSignatureModal', () => {
  it('enables save when text is entered', () => {
    const onSave = vi.fn();
    render(
      <TypedSignatureModal
        isOpen
        onOpenChange={vi.fn()}
        onSave={onSave}
        fieldType="text"
      />
    );

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    expect(saveButton).toBeDisabled();

    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Approved' } });
    expect(saveButton).not.toBeDisabled();

    fireEvent.click(saveButton);
    expect(onSave).toHaveBeenCalledWith('Approved');
  });
});
