import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient

from core.models import Organization
from documents.models import Document, DocumentVersion
from esign.models import SignatureRequest, Signer

User = get_user_model()


@pytest.fixture
def organization(db):
    return Organization.objects.create(name="Await List Org")


@pytest.fixture
def owner(db, organization):
    return User.objects.create_user(
        username="owner@example.com",
        email="owner@example.com",
        name="Owner",
        password="testpass123",
        organization=organization,
        is_active=True,
    )


@pytest.fixture
def signer_user(db, organization):
    return User.objects.create_user(
        username="signer@example.com",
        email="signer@example.com",
        name="Signer",
        password="testpass123",
        organization=organization,
        is_active=True,
    )


@pytest.fixture
def other_signer(db, organization):
    return User.objects.create_user(
        username="signer2@example.com",
        email="signer2@example.com",
        name="Signer Two",
        password="testpass123",
        organization=organization,
        is_active=True,
    )


@pytest.fixture
def document(db, organization, owner):
    doc = Document.objects.create(
        name="Contract.pdf",
        organization=organization,
        created_by=owner,
        type="pdf",
        status="ready",
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        storage_key="await-list-key",
        is_primary=True,
    )
    return doc


@pytest.fixture
def enable_esign(db, monkeypatch):
    from django.conf import settings
    monkeypatch.setattr(settings, "ESIGN_ENABLED", True)


@pytest.mark.django_db
class TestAwaitingListSerializer:
    def test_awaiting_view_includes_signer_token_and_status_ulids(
        self, owner, signer_user, document, enable_esign
    ):
        request = SignatureRequest.objects.create(
            organization=owner.organization,
            document=document,
            created_by=owner,
            title="Please sign",
            status="sent",
            expires_at=timezone.now() + timedelta(days=7),
        )
        signer = Signer.objects.create(
            signature_request=request,
            user=signer_user,
            signing_order=1,
            status="sent",
        )

        client = APIClient()
        client.force_authenticate(user=signer_user)
        response = client.get("/api/v1/esign/requests/", {"view": "awaiting"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        row = response.data[0]
        assert str(row["id"]) == str(request.id)
        assert row["signer_token"] == signer.token
        assert row["signer_status"] == "sent"
        assert row["can_sign"] is False
        assert "OTP" in row["can_sign_reason"]

    def test_created_view_omits_signer_token(
        self, owner, signer_user, document, enable_esign
    ):
        request = SignatureRequest.objects.create(
            organization=owner.organization,
            document=document,
            created_by=owner,
            title="Owner list",
            status="sent",
        )
        Signer.objects.create(
            signature_request=request,
            user=signer_user,
            status="sent",
        )

        client = APIClient()
        client.force_authenticate(user=owner)
        response = client.get("/api/v1/esign/requests/", {"view": "created"})
        assert response.status_code == status.HTTP_200_OK
        row = response.data[0]
        assert row["signer_token"] is None
        assert row["signer_status"] is None

    def test_sequential_second_signer_not_in_awaiting_until_sent(
        self, owner, signer_user, other_signer, document, enable_esign
    ):
        request = SignatureRequest.objects.create(
            organization=owner.organization,
            document=document,
            created_by=owner,
            title="Sequential",
            status="in_progress",
            signing_order=True,
        )
        Signer.objects.create(
            signature_request=request,
            user=signer_user,
            signing_order=1,
            status="signed",
        )
        Signer.objects.create(
            signature_request=request,
            user=other_signer,
            signing_order=2,
            status="pending",
        )

        client = APIClient()
        client.force_authenticate(user=other_signer)
        response = client.get("/api/v1/esign/requests/", {"view": "awaiting"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

        second = request.signers.get(user=other_signer)
        second.status = "sent"
        second.save()
        response = client.get("/api/v1/esign/requests/", {"view": "awaiting"})
        assert len(response.data) == 1
        assert response.data[0]["signer_token"] == second.token
        assert response.data[0]["can_sign"] is False
