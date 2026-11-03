import io

import pypdf
import pytest
from django.utils import timezone
from reportlab.pdfgen import canvas as pdf_canvas

from documents.models import DocumentVersion
from esign.services import download_document_pdf
from esign.tasks import generate_signed_pdf_task


def _minimal_pdf_bytes(label="Source") -> bytes:
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=(612, 792))
    pdf.drawString(72, 720, label)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


@pytest.mark.django_db
class TestGenerateSignedPdfTask:
    def test_download_document_pdf_uses_string_download_url(self, document, monkeypatch):
        version = document.versions.get(is_primary=True)
        pdf_bytes = _minimal_pdf_bytes()

        monkeypatch.setattr(
            "esign.services.fileserver_client.generate_download_url",
            lambda storage_key, filename=None, is_internal=True: (
                f"http://fileserver.test/internal/download/{storage_key}"
            ),
        )

        class FakeResponse:
            content = pdf_bytes

            def raise_for_status(self):
                return None

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            def get(self, url, **kwargs):
                assert url.startswith("http://fileserver.test/")
                return FakeResponse()

            def close(self):
                return None

        monkeypatch.setattr("httpx.Client", FakeClient)

        assert download_document_pdf(version) == pdf_bytes

    def test_generate_signed_pdf_task_creates_primary_signed_version(
        self,
        signature_request,
        signer_user,
        document,
        monkeypatch,
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
        signer.otp_verified_at = timezone.now()
        signer.save()

        source_pdf = _minimal_pdf_bytes("Original")
        uploads = {}

        monkeypatch.setattr(
            "esign.services.fileserver_client.generate_download_url",
            lambda storage_key, filename=None, is_internal=True: (
                f"http://fileserver.test/internal/download/{storage_key}"
            ),
        )

        class FakeDownloadResponse:
            content = source_pdf

            def raise_for_status(self):
                return None

        class FakeHttpxClient:
            def __init__(self, *args, **kwargs):
                pass

            def get(self, url, **kwargs):
                return FakeDownloadResponse()

            def close(self):
                return None

        monkeypatch.setattr("httpx.Client", FakeHttpxClient)

        def fake_upload(storage_key, data, content_type=None, timeout=(10, 60)):
            uploads[storage_key] = data

        monkeypatch.setattr("esign.services.fileserver_client.upload_file", fake_upload)
        monkeypatch.setattr(
            "documents.tasks.generate_pdf_pages_task.delay", lambda *_a, **_k: None
        )
        monkeypatch.setattr(
            "esign.tasks.send_completion_email_task.delay", lambda *_a, **_k: None
        )

        assert document.versions.count() == 1

        generate_signed_pdf_task.run(str(signature_request.id), send_completion_emails=False)

        signature_request.refresh_from_db()
        assert signature_request.signed_document_version_id is not None
        signed_version = signature_request.signed_document_version
        assert signed_version.version_number == 2
        assert signed_version.is_primary is True
        assert DocumentVersion.objects.filter(document=document, is_primary=True).count() == 1

        signed_key = f"signatures/{signature_request.id}/signed_{document.id}.pdf"
        cert_key = f"signatures/{signature_request.id}/certificate.pdf"
        assert signed_key in uploads
        assert cert_key in uploads

        signed_reader = pypdf.PdfReader(io.BytesIO(uploads[signed_key]))
        assert len(signed_reader.pages) == 1
        merged_text = signed_reader.pages[0].extract_text() or ""
        assert "Typed Signature" in merged_text

    def test_reuses_orphan_signed_version_from_partial_run(
        self,
        signature_request,
        signer_user,
        document,
        monkeypatch,
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
        signer.otp_verified_at = timezone.now()
        signer.save()

        orphan = DocumentVersion.objects.create(
            document=document,
            version_number=2,
            storage_key="orphan-signed",
            original_storage_key="orphan-signed",
            content_type="application/pdf",
            type="pdf",
            file_size=100,
            is_primary=False,
            metadata={"signature_request_id": str(signature_request.id)},
        )

        source_pdf = _minimal_pdf_bytes("Original")
        uploads = {}

        monkeypatch.setattr(
            "esign.services.fileserver_client.generate_download_url",
            lambda storage_key, filename=None, is_internal=True: (
                f"http://fileserver.test/internal/download/{storage_key}"
            ),
        )

        class FakeDownloadResponse:
            content = source_pdf

            def raise_for_status(self):
                return None

        class FakeHttpxClient:
            def __init__(self, *args, **kwargs):
                pass

            def get(self, url, **kwargs):
                return FakeDownloadResponse()

            def close(self):
                return None

        monkeypatch.setattr("httpx.Client", FakeHttpxClient)
        monkeypatch.setattr(
            "esign.services.fileserver_client.upload_file",
            lambda storage_key, data, content_type=None, timeout=(10, 60): uploads.__setitem__(
                storage_key, data
            ),
        )
        monkeypatch.setattr(
            "documents.tasks.generate_pdf_pages_task.delay", lambda *_a, **_k: None
        )
        monkeypatch.setattr(
            "esign.tasks.send_completion_email_task.delay", lambda *_a, **_k: None
        )

        generate_signed_pdf_task.run(str(signature_request.id), send_completion_emails=False)

        signature_request.refresh_from_db()
        assert signature_request.signed_document_version_id == orphan.id
        assert document.versions.count() == 2
        orphan.refresh_from_db()
        assert orphan.is_primary is True
