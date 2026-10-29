import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status

from cloudfiles.models import CloudConnection
from core.models import AppConfiguration


@pytest.fixture(autouse=True)
def disable_cache(settings):
    """Disable Django caching for tests to avoid needing Redis."""
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }


@pytest.fixture
def google_drive_connection(user):
    """Fixture for a Google Drive cloud connection."""
    return CloudConnection.objects.create(
        user=user,
        provider='google_drive',
        email='test@google.com',
        access_token='test_access_token',
        refresh_token='test_refresh_token',
    )


@pytest.mark.django_db
@patch('cloudfiles.providers.google_drive.get_dynamic_setting')
class TestGoogleDriveMode:
    """Test mode-dependent behavior for Google Drive."""
    
    def test_scopes_in_picker_mode(self, mock_get_setting, google_drive_connection):
        """Test that picker mode uses non-sensitive scopes."""
        def get_setting(key):
            return {
                'GOOGLE_DRIVE_MODE': 'picker',
                'GOOGLE_DRIVE_CLIENT_ID': 'test_client_id',
                'GOOGLE_DRIVE_CLIENT_SECRET': 'test_secret',
            }.get(key)
        mock_get_setting.side_effect = get_setting
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        provider = GoogleDriveProvider(connection=google_drive_connection)
        
        assert provider.mode == 'picker'
        assert 'https://www.googleapis.com/auth/drive.file' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/drive.readonly' not in provider.SCOPES
        assert 'openid' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.email' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.profile' in provider.SCOPES
    
    def test_scopes_in_browse_mode(self, mock_get_setting, google_drive_connection):
        """Test that browse mode uses full scopes including restricted ones."""
        def get_setting(key):
            return {
                'GOOGLE_DRIVE_MODE': 'browse',
                'GOOGLE_DRIVE_CLIENT_ID': 'test_client_id',
                'GOOGLE_DRIVE_CLIENT_SECRET': 'test_secret',
            }.get(key)
        mock_get_setting.side_effect = get_setting
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        provider = GoogleDriveProvider(connection=google_drive_connection)
        
        assert provider.mode == 'browse'
        assert 'https://www.googleapis.com/auth/drive.file' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/drive.readonly' in provider.SCOPES
        assert 'openid' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.email' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.profile' in provider.SCOPES
    
    def test_default_mode_is_picker(self, mock_get_setting, google_drive_connection):
        """Test that the default mode is picker when not configured."""
        def get_setting(key):
            return {
                'GOOGLE_DRIVE_CLIENT_ID': 'test_client_id',
                'GOOGLE_DRIVE_CLIENT_SECRET': 'test_secret',
            }.get(key)
        mock_get_setting.side_effect = get_setting
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        provider = GoogleDriveProvider(connection=google_drive_connection)
        
        assert provider.mode == 'picker'
        assert 'https://www.googleapis.com/auth/drive.readonly' not in provider.SCOPES


