import io

import pypdf
import pytest
from django.test import override_settings
from django.utils import timezone

from esign.services import process_signature_completion
from esign.tasks import generate_signed_pdf_task


def _patch_file_io(monkeypatch, original_pdf: bytes):
    uploads = {}

    monkeypatch.setattr(
        "esign.services.download_document_pdf",
        lambda _version: original_pdf,
    )

    def fake_upload(storage_key, data, content_type=None, timeout=(10, 60)):
        uploads[storage_key] = data

    monkeypatch.setattr("esign.services.fileserver_client.upload_file", fake_upload)
    return uploads


def _build_single_page_pdf() -> bytes:
    from reportlab.pdfgen import canvas as pdf_canvas

    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=(612, 792))
    c.drawString(100, 700, "Source document")
    c.save()
    buf.seek(0)
    return buf.getvalue()


@pytest.mark.django_db
class TestAppendCertificateFlag:
    @override_settings(ESIGN_APPEND_CERTIFICATE=False)
    def test_signed_pdf_page_count_matches_source_when_flag_off(
        self, signature_request, signer_user, monkeypatch
    ):
        from esign.models import SignatureField

        source_bytes = _build_single_page_pdf()
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
        signer.save()

        uploads = _patch_file_io(monkeypatch, source_bytes)
        _, _, _, final_hash, final_bytes = process_signature_completion(signature_request)

        reader = pypdf.PdfReader(io.BytesIO(final_bytes))
        assert len(reader.pages) == 1
        assert final_hash.startswith("sha256:")
        signed_key = f"signatures/{signature_request.id}/signed_{signature_request.document.id}.pdf"
        assert len(pypdf.PdfReader(io.BytesIO(uploads[signed_key])).pages) == 1
        assert "Certificate of Completion" not in (reader.pages[0].extract_text() or "")

    @override_settings(ESIGN_APPEND_CERTIFICATE=True)
    def test_certificate_appended_when_flag_on(self, signature_request, signer_user, monkeypatch):
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
        signer.save()

        source_bytes = _build_single_page_pdf()
        uploads = _patch_file_io(monkeypatch, source_bytes)
        process_signature_completion(signature_request)

        signed_key = f"signatures/{signature_request.id}/signed_{signature_request.document.id}.pdf"
        reader = pypdf.PdfReader(io.BytesIO(uploads[signed_key]))
        assert len(reader.pages) == 2
        assert "Certificate of Completion" in (reader.pages[-1].extract_text() or "")

    @override_settings(ESIGN_APPEND_CERTIFICATE=False)
    def test_generate_signed_pdf_task_respects_flag(
        self, signature_request, signer_user, document, monkeypatch
    ):
        signer = signature_request.signers.get(user=signer_user)
        field = signer.fields.first()
        field.value = "Typed Signature"
        field.filled_at = timezone.now()
        field.save()
        signature_request.status = "completed"
        signature_request.completed_at = timezone.now()
        signature_request.save()
        signer.status = "signed"
        signer.signed_at = timezone.now()
        signer.save()

        source_bytes = _build_single_page_pdf()
        uploads = _patch_file_io(monkeypatch, source_bytes)
        monkeypatch.setattr("documents.tasks.generate_pdf_pages_task.delay", lambda *_a, **_k: None)
        monkeypatch.setattr("django.db.transaction.on_commit", lambda fn: fn())

        generate_signed_pdf_task.run(str(signature_request.id), send_completion_emails=False)

        signed_key = f"signatures/{signature_request.id}/signed_{document.id}.pdf"
        reader = pypdf.PdfReader(io.BytesIO(uploads[signed_key]))
        assert len(reader.pages) == 1

        signature_request.refresh_from_db()
        assert signature_request.metadata.get("signed_document_hash", "").startswith("sha256:")
