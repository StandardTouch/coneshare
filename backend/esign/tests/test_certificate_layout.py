import io
from pathlib import Path

import pytest
from django.utils import timezone
from reportlab.platypus import Paragraph
from pypdf import PdfReader

from esign.models import SignerAction
from esign.services import (
    _certificate_content_width,
    _certificate_table_rows,
    generate_certificate_of_completion,
)
from reportlab.lib.styles import getSampleStyleSheet


@pytest.mark.django_db
class TestCertificateLayout:
    def test_table_column_widths_fit_page(self):
        content_width = _certificate_content_width()
        signer_fracs = [0.05, 0.13, 0.20, 0.15, 0.11, 0.26, 0.10]
        event_fracs = [0.18, 0.15, 0.16, 0.51]
        assert abs(sum(signer_fracs) - 1.0) < 1e-6
        assert abs(sum(event_fracs) - 1.0) < 1e-6
        assert sum(content_width * f for f in signer_fracs) <= content_width + 0.01
        assert sum(content_width * f for f in event_fracs) <= content_width + 0.01

    def test_table_uses_wrapped_paragraph_cells(self):
        styles = getSampleStyleSheet()
        cell_style = styles['Normal']
        header_style = styles['Heading4']
        long_email = 'kahkashan+tester1@standardtouch.com'
        long_ua = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        table = _certificate_table_rows(
            ['Email', 'User Agent'],
            [[long_email, long_ua]],
            [200, 268],
            header_style,
            cell_style,
        )
        assert isinstance(table._cellvalues[1][0], Paragraph)
        assert isinstance(table._cellvalues[1][1], Paragraph)

    def test_certificate_renders_long_signer_values(self, signature_request, signer_user):
        signer = signature_request.signers.get(user=signer_user)
        signer.user.email = 'kahkashan+tester1@standardtouch.com'
        signer.user.save()
        signer.signed_at = timezone.now()
        signer.otp_verified_at = timezone.now()
        signer.ip_address = '203.0.113.50'
        signer.user_agent = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        signer.save()

        SignerAction.objects.create(
            signer=signer,
            action='signed',
            timestamp=timezone.now(),
            ip_address='203.0.113.50',
            user_agent=signer.user_agent,
        )

        signature_request.status = 'completed'
        signature_request.completed_at = timezone.now()
        signature_request.save()

        signer.refresh_from_db()
        signer.user.refresh_from_db()
        assert signer.user.email == 'kahkashan+tester1@standardtouch.com'

        pdf_bytes = generate_certificate_of_completion(
            signature_request,
            [signer],
            'sha256:' + 'a' * 64,
            'sha256:' + 'b' * 64,
        )
        assert len(pdf_bytes) > 500
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = reader.pages[0].extract_text() or ''
        assert 'Certificate of Completion' in text
        assert 'Signers' in text or 'Event Log' in text

        artifact_dir = Path('/opt/cursor/artifacts')
        artifact_dir.mkdir(parents=True, exist_ok=True)
        png_path = artifact_dir / 'certificate_sample.png'
        (artifact_dir / 'certificate_sample.pdf').write_bytes(pdf_bytes)
        try:
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(pdf_bytes, dpi=144, first_page=1, last_page=1)
            images[0].save(png_path, 'PNG')
        except Exception:
            try:
                import fitz

                doc = fitz.open(stream=pdf_bytes, filetype='pdf')
                doc[0].get_pixmap(dpi=144).save(png_path)
            except Exception:
                pytest.skip('No PDF rasterizer available; PDF artifact saved')

        assert png_path.exists()
