from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import SignatureRequestViewSet, SigningViewSet, FieldTemplateViewSet

router = DefaultRouter()
router.register(r'requests', SignatureRequestViewSet, basename='signature-request')
router.register(r'templates', FieldTemplateViewSet, basename='field-template')

# Signing endpoints (token-based, no auth required)
signing_router = DefaultRouter()
signing_router.register(r'sign', SigningViewSet, basename='signing')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(signing_router.urls)),
]
