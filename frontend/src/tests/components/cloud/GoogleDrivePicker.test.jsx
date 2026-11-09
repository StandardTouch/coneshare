import { renderHook, act, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGoogleDrivePicker } from '../../../components/cloud/GoogleDrivePicker';
import api from '../../../services/api';
import '../../../i18n';

vi.mock('../../../services/api', () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
  },
}));

function createMockView() {
  const chain = {
    setSelectFolderEnabled: vi.fn(),
    setMimeTypes: vi.fn(),
    setIncludeFolders: vi.fn(),
    setParent: vi.fn(),
    setOwnedByMe: vi.fn(),
    setEnableTeamDrives: vi.fn(),
  };
  Object.values(chain).forEach((fn) => fn.mockReturnValue(chain));
  return chain;
}

function installGooglePickerMocks() {
  const createdViews = [];
  const builder = {
    setAppId: vi.fn(),
    setOAuthToken: vi.fn(),
    setDeveloperKey: vi.fn(),
    setCallback: vi.fn(),
    addView: vi.fn(),
    setTitle: vi.fn(),
    enableFeature: vi.fn(),
    build: vi.fn(() => ({ setVisible: vi.fn() })),
  };
  Object.values(builder).forEach((fn) => {
    if (fn !== builder.build) fn.mockReturnValue(builder);
  });

  const DocsView = vi.fn(() => {
    const view = createMockView();
    createdViews.push(view);
    return view;
  });

  window.google = {
    picker: {
      PickerBuilder: vi.fn(() => builder),
      ViewId: { FOLDERS: 'FOLDERS', DOCS: 'DOCS' },
      Action: { PICKED: 'picked', CANCEL: 'cancel' },
      Feature: { SUPPORT_TEAM_DRIVES: 'team_drives' },
      DocsView,
    },
  };

  window.gapi = {
    load: vi.fn((_, cb) => cb?.()),
  };

  return { builder, createdViews, DocsView };
}

async function renderReadyPickerHook(connection, onFilesPicked) {
  delete window.gapi;
  delete window.google;

  const hook = renderHook(() => useGoogleDrivePicker(connection, onFilesPicked));
  const mocks = installGooglePickerMocks();

  await waitFor(() => {
    expect(document.querySelector('script[src="https://apis.google.com/js/api.js"]')).toBeTruthy();
  });
  const script = document.querySelector('script[src="https://apis.google.com/js/api.js"]');
  act(() => {
    script.onload();
  });

  return { ...hook, ...mocks };
}

describe('useGoogleDrivePicker', () => {
  const connection = { id: 'conn_1' };
  const onFilesPicked = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    api.get.mockResolvedValue({
      data: { access_token: 'tok', api_key: 'key', app_id: 'app' },
    });
    document.querySelectorAll('script[src="https://apis.google.com/js/api.js"]').forEach((el) => el.remove());
  });

  it('opens hierarchical My Drive and Shared import views from root', async () => {
    const { result, builder, createdViews } = await renderReadyPickerHook(connection, onFilesPicked);

    await act(async () => {
      await result.current.openPicker();
    });

    expect(builder.addView).toHaveBeenCalledTimes(2);
    expect(createdViews[0].setParent).toHaveBeenCalledWith('root');
    expect(createdViews[0].setOwnedByMe).toHaveBeenCalledWith(true);
    expect(createdViews[1].setOwnedByMe).toHaveBeenCalledWith(false);
    expect(createdViews[1].setParent).not.toHaveBeenCalled();
    expect(builder.setTitle).toHaveBeenCalledWith('Select a File');
  });

  it('opens hierarchical folder destination view only when pickFolders is explicitly true', async () => {
    const { result, builder, createdViews, DocsView } = await renderReadyPickerHook(connection, onFilesPicked);

    await act(async () => {
      await result.current.openPicker(true);
    });

    expect(builder.addView).toHaveBeenCalledTimes(1);
    expect(DocsView).toHaveBeenCalledWith('DOCS');
    expect(createdViews[0].setParent).toHaveBeenCalledWith('root');
    expect(createdViews[0].setSelectFolderEnabled).toHaveBeenCalledWith(true);
    expect(builder.setTitle).toHaveBeenCalledWith('Select Destination Folder');
  });

  it('does not treat a React click event as folder selection mode', async () => {
    const { result, builder } = await renderReadyPickerHook(connection, onFilesPicked);
    const syntheticClickEvent = { nativeEvent: {}, preventDefault: vi.fn() };

    await act(async () => {
      await result.current.openPicker(syntheticClickEvent);
    });

    expect(builder.addView).toHaveBeenCalledTimes(2);
    expect(builder.setTitle).toHaveBeenCalledWith('Select a File');
  });
});
