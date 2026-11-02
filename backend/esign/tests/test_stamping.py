import io

import pypdf
import pytest
from reportlab.pdfgen import canvas as pdf_canvas

from esign.models import SignatureField
from esign.services import flatten_signature_fields


def _build_multipage_pdf(num_pages: int) -> bytes:
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=(612, 792))
    for page in range(1, num_pages + 1):
        pdf.drawString(72, 720, f"Page {page}")
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


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
