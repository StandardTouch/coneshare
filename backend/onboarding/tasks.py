from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation
from django.utils.translation import gettext as _


@shared_task
def send_user_invite_email_task(
    email: str,
    set_password_url: str,
    language: str = 'en',
    brand_name: str | None = None,
    brand_logo_url: str | None = None,
):
    with translation.override(language):
        display_brand = brand_name or 'Allure Clinic'
        context = {
            'set_password_url': set_password_url,
            'site_domain': settings.SITE_DOMAIN,
            'brand_name': display_brand,
            'brand_logo_url': brand_logo_url,
        }
        text_content = render_to_string('onboarding/user_invite_email.txt', context)
        html_content = render_to_string('onboarding/user_invite_email.html', context)

        send_mail(
            subject=_('Your Allure portal account is ready'),
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_content,
        )
