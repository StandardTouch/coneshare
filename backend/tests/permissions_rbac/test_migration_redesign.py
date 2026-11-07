"""Migration 0005 idempotency and data safety."""
import importlib

import pytest

from core.models import Organization, User
from permissions_rbac.catalogue import ROLE_SLUG_ADMIN, ROLE_SLUG_MANAGER, SYSTEM_ROLE_SLUGS
from permissions_rbac.models import DataroomFolderRoleRule, DataroomRole
from permissions_rbac.seed import ensure_default_roles_for_organization


@pytest.mark.django_db
def test_migration_redesign_idempotent(organization):
    migration = importlib.import_module('permissions_rbac.migrations.0005_rbac_redesign')
    from django.apps import apps

    migration.forwards(apps, None)
    migration.forwards(apps, None)

    slugs = set(
        DataroomRole.objects.filter(organization=organization, is_system=True).values_list('slug', flat=True)
    )
    assert slugs == set(SYSTEM_ROLE_SLUGS)


@pytest.mark.django_db
def test_obsolete_roles_removed_and_users_reassigned(organization, user):
    migration = importlib.import_module('permissions_rbac.migrations.0005_rbac_redesign')
    from django.apps import apps
    from permissions_rbac.models import DataroomRolePermission

    ensure_default_roles_for_organization(organization)
    viewer = DataroomRole.objects.create(
        organization=organization, slug='viewer', name='Viewer', is_system=True
    )
    DataroomRolePermission.objects.create(role=viewer, permission='file_view', scope='')
    user.organization_role = viewer
    user.save(update_fields=['organization_role'])

    migration.forwards(apps, None)

    user.refresh_from_db()
    assert user.organization_role.slug == ROLE_SLUG_MANAGER
    assert not DataroomRole.objects.filter(organization=organization, slug='viewer').exists()
    assert DataroomFolderRoleRule.objects.count() == 0


@pytest.mark.django_db
def test_admin_role_retains_full_grant_catalogue(organization):
    migration = importlib.import_module('permissions_rbac.migrations.0005_rbac_redesign')
    from django.apps import apps

    migration.forwards(apps, None)
    admin = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
    assert admin.permission_grants.count() >= 20
