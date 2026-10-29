import secrets
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone

from core.models import BaseModel, Organization, User
from documents.models import Document, DocumentVersion


class SignatureRequest(BaseModel):
    """
    Represents a signature request workflow.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='signature_requests')
    document = models.ForeignKey(Document, on_delete=models.PROTECT, related_name='signature_requests')
    signed_document_version = models.ForeignKey(
        DocumentVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signature_requests_created')
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    signing_order = models.BooleanField(default=False, help_text='True = sequential, False = parallel')
    
    expires_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    certificate_storage_key = models.CharField(max_length=1024, blank=True)
    
    # Original document hash for audit trail
    original_document_hash = models.CharField(max_length=64, blank=True)
    
    # Metadata for audit and tracking
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_by', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f'{self.title} ({self.status})'
    
    def can_cancel(self):
        """Check if request can be cancelled."""
        return self.status in ['sent', 'in_progress']
    
    def can_send_reminders(self):
        """Check if reminders can be sent."""
        return self.status in ['sent', 'in_progress']


class Signer(BaseModel):
    """
    Represents a signer in a signature request.
    Only supports internal Coneshare users in Phase 1.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('otp_verified', 'OTP Verified'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
    ]
    
    signature_request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name='signers'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='signature_requests_as_signer'
    )
    
    signing_order = models.IntegerField(default=1, help_text='1 = first, 2 = second, etc.')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    
    # Token for signing link
    token = models.CharField(max_length=64, unique=True, db_index=True)
    
    # OTP verification
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    email_sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)
    
    # Audit fields (captured at signing time)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    
    class Meta:
        ordering = ['signing_order', 'created_at']
        indexes = [
            models.Index(fields=['signature_request', 'signing_order']),
            models.Index(fields=['token']),
            models.Index(fields=['user', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['signature_request', 'user'],
                name='unique_signer_per_request'
            )
        ]
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.user.name} - {self.status}'
    
    def can_sign(self):
        """
        Check if this signer can currently sign.
        Considers signing order, OTP verification, and request status.
        """
        request = self.signature_request
        
        # Check request is in valid state
        if request.status not in ['sent', 'in_progress']:
            return False, "Signature request is not active"
        
        # Check not expired
        if request.expires_at and request.expires_at < timezone.now():
            return False, "Signature request has expired"
        
        # Check OTP verified
        if not self.otp_verified_at:
            return False, "OTP verification required"
        
        # Check already signed or declined
        if self.status in ['signed', 'declined']:
            return False, f"Already {self.status}"
        
        # If sequential signing, check previous signers have signed
        if request.signing_order and self.signing_order > 1:
            previous_signers = request.signers.filter(
                signing_order__lt=self.signing_order
            )
            if not all(s.status == 'signed' for s in previous_signers):
                return False, "Waiting for previous signers to complete"
        
        return True, "OK"


class SignatureField(BaseModel):
    """
    Represents a field to be filled by a signer.
    """
    FIELD_TYPE_CHOICES = [
        ('signature', 'Signature'),
        ('initials', 'Initials'),
        ('date_signed', 'Date Signed'),
        ('full_name', 'Full Name'),
        ('text', 'Text'),
    ]
    
    signature_request = models.ForeignKey(
        SignatureRequest,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    signer = models.ForeignKey(
        Signer,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    
    field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES)
    
    # Position on PDF (percentage-based for responsive rendering)
    page_number = models.IntegerField()
    x = models.FloatField(help_text='Left position (%)')
    y = models.FloatField(help_text='Top position (%)')
    width = models.FloatField(help_text='Field width (%)')
    height = models.FloatField(help_text='Field height (%)')
    
    # Field properties
    label = models.CharField(max_length=100, blank=True)
    required = models.BooleanField(default=True)
    
    # Value (filled by signer)
    value = models.TextField(blank=True)
    filled_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['page_number', 'y', 'x']
        indexes = [
            models.Index(fields=['signature_request', 'signer']),
            models.Index(fields=['page_number']),
        ]
    
    def __str__(self):
        return f'{self.get_field_type_display()} - Page {self.page_number}'
    
    def clean(self):
        super().clean()
        # Signature and initials must be required
        if self.field_type in ['signature', 'initials'] and not self.required:
            raise ValidationError("Signature and initials fields must be required")


class SignerAction(BaseModel):
    """
    Audit log for all signer actions.
    """
    ACTION_CHOICES = [
        ('email_sent', 'Email Sent'),
        ('link_opened', 'Link Opened'),
        ('document_viewed', 'Document Viewed'),
        ('otp_requested', 'OTP Requested'),
        ('otp_verified', 'OTP Verified'),
        ('otp_failed', 'OTP Failed'),
        ('field_filled', 'Field Filled'),
        ('signed', 'Signed'),
        ('declined', 'Declined'),
    ]
    
    signer = models.ForeignKey(
        Signer,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Audit metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    
    # Action-specific data
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['signer', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f'{self.get_action_display()} - {self.timestamp}'


class FieldTemplate(BaseModel):
    """
    Reusable field layout template (optional, cheap to implement).
    """
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='field_templates')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='field_templates_created')
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Template configuration (JSON)
    # Structure: {
    #   'signers_count': 2,
    #   'fields': [
    #     {'type': 'signature', 'signer_index': 0, 'page': 1, 'x': 10, 'y': 80, 'width': 30, 'height': 8, ...},
    #     ...
    #   ]
    # }
    config = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_by']),
        ]
    
    def __str__(self):
        return self.name


class SignatureOTP(models.Model):
    """
    One-time password for signer verification.
    Stored temporarily in database with short expiry.
    """
    signer = models.ForeignKey(Signer, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['signer', 'code', 'verified']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # 10-minute expiry
            self.expires_at = timezone.now() + timezone.timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Check if OTP is still valid."""
        return (
            not self.verified
            and self.expires_at > timezone.now()
            and self.attempts < 5
        )
    
    def __str__(self):
        return f'OTP for {self.signer} - {self.code}'
