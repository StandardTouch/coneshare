"""Unified organization RBAC roles (org role on user, migration, site permissions)."""
import pytest
from django.contrib.auth import get_user_model

from permissions_rbac.catalogue import PERM_DATAROOM_CREATE, ROLE_SLUG_MANAGER
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.services import has_site_perm
from rolelabels.models import RoleLabel, UserRoleLabel

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationRoleOnUser:
    def test_create_member_with_organization_role(self, admin_api_client, admin_user):
        ensure_default_roles_for_organization(admin_user.organization)
        manager = DataroomRole.objects.get(organization=admin_user.organization, slug=ROLE_SLUG_MANAGER)
        response = admin_api_client.post(
            '/api/v1/admin/users/',
            {
                'email': 'manager-user@example.com',
                'username': 'manager-user@example.com',
                'name': 'Manager User',
                'password': 'SecurePass123!',
                'organization_role_id': str(manager.id),
            },
            format='json',
        )
        assert response.status_code == 201, response.data
        created = User.objects.get(email='manager-user@example.com')
        assert created.organization_role_id == manager.id
        assert created.role == 'member'
        assert response.data['organization_role']['slug'] == ROLE_SLUG_MANAGER

    def test_site_create_dataroom_from_org_role_grants(self, organization, user):
        ensure_default_roles_for_organization(organization)
        custom = DataroomRole.objects.create(
            organization=organization,
            slug='custom-analyst',
            name='Analyst',
            is_system=False,
        )
        DataroomRolePermission.objects.create(role=custom, permission=PERM_DATAROOM_CREATE, scope='')
        user.role = 'member'
        user.organization_role = custom
        user.save(update_fields=['role', 'organization_role'])
        assert has_site_perm(user, PERM_DATAROOM_CREATE) is True

    def test_migrate_role_label_idempotent(self, organization, user, admin_user):
        ensure_default_roles_for_organization(organization)
        label = RoleLabel.objects.create(organization=organization, name='Deal Team', description='Deals')
        UserRoleLabel.objects.create(user=user, role_label=label)
        import importlib

        migration = importlib.import_module('permissions_rbac.migrations.0004_unify_role_labels')
        migrate_role_labels_to_rbac = migration.migrate_role_labels_to_rbac
        from django.apps import apps

        migrate_role_labels_to_rbac(apps, None)
        migrate_role_labels_to_rbac(apps, None)
        user.refresh_from_db()
        role = DataroomRole.objects.get(organization=organization, name__iexact='Deal Team')
        assert user.organization_role_id == role.id
        assert DataroomRole.objects.filter(organization=organization, name__iexact='Deal Team').count() == 1
