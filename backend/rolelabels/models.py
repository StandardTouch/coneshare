from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from core.models import BaseModel, Organization


class RoleLabel(BaseModel):
    """Display-only custom role label scoped to an organization."""

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='role_labels',
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                'organization',
                name='rolelabels_rolelabel_org_name_ci_unique',
            ),
        ]
        ordering = ['name']

    def __str__(self):
        return self.name


class UserRoleLabel(models.Model):
    """Assigns a display role label to a user (permissions remain member)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='role_label_assignment',
    )
    role_label = models.ForeignKey(
        RoleLabel,
        on_delete=models.PROTECT,
        related_name='user_assignments',
    )

    def __str__(self):
        return f'{self.user_id} -> {self.role_label.name}'
