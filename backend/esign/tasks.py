import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import activate, gettext as _

from documents.models import DocumentVersion
from .models import SignatureRequest, Signer
from .services import process_signature_completion

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_signature_request_email_task(self, signer_id):
    """
    Send signature request email to signer.
    """
    try:
        signer = Signer.objects.select_related('signature_request__document', 'user').get(id=signer_id)
        signature_request = signer.signature_request
        
        # Activate user's language preference
        user_lang = signer.user.language or 'en'
        activate(user_lang)
        
        # Build signing URL
        signing_url = f"{settings.SITE_DOMAIN}/sign/{signer.token}"
        
        # Prepare context
        context = {
            'signer_name': signer.user.name,
            'requester_name': signature_request.created_by.name,
            'document_title': signature_request.title,
            'message': signature_request.message,
            'signing_url': signing_url,
            'expires_at': signature_request.expires_at,
            'site_domain': settings.SITE_DOMAIN
        }
        
        # Render email
        subject = _('Signature Request: {title}').format(title=signature_request.title)
        
        html_message = render_to_string('esign/signature_request_email.html', context)
        text_message = render_to_string('esign/signature_request_email.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signer.user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Sent signature request email to {signer.user.email}")
        
    except Signer.DoesNotExist:
        logger.error(f"Signer {signer_id} not found")
    except Exception as exc:
        logger.error(f"Error sending signature request email: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_signature_reminder_email_task(self, signer_id):
    """
    Send reminder email to signer.
    """
    try:
        signer = Signer.objects.select_related('signature_request__document', 'user').get(id=signer_id)
        signature_request = signer.signature_request
        
        # Activate user's language preference
        user_lang = signer.user.language or 'en'
        activate(user_lang)
        
        # Build signing URL
        signing_url = f"{settings.SITE_DOMAIN}/sign/{signer.token}"
        
        # Prepare context
        context = {
            'signer_name': signer.user.name,
            'requester_name': signature_request.created_by.name,
            'document_title': signature_request.title,
            'signing_url': signing_url,
            'expires_at': signature_request.expires_at,
            'site_domain': settings.SITE_DOMAIN
        }
        
        # Render email
        subject = _('Reminder: Please sign {title}').format(title=signature_request.title)
        
        html_message = render_to_string('esign/signature_reminder_email.html', context)
        text_message = render_to_string('esign/signature_reminder_email.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signer.user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Sent reminder email to {signer.user.email}")
        
    except Signer.DoesNotExist:
        logger.error(f"Signer {signer_id} not found")
    except Exception as exc:
        logger.error(f"Error sending reminder email: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_otp_email_task(self, signer_id, otp_code):
    """
    Send OTP verification code email to signer.
    """
    try:
        signer = Signer.objects.select_related('signature_request', 'user').get(id=signer_id)
        signature_request = signer.signature_request
        
        # Activate user's language preference
        user_lang = signer.user.language or 'en'
        activate(user_lang)
        
        # Prepare context
        context = {
            'signer_name': signer.user.name,
            'document_title': signature_request.title,
            'otp_code': otp_code,
            'site_domain': settings.SITE_DOMAIN
        }
        
        # Render email
        subject = _('Verification Code: {code}').format(code=otp_code)
        
        html_message = render_to_string('esign/otp_email.html', context)
        text_message = render_to_string('esign/otp_email.txt', context)
        
        # Send email
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signer.user.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Sent OTP email to {signer.user.email}")
        
    except Signer.DoesNotExist:
        logger.error(f"Signer {signer_id} not found")
    except Exception as exc:
        logger.error(f"Error sending OTP email: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_completion_email_task(self, signature_request_id):
    """
    Send completion notification emails to all parties.
    """
    try:
        signature_request = SignatureRequest.objects.select_related(
            'document', 'created_by'
        ).prefetch_related('signers__user').get(id=signature_request_id)
        
        # Email to requester
        requester_context = {
            'name': signature_request.created_by.name,
            'document_title': signature_request.title,
            'completed_at': signature_request.completed_at,
            'download_url': f"{settings.SITE_DOMAIN}/documents/{signature_request.document.id}",
            'site_domain': settings.SITE_DOMAIN
        }
        
        # Activate requester's language
        activate(signature_request.created_by.language or 'en')
        
        subject = _('Signature Completed: {title}').format(title=signature_request.title)
        html_message = render_to_string('esign/completion_email_requester.html', requester_context)
        text_message = render_to_string('esign/completion_email_requester.txt', requester_context)
        
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[signature_request.created_by.email],
            html_message=html_message,
            fail_silently=False
        )
        
        # Email to each signer
        for signer in signature_request.signers.filter(status='signed'):
            activate(signer.user.language or 'en')
            
            signer_context = {
                'name': signer.user.name,
                'document_title': signature_request.title,
                'completed_at': signature_request.completed_at,
                'download_url': f"{settings.SITE_DOMAIN}/documents/{signature_request.document.id}",
                'site_domain': settings.SITE_DOMAIN
            }
            
            subject = _('Signature Completed: {title}').format(title=signature_request.title)
            html_message = render_to_string('esign/completion_email_signer.html', signer_context)
            text_message = render_to_string('esign/completion_email_signer.txt', signer_context)
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[signer.user.email],
                html_message=html_message,
                fail_silently=False
            )
        
        logger.info(f"Sent completion emails for signature request {signature_request_id}")
        
    except SignatureRequest.DoesNotExist:
        logger.error(f"SignatureRequest {signature_request_id} not found")
    except Exception as exc:
        logger.error(f"Error sending completion emails: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_signed_pdf_task(self, signature_request_id):
    """
    Generate signed PDF with all signatures and certificate.
    """
    try:
        signature_request = SignatureRequest.objects.select_related('document').get(id=signature_request_id)
        
        # Process completion (flatten, generate certificate, upload)
        signed_storage_key, cert_storage_key, original_hash, final_hash = process_signature_completion(
            signature_request
        )
        
        # Create new document version
        original_version = signature_request.document.versions.filter(is_primary=True).first()
        
        # Get next version number
        max_version = signature_request.document.versions.aggregate(
            max_ver=models.Max('version_number')
        )['max_ver'] or 0
        new_version_number = max_version + 1
        
        # Create signed version
        signed_version = DocumentVersion.objects.create(
            document=signature_request.document,
            version_number=new_version_number,
            storage_key=signed_storage_key,
            original_storage_key=signed_storage_key,
            content_type='application/pdf',
            type='pdf',
            file_size=0,  # Will be updated by file server callback
            is_primary=True,
            has_pages=False,
            render_status=DocumentVersion.RENDER_NOT_APPLICABLE,
            metadata={
                'signature_request_id': str(signature_request.id),
                'original_document_hash': original_hash,
                'signed_document_hash': final_hash,
                'signed_at': signature_request.completed_at.isoformat()
            }
        )
        
        # Mark original version as not primary
        if original_version:
            original_version.is_primary = False
            original_version.save()
        
        # Update signature request
        signature_request.signed_document_version = signed_version
        signature_request.certificate_storage_key = cert_storage_key
        signature_request.original_document_hash = original_hash
        signature_request.metadata['signed_document_hash'] = final_hash
        signature_request.save()
        
        # Send completion emails
        send_completion_email_task.delay(signature_request_id)
        
        logger.info(f"Generated signed PDF for signature request {signature_request_id}")
        
    except SignatureRequest.DoesNotExist:
        logger.error(f"SignatureRequest {signature_request_id} not found")
    except Exception as exc:
        logger.error(f"Error generating signed PDF: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def check_expired_requests_task():
    """
    Periodic task to mark expired signature requests.
    """
    from django.db.models import Q
    
    now = timezone.now()
    
    # Find expired requests
    expired_requests = SignatureRequest.objects.filter(
        Q(status='sent') | Q(status='in_progress'),
        expires_at__lte=now
    )
    
    count = expired_requests.count()
    
    # Mark as expired
    expired_requests.update(status='expired')
    
    logger.info(f"Marked {count} signature requests as expired")
    
    # TODO: Send notification emails to requesters
    
    return count
