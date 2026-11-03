"""Invite set-password link validation (read-only; links are consumed on successful POST)."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from .tokens import user_invite_token_generator

User = get_user_model()


def _load_user_from_uid(uid: str):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
    except (TypeError, ValueError, OverflowError, ValidationError):
        return None
    try:
        return User.objects.select_related('organization', 'invite_state').get(pk=user_id)
    except User.DoesNotExist:
        return None


def validate_invite_token(uid: str, token: str):
    """
    Validate an invite set-password link without mutating invite state.

    Returns (user, reason) where reason is one of:
    missing, invalid, expired, used, valid
    """
    if not uid or not token:
        return None, 'missing'

    user = _load_user_from_uid(uid)
    if user is None:
        return None, 'invalid'

    if user.has_usable_password():
        return None, 'used'

    token_status = user_invite_token_generator.token_status(user, token)
    if token_status == 'valid':
        return user, 'valid'
    if token_status == 'expired':
        return None, 'expired'
    return None, 'invalid'
