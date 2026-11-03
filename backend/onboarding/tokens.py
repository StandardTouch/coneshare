from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare

INVITE_TOKEN_TIMEOUT_SECONDS = 72 * 3600


class UserInviteTokenGenerator(PasswordResetTokenGenerator):
    """Invite tokens valid for 72 hours; invalidated by invite nonce bump or successful set-password."""

    def _parse_token_timestamp(self, token):
        if not token:
            return None
        try:
            ts_b36, _ = token.split('-', 1)
        except ValueError:
            return None
        try:
            from django.utils.http import base36_to_int

            return base36_to_int(ts_b36)
        except ValueError:
            return None

    def _token_matches(self, user, token, ts):
        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret),
                token,
            ):
                return True
        return False

    def token_status(self, user, token):
        """Return valid, expired, or invalid without treating expiry as a generic invalid token."""
        if not (user and token):
            return 'invalid'
        ts = self._parse_token_timestamp(token)
        if ts is None:
            return 'invalid'
        if not self._token_matches(user, token, ts):
            return 'invalid'
        if (self._num_seconds(self._now()) - ts) > INVITE_TOKEN_TIMEOUT_SECONDS:
            return 'expired'
        return 'valid'

    def check_token(self, user, token):
        return self.token_status(user, token) == 'valid'

    def _make_hash_value(self, user, timestamp):
        # Exclude password and last_login so invite links stay stable until consumed (nonce bump).
        try:
            nonce = user.invite_state.invite_nonce
        except Exception:
            nonce = 0
        return f'{user.pk}{nonce}{timestamp}'


user_invite_token_generator = UserInviteTokenGenerator()
