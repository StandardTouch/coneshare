from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SignatureRequestViewSet, SigningViewSet, FieldTemplateViewSet
from .pdf_views import (
    EsignDocumentPdfView,
    EsignRequestDocumentPdfView,
    EsignSignerDocumentPdfView,
)

router = DefaultRouter()
router.register(r'requests', SignatureRequestViewSet, basename='signature-request')
router.register(r'templates', FieldTemplateViewSet, basename='field-template')

# Signing endpoints (token-based, no auth required)
signing_router = DefaultRouter()
signing_router.register(r'sign', SigningViewSet, basename='signing')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(signing_router.urls)),
    path('documents/<str:document_id>/pdf/', EsignDocumentPdfView.as_view(), name='esign-document-pdf'),
    path('requests/<str:request_id>/pdf/', EsignRequestDocumentPdfView.as_view(), name='esign-request-pdf'),
    path('sign/<str:token>/pdf/', EsignSignerDocumentPdfView.as_view(), name='esign-signer-pdf'),
]
