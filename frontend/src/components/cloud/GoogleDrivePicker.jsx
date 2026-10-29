import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import api from '../../services/api';

let pickerApiLoaded = false;
let googleApiLoaded = false;

export function useGoogleDrivePicker(connection, onFilesPicked) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!window.gapi) {
      const script = document.createElement('script');
      script.src = 'https://apis.google.com/js/api.js';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        googleApiLoaded = true;
        window.gapi.load('picker', () => {
          pickerApiLoaded = true;
        });
      };
      document.body.appendChild(script);
    } else if (!pickerApiLoaded) {
      window.gapi.load('picker', () => {
        pickerApiLoaded = true;
      });
    }
  }, []);

  const openPicker = async (pickFolders = false) => {
    if (!connection) {
      toast.error(t('cloudImport.noConnection'));
      return;
    }

    if (!googleApiLoaded || !pickerApiLoaded) {
      toast.error(t('cloudImport.pickerNotReady'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(`/cloud/connections/${connection.id}/picker_token/`);
      const { access_token, api_key, app_id } = response.data;

      const google = window.google;
      const picker = new google.picker.PickerBuilder()
        .setAppId(app_id)
        .setOAuthToken(access_token)
        .setDeveloperKey(api_key)
        .setCallback((data) => {
          if (data.action === google.picker.Action.PICKED) {
            const files = data.docs.map(doc => ({
              id: doc.id,
              name: doc.name,
              size: doc.sizeBytes || 0,
              mimeType: doc.mimeType,
            }));
            onFilesPicked(files);
          } else if (data.action === google.picker.Action.CANCEL) {
            setLoading(false);
          }
        });

      if (pickFolders) {
        const folderView = new google.picker.DocsView(google.picker.ViewId.FOLDERS)
          .setSelectFolderEnabled(true)
          .setMimeTypes('application/vnd.google-apps.folder')
          .setIncludeFolders(true);
        picker.addView(folderView);
        picker.setTitle(t('cloudExport.selectFolder'));
      } else {
        const docsView = new google.picker.DocsView(google.picker.ViewId.DOCS)
          .setIncludeFolders(true)
          .setEnableTeamDrives(true);
        picker.addView(docsView);
        picker.setTitle(t('cloudImport.selectFile'));
        picker.enableFeature(google.picker.Feature.SUPPORT_TEAM_DRIVES);
      }

      picker.build().setVisible(true);
      setLoading(false);

    } catch (err) {
      console.error('Failed to open Google Drive Picker:', err);
      setLoading(false);
      
      if (err.response?.status === 400) {
        const detail = err.response?.data?.detail || '';
        if (detail.includes('reconnect') || detail.includes('expired') || detail.includes('revoked')) {
          setError(t('cloudImport.reconnectRequired'));
          toast.error(t('cloudImport.reconnectRequired'));
        } else {
          setError(detail || t('cloudImport.pickerFailed'));
          toast.error(detail || t('cloudImport.pickerFailed'));
        }
      } else {
        setError(t('cloudImport.pickerFailed'));
        toast.error(t('cloudImport.pickerFailed'));
      }
    }
  };

  return { openPicker, loading, error };
}

export function GoogleDrivePickerButton({ connection, onFilesPicked, pickFolders = false, children, disabled, ...props }) {
  const { openPicker, loading } = useGoogleDrivePicker(connection, onFilesPicked);

  return (
    <button
      onClick={() => openPicker(pickFolders)}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : children}
    </button>
  );
}
