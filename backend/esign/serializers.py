from rest_framework import serializers
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import User
from core.serializers import UserSerializer
from documents.serializers import DocumentSerializer
from .models import (
    SignatureRequest, Signer, SignatureField,
    SignerAction, FieldTemplate, SignatureOTP
)


class SignatureFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignatureField
        fields = [
            'id', 'field_type', 'page_number', 'x', 'y', 'width', 'height',
            'label', 'required', 'value', 'filled_at'
        ]
        read_only_fields = ['id', 'filled_at']


class SignerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=None,  # Set in view
        source='user',
        write_only=True
    )
    fields = SignatureFieldSerializer(many=True, read_only=True)
    can_sign = serializers.SerializerMethodField()
    can_sign_reason = serializers.SerializerMethodField()
    
    class Meta:
        model = Signer
        fields = [
            'id', 'user', 'user_id', 'signing_order', 'status',
            'email_sent_at', 'viewed_at', 'signed_at', 'declined_at',
            'decline_reason', 'otp_verified_at', 'fields',
            'can_sign', 'can_sign_reason', 'token'
        ]
        read_only_fields = [
            'id', 'status', 'email_sent_at', 'viewed_at', 'signed_at',
            'declined_at', 'otp_verified_at', 'token'
        ]
        extra_kwargs = {
            'token': {'write_only': False}  # Expose for signing links
        }
    
    def get_can_sign(self, obj):
        can_sign, _ = obj.can_sign()
        return can_sign
    
    def get_can_sign_reason(self, obj):
        _, reason = obj.can_sign()
        return reason


class SignerActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignerAction
        fields = ['id', 'action', 'timestamp', 'ip_address', 'user_agent', 'metadata']
        read_only_fields = fields


class SignatureRequestListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    created_by = UserSerializer(read_only=True)
    document = DocumentSerializer(read_only=True)
    signers_count = serializers.SerializerMethodField()
    signed_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SignatureRequest
        fields = [
            'id', 'title', 'document', 'created_by', 'status',
            'signing_order', 'expires_at', 'created_at', 'completed_at',
            'signers_count', 'signed_count'
        ]
        read_only_fields = fields
    
    def get_signers_count(self, obj):
        return obj.signers.count()
    
    def get_signed_count(self, obj):
        return obj.signers.filter(status='signed').count()


class SignatureRequestDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested signers and fields."""
    created_by = UserSerializer(read_only=True)
    document = DocumentSerializer(read_only=True)
    signers = SignerSerializer(many=True, read_only=True)
    
    class Meta:
        model = SignatureRequest
        fields = [
            'id', 'title', 'message', 'document', 'created_by', 'status',
            'signing_order', 'expires_at', 'created_at', 'updated_at',
            'completed_at', 'signed_document_version', 'certificate_storage_key',
            'original_document_hash', 'signers', 'metadata'
        ]
        read_only_fields = [
            'id', 'created_by', 'status', 'created_at', 'updated_at',
            'completed_at', 'signed_document_version', 'certificate_storage_key',
            'original_document_hash'
        ]


class SignatureRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating signature requests."""
    document_id = serializers.PrimaryKeyRelatedField(
        queryset=None,  # Set in view
        source='document',
        write_only=True
    )
    signers = SignerSerializer(many=True, write_only=True)
    
    class Meta:
        model = SignatureRequest
        fields = [
            'document_id', 'title', 'message', 'signing_order',
            'expires_at', 'signers'
        ]
    
    def validate_signers(self, value):
        if not value or len(value) < 1:
            raise serializers.ValidationError(_("At least one signer is required."))
        
        # Check for duplicate users
        user_ids = [s['user'].id for s in value]
        if len(user_ids) != len(set(user_ids)):
            raise serializers.ValidationError(_("Duplicate signers are not allowed."))
        
        # Validate signing order
        if self.initial_data.get('signing_order'):
            orders = [s.get('signing_order', 1) for s in value]
            if not all(isinstance(o, int) and o > 0 for o in orders):
                raise serializers.ValidationError(_("Invalid signing order."))
        
        return value
    
    def validate_expires_at(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError(_("Expiration date must be in the future."))
        return value
    
    def create(self, validated_data):
        signers_data = validated_data.pop('signers')
        request = super().create(validated_data)
        
        # Create signers
        for signer_data in signers_data:
            Signer.objects.create(
                signature_request=request,
                user=signer_data['user'],
                signing_order=signer_data.get('signing_order', 1)
            )
        
        return request


class UpdateFieldsSerializer(serializers.Serializer):
    """Serializer for updating signature fields."""
    fields = serializers.ListField(child=serializers.DictField())
    
    def validate_fields(self, value):
        for field_data in value:
            # Validate required keys
            required_keys = ['signer_id', 'field_type', 'page_number', 'x', 'y', 'width', 'height']
            if not all(k in field_data for k in required_keys):
                raise serializers.ValidationError(
                    _("Each field must have: signer_id, field_type, page_number, x, y, width, height")
                )
            
            # Validate field type
            valid_types = ['signature', 'initials', 'date_signed', 'full_name', 'text']
            if field_data['field_type'] not in valid_types:
                raise serializers.ValidationError(
                    _("Invalid field_type. Must be one of: {types}").format(types=', '.join(valid_types))
                )
            
            # Validate coordinates
            for coord in ['x', 'y', 'width', 'height']:
                if not (0 <= float(field_data[coord]) <= 100):
                    raise serializers.ValidationError(
                        _("{coord} must be between 0 and 100 (percentage)").format(coord=coord)
                    )
        
        return value


class SubmitSignatureSerializer(serializers.Serializer):
    """Serializer for submitting signatures."""
    fields = serializers.ListField(child=serializers.DictField())
    
    def validate_fields(self, value):
        for field_data in value:
            if 'field_id' not in field_data or 'value' not in field_data:
                raise serializers.ValidationError(
                    _("Each field must have: field_id, value")
                )
        return value


class DeclineSerializer(serializers.Serializer):
    """Serializer for declining to sign."""
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class RequestOTPSerializer(serializers.Serializer):
    """Serializer for requesting OTP."""
    # No fields needed; OTP sent to signer's email


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP."""
    code = serializers.CharField(max_length=6, min_length=6)


class FieldTemplateSerializer(serializers.ModelSerializer):
    """Serializer for field templates."""
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FieldTemplate
        fields = ['id', 'name', 'description', 'config', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']
