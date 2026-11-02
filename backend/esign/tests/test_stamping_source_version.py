import pytest

from documents.models import DocumentVersion
from esign.services import calculate_document_hash, get_stamping_source_version


@pytest.mark.django_db
class TestGetStampingSourceVersion:
    def test_prefers_newest_non_signed_when_no_hash(self, document, signature_request):
        v1 = document.versions.get(version_number=1)
        v2 = DocumentVersion.objects.create(
            document=document,
            version_number=2,
            storage_key="storage-v2",
            original_storage_key="storage-v2",
            content_type="application/pdf",
            type="pdf",
            file_size=2048,
            is_primary=True,
        )
        v1.is_primary = False
        v1.save(update_fields=["is_primary"])

        source = get_stamping_source_version(signature_request)
        assert source.pk == v2.pk

    def test_matches_original_document_hash_over_older_versions(
        self, document, signature_request, monkeypatch
    ):
        v1_bytes = b"pdf-bytes-version-one"
        v2_bytes = b"pdf-bytes-version-two"

        v1 = document.versions.get(version_number=1)
        v1.storage_key = "storage-v1"
        v1.original_storage_key = "storage-v1"
        v1.is_primary = False
        v1.save()

        v2 = DocumentVersion.objects.create(
            document=document,
            version_number=2,
            storage_key="storage-v2",
            original_storage_key="storage-v2",
            content_type="application/pdf",
            type="pdf",
            file_size=2048,
            is_primary=True,
        )

        signed_v3 = DocumentVersion.objects.create(
            document=document,
            version_number=3,
            storage_key="storage-signed",
            original_storage_key="storage-signed",
            content_type="application/pdf",
            type="pdf",
            file_size=4096,
            is_primary=True,
            metadata={"signature_request_id": str(signature_request.id)},
        )
        v2.is_primary = False
        v2.save(update_fields=["is_primary"])

        signature_request.signed_document_version = signed_v3
        signature_request.original_document_hash = calculate_document_hash(v2_bytes).removeprefix(
            "sha256:"
        )
        signature_request.save()

        def fake_download(version):
            if version.storage_key == "storage-v1":
                return v1_bytes
            if version.storage_key == "storage-v2":
                return v2_bytes
            raise AssertionError(f"unexpected download for {version.storage_key}")

        monkeypatch.setattr("esign.services.download_document_pdf", fake_download)

        source = get_stamping_source_version(signature_request)
        assert source.pk == v2.pk
        assert source.pk != v1.pk
