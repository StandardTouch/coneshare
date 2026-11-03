from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status

from core.models import AppConfiguration, User
from onboarding.models import UserInviteState
from onboarding.services import validate_invite_token
from onboarding.tokens import INVITE_TOKEN_TIMEOUT_SECONDS, user_invite_token_generator


def _set_user_invite_enabled(enabled: bool):
    AppConfiguration.objects.update_or_create(
        key='USER_INVITE_EMAIL_ENABLED',
        defaults={
            'value': 'true' if enabled else 'false',
            'description': 'User invite email toggle',
        },
    )
    cache.delete('app_config:USER_INVITE_EMAIL_ENABLED')


@pytest.fixture(autouse=True)
def _clear_invite_setting_cache():
    yield
    cache.delete('app_config:USER_INVITE_EMAIL_ENABLED')


@pytest.mark.django_db
class TestAdminCreateUserWithInvite:
    def test_create_with_invite_requires_toggle(self, admin_api_client):
        _set_user_invite_enabled(False)
        payload = {
            'email': 'invite-off@example.com',
            'name': 'Invite Off',
            'role': 'member',
            'send_invite': True,
        }
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'send_invite' in response.data

    @patch('django.db.transaction.on_commit', side_effect=lambda func: func())
    @patch('onboarding.services.send_user_invite_email_task.delay')
    def test_create_with_invite_when_enabled(self, mock_delay, _on_commit, admin_api_client, admin_user):
        _set_user_invite_enabled(True)
        payload = {
            'email': 'invited@example.com',
            'name': 'Invited User',
            'role': 'member',
            'send_invite': True,
        }
        response = admin_api_client.post('/api/v1/admin/users/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email='invited@example.com')
        assert user.has_usable_password() is False
        assert user.organization_id == admin_user.organization_id
        assert UserInviteState.objects.filter(user=user).exists()
        mock_delay.assert_called_once()


@pytest.mark.django_db
class TestInviteTokenLifecycle:
    def _invite_user(self, organization):
        user = User.objects.create_user(
            username='token-user@example.com',
            email='token-user@example.com',
            password='unused',
            organization=organization,
            name='Token User',
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
        UserInviteState.objects.create(user=user, invite_nonce=0)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = user_invite_token_generator.make_token(user)
        return user, uid, token

    def test_validate_twice_then_set_password(self, public_client, organization):
        _set_user_invite_enabled(True)
        user, uid, token = self._invite_user(organization)

        for _ in range(2):
            validate_resp = public_client.get(
                '/api/v1/onboarding/invite/validate/',
                {'uid': uid, 'token': token},
            )
            assert validate_resp.status_code == status.HTTP_200_OK
            assert validate_resp.data['valid'] is True

        set_resp = public_client.post(
            '/api/v1/onboarding/invite/set-password/',
            {
                'uid': uid,
                'token': token,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
            format='json',
        )
        assert set_resp.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.check_password('StrongPass123!') is True

    def test_link_rejected_after_successful_set_password(self, public_client, organization):
        _set_user_invite_enabled(True)
        user, uid, token = self._invite_user(organization)

        set_resp = public_client.post(
            '/api/v1/onboarding/invite/set-password/',
            {
                'uid': uid,
                'token': token,
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            },
            format='json',
        )
        assert set_resp.status_code == status.HTTP_200_OK

        reuse_resp = public_client.get(
            '/api/v1/onboarding/invite/validate/',
            {'uid': uid, 'token': token},
        )
        assert reuse_resp.status_code == status.HTTP_400_BAD_REQUEST
        assert reuse_resp.data.get('code') == 'used'

    def test_token_expires_after_72_hours(self, organization):
        from datetime import datetime

        user, uid, token = self._invite_user(organization)
        future = datetime.utcnow() + timedelta(seconds=INVITE_TOKEN_TIMEOUT_SECONDS + 60)
        with patch.object(user_invite_token_generator, '_now', return_value=future):
            assert user_invite_token_generator.check_token(user, token) is False
            assert user_invite_token_generator.token_status(user, token) == 'expired'
            _, reason = validate_invite_token(uid, token)
            assert reason == 'expired'

    def test_invite_token_survives_profile_save_before_password_set(self, organization):
        user, uid, token = self._invite_user(organization)
        user.name = 'Updated name'
        user.save(update_fields=['name', 'updated_at'])
        user.refresh_from_db()
        assert user.has_usable_password() is False
        assert user_invite_token_generator.check_token(user, token) is True
        _, reason = validate_invite_token(uid, token)
        assert reason == 'valid'

    @patch('django.db.transaction.on_commit', side_effect=lambda func: func())
    @patch('onboarding.services.send_user_invite_email_task.delay')
    def test_resend_invalidates_previous_token(
        self, mock_delay, _on_commit, admin_api_client, admin_user, organization, public_client
    ):
        _set_user_invite_enabled(True)
        user, uid, old_token = self._invite_user(organization)
        user.organization = admin_user.organization
        user.save(update_fields=['organization'])

        url = f'/api/v1/admin/users/{user.id}/resend-invite/'
        response = admin_api_client.post(url, format='json')
        assert response.status_code == status.HTTP_200_OK

        user.refresh_from_db()
        assert user.invite_state.invite_nonce == 1
        assert user_invite_token_generator.check_token(user, old_token) is False

        new_token = user_invite_token_generator.make_token(user)
        assert user_invite_token_generator.check_token(user, new_token) is True

        validate_resp = public_client.get(
            '/api/v1/onboarding/invite/validate/',
            {'uid': uid, 'token': new_token},
        )
        assert validate_resp.status_code == status.HTTP_200_OK
        mock_delay.assert_called_once()

    @patch('django.db.transaction.on_commit', side_effect=lambda func: func())
    @patch('onboarding.services.send_user_invite_email_task.delay')
    def test_admin_reset_for_invited_user_sends_link(
        self, mock_delay, _on_commit, admin_api_client, organization
    ):
        _set_user_invite_enabled(True)
        user, uid, old_token = self._invite_user(organization)

        url = f'/api/v1/admin/users/{user.id}/reset-password/'
        response = admin_api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert 'set-password link' in response.data['message'].lower()

        user.refresh_from_db()
        assert user.has_usable_password() is False
        assert user.invite_state.invite_nonce == 1
        assert user_invite_token_generator.check_token(user, old_token) is False
        new_token = user_invite_token_generator.make_token(user)
        _, reason = validate_invite_token(uid, new_token)
        assert reason == 'valid'
        mock_delay.assert_called_once()

    def test_public_endpoints_hidden_when_toggle_off(self, public_client, organization):
        _set_user_invite_enabled(False)
        user, uid, token = self._invite_user(organization)
        validate_resp = public_client.get(
            '/api/v1/onboarding/invite/validate/',
            {'uid': uid, 'token': token},
        )
        assert validate_resp.status_code == status.HTTP_404_NOT_FOUND
