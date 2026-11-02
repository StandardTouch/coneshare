import os
import tempfile

import pytest
from django.urls import reverse
from rest_framework import status

from esign.models import SignatureOTP


@pytest.mark.django_db
class TestUlidPdfRoutes:
    """Regression: PDF routes must accept ULID primary keys (not <int:> converters)."""

    def test_document_pdf_url_resolves_with_ulid(
        self, document, authenticated_client, enable_esign
    ):
        doc_id = str(document.id)
        assert len(doc_id) > 10
        url = reverse("esign-document-pdf", kwargs={"document_id": doc_id})

        pdf_bytes = b"%PDF-1.4 ulid-route-test"
        version = document.versions.filter(is_primary=True).first()

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["STORAGE_PATH"] = tmp
            file_path = os.path.join(tmp, version.storage_key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as handle:
                handle.write(pdf_bytes)

            response = authenticated_client.get(url)
            assert response.status_code == status.HTTP_200_OK
            assert response["Accept-Ranges"] == "bytes"

    def test_request_pdf_url_resolves_with_ulid(
        self, signature_request, authenticated_client, enable_esign, document
    ):
        request_id = str(signature_request.id)
        url = reverse("esign-request-pdf", kwargs={"request_id": request_id})
        version = document.versions.filter(is_primary=True).first()
        pdf_bytes = b"%PDF-1.4 request-ulid"

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["STORAGE_PATH"] = tmp
            file_path = os.path.join(tmp, version.storage_key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as handle:
                handle.write(pdf_bytes)

            response = authenticated_client.get(url)
            assert response.status_code == status.HTTP_200_OK

    def test_submit_signature_accepts_ulid_field_ids(
        self, signature_request, signer_authenticated_client, enable_esign
    ):
        signer = signature_request.signers.first()
        field = signer.fields.first()

        signature_request.status = "sent"
        signature_request.save()
        signer.status = "sent"
        signer.save()

        signer_authenticated_client.post(f"/api/v1/esign/sign/{signer.token}/request_otp/")
        otp = SignatureOTP.objects.get(signer=signer)
        signer_authenticated_client.post(
            f"/api/v1/esign/sign/{signer.token}/verify_otp/",
            {"code": otp.code},
            format="json",
        )

        field_id = str(field.id)
        response = signer_authenticated_client.post(
            f"/api/v1/esign/sign/{signer.token}/submit/",
            {"fields": [{"field_id": field_id, "value": "Signed Name"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
