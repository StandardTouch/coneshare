import os
import tempfile

import pytest
from django.conf import settings
from rest_framework import status

from esign.models import SignatureOTP


@pytest.mark.django_db
class TestSignerPdfAccess:
    def test_unverified_otp_denied(
        self, signature_request, signer_user, api_client, enable_esign, document
    ):
        signer = signature_request.signers.first()
        api_client.force_authenticate(user=signer_user)

        response = api_client.get(f"/api/v1/esign/sign/{signer.token}/pdf/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_other_user_denied(
        self, signature_request, another_user, api_client, enable_esign, document
    ):
        signer = signature_request.signers.first()
        signer.otp_verified_at = signer.created_at
        signer.save()
        api_client.force_authenticate(user=another_user)

        response = api_client.get(f"/api/v1/esign/sign/{signer.token}/pdf/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_verified_signer_can_stream(
        self, signature_request, signer_user, api_client, enable_esign, document
    ):
        signature_request.status = "sent"
        signature_request.save()
        signer = signature_request.signers.first()
        signer.status = "sent"
        signer.save()
        api_client.force_authenticate(user=signer_user)

        api_client.post(f"/api/v1/esign/sign/{signer.token}/request_otp/")
        otp = SignatureOTP.objects.get(signer=signer)
        api_client.post(
            f"/api/v1/esign/sign/{signer.token}/verify_otp/",
            {"code": otp.code},
            format="json",
        )

        pdf_bytes = b"%PDF-1.4 signer-access-test"
        version = document.versions.filter(is_primary=True).first()

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["STORAGE_PATH"] = tmp
            file_path = os.path.join(tmp, version.storage_key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as handle:
                handle.write(pdf_bytes)

            response = api_client.get(f"/api/v1/esign/sign/{signer.token}/pdf/")
            assert response.status_code == status.HTTP_200_OK
            assert response["Accept-Ranges"] == "bytes"
            body = getattr(response, "content", None) or b"".join(response.streaming_content)
            assert body == pdf_bytes
