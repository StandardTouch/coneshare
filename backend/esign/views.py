import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError as DRFValidationError

from core.permissions import APIKeyTierPermission
from core.services import get_dynamic_setting
from documents.models import Document, DocumentVersion
from .models import (
    SignatureRequest, Signer, SignatureField,
    SignerAction, FieldTemplate, SignatureOTP
)
from .serializers import (
    SignatureRequestListSerializer, SignatureRequestDetailSerializer,
    SignatureRequestCreateSerializer, SignerSerializer,
    SignatureFieldSerializer, UpdateFieldsSerializer,
    SubmitSignatureSerializer, DeclineSerializer,
    RequestOTPSerializer, VerifyOTPSerializer,
    FieldTemplateSerializer, SignerActionSerializer
)
from .services import (
    generate_otp_code, record_signer_action, get_client_info,
    process_signature_completion
)
from .tasks import (
    send_signature_request_email_task,
    send_signature_reminder_email_task,
    generate_signed_pdf_task
)

logger = logging.getLogger(__name__)


def check_esign_enabled():
    """Check if e-signature feature is enabled."""
    if not get_dynamic_setting('ESIGN_ENABLED', default=False):
        raise PermissionDenied(_("E-Signature feature is not enabled."))


class SignatureRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for signature requests.
    """
    permission_classes = [IsAuthenticated, APIKeyTierPermission]
    
    def get_queryset(self):
        check_esign_enabled()
        
        user = self.request.user
        
        # Filter based on view type
        view_type = self.request.query_params.get('view', 'created')
        
        if view_type == 'awaiting':
            # Requests where user is a signer and hasn't signed yet
            return SignatureRequest.objects.filter(
                signers__user=user,
                signers__status__in=['sent', 'otp_verified', 'viewed']
            ).distinct().select_related('document', 'created_by')
        else:
            # Requests created by user
            return SignatureRequest.objects.filter(
                organization=user.organization,
                created_by=user
            ).select_related('document', 'created_by')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SignatureRequestCreateSerializer
        elif self.action == 'list':
            return SignatureRequestListSerializer
        else:
            return SignatureRequestDetailSerializer
    
    def perform_create(self, serializer):
        check_esign_enabled()
        
        # Set document queryset for validation
        serializer.fields['document_id'].queryset = Document.objects.filter(
            organization=self.request.user.organization,
            deleted_at__isnull=True
        )
        
        # Set user queryset for signers
        for signer_serializer in serializer.fields['signers'].child.fields.values():
            if hasattr(signer_serializer, 'queryset'):
                signer_serializer.queryset = User.objects.filter(
                    organization=self.request.user.organization,
                    is_active=True
                )
        
        signature_request = serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def update_fields(self, request, pk=None):
        """
        Update signature fields for a request in draft status.
        """
        check_esign_enabled()
        
        signature_request = self.get_object()
        
        # Only allow updates in draft status
        if signature_request.status != 'draft':
            raise DRFValidationError(_("Can only update fields for draft requests."))
        
        # Validate request data
        serializer = UpdateFieldsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Delete existing fields
        SignatureField.objects.filter(signature_request=signature_request).delete()
        
        # Create new fields
        fields_data = serializer.validated_data['fields']
        signer_ids = {s.id for s in signature_request.signers.all()}
        
        for field_data in fields_data:
            signer_id = field_data['signer_id']
            
            # Validate signer belongs to this request
            if signer_id not in signer_ids:
                raise DRFValidationError(_(f"Invalid signer_id: {signer_id}"))
            
            SignatureField.objects.create(
                signature_request=signature_request,
                signer_id=signer_id,
                field_type=field_data['field_type'],
                page_number=field_data['page_number'],
                x=field_data['x'],
                y=field_data['y'],
                width=field_data['width'],
                height=field_data['height'],
                label=field_data.get('label', ''),
                required=field_data.get('required', True)
            )
        
        return Response({'message': _('Fields updated successfully.')})
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """
        Send signature request to signers.
        """
        check_esign_enabled()
        
        signature_request = self.get_object()
        
        # Validate status
        if signature_request.status != 'draft':
            raise DRFValidationError(_("Request has already been sent."))
        
        # Validate has signers
        signers = list(signature_request.signers.all())
        if not signers:
            raise DRFValidationError(_("Request must have at least one signer."))
        
        # Validate has fields
        if not signature_request.fields.exists():
            raise DRFValidationError(_("Request must have at least one signature field."))
        
        # Update status
        signature_request.status = 'sent'
        signature_request.save()
        
        # Send emails
        if signature_request.signing_order:
            # Sequential: send only to first signer
            first_signer = signers[0]
            first_signer.status = 'sent'
            first_signer.email_sent_at = timezone.now()
            first_signer.save()
            
            record_signer_action(first_signer, 'email_sent')
            send_signature_request_email_task.delay(first_signer.id)
        else:
            # Parallel: send to all signers
            for signer in signers:
                signer.status = 'sent'
                signer.email_sent_at = timezone.now()
                signer.save()
                
                record_signer_action(signer, 'email_sent')
                send_signature_request_email_task.delay(signer.id)
        
        return Response({'message': _('Signature request sent successfully.')})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancel/void signature request.
        """
        check_esign_enabled()
        
        signature_request = self.get_object()
        
        if not signature_request.can_cancel():
            raise DRFValidationError(_("Request cannot be cancelled in its current status."))
        
        signature_request.status = 'cancelled'
        signature_request.save()
        
        # Send cancellation emails to pending signers
        from .tasks import send_cancellation_email_task
        send_cancellation_email_task.delay(signature_request.id)
        
        return Response({'message': _('Signature request cancelled.')})
    
    @action(detail=True, methods=['post'])
    def remind(self, request, pk=None):
        """
        Send reminder to pending signers.
        """
        check_esign_enabled()
        
        signature_request = self.get_object()
        
        if not signature_request.can_send_reminders():
            raise DRFValidationError(_("Cannot send reminders for this request."))
        
        # Get pending signers
        pending_signers = signature_request.signers.filter(
            status__in=['sent', 'viewed', 'otp_verified']
        )
        
        if not pending_signers.exists():
            raise DRFValidationError(_("No pending signers to remind."))
        
        # Send reminders
        for signer in pending_signers:
            send_signature_reminder_email_task.delay(signer.id)
        
        # Update metadata
        reminders = signature_request.metadata.get('reminders_sent', [])
        reminders.append(timezone.now().isoformat())
        signature_request.metadata['reminders_sent'] = reminders
        signature_request.save()
        
        return Response({'message': _(f'Reminders sent to {pending_signers.count()} signer(s).')})
    
    @action(detail=True, methods=['get'])
    def download_signed(self, request, pk=None):
        """
        Get download URL for signed document.
        """
        check_esign_enabled()
        
        signature_request = self.get_object()
        
        if signature_request.status != 'completed':
            raise DRFValidationError(_("Document is not yet signed."))
        
        if not signature_request.signed_document_version:
            raise DRFValidationError(_("Signed document not available."))
        
        # Generate download URL
        from documents.fileserver import fileserver_client
        
        response = fileserver_client.generate_download_url(
            storage_key=signature_request.signed_document_version.storage_key,
            filename=f"signed_{signature_request.document.name}"
        )
        
        return Response({
            'download_url': response.get('url'),
            'filename': f"signed_{signature_request.document.name}"
        })
    
    @action(detail=True, methods=['get'])
    def download_certificate(self, request, pk=None):
        """
        Get download URL for certificate of completion.
        """
        check_esign_enabled()
        
        signature_request = self.get_object()
        
        if signature_request.status != 'completed':
            raise DRFValidationError(_("Document is not yet signed."))
        
        if not signature_request.certificate_storage_key:
            raise DRFValidationError(_("Certificate not available."))
        
        # Generate download URL
        from documents.fileserver import fileserver_client
        
        response = fileserver_client.generate_download_url(
            storage_key=signature_request.certificate_storage_key,
            filename=f"certificate_{signature_request.document.name}.pdf"
        )
        
        return Response({
            'download_url': response.get('url'),
            'filename': f"certificate_{signature_request.document.name}.pdf"
        })


