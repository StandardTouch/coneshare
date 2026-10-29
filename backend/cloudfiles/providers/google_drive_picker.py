"""
Helper module for Google Drive Picker integration.

Provides utilities for the picker mode, including token endpoint support.
"""
import logging
from datetime import timezone as dt_timezone

from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

from core.services import get_dynamic_setting
from .base import CloudProviderError

logger = logging.getLogger(__name__)


def get_picker_access_token(connection):
    """
    Get a fresh access token for the Google Drive Picker.
    
    Refreshes the token if needed and returns the access token along with
    API key and App ID for the picker.
    
    Args:
        connection: CloudConnection instance for Google Drive
        
    Returns:
        dict with access_token, api_key, app_id
        
    Raises:
        CloudProviderError: if token refresh fails or credentials are invalid
    """
    mode = get_dynamic_setting('GOOGLE_DRIVE_MODE') or 'picker'
    if mode != 'picker':
        raise CloudProviderError("Google Drive Picker is only available in picker mode.")
    
    api_key = get_dynamic_setting('GOOGLE_DRIVE_API_KEY')
    app_id = get_dynamic_setting('GOOGLE_DRIVE_APP_ID')
    
    if not api_key or not app_id:
        raise CloudProviderError(
            "Google Drive Picker credentials (API Key and App ID) are not configured. "
            "Please configure GOOGLE_DRIVE_API_KEY and GOOGLE_DRIVE_APP_ID in admin settings."
        )
    
    client_id = get_dynamic_setting('GOOGLE_DRIVE_CLIENT_ID')
    client_secret = get_dynamic_setting('GOOGLE_DRIVE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        raise CloudProviderError("Google Drive OAuth credentials are not configured.")
    
    # Build credentials object
    naive_expiry = None
    if connection.expires_at:
        if timezone.is_aware(connection.expires_at):
            naive_expiry = connection.expires_at.astimezone(dt_timezone.utc).replace(tzinfo=None)
        else:
            naive_expiry = connection.expires_at
    
    creds = Credentials(
        token=connection.access_token,
        refresh_token=connection.refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        expiry=naive_expiry,
    )
    
    # Refresh if expired
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            
            # Update connection with new token
            connection.access_token = creds.token
            if creds.expiry:
                connection.expires_at = (
                    timezone.make_aware(creds.expiry, dt_timezone.utc)
                    if timezone.is_naive(creds.expiry)
                    else creds.expiry
                )
            else:
                connection.expires_at = None
            
            update_fields = ['access_token', 'expires_at']
            
            # Handle refresh token rotation
            if creds.refresh_token and creds.refresh_token != connection.refresh_token:
                connection.refresh_token = creds.refresh_token
                update_fields.append('refresh_token')
            
            connection.save(update_fields=update_fields)
            logger.info(f"Refreshed Google Drive token for picker, connection {connection.id}")
            
        except RefreshError as e:
            logger.error(f"Google Drive token refresh failed for connection {connection.id}: {e}")
            raise CloudProviderError(
                "Failed to refresh your Google Drive access token. "
                "Your authorization may have expired or been revoked. "
                "Please reconnect your Google Drive account."
            )
    
    return {
        'access_token': creds.token,
        'api_key': api_key,
        'app_id': app_id,
    }
