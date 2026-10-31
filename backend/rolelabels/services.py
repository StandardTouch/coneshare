from django.contrib.auth import get_user_model
from django.db.models import Count

from core.services import get_dynamic_setting
from rest_framework.exceptions import NotFound

from .models import RoleLabel, UserRoleLabel

User = get_user_model()


def role_labels_enabled() -> bool:
    return bool(get_dynamic_setting('ROLE_LABELS_ENABLED'))


def ensure_role_labels_enabled():
    if not role_labels_enabled():
        raise NotFound()


def set_user_role_label(user, role_label_id):
    """Assign or clear a user's display role label."""
    UserRoleLabel.objects.filter(user=user).delete()
    if not role_label_id:
        return
    label = RoleLabel.objects.get(id=role_label_id, organization=user.organization)
    UserRoleLabel.objects.create(user=user, role_label=label)


def clear_user_role_label(user):
    UserRoleLabel.objects.filter(user=user).delete()


def role_label_user_count(role_label: RoleLabel) -> int:
    return UserRoleLabel.objects.filter(role_label=role_label).count()


def get_user_role_label(user):
    try:
        return user.role_label_assignment.role_label
    except UserRoleLabel.DoesNotExist:
        return None
