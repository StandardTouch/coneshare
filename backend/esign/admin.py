from django.contrib import admin
from .models import (
    SignatureRequest, Signer, SignatureField,
    SignerAction, FieldTemplate, SignatureOTP
)


@admin.register(SignatureRequest)
class SignatureRequestAdmin(admin.ModelAdmin):
    list_display = ['title', 'organization', 'created_by', 'status', 'created_at', 'completed_at']
    list_filter = ['status', 'signing_order', 'created_at']
    search_fields = ['title', 'created_by__email', 'created_by__name']
    readonly_fields = ['created_at', 'updated_at', 'original_document_hash', 'completed_at']
    
    fieldsets = (
        (None, {
            'fields': ('organization', 'document', 'created_by', 'title', 'message')
        }),
        ('Settings', {
            'fields': ('status', 'signing_order', 'expires_at')
        }),
        ('Completion', {
            'fields': ('signed_document_version', 'completed_at', 'certificate_storage_key', 'original_document_hash')
        }),
        ('Metadata', {
            'fields': ('metadata', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Signer)
class SignerAdmin(admin.ModelAdmin):
    list_display = ['user', 'signature_request', 'signing_order', 'status', 'signed_at']
    list_filter = ['status', 'signing_order']
    search_fields = ['user__email', 'user__name', 'signature_request__title']
    readonly_fields = ['token', 'created_at', 'updated_at', 'email_sent_at', 'viewed_at', 'signed_at', 'declined_at', 'otp_verified_at']


@admin.register(SignatureField)
class SignatureFieldAdmin(admin.ModelAdmin):
    list_display = ['field_type', 'signer', 'page_number', 'required', 'filled_at']
    list_filter = ['field_type', 'required', 'page_number']
    search_fields = ['signer__user__email', 'label']


@admin.register(SignerAction)
class SignerActionAdmin(admin.ModelAdmin):
    list_display = ['signer', 'action', 'timestamp', 'ip_address']
    list_filter = ['action', 'timestamp']
    search_fields = ['signer__user__email']
    readonly_fields = ['timestamp', 'ip_address', 'user_agent', 'metadata']


@admin.register(FieldTemplate)
class FieldTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'created_by', 'created_at']
    list_filter = ['organization', 'created_at']
    search_fields = ['name', 'description', 'created_by__email']


@admin.register(SignatureOTP)
class SignatureOTPAdmin(admin.ModelAdmin):
    list_display = ['signer', 'code', 'created_at', 'expires_at', 'verified', 'attempts']
    list_filter = ['verified', 'created_at']
    search_fields = ['signer__user__email', 'code']
    readonly_fields = ['created_at', 'expires_at']
