"""Safety rails so organizations cannot lock out administration."""
from __future__ import annotations

from django.contrib.auth import get_user_model

User = get_user_model()


def is_primary_org_admin(user) -> bool:
    """First organization administrator (by account creation) — always retains full access."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'role', '') != 'admin':
        return False
    org_id = getattr(user, 'organization_id', None)
    if not org_id:
        return False
    first_admin_id = (
        User.objects.filter(organization_id=org_id, role='admin')
        .order_by('date_joined', 'id')
        .values_list('id', flat=True)
        .first()
    )
    return first_admin_id is not None and str(first_admin_id) == str(user.id)


def user_has_full_access(user) -> bool:
    if user is None or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'is_superuser', False):
        return True
    return is_primary_org_admin(user)
