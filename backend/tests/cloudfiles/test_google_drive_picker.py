import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status

from cloudfiles.models import CloudConnection
from core.models import AppConfiguration


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
class TestGoogleDriveMode:
    """Test mode-dependent behavior for Google Drive."""
    
    def test_scopes_in_picker_mode(self, google_drive_connection):
        """Test that picker mode uses non-sensitive scopes."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='picker')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        provider = GoogleDriveProvider(connection=google_drive_connection)
        
        assert provider.mode == 'picker'
        assert 'https://www.googleapis.com/auth/drive.file' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/drive.readonly' not in provider.SCOPES
        assert 'openid' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.email' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.profile' in provider.SCOPES
    
    def test_scopes_in_browse_mode(self, google_drive_connection):
        """Test that browse mode uses full scopes including restricted ones."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='browse')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        provider = GoogleDriveProvider(connection=google_drive_connection)
        
        assert provider.mode == 'browse'
        assert 'https://www.googleapis.com/auth/drive.file' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/drive.readonly' in provider.SCOPES
        assert 'openid' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.email' in provider.SCOPES
        assert 'https://www.googleapis.com/auth/userinfo.profile' in provider.SCOPES
    
    def test_default_mode_is_picker(self, google_drive_connection):
        """Test that the default mode is picker when not configured."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        
        from cloudfiles.providers.google_drive import GoogleDriveProvider
        provider = GoogleDriveProvider(connection=google_drive_connection)
        
        assert provider.mode == 'picker'
        assert 'https://www.googleapis.com/auth/drive.readonly' not in provider.SCOPES


@pytest.mark.django_db
class TestGoogleDrivePickerTokenView:
    """Test the picker token endpoint."""
    
    def test_get_picker_token_success(self, authenticated_client, user, google_drive_connection):
        """Test successful retrieval of picker token."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='picker')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_API_KEY', value='test_api_key')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_APP_ID', value='123456789')
        
        with patch('cloudfiles.providers.google_drive_picker.Credentials') as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.token = 'fresh_access_token'
            mock_creds.expired = False
            mock_creds_class.return_value = mock_creds
            
            response = authenticated_client.get(
                f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access_token' in response.data
        assert 'api_key' in response.data
        assert 'app_id' in response.data
        assert response.data['api_key'] == 'test_api_key'
        assert response.data['app_id'] == '123456789'
    
    def test_picker_token_requires_auth(self, public_client, google_drive_connection):
        """Test that the picker token endpoint requires authentication."""
        response = public_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_picker_token_connection_not_found(self, authenticated_client, user):
        """Test 404 when connection doesn't exist."""
        response = authenticated_client.get(
            '/api/v1/cloud/connections/nonexistent-id/picker_token/'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_picker_token_only_for_google_drive(self, authenticated_client, user):
        """Test that the endpoint rejects non-Google Drive connections."""
        dropbox_connection = CloudConnection.objects.create(
            user=user,
            provider='dropbox',
            email='test@dropbox.com',
            access_token='test_token',
        )
        
        response = authenticated_client.get(
            f'/api/v1/cloud/connections/{dropbox_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'only available for Google Drive' in response.data['detail']
    
    def test_picker_token_requires_picker_mode(self, authenticated_client, user, google_drive_connection):
        """Test that picker token endpoint requires picker mode."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='browse')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        
        response = authenticated_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'only available in picker mode' in response.data['detail']
    
    def test_picker_token_requires_credentials(self, authenticated_client, user, google_drive_connection):
        """Test that picker token endpoint requires API key and App ID."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='picker')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        
        response = authenticated_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'API Key and App ID' in response.data['detail']
    
    def test_picker_token_no_secrets_leaked(self, authenticated_client, user, google_drive_connection):
        """Test that refresh token and client secret are never returned."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='picker')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_API_KEY', value='test_api_key')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_APP_ID', value='123456789')
        
        with patch('cloudfiles.providers.google_drive_picker.Credentials') as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.token = 'fresh_access_token'
            mock_creds.expired = False
            mock_creds_class.return_value = mock_creds
            
            response = authenticated_client.get(
                f'/api/v1/cloud/connections/{google_drive_connection.id}/picker_token/'
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'refresh_token' not in response.data
        assert 'client_secret' not in response.data
        assert 'test_secret' not in str(response.data)
        assert 'test_refresh_token' not in str(response.data)


@pytest.mark.django_db
class TestListEndpointGating:
    """Test that list endpoints are blocked in picker mode."""
    
    def test_list_files_blocked_in_picker_mode(self, authenticated_client, user, google_drive_connection):
        """Test that CloudFileListView returns 400 in picker mode."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='picker')
        
        response = authenticated_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/list/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'picker mode' in response.data['detail']
    
    def test_list_folders_blocked_in_picker_mode(self, authenticated_client, user, google_drive_connection):
        """Test that CloudFolderListView returns 400 in picker mode."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='picker')
        
        response = authenticated_client.get(
            f'/api/v1/cloud/connections/{google_drive_connection.id}/folders/'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'picker mode' in response.data['detail']
    
    def test_list_files_works_in_browse_mode(self, authenticated_client, user, google_drive_connection):
        """Test that list endpoints work in browse mode."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='browse')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_ID', value='test_client_id')
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_CLIENT_SECRET', value='test_secret')
        
        with patch('cloudfiles.providers.google_drive.build') as mock_build:
            mock_service = MagicMock()
            mock_files = MagicMock()
            mock_list = MagicMock()
            mock_execute = MagicMock(return_value={'files': []})
            
            mock_list.execute = mock_execute
            mock_files.list.return_value = mock_list
            mock_service.files.return_value = mock_files
            mock_build.return_value = mock_service
            
            with patch('cloudfiles.providers.google_drive.Credentials'):
                response = authenticated_client.get(
                    f'/api/v1/cloud/connections/{google_drive_connection.id}/list/'
                )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_endpoints_work_for_other_providers(self, authenticated_client, user):
        """Test that list endpoint gating only applies to Google Drive."""
        AppConfiguration.objects.create(key='GOOGLE_DRIVE_MODE', value='picker')
        
        dropbox_connection = CloudConnection.objects.create(
            user=user,
            provider='dropbox',
            email='test@dropbox.com',
            access_token='test_token',
        )
        
        AppConfiguration.objects.create(key='DROPBOX_APP_KEY', value='test_key')
        AppConfiguration.objects.create(key='DROPBOX_APP_SECRET', value='test_secret')
        
        with patch('cloudfiles.providers.dropbox.Dropbox') as mock_dropbox_class:
            mock_dbx = MagicMock()
            mock_dbx.files_list_folder.return_value.entries = []
            mock_dropbox_class.return_value = mock_dbx
            
            response = authenticated_client.get(
                f'/api/v1/cloud/connections/{dropbox_connection.id}/list/'
            )
        
        assert response.status_code == status.HTTP_200_OK
