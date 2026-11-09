"""Create and reset default RBAC roles for an organization."""
from __future__ import annotations

from typing import Dict, Optional

from django.db import transaction

from permissions_rbac.catalogue import (
    DEFAULT_SITE_ROLE_GRANTS,
    SYSTEM_ROLE_SLUGS,
    default_grants_for_role_slug,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission, SiteRolePermission


ROLE_DISPLAY_NAMES = {
    'admin': 'Admin',
    'manager': 'Manager',
}


def ensure_default_roles_for_organization(organization) -> Dict[str, DataroomRole]:
    roles: Dict[str, DataroomRole] = {}
    with transaction.atomic():
        for slug in SYSTEM_ROLE_SLUGS:
            role, created = DataroomRole.objects.get_or_create(
                organization=organization,
                slug=slug,
                defaults={
                    'name': ROLE_DISPLAY_NAMES[slug],
                    'description': '',
                    'is_system': True,
                },
            )
            updates = []
            if role.name != ROLE_DISPLAY_NAMES[slug]:
                role.name = ROLE_DISPLAY_NAMES[slug]
                updates.append('name')
            if not role.is_system:
                role.is_system = True
                updates.append('is_system')
            if updates:
                updates.append('updated_at')
                role.save(update_fields=updates)
            # Apply the template only when the role is first created.
            # Repeating this on every roles-list load wiped saved grants.
            if created:
                _apply_role_grants(role, default_grants_for_role_slug(slug))
            roles[slug] = role
        _ensure_site_role_grants(organization)
    return roles


def _apply_role_grants(role: DataroomRole, grants: Dict[str, Optional[str]]) -> None:
    DataroomRolePermission.objects.filter(role=role).delete()
    rows = []
    for permission, scope in grants.items():
        rows.append(
            DataroomRolePermission(
                role=role,
                permission=permission,
                scope=scope or '',
            )
        )
    if rows:
        DataroomRolePermission.objects.bulk_create(rows)


def _ensure_site_role_grants(organization) -> None:
    for site_role, grants in DEFAULT_SITE_ROLE_GRANTS.items():
        for permission in grants:
            SiteRolePermission.objects.get_or_create(
                organization=organization,
                site_role=site_role,
                permission=permission,
            )


def reset_system_role_to_defaults(role: DataroomRole) -> None:
    if not role.is_system:
        raise ValueError('Only system roles can be reset via this helper.')
    grants = default_grants_for_role_slug(role.slug)
    _apply_role_grants(role, grants)


def reset_all_system_roles_for_organization(organization) -> None:
    for role in DataroomRole.objects.filter(organization=organization, is_system=True):
        if role.slug in SYSTEM_ROLE_SLUGS:
            reset_system_role_to_defaults(role)
    _ensure_site_role_grants(organization)
