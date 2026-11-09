import { describe, expect, it, vi } from 'vitest';
import {
  buildGoogleDriveFolderDestinationView,
  buildGoogleDriveImportViews,
} from '../../../components/cloud/googleDrivePickerViews';

function createMockView() {
  const chain = {
    setIncludeFolders: vi.fn(),
    setParent: vi.fn(),
    setOwnedByMe: vi.fn(),
    setSelectFolderEnabled: vi.fn(),
    setMimeTypes: vi.fn(),
    setEnableTeamDrives: vi.fn(),
  };
  Object.values(chain).forEach((fn) => fn.mockReturnValue(chain));
  return chain;
}

function installGooglePickerStub() {
  const views = [];
  const DocsView = vi.fn(() => {
    const view = createMockView();
    views.push(view);
    return view;
  });

  return {
    views,
    google: {
      picker: {
        ViewId: { DOCS: 'DOCS', FOLDERS: 'FOLDERS' },
        DocsView,
      },
    },
  };
}

describe('googleDrivePickerViews', () => {
  it('configures hierarchical My Drive import browsing from root', () => {
    const { google, views } = installGooglePickerStub();

    const { myDriveView, sharedView } = buildGoogleDriveImportViews(google);

    expect(google.picker.DocsView).toHaveBeenCalledWith('DOCS');
    expect(views).toHaveLength(2);
    expect(myDriveView.setParent).toHaveBeenCalledWith('root');
    expect(myDriveView.setOwnedByMe).toHaveBeenCalledWith(true);
    expect(myDriveView.setIncludeFolders).toHaveBeenCalledWith(true);
    expect(sharedView.setOwnedByMe).toHaveBeenCalledWith(false);
    expect(sharedView.setIncludeFolders).toHaveBeenCalledWith(true);
    expect(sharedView.setParent).not.toHaveBeenCalled();
  });

  it('configures hierarchical folder destination selection from root', () => {
    const { google, views } = installGooglePickerStub();

    const folderView = buildGoogleDriveFolderDestinationView(google);

    expect(views).toHaveLength(1);
    expect(folderView.setParent).toHaveBeenCalledWith('root');
    expect(folderView.setSelectFolderEnabled).toHaveBeenCalledWith(true);
    expect(folderView.setMimeTypes).toHaveBeenCalledWith('application/vnd.google-apps.folder');
    expect(google.picker.DocsView).toHaveBeenCalledWith('DOCS');
    expect(google.picker.DocsView).not.toHaveBeenCalledWith('FOLDERS');
  });
});
