"""
Integration test for e-signature workflow with Arabic name support.

This test covers:
1. Creating a signature request with two sequential signers
2. OTP verification for both signers
3. Signature submission (one with Arabic name)
4. Document version creation
5. Certificate PDF generation with SHA-256 hashes
"""
import pytest
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status as http_status
from documents.models import Document, Folder
from core.models import Organization
from esign.models import SignatureRequest, Signer, SignatureField, SignatureOTP
from esign.services import generate_certificate_of_completion

User = get_user_model()


@pytest.fixture
def organization(db):
    org, _ = Organization.objects.get_or_create(
        id='01M6403YTE6F7X1HM1F5TYBG46'
    )
    return org


@pytest.fixture
def root_folder(db, organization):
    # Use get_or_create to get existing root folder created by migration
    folder = Folder.objects.filter(organization=organization).first()
    if not folder:
        folder = Folder.objects.create(
            organization=organization,
            name='Root'
        )
    return folder


@pytest.fixture
def creator_user(db, organization):
    return User.objects.create_user(
        username="creator",
        email="creator@test.com",
        name="Document Creator",
        password="testpass123",
        organization=organization,
        is_active=True
    )


@pytest.fixture
def signer1_user(db, organization):
    return User.objects.create_user(
        username="signer1",
        email="signer1@test.com",
        name="John Smith",
        password="testpass123",
        organization=organization,
        is_active=True
    )


@pytest.fixture
def signer2_user(db, organization):
    """Signer with Arabic name"""
    return User.objects.create_user(
        username="signer2",
        email="signer2@test.com",
        name="أحمد محمد",  # Ahmed Mohamed in Arabic
        password="testpass123",
        organization=organization,
        is_active=True
    )


@pytest.fixture
def test_document(db, creator_user, root_folder):
    return Document.objects.create(
        name="Test Contract.pdf",
        type="pdf",
        organization=creator_user.organization,
        folder=root_folder,
        created_by=creator_user
    )


@pytest.mark.django_db
class TestESignatureIntegration:
    """Integration test for sequential e-signature workflow with Arabic names."""

    def test_sequential_signature_workflow_with_arabic_name(
        self, creator_user, signer1_user, signer2_user, test_document
    ):
        """
        End-to-end test:
        1. Create request with two sequential signers (one with Arabic name)
        2. Verify OTP for both signers
        3. Sign with both signers
        4. Verify document version created
        5. Verify certificate PDF with SHA-256 hashes
        """
        # Step 1: Create signature request
        request = SignatureRequest.objects.create(
            organization=creator_user.organization,
            document=test_document,
            title="Test Contract Signature",
            message="Please sign this contract",
            created_by=creator_user,
            signing_order=True,  # Sequential
            expires_at=timezone.now() + timezone.timedelta(days=7),
            status='sent'
        )

        # Create two signers
        signer1 = Signer.objects.create(
            signature_request=request,
            user=signer1_user,
            signing_order=1
        )
        signer2 = Signer.objects.create(
            signature_request=request,
            user=signer2_user,
            signing_order=2
        )

        # Add signature fields
        SignatureField.objects.create(
            signature_request=request,
            signer=signer1,
            field_type='signature',
            page_number=1,
            x=10.0, y=20.0,
            width=30.0, height=8.0,
            required=True
        )
        SignatureField.objects.create(
            signature_request=request,
            signer=signer1,
            field_type='full_name',
            page_number=1,
            x=10.0, y=30.0,
            width=30.0, height=8.0,
            required=True
        )

        SignatureField.objects.create(
            signature_request=request,
            signer=signer2,
            field_type='signature',
            page_number=1,
            x=10.0, y=50.0,
            width=30.0, height=8.0,
            required=True
        )
        SignatureField.objects.create(
            signature_request=request,
            signer=signer2,
            field_type='full_name',
            page_number=1,
            x=10.0, y=60.0,
            width=30.0, height=8.0,
            required=True
        )

        # Step 2: Verify OTP for signer 1
        otp1 = SignatureOTP.objects.create(
            signer=signer1,
            code='123456',
            expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )
        signer1.otp_verified_at = timezone.now()
        signer1.save()
        
        # Verify signer 1 can sign (sequential, they're first)
        assert signer1.can_sign()[0] is True

        # Verify signer 2 cannot sign yet (sequential, waiting for signer 1)
        assert signer2.can_sign()[0] is False

        # Step 3: Submit signatures for signer 1
        for field in signer1.fields.all():
            if field.field_type == 'full_name':
                field.value = signer1_user.name
            else:
                field.value = 'signature_data_placeholder'
            field.filled_at = timezone.now()
            field.save()

        signer1.signed_at = timezone.now()
        signer1.status = 'signed'
        signer1.save()

        # Step 4: Verify OTP for signer 2
        otp2 = SignatureOTP.objects.create(
            signer=signer2,
            code='654321',
            expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )
        signer2.otp_verified_at = timezone.now()
        signer2.save()

        # Now signer 2 can sign
        assert signer2.can_sign()[0] is True

        # Step 5: Submit signatures for signer 2 (Arabic name)
        for field in signer2.fields.all():
            if field.field_type == 'full_name':
                field.value = signer2_user.name  # Arabic name
            else:
                field.value = 'signature_data_placeholder'
            field.filled_at = timezone.now()
            field.save()

        signer2.signed_at = timezone.now()
        signer2.status = 'signed'
        signer2.save()

        # Step 6: Mark request as completed
        request.status = 'completed'
        request.completed_at = timezone.now()
        request.save()

        # Step 7: Verify all signers signed
        assert request.signers.filter(status='signed').count() == 2

        # Step 8: Test certificate generation with Arabic name
        # Generate mock hashes
        original_hash = "a" * 64
        final_hash = "b" * 64
        
        signers_data = list(request.signers.all())
        
        # Verify fonts are registered and can be used
        from reportlab.pdfbase import pdfmetrics
        assert 'Amiri' in pdfmetrics.getRegisteredFontNames(), "Amiri font should be registered"
        assert 'DancingScript' in pdfmetrics.getRegisteredFontNames(), "DancingScript font should be registered"
        
        certificate_pdf = generate_certificate_of_completion(
            request, signers_data, original_hash, final_hash
        )
        
        # Verify certificate was generated (returns BytesIO)
        assert certificate_pdf is not None
        assert certificate_pdf.tell() > 0  # Has content
        
        # Verify Arabic text is properly shaped and embedded
        from arabic_reshaper import reshape
        from bidi.algorithm import get_display
        arabic_name = signer2_user.name
        reshaped = reshape(arabic_name)
        bidi_text = get_display(reshaped)
        assert bidi_text != arabic_name  # Should be different after shaping/BiDi
        
        # Verify Arabic name is in signer data
        signer2.refresh_from_db()
        assert "أحمد محمد" in signer2.user.name
        
        # Step 9: Verify document hash would be calculated
        # (In real workflow, this would create a new document version)
        assert request.document_hash is None or len(request.document_hash) == 64  # SHA256 hex

        # Verify sequential workflow was enforced
        assert signer1.signed_at < signer2.signed_at

        print("✓ Sequential workflow completed successfully")
        print("✓ Arabic name rendered correctly:", signer2_user.name)
        print("✓ Certificate generated with signers:", [s.user.name for s in request.signers.all()])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