@pytest.mark.django_db
@patch('cloudfiles.views.get_picker_access_token')
class TestGoogleDrivePickerTokenView:
    """Test the picker token endpoint."""
    
    def test_get_picker_token_success(self, mock_get_token, api_client, user, google_drive_connection):
        """Test successful retrieval of picker token."""
        mock_get_token.return_value = {
            'access_token': 'fresh_access_token',
            'api_key': 'test_api_key',
            'app_id': '123456789',
        }
        
        response = api_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['access_token'] == 'fresh_access_token'
        assert response.data['api_key'] == 'test_api_key'
        assert response.data['app_id'] == '123456789'
        mock_get_token.assert_called_once_with(google_drive_connection)
    
    def test_picker_token_requires_auth(self, mock_get_token, public_client, google_drive_connection):
        """Test that the picker token endpoint requires authentication."""
        response = public_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_picker_token_connection_not_found(self, mock_get_token, api_client, user):
        """Test 404 when connection doesn't exist."""
        response = api_client.get(
            '/api/v1/cloud/connections/nonexistent-id/picker_token/'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_picker_token_only_for_google_drive(self, mock_get_token, api_client, user):
        """Test that the endpoint rejects non-Google Drive connections."""
        dropbox_connection = CloudConnection.objects.create(
            user=user,
            provider='dropbox',
            email='test@dropbox.com',
            access_token='test_token',
        )
        
        response = api_client.get(
            f'/api/v1/cloud/connections/{dropbox_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'only available for Google Drive' in response.data['detail']
    
    def test_picker_token_requires_picker_mode(self, mock_get_token, api_client, user, google_drive_connection):
        """Test that picker token endpoint requires picker mode."""
        from cloudfiles.providers import CloudProviderError
        mock_get_token.side_effect = CloudProviderError("Google Drive Picker is only available in picker mode.")
        
        response = api_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'only available in picker mode' in response.data['detail']
    
    def test_picker_token_requires_credentials(self, mock_get_token, api_client, user, google_drive_connection):
        """Test that picker token endpoint requires API key and App ID."""
        from cloudfiles.providers import CloudProviderError
        mock_get_token.side_effect = CloudProviderError("Google Drive Picker credentials (API Key and App ID) are not configured. Please configure GOOGLE_DRIVE_API_KEY and GOOGLE_DRIVE_APP_ID in admin settings.")
        
        response = api_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'API Key and App ID' in response.data['detail']
    
    def test_picker_token_no_secrets_leaked(self, mock_get_token, api_client, user, google_drive_connection):
        """Test that refresh token and client secret are never returned."""
        mock_get_token.return_value = {
            'access_token': 'fresh_access_token',
            'api_key': 'test_api_key',
            'app_id': '123456789',
        }
        
        response = api_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'refresh_token' not in response.data
        assert 'client_secret' not in response.data
        assert 'test_secret' not in str(response.data)
        assert 'test_refresh_token' not in str(response.data)


@pytest.mark.django_db
@patch('cloudfiles.views.get_dynamic_setting')
class TestListEndpointGating:
    """Test that list endpoints are blocked in picker mode."""
    
    def test_list_files_blocked_in_picker_mode(self, mock_get_setting, api_client, user, google_drive_connection):
        """Test that CloudFileListView returns 400 in picker mode."""
        mock_get_setting.return_value = 'picker'
        
        response = api_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/list/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'picker mode' in response.data['detail']
    
    def test_list_folders_blocked_in_picker_mode(self, mock_get_setting, api_client, user, google_drive_connection):
        """Test that CloudFolderListView returns 400 in picker mode."""
        mock_get_setting.return_value = 'picker'
        
        response = api_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/folders/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'picker mode' in response.data['detail']
    
    def test_list_files_works_in_browse_mode(self, mock_get_setting, api_client, user, google_drive_connection):
        """Test that list endpoints work in browse mode."""
        mock_get_setting.return_value = 'browse'
        
        with patch('cloudfiles.views.get_cloud_provider') as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.list_files.return_value = []
            mock_get_provider.return_value = mock_provider
            
            response = api_client.get(
                f'/api/v1/cloud/connections/{google_drive_connection.id}/list/'
            )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_endpoints_work_for_other_providers(self, mock_get_setting, api_client, user):
        """Test that list endpoint gating only applies to Google Drive."""
        mock_get_setting.return_value = 'picker'
        
        dropbox_connection = CloudConnection.objects.create(
            user=user,
            provider='dropbox',
            email='test@dropbox.com',
            access_token='test_token',
        )
        
        with patch('cloudfiles.views.get_cloud_provider') as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.list_files.return_value = []
            mock_get_provider.return_value = mock_provider
            
            response = api_client.get(
                f'/api/v1/cloud/connections/{dropbox_connection.id}/list/'
            )
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@patch('cloudfiles.providers.google_drive.get_dynamic_setting')
class TestGoogleDriveUploadPermissions:
    """Test upload behavior in picker mode with folder permissions."""
    
    def test_upload_with_accessible_folder(self, mock_get_setting, google_drive_connection):
        """Test that upload works when folder is accessible (picker mode)."""
        def get_setting(key):
            return {
                'GOOGLE_DRIVE_MODE': 'picker',
                'GOOGLE_DRIVE_CLIENT_ID': 'test_client_id',
                'GOOGLE_DRIVE_CLIENT_SECRET': 'test_secret',
            }.get(key)
        mock_get_setting.side_effect = get_setting
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        from io import BytesIO
        
        provider = GoogleDriveProvider(connection=google_drive_connection)
        test_file = BytesIO(b"test content")
        
        with patch('cloudfiles.providers.google_drive.build') as mock_build:
            mock_service = MagicMock()
            mock_files = MagicMock()
            mock_create = MagicMock()
            mock_execute = MagicMock(return_value={'id': 'uploaded_file_id'})
            
            mock_create.execute = mock_execute
            mock_files.create.return_value = mock_create
            mock_service.files.return_value = mock_files
            mock_build.return_value = mock_service
            
            with patch('cloudfiles.providers.google_drive.Credentials') as mock_creds_class:
                mock_creds = MagicMock()
                mock_creds.expired = False
                mock_creds.token = 'test_token'
                mock_creds_class.return_value = mock_creds
                
                file_id = provider.upload_file(test_file, "test.pdf", "folder_id_123")
        
        assert file_id == 'uploaded_file_id'
    
    def test_upload_folder_permission_error(self, mock_get_setting, google_drive_connection):
        """Test clear error message when folder is not accessible (403/404)."""
        def get_setting(key):
            return {
                'GOOGLE_DRIVE_MODE': 'picker',
                'GOOGLE_DRIVE_CLIENT_ID': 'test_client_id',
                'GOOGLE_DRIVE_CLIENT_SECRET': 'test_secret',
            }.get(key)
        mock_get_setting.side_effect = get_setting
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        from cloudfiles.providers import CloudProviderError
        from googleapiclient.errors import HttpError
        from io import BytesIO
        
        provider = GoogleDriveProvider(connection=google_drive_connection)
        test_file = BytesIO(b"test content")
        
        with patch('cloudfiles.providers.google_drive.build') as mock_build:
            mock_service = MagicMock()
            mock_files = MagicMock()
            
            # Create a proper HttpError
            http_error = HttpError(
                resp=MagicMock(status=403),
                content=b'{"error": {"message": "Insufficient Permission"}}'
            )
            mock_files.create.side_effect = http_error
            mock_service.files.return_value = mock_files
            mock_build.return_value = mock_service
            
            with patch('cloudfiles.providers.google_drive.Credentials') as mock_creds_class:
                mock_creds = MagicMock()
                mock_creds.expired = False
                mock_creds.token = 'test_token'
                mock_creds_class.return_value = mock_creds
                
                with pytest.raises(CloudProviderError) as exc_info:
                    provider.upload_file(test_file, "test.pdf", "old_folder_id")
        
        error_msg = str(exc_info.value)
        assert "Cannot upload file" in error_msg
        assert "re-select the destination folder" in error_msg or "reconnect" in error_msg
