import hashlib
import io
import logging
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
    font_name: str = 'Helvetica',
    font_size: int = 12,
    is_arabic: bool = False
) -> bytes:
    """
    Create a transparent PDF with text at specified position.
    Coordinates are in percentages.
    """
    # Convert percentages to points
    x = (x_percent / 100) * page_width
    y = (y_percent / 100) * page_height
    width = (width_percent / 100) * page_width
    height = (height_percent / 100) * page_height
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = pdf_canvas.Canvas(buffer, pagesize=(page_width, page_height))
    
    # Set font (use a font that supports Arabic if needed)
    if is_arabic:
        # For now, use Helvetica; in production, bundle an Arabic-supporting font
        c.setFont('Helvetica', font_size)
    else:
        c.setFont(font_name, font_size)
    
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
    Generate certificate of completion as PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    
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
    story.append(Paragraph(
        f"<b>Completed:</b> {timezone.localtime(signature_request.completed_at).strftime('%Y-%m-%d %H:%M:%S %Z')}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.3 * inch))
    
    # Signers table
    story.append(Paragraph("<b>Signers:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))
    
    signer_data = [['#', 'Name', 'Email', 'Signed At', 'IP Address', 'Verification']]
    for idx, signer in enumerate(signers, 1):
        signed_time = timezone.localtime(signer.signed_at).strftime('%Y-%m-%d %H:%M:%S') if signer.signed_at else '-'
        ip = signer.ip_address or '-'
        verification = 'Email OTP' if signer.otp_verified_at else '-'
        signer_data.append([
            str(idx),
            signer.user.name,
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
    
    # Document hashes
    story.append(Paragraph("<b>Document Integrity:</b>", styles['Heading2']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"<b>Original Document Hash:</b><br/><font size=8>{original_hash}</font>", styles['Normal']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(f"<b>Signed Document Hash:</b><br/><font size=8>{final_hash}</font>", styles['Normal']))
    story.append(Spacer(1, 0.3 * inch))
    
    # Footer
    story.append(Paragraph(
        f"<i>This certificate was generated by Coneshare E-Signature on {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}.</i>",
        styles['Normal']
    ))
    story.append(Paragraph(
        f"<i>Audit logs are available to authorized users in the system.</i>",
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
