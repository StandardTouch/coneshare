from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core.services import get_dynamic_setting

from .serializers import InviteSetPasswordSerializer
from .services import invite_feature_enabled, validate_invite_token
from .tokens import user_invite_token_generator

User = get_user_model()


class InviteFeatureRequiredMixin:
    def _feature_disabled_response(self):
        return Response({'detail': _('Invite links are not enabled.')}, status=status.HTTP_404_NOT_FOUND)

    def _check_feature(self):
        return invite_feature_enabled()


@extend_schema(tags=['onboarding'])
class InviteValidateView(InviteFeatureRequiredMixin, APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'invite_validate'

    @extend_schema(responses={200: dict, 400: dict, 404: dict})
    def get(self, request):
        if not self._check_feature():
            return self._feature_disabled_response()

        uid = request.query_params.get('uid', '').strip()
        token = request.query_params.get('token', '').strip()
        user, reason = validate_invite_token(uid, token)

        if reason == 'valid' and user:
            return Response({'valid': True, 'email': user.email}, status=status.HTTP_200_OK)
        if reason == 'used':
            return Response({'valid': False, 'detail': _('This invite link has already been used.')}, status=status.HTTP_400_BAD_REQUEST)
        if reason == 'missing':
            return Response({'valid': False, 'detail': _('Invalid invite link.')}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'valid': False, 'detail': _('Invalid or expired invite link.')}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['onboarding'])
class InviteSetPasswordView(InviteFeatureRequiredMixin, APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'invite_set_password'

    @extend_schema(request=InviteSetPasswordSerializer, responses={200: dict, 400: dict, 404: dict})
    def post(self, request):
        if not self._check_feature():
            return self._feature_disabled_response()

        serializer = InviteSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        password = serializer.validated_data['password1']

        user, reason = validate_invite_token(uid, token)
        if reason != 'valid' or not user:
            if reason == 'used':
                return Response({'detail': _('This invite link has already been used.')}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': _('Invalid or expired invite link.')}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=user.pk)
            if locked.has_usable_password():
                return Response({'detail': _('This invite link has already been used.')}, status=status.HTTP_400_BAD_REQUEST)
            if not user_invite_token_generator.check_token(locked, token):
                return Response({'detail': _('Invalid or expired invite link.')}, status=status.HTTP_400_BAD_REQUEST)

            locked.set_password(password)
            if not locked.is_active:
                locked.is_active = True
            locked.updated_at = timezone.now()
            locked.save(update_fields=['password', 'is_active', 'updated_at'])

        return Response({'detail': _('Password set successfully. You can now sign in.')}, status=status.HTTP_200_OK)
