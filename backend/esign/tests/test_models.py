import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from core.models import Organization, User
from documents.models import Document, Folder
from esign.models import (
    SignatureRequest, Signer, SignatureField,
    SignerAction, SignatureOTP
)


@pytest.fixture
def organization(db):
    return Organization.objects.create(name='Test Org')


@pytest.fixture
def user(db, organization):
    return User.objects.create(
        organization=organization,
        email='user@test.com',
        username='user',
        name='Test User'
    )


@pytest.fixture
def signer_user(db, organization):
    return User.objects.create(
        organization=organization,
        email='signer@test.com',
        username='signer',
        name='Test Signer'
    )


@pytest.fixture
def document(db, organization, user):
    root_folder = Folder.objects.create(
        organization=organization,
        name='__root__',
        folder_type='root'
    )
    return Document.objects.create(
        organization=organization,
        folder=root_folder,
        name='test.pdf',
        type='pdf',
        created_by=user
    )


@pytest.mark.django_db
class TestSignatureRequestModel:
    def test_create_signature_request(self, organization, user, document):
        """Test creating a basic signature request."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test Request',
            signing_order=False
        )
        
        assert request.status == 'draft'
        assert request.title == 'Test Request'
        assert not request.signing_order
    
    def test_can_cancel(self, organization, user, document):
        """Test can_cancel method."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test',
            status='draft'
        )
        assert not request.can_cancel()
        
        request.status = 'sent'
        request.save()
        assert request.can_cancel()
        
        request.status = 'completed'
        request.save()
        assert not request.can_cancel()


@pytest.mark.django_db
class TestSignerModel:
    def test_create_signer(self, organization, user, signer_user, document):
        """Test creating a signer."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test'
        )
        
        signer = Signer.objects.create(
            signature_request=request,
            user=signer_user,
            signing_order=1
        )
        
        assert signer.status == 'pending'
        assert signer.token
        assert len(signer.token) > 32
    
    def test_can_sign_requires_otp(self, organization, user, signer_user, document):
        """Test that signing requires OTP verification."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test',
            status='sent'
        )
        
        signer = Signer.objects.create(
            signature_request=request,
            user=signer_user,
            status='sent'
        )
        
        can_sign, reason = signer.can_sign()
        assert not can_sign
        assert 'OTP' in reason
    
    def test_can_sign_sequential_order(self, organization, user, signer_user, document):
        """Test sequential signing order enforcement."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test',
            status='sent',
            signing_order=True
        )
        
        signer1 = Signer.objects.create(
            signature_request=request,
            user=user,
            signing_order=1,
            status='sent',
            otp_verified_at=timezone.now()
        )
        
        signer2 = Signer.objects.create(
            signature_request=request,
            user=signer_user,
            signing_order=2,
            status='pending',
            otp_verified_at=timezone.now()
        )
        
        # Signer 2 cannot sign before signer 1
        can_sign, reason = signer2.can_sign()
        assert not can_sign
        assert 'previous signers' in reason.lower()
        
        # After signer 1 signs
        signer1.status = 'signed'
        signer1.save()
        
        # Signer 2 can now sign
        can_sign, reason = signer2.can_sign()
        assert can_sign
    
    def test_unique_constraint(self, organization, user, signer_user, document):
        """Test that same user cannot be added twice to same request."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test'
        )
        
        Signer.objects.create(
            signature_request=request,
            user=signer_user,
            signing_order=1
        )
        
        with pytest.raises(Exception):  # IntegrityError
            Signer.objects.create(
                signature_request=request,
                user=signer_user,
                signing_order=2
            )


@pytest.mark.django_db
class TestSignatureFieldModel:
    def test_create_field(self, organization, user, signer_user, document):
        """Test creating a signature field."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test'
        )
        
        signer = Signer.objects.create(
            signature_request=request,
            user=signer_user
        )
        
        field = SignatureField.objects.create(
            signature_request=request,
            signer=signer,
            field_type='signature',
            page_number=1,
            x=10.0,
            y=80.0,
            width=30.0,
            height=8.0
        )
        
        assert field.field_type == 'signature'
        assert field.required


@pytest.mark.django_db
class TestSignatureOTP:
    def test_otp_generation(self, organization, user, signer_user, document):
        """Test OTP creation and validation."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test'
        )
        
        signer = Signer.objects.create(
            signature_request=request,
            user=signer_user
        )
        
        otp = SignatureOTP.objects.create(
            signer=signer,
            code='123456'
        )
        
        assert otp.is_valid()
        assert not otp.verified
        assert otp.attempts == 0
    
    def test_otp_expiry(self, organization, user, signer_user, document):
        """Test OTP expiration."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test'
        )
        
        signer = Signer.objects.create(
            signature_request=request,
            user=signer_user
        )
        
        # Create expired OTP
        otp = SignatureOTP.objects.create(
            signer=signer,
            code='123456',
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        
        assert not otp.is_valid()
    
    def test_otp_max_attempts(self, organization, user, signer_user, document):
        """Test OTP max attempts."""
        request = SignatureRequest.objects.create(
            organization=organization,
            document=document,
            created_by=user,
            title='Test'
        )
        
        signer = Signer.objects.create(
            signature_request=request,
            user=signer_user
        )
        
        otp = SignatureOTP.objects.create(
            signer=signer,
            code='123456',
            attempts=5
        )
        
        assert not otp.is_valid()
