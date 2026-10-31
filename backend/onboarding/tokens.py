from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare

INVITE_TOKEN_TIMEOUT_SECONDS = 72 * 3600


class UserInviteTokenGenerator(PasswordResetTokenGenerator):
    """Single-use invite tokens valid for 72 hours, invalidated on password change or nonce bump."""

    def check_token(self, user, token):
        if not (user and token):
            return False
        try:
            ts_b36, _ = token.split('-')
        except ValueError:
            return False

        try:
            from django.utils.http import base36_to_int

            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret),
                token,
            ):
                break
        else:
            return False

        if (self._num_seconds(self._now()) - ts) > INVITE_TOKEN_TIMEOUT_SECONDS:
            return False

        return True

    def _make_hash_value(self, user, timestamp):
        base = super()._make_hash_value(user, timestamp)
        try:
            nonce = user.invite_state.invite_nonce
        except Exception:
            nonce = 0
        return f'{base}{nonce}'


user_invite_token_generator = UserInviteTokenGenerator()
