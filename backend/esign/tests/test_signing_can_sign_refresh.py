import pytest
from rest_framework import status

from esign.models import SignatureOTP


@pytest.mark.django_db
class TestSigningCanSignAfterOtp:
    def test_signing_data_can_sign_after_otp_verify(
        self, signature_request, signer_authenticated_client, enable_esign
    ):
        signer = signature_request.signers.first()
        signature_request.status = "sent"
        signature_request.save()
        signer.status = "sent"
        signer.save()

        before = signer_authenticated_client.get(f"/api/v1/esign/sign/{signer.token}/")
        assert before.status_code == status.HTTP_200_OK
        assert before.data["can_sign"] is False
        assert "OTP" in before.data["can_sign_reason"]

        signer_authenticated_client.post(f"/api/v1/esign/sign/{signer.token}/request_otp/")
        otp = SignatureOTP.objects.get(signer=signer)
        verify = signer_authenticated_client.post(
            f"/api/v1/esign/sign/{signer.token}/verify_otp/",
            {"code": otp.code},
            format="json",
        )
        assert verify.status_code == status.HTTP_200_OK

        after = signer_authenticated_client.get(f"/api/v1/esign/sign/{signer.token}/")
        assert after.status_code == status.HTTP_200_OK
        assert after.data["can_sign"] is True
        assert after.data["otp_verified_at"]
