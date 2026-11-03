import io
import pytest
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.conf import settings
from reportlab.pdfgen import canvas as pdf_canvas

from core.models import Organization
from documents.models import Document, DocumentVersion
from esign.models import SignatureRequest, Signer, SignatureField, SignatureOTP

User = get_user_model()


@pytest.fixture
def organization(db):
    return Organization.objects.create(
        name="Test Org"
    )


@pytest.fixture
def user(db, organization):
    return User.objects.create_user(
        username="requester@example.com",
        email="requester@example.com",
        name="Test Requester",
        password="testpass123",
        organization=organization,
        is_active=True
    )


@pytest.fixture
def signer_user(db, organization):
    return User.objects.create_user(
        username="signer@example.com",
        email="signer@example.com",
        name="Test Signer",
        password="testpass123",
        organization=organization,
        is_active=True
    )


@pytest.fixture
def second_signer_user(db, organization):
    return User.objects.create_user(
        username="signer2@example.com",
        email="signer2@example.com",
        name="Second Signer",
        password="testpass123",
        organization=organization,
        is_active=True,
    )


@pytest.fixture
def other_organization(db):
    return Organization.objects.create(name="Other Org")


@pytest.fixture
def outsider_user(db, other_organization):
    return User.objects.create_user(
        username="outsider@example.com",
        email="outsider@example.com",
        name="Outsider",
        password="testpass123",
        organization=other_organization,
        is_active=True,
    )


@pytest.fixture
def mock_esign_pdf_pipeline(monkeypatch):
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=(612, 792))
    pdf.drawString(100, 700, "Test document")
    pdf.showPage()
    pdf.save()
    pdf_bytes = buffer.getvalue()

    def fake_download(_version):
        return pdf_bytes

    uploads = {}

    def fake_upload(storage_key, data, content_type=None, timeout=(10, 60)):
        uploads[storage_key] = data

    monkeypatch.setattr("esign.services.download_document_pdf", fake_download)
    monkeypatch.setattr("esign.services.fileserver_client.upload_file", fake_upload)


@pytest.fixture
def another_user(db, organization):
    """User not involved in the signature request"""
    return User.objects.create_user(
        username="other@example.com",
        email="other@example.com",
        name="Other User",
        password="testpass123",
        organization=organization,
        is_active=True
    )


@pytest.fixture
def document(db, organization, user):
    doc = Document.objects.create(
        name="Test Document.pdf",
        organization=organization,
        created_by=user,
        type="pdf",
        content_type="application/pdf",
        num_pages=3,
        status="ready",
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        storage_key="test-storage-key",
        original_storage_key="test-storage-key",
        content_type="application/pdf",
        type="pdf",
        file_size=1024,
        is_primary=True,
    )
    return doc


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def signer_authenticated_client(api_client, signer_user):
    api_client.force_authenticate(user=signer_user)
    return api_client


@pytest.fixture
def enable_esign(db, monkeypatch):
    """Enable esign feature via settings for tests"""
    # Just set the Django setting directly for tests
    monkeypatch.setattr(settings, 'ESIGN_ENABLED', True)
    yield
    monkeypatch.setattr(settings, 'ESIGN_ENABLED', False)


@pytest.fixture
def signature_request(db, organization, user, document, signer_user):
    """Create a signature request in draft status"""
    request = SignatureRequest.objects.create(
        organization=organization,
        document=document,
        created_by=user,
        title="Test Signature Request",
        message="Please sign this document",
        status='draft',
        signing_order=False,  # Parallel
        expires_at=timezone.now() + timedelta(days=7)
    )
    
    # Add signer
    signer = Signer.objects.create(
        signature_request=request,
        user=signer_user,
        signing_order=1
    )
    
    # Add signature field
    SignatureField.objects.create(
        signature_request=request,
        signer=signer,
        field_type='signature',
        page_number=1,
        x=10.0,
        y=80.0,
        width=30.0,
        height=8.0,
        required=True
    )
    
    return request


