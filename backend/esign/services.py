import hashlib
import io
import logging
import os
import secrets
from datetime import datetime
from typing import Dict, List
from xml.sax.saxutils import escape

from django.conf import settings
from backend.utils import get_client_ip
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from PIL import Image
import pypdf

# Arabic text shaping libraries
from arabic_reshaper import reshape
from bidi.algorithm import get_display

from documents.fileserver import fileserver_client
from documents.models import DocumentVersion
from .models import SignatureRequest, Signer, SignatureField, SignerAction

logger = logging.getLogger(__name__)

# Register custom fonts for signatures (Arabic + handwriting style)
FONTS_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
try:
    pdfmetrics.registerFont(TTFont('Amiri', os.path.join(FONTS_DIR, 'Amiri-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('DancingScript', os.path.join(FONTS_DIR, 'DancingScript-Regular.ttf')))
    logger.info("Custom fonts registered successfully")
except Exception as e:
    logger.error(f"Failed to register custom fonts: {e}")


def generate_otp_code() -> str:
    """Generate a 6-digit OTP code."""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def prepare_arabic_text(text: str) -> str:
    """
    Prepare Arabic text for PDF rendering with proper shaping and BiDi.
    
    Arabic text needs:
    1. Reshaping (letter joining based on position)
    2. BiDi algorithm (right-to-left display order)
    """
    if not text:
        return text
    
    # Check if text contains Arabic characters
    arabic_range = range(0x0600, 0x06FF + 1)
    has_arabic = any(ord(char) in arabic_range for char in text)
    
    if has_arabic:
        # Reshape Arabic letters (handles letter joining)
        reshaped = reshape(text)
        # Apply BiDi algorithm for proper RTL display
        return get_display(reshaped)
    
    return text


def calculate_document_hash(pdf_bytes: bytes) -> str:
    """Calculate SHA-256 hash of document."""
    return f"sha256:{hashlib.sha256(pdf_bytes).hexdigest()}"


def get_client_info(request) -> tuple:
    """Extract IP address and user agent from request (via shared proxy-aware helper)."""
    ip_address = get_client_ip(request) if request else None
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:512] if request else ''
    return ip_address, user_agent


def record_signer_action(
    signer: Signer,
    action: str,
    request=None,
    metadata: dict = None
):
    """Record a signer action for audit trail."""
    ip_address, user_agent = None, ''
    if request:
        ip_address, user_agent = get_client_info(request)
    
    SignerAction.objects.create(
        signer=signer,
        action=action,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )


def download_document_pdf(document_version: DocumentVersion) -> bytes:
    """Download PDF bytes from file server."""
    storage_key = document_version.storage_key or document_version.original_storage_key
    if not storage_key:
        raise ValueError("Document version has no storage key")
    
    download_url = fileserver_client.generate_download_url(
        storage_key,
        filename=document_version.document.name,
        is_internal=True,
    )
    if not download_url:
        raise ValueError("Failed to generate download URL")

    import httpx

    client = httpx.Client(follow_redirects=True)
    try:
        resp = client.get(download_url)
        resp.raise_for_status()
        return resp.content
    finally:
        client.close()


def _field_rect_from_top_left_percent(
    page_width: float,
    page_height: float,
    x_percent: float,
    y_percent: float,
    width_percent: float,
    height_percent: float,
) -> tuple:
    """Convert top-left percentage box to ReportLab bottom-left coordinates."""
    width = (width_percent / 100) * page_width
    height = (height_percent / 100) * page_height
    x = (x_percent / 100) * page_width
    y_top = page_height - (y_percent / 100) * page_height
    y = y_top - height
    return x, y, width, height


def create_text_overlay_pdf(
    text: str,
    page_width: float,
    page_height: float,
    x_percent: float,
    y_percent: float,
    width_percent: float,
    height_percent: float,
    font_name: str = 'DancingScript',
    font_size: int = 14,
    is_arabic: bool = False
) -> bytes:
    """
    Create a transparent PDF with text at specified position.
    Coordinates are in percentages from the top-left of the page.
    Uses DancingScript for Latin text and Amiri for Arabic text.
    """
    x, y, width, height = _field_rect_from_top_left_percent(
        page_width, page_height, x_percent, y_percent, width_percent, height_percent
    )
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Select appropriate font based on text content
    # Check if text contains Arabic characters
    has_arabic = any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or 
                     '\u08A0' <= char <= '\u08FF' or '\uFB50' <= char <= '\uFDFF' or 
                     '\uFE70' <= char <= '\uFEFF' for char in text)
    
    # Prepare Arabic text with proper shaping and BiDi
    display_text = prepare_arabic_text(text) if has_arabic else text
    
    if has_arabic or is_arabic:
        # Use Amiri for Arabic text
        try:
            c.setFont('Amiri', font_size)
        except:
            logger.warning("Amiri font not available, falling back to Helvetica")
            c.setFont('Helvetica', font_size)
    else:
        # Use DancingScript for Latin handwriting style
        try:
            c.setFont(font_name if font_name != 'Helvetica' else 'DancingScript', font_size)
        except:
            logger.warning(f"{font_name} not available, falling back to Helvetica")
            c.setFont('Helvetica', font_size)
    
    # Draw text (centered in box, RTL for Arabic)
    text_y = y + (height / 2)
    if has_arabic:
        # Right-aligned for Arabic
        c.drawRightString(x + width, text_y, display_text)
    else:
        c.drawCentredString(x + width / 2, text_y, display_text)
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def create_signature_image_overlay_pdf(
    image_data_url: str,
    page_width: float,
    page_height: float,
    x_percent: float,
    y_percent: float,
    width_percent: float,
    height_percent: float
) -> bytes:
    """
    Create a transparent PDF with image (signature drawing) at specified position.
    image_data_url format: "data:image/png;base64,..."
    """
    import base64
    
    # Extract base64 data
    if ',' not in image_data_url:
        raise ValueError("Invalid image data URL format")
    
    header, encoded = image_data_url.split(',', 1)
    image_bytes = base64.b64decode(encoded)
    
    x, y, width, height = _field_rect_from_top_left_percent(
        page_width, page_height, x_percent, y_percent, width_percent, height_percent
    )
    
    # Load image
    img = Image.open(io.BytesIO(image_bytes))
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Draw image
    c.drawImage(
        ImageReader(img),
        x, y, width, height,
        preserveAspectRatio=True,
        mask='auto'
    )
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def flatten_signature_fields(
    original_pdf_bytes: bytes,
    fields: List[SignatureField]
) -> bytes:
    """
    Flatten signature fields into PDF.
    Returns modified PDF bytes with all fields embedded.
    """
    pdf_reader = pypdf.PdfReader(io.BytesIO(original_pdf_bytes))
    pdf_writer = pypdf.PdfWriter()
    
    # Group fields by page
    fields_by_page = {}
    for field in fields:
        page_num = field.page_number - 1  # 0-indexed
        if page_num not in fields_by_page:
            fields_by_page[page_num] = []
        fields_by_page[page_num].append(field)
    
    # Process each page
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        
        # Get fields for this page
        page_fields = fields_by_page.get(page_num, [])
        
        # Create overlay for each field
        for field in page_fields:
            try:
                if field.field_type in ['signature', 'initials']:
                    # Signature/initials are drawn or typed
                    if field.value.startswith('data:image'):
                        # Drawn signature
                        overlay_pdf = create_signature_image_overlay_pdf(
                            field.value,
                            page_width, page_height,
                            field.x, field.y, field.width, field.height
                        )
                    else:
                        # Typed signature (render as text in handwriting-style font)
                        # For Phase 1, use a simple cursive style
                        overlay_pdf = create_text_overlay_pdf(
                            field.value,
                            page_width, page_height,
                            field.x, field.y, field.width, field.height,
                            font_name='Helvetica-Oblique',  # Closest to handwriting in standard fonts
                            font_size=16 if field.field_type == 'signature' else 12,
                            is_arabic='arabic' in getattr(settings, 'LANGUAGE_CODE', 'en').lower()
                        )
                    
                    overlay_reader = pypdf.PdfReader(io.BytesIO(overlay_pdf))
                    page.merge_page(overlay_reader.pages[0])
                
                elif field.field_type in ['date_signed', 'full_name', 'text']:
                    # Text fields
                    overlay_pdf = create_text_overlay_pdf(
                        field.value,
                        page_width, page_height,
                        field.x, field.y, field.width, field.height,
                        font_size=10
                    )
                    overlay_reader = pypdf.PdfReader(io.BytesIO(overlay_pdf))
                    page.merge_page(overlay_reader.pages[0])
            
            except Exception as e:
                logger.exception("Error overlaying field %s: %s", field.id, e)
                # Continue processing other fields
        
        pdf_writer.add_page(page)
    
    # Write to buffer
    output_buffer = io.BytesIO()
    pdf_writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.getvalue()


def _certificate_content_width() -> float:
    """Usable width inside letter page with default SimpleDocTemplate margins."""
    return letter[0] - 144  # 72pt left + 72pt right


def _certificate_paragraph(text, style) -> Paragraph:
    safe = escape(str(text if text not in (None, '') else '-'))
    return Paragraph(safe, style)


def _certificate_table_rows(header_labels, body_rows, col_widths, header_style, cell_style):
    """Build a wrapped table that fits the certificate content area."""
    table_data = [[_certificate_paragraph(label, header_style) for label in header_labels]]
    for row in body_rows:
        table_data.append([_certificate_paragraph(cell, cell_style) for cell in row])
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
            ]
        )
    )
    return table


