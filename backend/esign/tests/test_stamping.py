import base64
import io

import pypdf
import pytest
from django.utils import timezone
from PIL import Image
from reportlab.pdfgen import canvas as pdf_canvas

from esign.models import SignatureField
from esign.services import (
    _field_rect_from_top_left_percent,
    append_certificate_to_pdf,
    flatten_signature_fields,
    generate_certificate_of_completion,
)


def _build_single_page_pdf(width=612, height=792) -> bytes:
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=(width, height))
    pdf.drawString(72, height - 72, "Source page")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _build_multipage_pdf(num_pages: int) -> bytes:
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=(612, 792))
    for page in range(1, num_pages + 1):
        pdf.drawString(72, 720, f"Page {page}")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _png_data_url(width=24, height=12) -> str:
    buf = io.BytesIO()
    Image.new("RGBA", (width, height), color=(0, 0, 0, 255)).save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _page_image_count(page) -> int:
    try:
        return len(list(page.images))
    except Exception:
        resources = page.get("/Resources")
        if not resources:
            return 0
        xobjects = resources.get("/XObject")
        if not xobjects:
            return 0
        xobj = xobjects.get_object()
        count = 0
        for name in xobj:
            obj = xobj[name].get_object()
            if obj.get("/Subtype") == "/Image":
                count += 1
        return count


@pytest.fixture
def signer(signature_request):
    return signature_request.signers.first()


@pytest.mark.django_db
class TestStampingCoordinates:
    def test_field_on_last_page(self, signature_request, signer):
        num_pages = 5
        original_bytes = _build_multipage_pdf(num_pages)

        field = SignatureField.objects.create(
            signature_request=signature_request,
            signer=signer,
            field_type="full_name",
            page_number=num_pages,
            x=10.0,
            y=85.0,
            width=40.0,
            height=5.0,
            required=True,
            value="Last Page Signer",
        )
        field.filled_at = field.created_at
        field.save()

        result_bytes = flatten_signature_fields(original_bytes, [field])
        reader = pypdf.PdfReader(io.BytesIO(result_bytes))
        assert len(reader.pages) == num_pages

        last_text = reader.pages[num_pages - 1].extract_text() or ""
        assert "Last Page Signer" in last_text

        first_text = reader.pages[0].extract_text() or ""
        assert "Last Page Signer" not in first_text

    def test_drawn_signature_embeds_image_on_page(self, signature_request, signer):
        original_bytes = _build_single_page_pdf()
        field = SignatureField.objects.create(
            signature_request=signature_request,
            signer=signer,
            field_type="signature",
            page_number=1,
            x=10.0,
            y=80.0,
            width=30.0,
            height=10.0,
            required=True,
            value=_png_data_url(),
        )
        field.filled_at = timezone.now()
        field.save()

        result_bytes = flatten_signature_fields(original_bytes, [field])
        reader = pypdf.PdfReader(io.BytesIO(result_bytes))
        page = reader.pages[0]

        assert _page_image_count(page) >= 1

        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        x, y, width, height = _field_rect_from_top_left_percent(
            page_width, page_height, field.x, field.y, field.width, field.height
        )
        assert 0 <= x <= page_width
        assert 0 <= y <= page_height
        assert width > 0 and height > 0

    def test_typed_signature_renders_text(self, signature_request, signer):
        original_bytes = _build_single_page_pdf()
        field = SignatureField.objects.create(
            signature_request=signature_request,
            signer=signer,
            field_type="signature",
            page_number=1,
            x=15.0,
            y=70.0,
            width=35.0,
            height=8.0,
            required=True,
            value="Typed Signer Name",
        )
        field.filled_at = timezone.now()
        field.save()

        result_bytes = flatten_signature_fields(original_bytes, [field])
        reader = pypdf.PdfReader(io.BytesIO(result_bytes))
        text = reader.pages[0].extract_text() or ""
        assert "Typed Signer Name" in text

    def test_audit_certificate_page_appended(self, signature_request, signer):
        signature_request.status = "completed"
        signature_request.completed_at = timezone.now()
        signature_request.save()
        signer.status = "signed"
        signer.signed_at = timezone.now()
        signer.save()

        original_bytes = _build_single_page_pdf()
        cert_bytes = generate_certificate_of_completion(
            signature_request,
            [signer],
            "sha256:" + "a" * 64,
            "sha256:" + "b" * 64,
        )
        merged = append_certificate_to_pdf(original_bytes, cert_bytes)
        reader = pypdf.PdfReader(io.BytesIO(merged))
        assert len(reader.pages) == 2
        audit_text = reader.pages[-1].extract_text() or ""
        assert "Certificate of Completion" in audit_text
