"""
Verify signed PDF output from the e-sign E2E flow.

Usage: verify_esign_e2e --request-id=<id> --landscape-page=250 --num-pages=500
"""
import argparse
import io
import sys

import pypdf
from django.core.management.base import BaseCommand

from esign.models import SignatureField, SignatureRequest, Signer


class Command(BaseCommand):
    help = "Verify stamped fields and audit page for e-sign E2E."

    def add_arguments(self, parser):
        parser.add_argument("--request-id", required=True)
        parser.add_argument("--num-pages", type=int, default=500)
        parser.add_argument("--landscape-page", type=int, default=250)

    def handle(self, *args, **options):
        request_id = options["request_id"]
        num_pages = options["num_pages"]
        landscape_page = options["landscape_page"]

        signature_request = SignatureRequest.objects.select_related(
            "signed_document_version"
        ).get(pk=request_id)

        if signature_request.status != "completed":
            self.stderr.write(f"Request not completed: {signature_request.status}\n")
            sys.exit(1)

        version = signature_request.signed_document_version
        if not version or not version.storage_key:
            self.stderr.write("Missing signed document version\n")
            sys.exit(1)

        from documents.fileserver import fileserver_client
        from django.conf import settings
        import httpx

        download_url = fileserver_client.generate_download_url(
            storage_key=version.storage_key,
            filename="signed.pdf",
            is_internal=True,
        )
        resp = httpx.get(download_url, timeout=120.0, follow_redirects=True)
        resp.raise_for_status()
        pdf_bytes = resp.content

        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        expected_pages = num_pages + 1  # audit certificate appended
        if len(reader.pages) != expected_pages:
            self.stderr.write(
                f"Page count mismatch: got {len(reader.pages)}, expected {expected_pages}\n"
            )
            sys.exit(1)

        last_idx = num_pages - 1
        landscape_idx = landscape_page - 1
        page1_text = reader.pages[0].extract_text() or ""
        landscape_text = reader.pages[landscape_idx].extract_text() or ""
        last_text = reader.pages[last_idx].extract_text() or ""
        audit_text = reader.pages[-1].extract_text() or ""

        fields = list(
            SignatureField.objects.filter(signature_request=signature_request).select_related(
                "signer__user"
            )
        )

        errors = []
        for field in fields:
            if field.field_type in ("signature", "initials", "full_name", "text", "date_signed"):
                if not field.value:
                    errors.append(f"Field {field.id} missing value")
                    continue
                page_text = reader.pages[field.page_number - 1].extract_text() or ""
                if field.field_type == "date_signed":
                    if field.value not in page_text:
                        errors.append(
                            f"Date {field.value!r} not found on page {field.page_number}"
                        )
                elif field.value.startswith("data:image"):
                    pass  # drawn signatures may not appear in extract_text
                elif field.value not in page_text:
                    errors.append(
                        f"Value {field.value!r} not on page {field.page_number}"
                    )

        signers = Signer.objects.filter(signature_request=signature_request, status="signed")
        for signer in signers:
            if signer.user.email not in audit_text:
                errors.append(f"Signer email {signer.user.email} missing from audit page")
            if signer.user.name not in audit_text:
                errors.append(f"Signer name {signer.user.name} missing from audit page")

        if signature_request.original_document_hash:
            if signature_request.original_document_hash.replace("sha256:", "") not in audit_text.replace(
                "sha256:", ""
            ):
                if signature_request.original_document_hash not in audit_text:
                    errors.append("Original document hash missing from audit page")

        if errors:
            for err in errors:
                self.stderr.write(err + "\n")
            sys.exit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Verified signed PDF: {len(reader.pages)} pages, "
                f"markers ok (p1={len(page1_text)}, landscape={len(landscape_text)}, "
                f"last={len(last_text)}, audit={len(audit_text)})"
            )
        )
