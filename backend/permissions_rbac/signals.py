"""Seed default dataroom roles for new organizations."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import Organization

from .seed import ensure_default_roles_for_organization


@receiver(post_save, sender=Organization)
def seed_rbac_on_organization_create(sender, instance, created, **kwargs):
    if created:
        ensure_default_roles_for_organization(instance)
