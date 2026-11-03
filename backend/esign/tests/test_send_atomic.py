import pytest


@pytest.mark.django_db
class TestSendSignatureRequestAtomic:
    def test_send_rolls_back_status_when_signer_action_fails(
        self, signature_request, authenticated_client, enable_esign, monkeypatch
    ):
        signature_request.status = "draft"
        signature_request.save()
        assert signature_request.fields.exists()
        assert signature_request.signers.exists()

        def flaky_record(signer, action, request=None, metadata=None):
            raise RuntimeError("simulated audit failure")

        monkeypatch.setattr("esign.views.record_signer_action", flaky_record)

        authenticated_client.raise_request_exception = True
        with pytest.raises(RuntimeError, match="simulated audit failure"):
            authenticated_client.post(f"/api/v1/esign/requests/{signature_request.id}/send/")

        signature_request.refresh_from_db()
        assert signature_request.status == "draft"
