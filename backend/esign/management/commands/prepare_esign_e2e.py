"""
Seed data and a large PDF for the e-sign Playwright E2E flow.

Prints a single JSON line to stdout with document_id, file_size_bytes, page markers, and user emails.
"""
import hashlib
import io
import json
import uuid

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db import transaction
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas as pdf_canvas

from core.models import AppConfiguration, Organization, User
from documents.fileserver import fileserver_client
from documents.models import Document, DocumentVersion, Folder


NUM_PAGES = 500
LANDSCAPE_PAGE = 250
MARKER_LAST = "E2E_LAST_PAGE_MARKER"
MARKER_LANDSCAPE = "E2E_LANDSCAPE_PAGE_MARKER"


def build_large_pdf_bytes() -> bytes:
    buffer = io.BytesIO()
    page_size = letter
    pdf = pdf_canvas.Canvas(buffer, pagesize=page_size)

    for page_num in range(1, NUM_PAGES + 1):
        if page_num == LANDSCAPE_PAGE:
            pdf.setPageSize(landscape(letter))
            pdf.drawString(72, 520, MARKER_LANDSCAPE)
            pdf.drawString(72, 500, f"Page {page_num} landscape")
        else:
            pdf.setPageSize(letter)
            pdf.drawString(72, 720, f"Page {page_num}")
            if page_num == NUM_PAGES:
                pdf.drawString(72, 700, MARKER_LAST)
        pdf.showPage()

    pdf.save()
    return buffer.getvalue()


class Command(BaseCommand):
    help = "Prepare e-sign E2E fixtures (large PDF, signers, ESIGN enabled)."

    @transaction.atomic
    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(name="Default Organization")
        other_org, _ = Organization.objects.get_or_create(name="E2E Other Organization")

        AppConfiguration.objects.update_or_create(
            key="ESIGN_ENABLED",
            defaults={"value": "true"},
        )
        cache.delete("app_config:ESIGN_ENABLED")

        def ensure_user(email, organization, name):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "organization": organization,
                    "name": name,
                    "is_active": True,
                },
            )
            if created or not user.has_usable_password():
                user.set_password("password123")
                user.save()
            return user

        requester = ensure_user("test@coneshare.com", org, "Test User")
        signer1 = ensure_user("esign-signer1@coneshare.com", org, "E2E Signer One")
        signer2 = ensure_user("esign-signer2@coneshare.com", org, "E2E Signer Two")
        outsider = ensure_user("esign-outsider@other.com", other_org, "E2E Outsider")

        pdf_bytes = build_large_pdf_bytes()
        original_hash = f"sha256:{hashlib.sha256(pdf_bytes).hexdigest()}"
        storage_key = f"e2e/esign/{uuid.uuid4().hex}/large-500.pdf"

        fileserver_client.upload_file(
            storage_key,
            pdf_bytes,
            content_type="application/pdf",
            timeout=(30, 600),
        )

        root_folder = Folder.objects.get_root_for_org(org)
        doc_name = "E2E E-Sign 500-Page.pdf"
        Document.objects.filter(name=doc_name, organization=org).delete()

        document = Document.objects.create(
            name=doc_name,
            organization=org,
            created_by=requester,
            folder=root_folder,
            type="pdf",
            content_type="application/pdf",
            num_pages=NUM_PAGES,
            status="ready",
            file_size=len(pdf_bytes),
        )
        DocumentVersion.objects.create(
            document=document,
            version_number=1,
            storage_key=storage_key,
            original_storage_key=storage_key,
            content_type="application/pdf",
            type="pdf",
            file_size=len(pdf_bytes),
            is_primary=True,
        )

        payload = {
            "document_id": document.id,
            "document_name": doc_name,
            "file_size_bytes": len(pdf_bytes),
            "num_pages": NUM_PAGES,
            "landscape_page": LANDSCAPE_PAGE,
            "last_page": NUM_PAGES,
            "original_hash": original_hash,
            "requester_email": requester.email,
            "signer1_email": signer1.email,
            "signer2_email": signer2.email,
            "outsider_email": outsider.email,
            "signer1_id": str(signer1.id),
            "signer2_id": str(signer2.id),
        }
        self.stdout.write(json.dumps(payload))
