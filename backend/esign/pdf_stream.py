"""
Range-aware PDF streaming for e-sign viewers.

Proxies bytes from the Go file server (http.ServeFile supports Range) through
authenticated Django endpoints for pdf.js byte-range loading.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Iterator, Optional, Tuple

import httpx
from django.conf import settings
from django.http import FileResponse, HttpResponse, StreamingHttpResponse

from documents.fileserver import fileserver_client
from documents.models import DocumentVersion

logger = logging.getLogger(__name__)

RANGE_HEADER_RE = re.compile(r"^bytes=(\d*)-(\d*)$", re.IGNORECASE)


def parse_range_header(range_header: str, file_size: int) -> Optional[Tuple[int, int]]:
    """Parse a Range header into (start, end) inclusive byte indices."""
    if not range_header or file_size <= 0:
        return None

    match = RANGE_HEADER_RE.match(range_header.strip())
    if not match:
        return None

    start_str, end_str = match.groups()
    if start_str == "" and end_str == "":
        return None

    if start_str == "":
        suffix_length = int(end_str)
        if suffix_length <= 0:
            return None
        start = max(file_size - suffix_length, 0)
        end = file_size - 1
    else:
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1

    if start >= file_size or start < 0:
        return None
    end = min(end, file_size - 1)
    if end < start:
        return None
    return start, end


def _local_storage_path(storage_key: str) -> Optional[str]:
    storage_root = getattr(settings, "ESIGN_PDF_STORAGE_PATH", None) or os.environ.get("STORAGE_PATH")
    if not storage_root:
        return None
    clean_key = os.path.normpath(storage_key).lstrip(os.sep)
    if clean_key.startswith(".."):
        return None
    full_path = os.path.join(storage_root, clean_key)
    if os.path.isfile(full_path):
        return full_path
    return None


def _stream_local_file(
    file_path: str,
    file_size: int,
    range_header: Optional[str],
    content_type: str,
    disposition: str,
) -> HttpResponse:
    byte_range = parse_range_header(range_header, file_size) if range_header else None

    if byte_range:
        start, end = byte_range
        length = end - start + 1
        with open(file_path, "rb") as handle:
            handle.seek(start)
            data = handle.read(length)
        response = HttpResponse(data, status=206, content_type=content_type)
        response["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        response["Content-Length"] = str(length)
    else:
        response = FileResponse(open(file_path, "rb"), content_type=content_type)
        response["Content-Length"] = str(file_size)

    response["Accept-Ranges"] = "bytes"
    response["Content-Disposition"] = disposition
    response["Cache-Control"] = "private, no-store"
    return response


class _FileserverByteIterator:
    """Keeps the httpx stream open while Django consumes the response body."""

    def __init__(self, download_url: str, headers: dict):
        self._client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=10.0),
            follow_redirects=True,
        )
        self._stream = self._client.stream("GET", download_url, headers=headers)
        self.response = self._stream.__enter__()
        self.response.raise_for_status()

    def iter_bytes(self) -> Iterator[bytes]:
        try:
            for chunk in self.response.iter_bytes():
                yield chunk
        finally:
            self.close()

    def close(self):
        try:
            self._stream.__exit__(None, None, None)
        finally:
            self._client.close()


def _proxy_fileserver_stream(
    storage_key: str,
    filename: str,
    range_header: Optional[str],
    content_type: str,
    disposition: str,
) -> HttpResponse:
    download_url = fileserver_client.generate_download_url(
        storage_key=storage_key,
        filename=filename,
        is_internal=True,
    )

    headers = {}
    if range_header:
        headers["Range"] = range_header

    try:
        upstream = _FileserverByteIterator(download_url, headers)
    except httpx.HTTPError as exc:
        logger.error("E-sign PDF proxy failed for %s: %s", storage_key, exc)
        return HttpResponse("Failed to load document", status=502)

    upstream_response = upstream.response
    response = StreamingHttpResponse(
        streaming_content=upstream.iter_bytes(),
        status=upstream_response.status_code,
        content_type=upstream_response.headers.get("content-type", content_type),
    )

    for header in ("Content-Range", "Content-Length", "Accept-Ranges", "ETag", "Last-Modified"):
        if header in upstream_response.headers:
            response[header] = upstream_response.headers[header]

    if "Accept-Ranges" not in response:
        response["Accept-Ranges"] = "bytes"

    response["Content-Disposition"] = disposition
    response["Cache-Control"] = "private, no-store"
    return response


def build_pdf_response_for_version(
    document_version: DocumentVersion,
    django_request,
    *,
    filename: Optional[str] = None,
    as_attachment: bool = False,
) -> HttpResponse:
    """Return a full or partial PDF response for the given document version."""
    storage_key = document_version.storage_key or document_version.original_storage_key
    if not storage_key:
        return HttpResponse("Document file not found", status=404)

    display_name = filename or document_version.document.name or "document.pdf"
    disposition_type = "attachment" if as_attachment else "inline"
    disposition = f'{disposition_type}; filename="{display_name}"'
    content_type = document_version.content_type or "application/pdf"
    range_header = django_request.META.get("HTTP_RANGE")

    local_path = _local_storage_path(storage_key)
    if local_path:
        file_size = os.path.getsize(local_path)
        return _stream_local_file(
            local_path,
            file_size,
            range_header,
            content_type,
            disposition,
        )

    try:
        info = fileserver_client.get_file_info(storage_key)
    except Exception as exc:
        logger.error("File info lookup failed for %s: %s", storage_key, exc)
        return HttpResponse("Document file not found", status=404)

    if not info.get("exists"):
        return HttpResponse("Document file not found", status=404)

    return _proxy_fileserver_stream(
        storage_key,
        display_name,
        range_header,
        content_type,
        disposition,
    )
