from django.conf import settings
from django.db import models

from core.models import BaseModel


class UserInviteState(BaseModel):
    """Tracks invite link nonces so older invite URLs can be invalidated on resend."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invite_state',
    )
    invite_nonce = models.PositiveIntegerField(default=0)
    last_invite_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'User invite state'
        verbose_name_plural = 'User invite states'

    def __str__(self):
        return f'Invite state for {self.user_id}'