class SigningViewSet(viewsets.ViewSet):
    """
    ViewSet for signing workflow (authenticated users only - Phase 1).
    Token in URL identifies which signature request, but user must be logged in
    and must be the assigned signer.
    """
    permission_classes = [IsAuthenticated, APIKeyTierPermission]
    
    def retrieve(self, request, token=None):
        """
        Get signing page data by token.
        """
        check_esign_enabled()
        
        signer = get_object_or_404(Signer, token=token)
        signature_request = signer.signature_request
        
        # CRITICAL: Verify authenticated user is the assigned signer
        if request.user != signer.user:
            return Response(
                {'detail': _('You are not authorized to sign this request.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check request status
        if signature_request.status not in ['sent', 'in_progress']:
            return Response(
                {'detail': _('This signature request is no longer active.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check expiration
        if signature_request.expires_at and signature_request.expires_at < timezone.now():
            signature_request.status = 'expired'
            signature_request.save()
            return Response(
                {'detail': _('This signature request has expired.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Record view action
        if signer.status == 'sent' or not signer.viewed_at:
            signer.status = 'viewed'
            signer.viewed_at = timezone.now()
            signer.save()
            record_signer_action(signer, 'link_opened', request)
        
        # Prepare response
        serializer = SignerSerializer(signer)
        data = serializer.data
        
        # Add request info
        data['signature_request'] = {
            'id': signature_request.id,
            'title': signature_request.title,
            'message': signature_request.message,
            'document': {
                'id': signature_request.document.id,
                'name': signature_request.document.name,
                'num_pages': signature_request.document.num_pages
            },
            'signing_order': signature_request.signing_order,
            'expires_at': signature_request.expires_at
        }
        
        # Add can_sign status
        can_sign, reason = signer.can_sign()
        data['can_sign'] = can_sign
        data['can_sign_reason'] = reason
        
        return Response(data)
    
    @action(detail=True, methods=['post'])
    def request_otp(self, request, token=None):
        """
        Request OTP for signing.
        """
        check_esign_enabled()
        
        signer = get_object_or_404(Signer, token=token)
        
        # CRITICAL: Verify authenticated user is the assigned signer
        if request.user != signer.user:
            return Response(
                {'detail': _('You are not authorized to sign this request.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already verified
        if signer.otp_verified_at:
            return Response({'message': _('Already verified.')})
        
        # Generate OTP
        otp_code = generate_otp_code()
        
        # Delete old OTPs for this signer
        SignatureOTP.objects.filter(signer=signer, verified=False).delete()
        
        # Create new OTP
        otp = SignatureOTP.objects.create(
            signer=signer,
            code=otp_code
        )
        
        # Record action
        record_signer_action(signer, 'otp_requested', request)
        
        # Send OTP email
        from .tasks import send_otp_email_task
        send_otp_email_task.delay(signer.id, otp_code)
        
        return Response({
            'message': _('Verification code sent to your email.'),
            'expires_in_seconds': 600
        })
    
    @action(detail=True, methods=['post'])
    def verify_otp(self, request, token=None):
        """
        Verify OTP for signing.
        """
        check_esign_enabled()
        
        signer = get_object_or_404(Signer, token=token)
        
        # CRITICAL: Verify authenticated user is the assigned signer
        if request.user != signer.user:
            return Response(
                {'detail': _('You are not authorized to sign this request.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already verified
        if signer.otp_verified_at:
            return Response({'message': _('Already verified.'), 'verified': True})
        
        # Validate request
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        code = serializer.validated_data['code']
        
        # Find valid OTP
        try:
            otp = SignatureOTP.objects.get(
                signer=signer,
                code=code,
                verified=False
            )
        except SignatureOTP.DoesNotExist:
            record_signer_action(signer, 'otp_failed', request, {'code': code[:2] + '****'})
            return Response(
                {'detail': _('Invalid verification code.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check validity
        if not otp.is_valid():
            if otp.expires_at < timezone.now():
                return Response(
                    {'detail': _('Verification code has expired. Please request a new one.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                return Response(
                    {'detail': _('Too many failed attempts. Please request a new code.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Increment attempts
        otp.attempts += 1
        
        # Verify
        otp.verified = True
        otp.save()
        
        signer.status = 'otp_verified'
        signer.otp_verified_at = timezone.now()
        signer.save()
        
        # Record action
        ip_address, user_agent = get_client_info(request)
        signer.ip_address = ip_address
        signer.user_agent = user_agent
        signer.save()
        
        record_signer_action(signer, 'otp_verified', request)
        
        return Response({'message': _('Verified successfully.'), 'verified': True})
    
    @action(detail=True, methods=['post'])
    def submit(self, request, token=None):
        """
        Submit signature.
        """
        check_esign_enabled()
        
        signer = get_object_or_404(Signer, token=token)
        signature_request = signer.signature_request
        
        # CRITICAL: Verify authenticated user is the assigned signer
        if request.user != signer.user:
            return Response(
                {'detail': _('You are not authorized to sign this request.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check can sign
        can_sign, reason = signer.can_sign()
        if not can_sign:
            return Response(
                {'detail': reason},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate request
        serializer = SubmitSignatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        fields_data = serializer.validated_data['fields']
        
        # Update signature with transaction
        with transaction.atomic():
            # Get signer's fields
            signer_fields = {f.id: f for f in signer.fields.all()}
            
            # Validate all required fields are filled
            required_field_ids = {f.id for f in signer_fields.values() if f.required}
            filled_field_ids = {fd['field_id'] for fd in fields_data}
            
            missing_fields = required_field_ids - filled_field_ids
            if missing_fields:
                return Response(
                    {'detail': _('All required fields must be filled.')},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update fields
            for field_data in fields_data:
                field_id = field_data['field_id']
                if field_id not in signer_fields:
                    return Response(
                        {'detail': _(f'Invalid field_id: {field_id}')},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                field = signer_fields[field_id]
                field.value = field_data['value']
                field.filled_at = timezone.now()
                field.save()
                
                record_signer_action(
                    signer, 'field_filled', request,
                    {'field_id': field_id, 'field_type': field.field_type}
                )
            
            # Update signer status
            signer.status = 'signed'
            signer.signed_at = timezone.now()
            signer.save()
            
            # Record signing action
            record_signer_action(signer, 'signed', request)
            
            # Check if all signers have signed
            all_signed = not signature_request.signers.exclude(status='signed').exists()
            
            if all_signed:
                # Mark request as completed
                signature_request.status = 'completed'
                signature_request.completed_at = timezone.now()
                signature_request.save()
                
                # Queue PDF generation
                generate_signed_pdf_task.delay(signature_request.id)
                
                return Response({
                    'message': _('Thank you! All signers have completed. The signed document is being prepared.'),
                    'status': 'completed'
                })
            else:
                # Update request status to in_progress
                if signature_request.status == 'sent':
                    signature_request.status = 'in_progress'
                    signature_request.save()
                
                # If sequential, send email to next signer
                if signature_request.signing_order:
                    next_signer = signature_request.signers.filter(
                        signing_order=signer.signing_order + 1,
                        status='pending'
                    ).first()
                    
                    if next_signer:
                        next_signer.status = 'sent'
                        next_signer.email_sent_at = timezone.now()
                        next_signer.save()
                        
                        record_signer_action(next_signer, 'email_sent')
                        send_signature_request_email_task.delay(next_signer.id)
                
                return Response({
                    'message': _('Thank you! Your signature has been recorded.'),
                    'status': 'signed'
                })
    
    @action(detail=True, methods=['post'])
    def decline(self, request, token=None):
        """
        Decline to sign.
        """
        check_esign_enabled()
        
        signer = get_object_or_404(Signer, token=token)
        signature_request = signer.signature_request
        
        # CRITICAL: Verify authenticated user is the assigned signer
        if request.user != signer.user:
            return Response(
                {'detail': _('You are not authorized to decline this request.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check request status
        if signature_request.status not in ['sent', 'in_progress']:
            return Response(
                {'detail': _('This signature request is no longer active.')},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check signer status
        if signer.status in ['signed', 'declined']:
            return Response(
                {'detail': _(f'You have already {signer.status} this request.')},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate request
        serializer = DeclineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        reason = serializer.validated_data.get('reason', '')
        
        # Update signer
        signer.status = 'declined'
        signer.declined_at = timezone.now()
        signer.decline_reason = reason
        signer.save()
        
        # Record action
        record_signer_action(signer, 'declined', request, {'reason': reason})
        
        # Update request status
        signature_request.status = 'declined'
        signature_request.save()
        
        # Send notification email to requester
        from .tasks import send_decline_notification_email_task
        send_decline_notification_email_task.delay(signature_request.id, signer.id)
        
        return Response({'message': _('Your response has been recorded.')})


class FieldTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for field templates.
    """
    permission_classes = [IsAuthenticated, APIKeyTierPermission]
    serializer_class = FieldTemplateSerializer
    
    def get_queryset(self):
        check_esign_enabled()
        
        return FieldTemplate.objects.filter(
            organization=self.request.user.organization,
            created_by=self.request.user
        )
    
    def perform_create(self, serializer):
        check_esign_enabled()
        
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user
        )
