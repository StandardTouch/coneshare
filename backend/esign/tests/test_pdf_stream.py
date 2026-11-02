import os
import tempfile

import pytest
from django.test import RequestFactory

from esign.pdf_stream import build_pdf_response_for_version, parse_range_header


class TestParseRangeHeader:
    def test_full_file_range(self):
        assert parse_range_header("bytes=0-99", 1000) == (0, 99)

    def test_open_ended_range(self):
        assert parse_range_header("bytes=500-", 1000) == (500, 999)

    def test_suffix_range(self):
        assert parse_range_header("bytes=-100", 1000) == (900, 999)

    def test_invalid_range(self):
        assert parse_range_header("invalid", 100) is None


@pytest.mark.django_db
class TestLocalPdfStream:
    def test_serves_full_pdf_with_accept_ranges(self, document):
        version = document.versions.filter(is_primary=True).first()
        pdf_bytes = b"%PDF-1.4 test content for range"

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["STORAGE_PATH"] = tmp
            file_path = os.path.join(tmp, version.storage_key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as handle:
                handle.write(pdf_bytes)

            factory = RequestFactory()
            request = factory.get("/api/v1/esign/documents/1/pdf/")
            response = build_pdf_response_for_version(version, request)

            assert response.status_code == 200
            assert response["Accept-Ranges"] == "bytes"
            body = getattr(response, "content", None) or b"".join(response.streaming_content)
            assert body == pdf_bytes

    def test_serves_partial_content(self, document):
        version = document.versions.filter(is_primary=True).first()
        pdf_bytes = b"%PDF-1.4 range-test-bytes"

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["STORAGE_PATH"] = tmp
            file_path = os.path.join(tmp, version.storage_key)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as handle:
                handle.write(pdf_bytes)

            factory = RequestFactory()
            request = factory.get(
                "/api/v1/esign/documents/1/pdf/",
                HTTP_RANGE="bytes=0-4",
            )
            response = build_pdf_response_for_version(version, request)

            assert response.status_code == 206
            assert response["Content-Range"] == f"bytes 0-4/{len(pdf_bytes)}"
            assert response.content == pdf_bytes[0:5]
