import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CloudImportDialog } from '../../../components/dialogs/CloudImportDialog';
import * as api from '../../../services/api';
import '../../../i18n';

const openPickerMock = vi.fn();

vi.mock('../../../components/cloud/GoogleDrivePicker', () => ({
  useGoogleDrivePicker: () => ({
    openPicker: openPickerMock,
    loading: false,
    error: null,
  }),
}));

vi.mock('../../../services/api', () => ({
  listCloudFiles: vi.fn(),
  importCloudFile: vi.fn(),
}));

describe('CloudImportDialog Google Drive picker mode', () => {
  const provider = { name: 'google_drive', display_name: 'Google Drive' };
  const connection = { id: 'conn_1', provider: 'google_drive' };

  beforeEach(() => {
    vi.clearAllMocks();
    api.listCloudFiles.mockRejectedValue({
      response: {
        status: 400,
        data: { detail: 'Google Drive is in picker mode. Use the file picker instead.' },
      },
    });
  });

  it('opens the file picker without folder-only mode when the picker button is clicked', async () => {
    const user = userEvent.setup();

    render(
      <CloudImportDialog
        isOpen
        onOpenChange={vi.fn()}
        provider={provider}
        connection={connection}
        onImportSuccess={vi.fn()}
      />
    );

    const openButton = await screen.findByRole('button', { name: 'Open Google Drive Picker' });
    await user.click(openButton);

    expect(openPickerMock).toHaveBeenCalledTimes(1);
    expect(openPickerMock).toHaveBeenCalledWith();
  });
});