def generate_certificate_of_completion(
    signature_request: SignatureRequest,
    signers: List[Signer],
    original_hash: str,
    final_hash: str
) -> bytes:
    """
    Generate certificate of completion as PDF with Arabic support.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom font for Arabic support in certificates
    try:
        from reportlab.lib.styles import ParagraphStyle as PS
        from reportlab.lib.enums import TA_LEFT
        
        # Register fonts if not already done
        try:
            pdfmetrics.getFont('Amiri')
        except:
            pass  # Already registered at module load
        
        # Create style with Amiri font for names
        name_style = PS(
            'ArabicName',
            parent=styles['Normal'],
            fontName='Amiri',
            fontSize=9
        )
    except:
        name_style = styles['Normal']
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Add title
    story.append(Paragraph("Certificate of Completion", title_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Document info
    story.append(Paragraph(f"<b>Document:</b> {signature_request.title}", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(
        f"<b>Signature Request ID:</b> {signature_request.id}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.1 * inch))
    
    # Format completed time in Asia/Riyadh timezone as per requirements
    import pytz
    riyadh_tz = pytz.timezone('Asia/Riyadh')
    completed_riyadh = signature_request.completed_at.astimezone(riyadh_tz)
    
    story.append(Paragraph(
        f"<b>Completed:</b> {completed_riyadh.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Riyadh)",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.3 * inch))
    
    created_riyadh = signature_request.created_at.astimezone(riyadh_tz)
    story.append(Paragraph(
        f"<b>Created:</b> {created_riyadh.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Riyadh)",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.2 * inch))

    content_width = _certificate_content_width()
    cell_style = ParagraphStyle(
        'CertTableCell',
        parent=styles['Normal'],
        fontSize=7,
        leading=8,
        wordWrap='CJK',
    )
    header_style = ParagraphStyle(
        'CertTableHeader',
        parent=cell_style,
        fontName='Helvetica-Bold',
    )

    # Signers table (Paragraph cells wrap long email / user agent on one page width)
    story.append(Paragraph("<b>Signers:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))

    signer_col_fracs = [0.05, 0.13, 0.20, 0.15, 0.11, 0.26, 0.10]
    signer_col_widths = [content_width * f for f in signer_col_fracs]
    signer_header = ['#', 'Name', 'Email', 'Signed At (AST)', 'IP Address', 'User Agent', 'OTP Verified']
    signer_rows = []
    for idx, signer in enumerate(signers, 1):
        if signer.signed_at:
            signed_riyadh = signer.signed_at.astimezone(riyadh_tz)
            signed_time = signed_riyadh.strftime('%Y-%m-%d %H:%M:%S')
        else:
            signed_time = '-'

        if signer.otp_verified_at:
            otp_time_riyadh = signer.otp_verified_at.astimezone(riyadh_tz)
            verification = otp_time_riyadh.strftime('%Y-%m-%d %H:%M:%S')
        else:
            verification = '-'

        signer_rows.append(
            [
                str(idx),
                signer.user.name,
                signer.user.email,
                signed_time,
                signer.ip_address or '-',
                signer.user_agent or '-',
                verification,
            ]
        )

    signer_table = _certificate_table_rows(
        signer_header, signer_rows, signer_col_widths, header_style, cell_style
    )
    story.append(signer_table)
    story.append(Spacer(1, 0.3 * inch))

    # Event log table
    story.append(Paragraph("<b>Event Log:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))

    event_col_fracs = [0.18, 0.15, 0.16, 0.51]
    event_col_widths = [content_width * f for f in event_col_fracs]
    event_header = ['Timestamp (AST)', 'Signer', 'Action', 'User Agent']
    event_rows = []
    for signer in signers:
        for action in signer.actions.all().order_by('timestamp'):
            action_riyadh = action.timestamp.astimezone(riyadh_tz)
            event_rows.append(
                [
                    action_riyadh.strftime('%Y-%m-%d %H:%M:%S'),
                    signer.user.name,
                    action.get_action_display(),
                    action.user_agent or '-',
                ]
            )

    event_table = _certificate_table_rows(
        event_header, event_rows, event_col_widths, header_style, cell_style
    )
    story.append(event_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Document hashes
    story.append(Paragraph("<b>Document Integrity:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"<b>Original Document Hash:</b><br/><font size=8>{original_hash}</font>", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"<b>Signed Document Hash:</b><br/><font size=8>{final_hash}</font>", styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))
    
    # Footer
    now_riyadh = datetime.now(riyadh_tz)
    story.append(Paragraph(
        f"<i>This certificate was generated by Coneshare E-Signature on {now_riyadh.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Riyadh).</i>",
        styles['Normal']
    ))
    story.append(Paragraph(
        f"<i>All timestamps are in Arabian Standard Time (AST, UTC+3). Audit logs are available to authorized users.</i>",
        styles['Normal']
    ))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def append_certificate_to_pdf(pdf_bytes: bytes, certificate_pdf_bytes: bytes) -> bytes:
    """
    Append certificate page to signed PDF.
    """
    pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    cert_reader = pypdf.PdfReader(io.BytesIO(certificate_pdf_bytes))
    pdf_writer = pypdf.PdfWriter()
    
    # Add all original pages
    for page in pdf_reader.pages:
        pdf_writer.add_page(page)
    
    # Add certificate page(s)
    for page in cert_reader.pages:
        pdf_writer.add_page(page)
    
    # Write to buffer
    output_buffer = io.BytesIO()
    pdf_writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.getvalue()


def get_stamping_source_version(signature_request: SignatureRequest) -> DocumentVersion:
    """
    PDF version to stamp fields onto (unsigned source).
    After completion the signed copy is primary; exclude it when regenerating.
    """
    document = signature_request.document
    signed_version = signature_request.signed_document_version
    qs = document.versions.order_by('version_number')
    if signed_version:
        qs = qs.exclude(pk=signed_version.pk)
    source = qs.first()
    if not source:
        source = document.versions.filter(is_primary=True).first()
    if not source:
        raise ValueError("No document version available for signature stamping")
    return source


def process_signature_completion(signature_request: SignatureRequest) -> tuple:
    """
    Process signature request completion:
    1. Download original PDF
    2. Flatten all signature fields
    3. Generate certificate
    4. Append certificate to PDF
    5. Upload signed PDF
    6. Calculate hashes
    
    Returns: (signed_pdf_storage_key, certificate_storage_key, original_hash, signed_hash, final_pdf_bytes)
    """
    source_version = get_stamping_source_version(signature_request)
    original_pdf_bytes = download_document_pdf(source_version)
    
    # Calculate original hash
    original_hash = calculate_document_hash(original_pdf_bytes)
    
    # Get all filled fields
    fields = SignatureField.objects.filter(
        signature_request=signature_request,
        filled_at__isnull=False
    ).select_related('signer__user')
    
    # Flatten fields into PDF
    flattened_pdf_bytes = flatten_signature_fields(original_pdf_bytes, list(fields))
    
    # Get signers for certificate
    signers = list(signature_request.signers.filter(status='signed').select_related('user').order_by('signing_order'))
    
    append_certificate = getattr(settings, 'ESIGN_APPEND_CERTIFICATE', False)
    stamped_hash = calculate_document_hash(flattened_pdf_bytes)

    if append_certificate:
        certificate_pdf_bytes = generate_certificate_of_completion(
            signature_request,
            signers,
            original_hash,
            stamped_hash,
        )
        final_pdf_bytes = append_certificate_to_pdf(flattened_pdf_bytes, certificate_pdf_bytes)
        final_hash = calculate_document_hash(final_pdf_bytes)
    else:
        final_pdf_bytes = flattened_pdf_bytes
        final_hash = stamped_hash
        certificate_pdf_bytes = generate_certificate_of_completion(
            signature_request,
            signers,
            original_hash,
            final_hash,
        )
    
    signed_storage_key = f"signatures/{signature_request.id}/signed_{signature_request.document.id}.pdf"
    fileserver_client.upload_file(
        signed_storage_key,
        final_pdf_bytes,
        content_type="application/pdf",
    )

    cert_storage_key = f"signatures/{signature_request.id}/certificate.pdf"
    fileserver_client.upload_file(
        cert_storage_key,
        certificate_pdf_bytes,
        content_type="application/pdf",
    )
    
    return signed_storage_key, cert_storage_key, original_hash, final_hash, final_pdf_bytes
