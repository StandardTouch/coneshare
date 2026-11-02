"""
Authenticated PDF endpoints for e-sign field placement and signing.
"""
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import APIKeyTierPermission
from documents.models import Document
from .models import Signer, SignatureRequest
from .pdf_stream import build_pdf_response_for_version
from .views import check_esign_enabled


def _primary_version(document):
    return document.versions.filter(is_primary=True).first()


class EsignDocumentPdfView(APIView):
    """Stream the source PDF for field placement (organization member)."""

    permission_classes = [IsAuthenticated, APIKeyTierPermission]

    def get(self, request, document_id: str):
        check_esign_enabled()
        document = get_object_or_404(
            Document,
            pk=document_id,
            organization=request.user.organization,
            deleted_at__isnull=True,
        )
        version = _primary_version(document)
        if not version:
            return Response({"detail": _("Document version not found.")}, status=status.HTTP_404_NOT_FOUND)

        as_attachment = request.query_params.get("download") in ("1", "true", "yes")
        return build_pdf_response_for_version(
            version,
            request,
            filename=document.name,
            as_attachment=as_attachment,
        )


class EsignRequestDocumentPdfView(APIView):
    """Stream source PDF for a signature request (owner or assigned signer)."""

    permission_classes = [IsAuthenticated, APIKeyTierPermission]

    def get(self, request, request_id: str):
        check_esign_enabled()
        signature_request = get_object_or_404(SignatureRequest, pk=request_id)
        user = request.user
        is_owner = (
            signature_request.organization_id == user.organization_id
            and signature_request.created_by_id == user.id
        )
        is_signer = signature_request.signers.filter(user=user).exists()
        if not (is_owner or is_signer):
            return Response({"detail": _("Not authorized.")}, status=status.HTTP_403_FORBIDDEN)

        version = _primary_version(signature_request.document)
        if not version:
            return Response({"detail": _("Document version not found.")}, status=status.HTTP_404_NOT_FOUND)

        as_attachment = request.query_params.get("download") in ("1", "true", "yes")
        return build_pdf_response_for_version(
            version,
            request,
            filename=signature_request.document.name,
            as_attachment=as_attachment,
        )


class EsignSignerDocumentPdfView(APIView):
    """Stream source PDF for an assigned signer (requires verified OTP)."""

    permission_classes = [IsAuthenticated, APIKeyTierPermission]

    def get(self, request, token: str):
        check_esign_enabled()
        signer = get_object_or_404(Signer, token=token)
        signature_request = signer.signature_request

        if request.user != signer.user:
            return Response(
                {"detail": _("You are not authorized to access this document.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if signature_request.status not in ("sent", "in_progress", "completed"):
            return Response(
                {"detail": _("This signature request is no longer active.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not signer.otp_verified_at:
            return Response(
                {"detail": _("OTP verification required before viewing the document.")},
                status=status.HTTP_403_FORBIDDEN,
            )

        version = _primary_version(signature_request.document)
        if not version:
            return Response({"detail": _("Document version not found.")}, status=status.HTTP_404_NOT_FOUND)

        as_attachment = request.query_params.get("download") in ("1", "true", "yes")
        return build_pdf_response_for_version(
            version,
            request,
            filename=signature_request.document.name,
            as_attachment=as_attachment,
        )
