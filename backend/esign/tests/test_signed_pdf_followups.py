import pytest
from django.utils import timezone

from esign.tasks import _execute_signed_pdf_followups, generate_signed_pdf_task


@pytest.mark.django_db
class TestSignedPdfFollowups:
    def test_enqueue_failure_does_not_propagate(self, monkeypatch):
        def boom(*_args, **_kwargs):
            raise RuntimeError("broker unavailable")

        monkeypatch.setattr("documents.tasks.generate_pdf_pages_task.delay", boom)
        monkeypatch.setattr("esign.tasks.send_completion_email_task.delay", boom)

        _execute_signed_pdf_followups("version-id", "request-id", False, sync=False)

    def test_generate_signed_pdf_task_survives_followup_enqueue_failure(
        self,
        signature_request,
        signer_user,
        document,
        monkeypatch,
    ):
        from esign.models import SignatureField

        signer = signature_request.signers.get(user=signer_user)
        field = signer.fields.first()
        field.value = "Signed"
        field.filled_at = timezone.now()
        field.save()

        signature_request.status = "completed"
        signature_request.completed_at = timezone.now()
        signature_request.save()
        signer.status = "signed"
        signer.signed_at = timezone.now()
        signer.otp_verified_at = timezone.now()
        signer.save()

        monkeypatch.setattr(
            "esign.tasks.process_signature_completion",
            lambda _req: ("signed/key.pdf", "cert/key.pdf", "sha256:" + "a" * 64, "sha256:" + "b" * 64, b"%PDF-1.4"),
        )

        def boom(*_args, **_kwargs):
            raise RuntimeError("broker unavailable")

        monkeypatch.setattr("documents.tasks.generate_pdf_pages_task.delay", boom)
        monkeypatch.setattr("django.db.transaction.on_commit", lambda fn: fn())

        generate_signed_pdf_task.run(
            str(signature_request.id),
            send_completion_emails=False,
            run_followups_sync=False,
        )

        signature_request.refresh_from_db()
        assert signature_request.signed_document_version_id is not None
