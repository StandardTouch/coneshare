import hashlib
import io
import logging
import os
import secrets
from datetime import datetime
from typing import Dict, List

from django.conf import settings
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
from PIL import Image
import pypdf

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


def calculate_document_hash(pdf_bytes: bytes) -> str:
    """Calculate SHA-256 hash of document."""
    return f"sha256:{hashlib.sha256(pdf_bytes).hexdigest()}"


def get_client_info(request) -> tuple:
    """Extract IP address and user agent from request."""
    # Get IP address (handle proxy headers)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0].strip()
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:512]
    
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
    
    # Generate download URL
    response = fileserver_client.generate_download_url(
        storage_key=storage_key,
        filename=document_version.document.name
    )
    download_url = response.get('url')
    
    if not download_url:
        raise ValueError("Failed to generate download URL")
    
    # Download file
    import httpx
    client = httpx.Client()
    try:
        resp = client.get(settings.CORE_API_URL + download_url)
        resp.raise_for_status()
        return resp.content
    finally:
        client.close()


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
    Coordinates are in percentages.
    Uses DancingScript for Latin text and Amiri for Arabic text.
    """
    # Convert percentages to points
    x = (x_percent / 100) * page_width
    y = (y_percent / 100) * page_height
    width = (width_percent / 100) * page_width
    height = (height_percent / 100) * page_height
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Select appropriate font based on text content
    # Check if text contains Arabic characters
    has_arabic = any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or 
                     '\u08A0' <= char <= '\u08FF' or '\uFB50' <= char <= '\uFDFF' or 
                     '\uFE70' <= char <= '\uFEFF' for char in text)
    
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
    
    # Draw text (centered in box)
    text_y = y + (height / 2)
    c.drawCentredString(x + width / 2, text_y, text)
    
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
    
    # Convert percentages to points
    x = (x_percent / 100) * page_width
    y = (y_percent / 100) * page_height
    width = (width_percent / 100) * page_width
    height = (height_percent / 100) * page_height
    
    # Load image
    img = Image.open(io.BytesIO(image_bytes))
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Draw image
    c.drawImage(
        pypdf.generic.ImageReader(img),
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
                logger.error(f"Error overlaying field {field.id}: {e}")
                # Continue processing other fields
        
        pdf_writer.add_page(page)
    
    # Write to buffer
    output_buffer = io.BytesIO()
    pdf_writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer.getvalue()


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
    
    # Signers table - build manually to support Arabic names
    story.append(Paragraph("<b>Signers:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))
    
    # Header row
    signer_data = [['#', 'Name', 'Email', 'Signed At (AST)', 'IP Address', 'OTP Verified']]
    
    # Data rows with proper timezone handling
    for idx, signer in enumerate(signers, 1):
        if signer.signed_at:
            signed_riyadh = signer.signed_at.astimezone(riyadh_tz)
            signed_time = signed_riyadh.strftime('%Y-%m-%d %H:%M:%S')
        else:
            signed_time = '-'
        
        ip = signer.ip_address or '-'
        
        if signer.otp_verified_at:
            otp_time_riyadh = signer.otp_verified_at.astimezone(riyadh_tz)
            verification = otp_time_riyadh.strftime('%H:%M:%S')
        else:
            verification = '-'
        
        signer_data.append([
            str(idx),
            signer.user.name,  # ReportLab handles Unicode
            signer.user.email,
            signed_time,
            ip,
            verification
        ])
    
    signer_table = Table(signer_data, colWidths=[0.5*inch, 1.5*inch, 2*inch, 1.5*inch, 1.2*inch, 1*inch])
    signer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    story.append(signer_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Event log table
    story.append(Paragraph("<b>Event Log:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))
    
    event_data = [['Timestamp (AST)', 'Signer', 'Action', 'User Agent']]
    for signer in signers:
        for action in signer.actions.all().order_by('timestamp'):
            action_riyadh = action.timestamp.astimezone(riyadh_tz)
            event_data.append([
                action_riyadh.strftime('%Y-%m-%d %H:%M:%S'),
                signer.user.name,
                action.get_action_display(),
                (action.user_agent[:30] + '...') if len(action.user_agent) > 30 else action.user_agent
            ])
    
    event_table = Table(event_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 3*inch])
    event_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
    ]))
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


def process_signature_completion(signature_request: SignatureRequest) -> tuple:
    """
    Process signature request completion:
    1. Download original PDF
    2. Flatten all signature fields
    3. Generate certificate
    4. Append certificate to PDF
    5. Upload signed PDF
    6. Calculate hashes
    
    Returns: (signed_pdf_storage_key, certificate_storage_key, original_hash, signed_hash)
    """
    # Download original PDF
    original_pdf_bytes = download_document_pdf(signature_request.document.versions.filter(is_primary=True).first())
    
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
    
    # Generate certificate
    certificate_pdf_bytes = generate_certificate_of_completion(
        signature_request,
        signers,
        original_hash,
        calculate_document_hash(flattened_pdf_bytes)
    )
    
    # Append certificate to signed PDF
    final_pdf_bytes = append_certificate_to_pdf(flattened_pdf_bytes, certificate_pdf_bytes)
    
    # Calculate final hash
    final_hash = calculate_document_hash(final_pdf_bytes)
    
    # Upload signed PDF
    signed_storage_key = f"signatures/{signature_request.id}/signed_{signature_request.document.id}.pdf"
    upload_response = fileserver_client.generate_upload_url(
        storage_key=signed_storage_key,
        filename=f"signed_{signature_request.document.name}"
    )
    upload_url = upload_response.get('url')
    
    # Upload file
    import httpx
    client = httpx.Client()
    try:
        resp = client.put(settings.CORE_API_URL + upload_url, content=final_pdf_bytes)
        resp.raise_for_status()
    finally:
        client.close()
    
    # Upload certificate separately (for download)
    cert_storage_key = f"signatures/{signature_request.id}/certificate.pdf"
    cert_upload_response = fileserver_client.generate_upload_url(
        storage_key=cert_storage_key,
        filename=f"certificate_{signature_request.document.name}"
    )
    cert_upload_url = cert_upload_response.get('url')
    
    client = httpx.Client()
    try:
        resp = client.put(settings.CORE_API_URL + cert_upload_url, content=certificate_pdf_bytes)
        resp.raise_for_status()
    finally:
        client.close()
    
    return signed_storage_key, cert_storage_key, original_hash, final_hash
