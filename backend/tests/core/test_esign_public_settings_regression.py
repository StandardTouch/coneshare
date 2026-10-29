"""
Regression tests for esign public settings 500 error hotfix.
Tests that get_dynamic_setting works correctly without default= parameter,
and that esign endpoints properly enforce the runtime toggle.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import AppConfiguration, Organization
from documents.models import Document, DocumentVersion

User = get_user_model()


def _set_esign_enabled(enabled: bool):
    """Helper to set ESIGN_ENABLED via AppConfiguration."""
    AppConfiguration.objects.update_or_create(
        key='ESIGN_ENABLED',
        defaults={
            'value': 'true' if enabled else 'false',
            'description': 'Enable electronic signature feature.',
        }
    )
    cache.delete('app_config:ESIGN_ENABLED')
    cache.clear()


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Test Org")


@pytest.fixture
def user(db, organization):
    return User.objects.create_user(
        username="testuser@example.com",
        email="testuser@example.com",
        name="Test User",
        password="testpass123",
        organization=organization,
        is_active=True
    )


@pytest.fixture
def public_client():
    """Unauthenticated client."""
    return APIClient()


@pytest.fixture
def authenticated_client(user):
    """Authenticated client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def document_with_version(user, organization):
    """Create a document with a version for esign tests."""
    doc = Document.objects.create(
        name="test.pdf",
        owner=user,
        organization=organization,
        size_bytes=1024,
        mime_type="application/pdf"
    )
    version = DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        size_bytes=1024,
        mime_type="application/pdf",
        uploaded_by=user
    )
    return doc, version


@pytest.mark.django_db
class TestPublicSettingsEsignRegression:
    """Test that GET /api/v1/public/settings/ returns 200 with esign_enabled field."""

    def test_public_settings_returns_200_with_esign_disabled_by_default(self, public_client):
        """(a) GET /api/v1/public/settings/ returns 200 with esign_enabled false by default."""
        cache.clear()
        response = public_client.get(reverse('public_settings'))
        
        assert response.status_code == status.HTTP_200_OK
        assert 'esign_enabled' in response.data
        assert response.data['esign_enabled'] is False

    def test_public_settings_returns_200_with_esign_enabled_via_db(self, public_client):
        """(b) After creating AppConfiguration ESIGN_ENABLED=true it returns true."""
        _set_esign_enabled(True)
        
        response = public_client.get(reverse('public_settings'))
        
        assert response.status_code == status.HTTP_200_OK
        assert 'esign_enabled' in response.data
        assert response.data['esign_enabled'] is True

    def test_public_settings_toggle_esign_off_then_on(self, public_client):
        """Test toggling esign_enabled off and back on."""
        _set_esign_enabled(False)
        response = public_client.get(reverse('public_settings'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['esign_enabled'] is False
        
        _set_esign_enabled(True)
        response = public_client.get(reverse('public_settings'))
        assert response.status_code == status.HTTP_200_OK
        assert response.data['esign_enabled'] is True


@pytest.mark.django_db
class TestEsignEndpointRuntimeToggle:
    """(c) Test that esign endpoints respect the runtime toggle via AppConfiguration."""

    def test_signature_requests_list_returns_403_when_esign_disabled(self, authenticated_client):
        """Esign list endpoint returns 403 when ESIGN_ENABLED is off."""
        _set_esign_enabled(False)
        
        url = reverse('esign:signaturerequest-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'not enabled' in str(response.data).lower()

    def test_signature_requests_list_returns_200_when_esign_enabled(self, authenticated_client):
        """Esign list endpoint returns 200 when ESIGN_ENABLED is on via AppConfiguration."""
        _set_esign_enabled(True)
        
        url = reverse('esign:signaturerequest-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, dict)

    def test_signature_request_create_returns_403_when_esign_disabled(
        self, authenticated_client, document_with_version
    ):
        """Esign create endpoint returns 403 when ESIGN_ENABLED is off."""
        _set_esign_enabled(False)
        document, _ = document_with_version
        
        url = reverse('esign:signaturerequest-list')
        payload = {
            'document': document.id,
            'title': 'Test Request',
            'signers': [],
            'fields': []
        }
        response = authenticated_client.post(url, payload, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'not enabled' in str(response.data).lower()

    def test_signature_request_detail_returns_403_when_esign_disabled(
        self, authenticated_client
    ):
        """Esign detail endpoint returns 403 when ESIGN_ENABLED is off."""
        _set_esign_enabled(False)
        
        url = reverse('esign:signaturerequest-detail', kwargs={'pk': 99999})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'not enabled' in str(response.data).lower()