@pytest.mark.django_db
class TestFeatureToggle:
    """Test that ESIGN_ENABLED toggle works correctly"""
    
    def test_esign_disabled_blocks_list(self, authenticated_client):
        """When toggle is OFF, all endpoints should return 403"""
        response = authenticated_client.get('/api/v1/esign/requests/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'not enabled' in response.data['detail'].lower()
    
    def test_esign_enabled_allows_access(self, authenticated_client, enable_esign):
        """When toggle is ON, endpoints should be accessible"""
        response = authenticated_client.get('/api/v1/esign/requests/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPermissions:
    """Test authentication and authorization requirements"""
    
    def test_unauthenticated_cannot_list_requests(self, api_client, enable_esign):
        """Anonymous users cannot list signature requests"""
        response = api_client.get('/api/v1/esign/requests/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_authenticated_can_list_own_requests(self, authenticated_client, enable_esign, signature_request):
        """Users can list signature requests they created"""
        response = authenticated_client.get('/api/v1/esign/requests/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_organization_users_endpoint(self, authenticated_client, enable_esign, signer_user, another_user):
        """Authenticated users can fetch organization users for esign"""
        response = authenticated_client.get('/api/v1/esign/requests/organization-users/')
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        # Should include at least the signer_user and another_user
        user_ids = [u['id'] for u in response.data]
        assert signer_user.id in user_ids
        assert another_user.id in user_ids
        # Check structure
        if len(response.data) > 0:
            assert 'id' in response.data[0]
            assert 'name' in response.data[0]
            assert 'email' in response.data[0]
    
    def test_only_assigned_signer_can_sign(self, signature_request, signer_authenticated_client, 
                                          another_user, api_client, enable_esign):
        """Only the assigned signer (when authenticated) can access signing endpoints"""
        signer = signature_request.signers.first()
        token = signer.token
        
        # Send the request
        signature_request.status = 'sent'
        signature_request.save()
        signer.status = 'sent'
        signer.save()
        
        # Assigned signer can access
        response = signer_authenticated_client.get(f'/api/v1/esign/sign/{token}/')
        assert response.status_code == status.HTTP_200_OK
        
        # Different user cannot access (even when authenticated)
        api_client.force_authenticate(user=another_user)
        response = api_client.get(f'/api/v1/esign/sign/{token}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'not authorized' in response.data['detail'].lower()
    
    def test_unauthenticated_cannot_sign(self, signature_request, api_client, enable_esign):
        """Unauthenticated users cannot access signing endpoints"""
        signer = signature_request.signers.first()
        token = signer.token
        
        signature_request.status = 'sent'
        signature_request.save()
        
        response = api_client.get(f'/api/v1/esign/sign/{token}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestOTPGate:
    """Test OTP verification requirement"""
    
    def test_cannot_sign_without_otp(self, signature_request, signer_authenticated_client, enable_esign):
        """Signer cannot submit signature without OTP verification"""
        signer = signature_request.signers.first()
        field = signer.fields.first()
        
        signature_request.status = 'sent'
        signature_request.save()
        signer.status = 'sent'
        signer.save()
        
        # Try to submit without OTP
        response = signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/submit/',
            {
                'fields': [
                    {'field_id': field.id, 'value': 'data:image/png;base64,iVBORw0KGgo='}
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'OTP verification required' in response.data['detail']
    
    def test_can_request_otp(self, signature_request, signer_authenticated_client, enable_esign):
        """Signer can request OTP"""
        signer = signature_request.signers.first()
        
        signature_request.status = 'sent'
        signature_request.save()
        
        response = signer_authenticated_client.post(f'/api/v1/esign/sign/{signer.token}/request_otp/')
        assert response.status_code == status.HTTP_200_OK
        assert 'Verification code sent' in response.data['message']
        
        # OTP should be created
        assert SignatureOTP.objects.filter(signer=signer).exists()
    
    def test_can_verify_valid_otp(self, signature_request, signer_authenticated_client, enable_esign):
        """Signer can verify valid OTP"""
        signer = signature_request.signers.first()
        
        signature_request.status = 'sent'
        signature_request.save()
        
        # Request OTP
        signer_authenticated_client.post(f'/api/v1/esign/sign/{signer.token}/request_otp/')
        otp = SignatureOTP.objects.get(signer=signer)
        
        # Verify OTP
        response = signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/verify_otp/',
            {'code': otp.code}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['verified'] is True
        
        # Check signer status updated
        signer.refresh_from_db()
        assert signer.otp_verified_at is not None
        assert signer.status == 'otp_verified'
    
    def test_invalid_otp_rejected(self, signature_request, signer_authenticated_client, enable_esign):
        """Invalid OTP is rejected"""
        signer = signature_request.signers.first()
        
        signature_request.status = 'sent'
        signature_request.save()
        
        # Request OTP
        signer_authenticated_client.post(f'/api/v1/esign/sign/{signer.token}/request_otp/')
        
        # Try invalid OTP
        response = signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/verify_otp/',
            {'code': '999999'}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Invalid' in response.data['detail']


@pytest.mark.django_db
class TestSigningFlow:
    """Test signature workflow"""
    
    def test_parallel_signing_flow(self, signature_request, signer_authenticated_client, enable_esign):
        """Test parallel signing workflow"""
        signer = signature_request.signers.first()
        field = signer.fields.first()
        
        # Send request
        signature_request.status = 'sent'
        signature_request.save()
        signer.status = 'sent'
        signer.save()
        
        # Request and verify OTP
        signer_authenticated_client.post(f'/api/v1/esign/sign/{signer.token}/request_otp/')
        otp = SignatureOTP.objects.get(signer=signer)
        signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/verify_otp/',
            {'code': otp.code}
        )
        
        # Submit signature
        response = signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/submit/',
            {
                'fields': [
                    {'field_id': field.id, 'value': 'John Doe'}
                ]
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check signer marked as signed
        signer.refresh_from_db()
        assert signer.status == 'signed'
        assert signer.signed_at is not None
        
        # Check request completed (single signer)
        signature_request.refresh_from_db()
        assert signature_request.status == 'completed'
    
    def test_sequential_signing_flow(self, organization, user, document, api_client, enable_esign):
        """Test sequential signing workflow"""
        # Create request with 2 signers in sequential order
        signer1_user = User.objects.create_user(
            username="signer1@example.com",
            email="signer1@example.com",
            name="Signer One",
            password="test123",
            organization=organization,
            is_active=True
        )
        signer2_user = User.objects.create_user(
            username="signer2@example.com",
            email="signer2@example.com",
            name="Signer Two",
            password="test123",
            organization=organization,
            is_active=True
        )
        
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title="Sequential Test",
            status='sent',
            signing_order=True,  # Sequential
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        signer1 = Signer.objects.create(
            signature_request=request,
            user=signer1_user,
            signing_order=1,
            status='sent'
        )
        signer2 = Signer.objects.create(
            signature_request=request,
            user=signer2_user,
            signing_order=2,
            status='pending'
        )
        
        field1 = SignatureField.objects.create(
            signature_request=request,
            signer=signer1,
            field_type='signature',
            page_number=1,
            x=10.0, y=80.0, width=30.0, height=8.0,
            required=True
        )
        
        field2 = SignatureField.objects.create(
            signature_request=request,
            signer=signer2,
            field_type='signature',
            page_number=1,
            x=50.0, y=80.0, width=30.0, height=8.0,
            required=True
        )
        
        # Signer 2 cannot sign before signer 1
        api_client.force_authenticate(user=signer2_user)
        
        # Even with OTP, should be blocked
        api_client.post(f'/api/v1/esign/sign/{signer2.token}/request_otp/')
        otp2 = SignatureOTP.objects.get(signer=signer2)
        api_client.post(f'/api/v1/esign/sign/{signer2.token}/verify_otp/', {'code': otp2.code})
        
        response = api_client.post(
            f'/api/v1/esign/sign/{signer2.token}/submit/',
            {'fields': [{'field_id': field2.id, 'value': 'Signer Two'}]},
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'previous signers' in response.data['detail'].lower()
        
        # Signer 1 signs
        api_client.force_authenticate(user=signer1_user)
        api_client.post(f'/api/v1/esign/sign/{signer1.token}/request_otp/')
        otp1 = SignatureOTP.objects.get(signer=signer1)
        api_client.post(f'/api/v1/esign/sign/{signer1.token}/verify_otp/', {'code': otp1.code})
        
        response = api_client.post(
            f'/api/v1/esign/sign/{signer1.token}/submit/',
            {'fields': [{'field_id': field1.id, 'value': 'Signer One'}]},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        
        request.refresh_from_db()
        assert request.status == 'in_progress'
        
        # Now signer 2 can sign
        api_client.force_authenticate(user=signer2_user)
        response = api_client.post(
            f'/api/v1/esign/sign/{signer2.token}/submit/',
            {'fields': [{'field_id': field2.id, 'value': 'Signer Two'}]},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        
        request.refresh_from_db()
        assert request.status == 'completed'
    
    def test_can_decline_to_sign(self, signature_request, signer_authenticated_client, enable_esign):
        """Signer can decline to sign"""
        signer = signature_request.signers.first()
        
        signature_request.status = 'sent'
        signature_request.save()
        signer.status = 'sent'
        signer.save()
        
        response = signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/decline/',
            {'reason': 'I do not agree with the terms'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check signer declined
        signer.refresh_from_db()
        assert signer.status == 'declined'
        assert signer.decline_reason == 'I do not agree with the terms'
        
        # Check request declined
        signature_request.refresh_from_db()
        assert signature_request.status == 'declined'


@pytest.mark.django_db
class TestRequestManagement:
    """Test request creation, cancellation, reminders"""
    
    def test_can_cancel_request(self, signature_request, authenticated_client, enable_esign):
        """Requester can cancel active request"""
        signature_request.status = 'sent'
        signature_request.save()
        
        response = authenticated_client.post(f'/api/v1/esign/requests/{signature_request.id}/cancel/')
        assert response.status_code == status.HTTP_200_OK
        
        signature_request.refresh_from_db()
        assert signature_request.status == 'cancelled'
    
    def test_cannot_cancel_completed_request(self, signature_request, authenticated_client, enable_esign):
        """Cannot cancel completed request"""
        signature_request.status = 'completed'
        signature_request.save()
        
        response = authenticated_client.post(f'/api/v1/esign/requests/{signature_request.id}/cancel/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_can_send_reminders(self, signature_request, authenticated_client, enable_esign):
        """Requester can send reminders to pending signers"""
        signature_request.status = 'sent'
        signature_request.save()
        signer = signature_request.signers.first()
        signer.status = 'sent'
        signer.save()
        
        response = authenticated_client.post(f'/api/v1/esign/requests/{signature_request.id}/remind/')
        assert response.status_code == status.HTTP_200_OK
        assert 'Reminders sent' in response.data['message']


@pytest.mark.django_db
class TestAuditTrail:
    """Test that audit trail is properly recorded"""
    
    def test_actions_recorded(self, signature_request, signer_authenticated_client, enable_esign):
        """All signer actions are recorded"""
        signer = signature_request.signers.first()
        field = signer.fields.first()
        
        signature_request.status = 'sent'
        signature_request.save()
        signer.status = 'sent'
        signer.save()
        
        # View document
        signer_authenticated_client.get(f'/api/v1/esign/sign/{signer.token}/')
        assert signer.actions.filter(action='link_opened').exists()
        
        # Request OTP
        signer_authenticated_client.post(f'/api/v1/esign/sign/{signer.token}/request_otp/')
        assert signer.actions.filter(action='otp_requested').exists()
        
        # Verify OTP
        otp = SignatureOTP.objects.get(signer=signer)
        signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/verify_otp/',
            {'code': otp.code}
        )
        assert signer.actions.filter(action='otp_verified').exists()
        
        # Sign
        signer_authenticated_client.post(
            f'/api/v1/esign/sign/{signer.token}/submit/',
            {'fields': [{'field_id': field.id, 'value': 'Test Signature'}]},
            format='json'
        )
        assert signer.actions.filter(action='signed').exists()
        
        # IP and user agent should be recorded
        signed_action = signer.actions.filter(action='signed').first()
        assert signed_action.ip_address is not None


def _sign_with_otp(client, signer, field_id, value="Signed"):
    client.post(f"/api/v1/esign/sign/{signer.token}/request_otp/")
    otp = SignatureOTP.objects.get(signer=signer)
    client.post(
        f"/api/v1/esign/sign/{signer.token}/verify_otp/",
        {"code": otp.code},
    )
    return client.post(
        f"/api/v1/esign/sign/{signer.token}/submit/",
        {"fields": [{"field_id": field_id, "value": value}]},
        format="json",
    )


@pytest.mark.django_db
class TestUlidSignerIntegrationFlow:
    def test_full_flow_with_ulid_signers_and_pdf_completion(
        self,
        authenticated_client,
        api_client,
        enable_esign,
        mock_esign_pdf_pipeline,
        user,
        signer_user,
        second_signer_user,
        document,
    ):
        assert isinstance(signer_user.id, str)
        assert isinstance(second_signer_user.id, str)

        expires_at = (timezone.now() + timedelta(days=7)).isoformat()
        create_response = authenticated_client.post(
            "/api/v1/esign/requests/",
            {
                "document_id": document.id,
                "title": "ULID Signers Agreement",
                "message": "Please sign",
                "signing_order": False,
                "expires_at": expires_at,
                "signers": [
                    {"user_id": signer_user.id, "signing_order": 1},
                    {"user_id": second_signer_user.id, "signing_order": 1},
                ],
            },
            format="json",
        )
        assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
        request_id = create_response.data["id"]

        detail = authenticated_client.get(f"/api/v1/esign/requests/{request_id}/")
        signers_by_user = {s["user"]["id"]: s for s in detail.data["signers"]}
        signer_one = signers_by_user[signer_user.id]
        signer_two = signers_by_user[second_signer_user.id]

        fields_response = authenticated_client.post(
            f"/api/v1/esign/requests/{request_id}/update_fields/",
            {
                "fields": [
                    {
                        "signer_id": signer_one["id"],
                        "field_type": "signature",
                        "page_number": 1,
                        "x": 10.0,
                        "y": 20.0,
                        "width": 30.0,
                        "height": 8.0,
                        "required": True,
                    },
                    {
                        "signer_id": signer_two["id"],
                        "field_type": "signature",
                        "page_number": 1,
                        "x": 50.0,
                        "y": 20.0,
                        "width": 30.0,
                        "height": 8.0,
                        "required": True,
                    },
                ]
            },
            format="json",
        )
        assert fields_response.status_code == status.HTTP_200_OK, fields_response.data

        signature_request = SignatureRequest.objects.get(id=request_id)
        signer_one_model = signature_request.signers.get(user=signer_user)
        signer_two_model = signature_request.signers.get(user=second_signer_user)
        assert signer_one_model.fields.first().signer_id == signer_one_model.id
        assert signer_two_model.fields.first().signer_id == signer_two_model.id

        assert authenticated_client.post(
            f"/api/v1/esign/requests/{request_id}/send/"
        ).status_code == status.HTTP_200_OK

        api_client.force_authenticate(user=signer_user)
        submit_one = _sign_with_otp(
            api_client, signer_one_model, signer_one_model.fields.first().id, "Signer One"
        )
        assert submit_one.status_code == status.HTTP_200_OK

        api_client.force_authenticate(user=second_signer_user)
        submit_two = _sign_with_otp(
            api_client, signer_two_model, signer_two_model.fields.first().id, "Signer Two"
        )
        assert submit_two.status_code == status.HTTP_200_OK
        assert submit_two.data["status"] == "completed"

        signature_request.refresh_from_db()
        assert signature_request.status == "completed"
        assert signature_request.signed_document_version is not None
        assert signature_request.certificate_storage_key.endswith("certificate.pdf")
        assert DocumentVersion.objects.filter(document=document).count() >= 2

        from esign.services import generate_certificate_of_completion
        from pypdf import PdfReader

        cert_bytes = generate_certificate_of_completion(
            signature_request,
            list(signature_request.signers.order_by("signing_order")),
            signature_request.original_document_hash or "a" * 64,
            signature_request.metadata.get("signed_document_hash", "b" * 64),
        )
        assert len(PdfReader(io.BytesIO(cert_bytes)).pages) >= 1

    def test_create_rejects_signer_outside_organization(
        self,
        authenticated_client,
        enable_esign,
        document,
        outsider_user,
    ):
        expires_at = (timezone.now() + timedelta(days=7)).isoformat()
        response = authenticated_client.post(
            "/api/v1/esign/requests/",
            {
                "document_id": document.id,
                "title": "Invalid signer",
                "message": "",
                "signing_order": False,
                "expires_at": expires_at,
                "signers": [{"user_id": outsider_user.id, "signing_order": 1}],
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert SignatureRequest.objects.filter(title="Invalid signer").count() == 0
