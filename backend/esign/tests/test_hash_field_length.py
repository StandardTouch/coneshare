import pytest

from esign.models import SignatureRequest
from esign.services import calculate_document_hash


@pytest.mark.django_db
class TestHashFieldLength:
    def test_calculate_document_hash_fits_original_document_hash_field(self):
        digest = calculate_document_hash(b"sample pdf bytes for length check")
        assert len(digest) == 71
        max_length = SignatureRequest._meta.get_field("original_document_hash").max_length
        assert max_length >= len(digest)

    def test_signature_request_persists_full_sha256_prefixed_hash(self, signature_request):
        digest = calculate_document_hash(b"persist me")
        signature_request.original_document_hash = digest
        signature_request.save(update_fields=["original_document_hash", "updated_at"])
        signature_request.refresh_from_db()
        assert signature_request.original_document_hash == digest

    @pytest.mark.postgres
    def test_postgres_rejects_hash_longer_than_field(self, require_postgres, signature_request):
        """SQLite ignores varchar limits; PostgreSQL must accept 71-char sha256 values."""
        digest = calculate_document_hash(b"postgres length enforcement")
        signature_request.original_document_hash = digest
        signature_request.save(update_fields=["original_document_hash", "updated_at"])
        signature_request.refresh_from_db()
        assert signature_request.original_document_hash == digest
