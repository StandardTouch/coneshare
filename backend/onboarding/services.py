import logging
from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils import timezone

from core.i18n_utils import resolve_email_language
from core.models import Organization
from core.services import get_dynamic_setting

from .models import UserInviteState
from .tasks import send_user_invite_email_task
from .tokens import user_invite_token_generator

User = get_user_model()
logger = logging.getLogger(__name__)

RESEND_RATE_LIMIT_SECONDS = 60


def invite_feature_enabled() -> bool:
    return bool(get_dynamic_setting('USER_INVITE_EMAIL_ENABLED'))


def _branding_for_user(user):
    org = user.organization
    brand_name = org.brand_name if org and org.brand_name else 'Allure Clinic'
    brand_logo_url = None
    if org and org.brand_logo and hasattr(org.brand_logo, 'url'):
        brand_logo_url = urljoin(settings.SITE_DOMAIN, org.brand_logo.url)
    return brand_name, brand_logo_url


def build_invite_set_password_url(user) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = user_invite_token_generator.make_token(user)
    base = settings.SITE_DOMAIN.rstrip('/')
    return f'{base}/set-password/{uid}/{token}'


def _queue_invite_email(user, request=None):
    accept_header = ''
    if request is not None:
        accept_header = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    language = resolve_email_language(
        accept_header=accept_header,
        user_lang=getattr(user, 'language', None),
        request_lang=getattr(request, 'LANGUAGE_CODE', None) if request else None,
        default_lang='en',
    )
    brand_name, brand_logo_url = _branding_for_user(user)
    set_password_url = build_invite_set_password_url(user)

    def _send():
        send_user_invite_email_task.delay(
            email=user.email,
            set_password_url=set_password_url,
            language=language,
            brand_name=brand_name,
            brand_logo_url=brand_logo_url,
        )

    transaction.on_commit(_send)


def ensure_invite_state(user) -> UserInviteState:
    state, _ = UserInviteState.objects.get_or_create(user=user)
    return state


@transaction.atomic
def create_user_with_invite(validated_data, request):
    organization = validated_data.get('organization') or Organization.objects.first()
    if not organization:
        raise ValueError('Server is not configured with a default organization.')
    validated_data['organization'] = organization
    if 'username' not in validated_data and 'email' in validated_data:
        validated_data['username'] = validated_data['email']

    user = User(**validated_data)
    user.set_unusable_password()
    user.save()

    ensure_invite_state(user)
    now = timezone.now()
    UserInviteState.objects.filter(user=user).update(last_invite_sent_at=now)

    admin_email = getattr(request.user, 'email', None) if request else None
    logger.info(
        'user_invite_sent user_id=%s user_email=%s admin_email=%s',
        user.id,
        user.email,
        admin_email,
    )

    _queue_invite_email(user, request)
    return user


@transaction.atomic
def resend_user_invite(user, request):
    if not invite_feature_enabled():
        return False, 'disabled'

    cache_key = f'user_invite_resend:{user.id}'
    if cache.get(cache_key):
        return False, 'rate_limited'

    state = ensure_invite_state(user)
    state.invite_nonce += 1
    state.last_invite_sent_at = timezone.now()
    state.save(update_fields=['invite_nonce', 'last_invite_sent_at', 'updated_at'])

    cache.set(cache_key, 1, timeout=RESEND_RATE_LIMIT_SECONDS)

    admin_email = getattr(request.user, 'email', None)
    logger.info(
        'user_invite_resent user_id=%s user_email=%s admin_email=%s',
        user.id,
        user.email,
        admin_email,
    )

    _queue_invite_email(user, request)
    return True, 'sent'


def validate_invite_token(uid: str, token: str):
    from django.utils.encoding import force_str
    from django.utils.http import urlsafe_base64_decode
    from django.core.exceptions import ValidationError

    if not uid or not token:
        return None, 'missing'

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.select_related('organization').get(pk=user_id)
    except (TypeError, ValueError, OverflowError, ValidationError, User.DoesNotExist):
        return None, 'invalid'

    if user.has_usable_password():
        return None, 'used'

    if not user_invite_token_generator.check_token(user, token):
        return None, 'invalid'

    return user, 'valid'
