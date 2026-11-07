"""RBAC redesign: Admin/Manager roles, new permission codenames, retire toggles."""
from django.core.cache import cache
from django.db import migrations

from permissions_rbac.catalogue import (
    LEGACY_PERMISSION_MAP,
    RETIRED_GLOBAL_FEATURE_KEYS,
    ROLE_SLUG_MANAGER,
    SYSTEM_ROLE_SLUGS,
    default_grants_for_role_slug,
)

OBSOLETE_SYSTEM_SLUGS = ('viewer', 'contributor', 'editor')


def _map_legacy_grants(old_grants):
    merged = {}
    for perm, scope in old_grants.items():
        targets = LEGACY_PERMISSION_MAP.get(perm)
        if targets is None:
            if perm.startswith('system_') or perm.startswith('dataroom_') or perm.startswith('folder_'):
                merged[perm] = scope
            continue
        if not targets:
            continue
        for target in targets:
            if target not in merged:
                merged[target] = scope
            elif scope == 'any':
                merged[target] = scope
    return merged


def forwards(apps, schema_editor):
    Organization = apps.get_model('core', 'Organization')
    User = apps.get_model('core', 'User')
    DataroomRole = apps.get_model('permissions_rbac', 'DataroomRole')
    DataroomRolePermission = apps.get_model('permissions_rbac', 'DataroomRolePermission')
    DataroomFolderRoleRule = apps.get_model('permissions_rbac', 'DataroomFolderRoleRule')
    SiteRolePermission = apps.get_model('permissions_rbac', 'SiteRolePermission')
    DataroomCollaborator = apps.get_model('datarooms', 'DataroomCollaborator')
    AppConfiguration = apps.get_model('core', 'AppConfiguration')

    manager_by_org = {}

    for org in Organization.objects.all().iterator():
        # Ensure admin + manager system roles
        for slug in SYSTEM_ROLE_SLUGS:
            display = 'Admin' if slug == 'admin' else 'Manager'
            role, _ = DataroomRole.objects.get_or_create(
                organization_id=org.id,
                slug=slug,
                defaults={'name': display, 'description': '', 'is_system': True},
            )
            if slug == ROLE_SLUG_MANAGER:
                manager_by_org[org.id] = role
            default = default_grants_for_role_slug(slug)
            DataroomRolePermission.objects.filter(role_id=role.id).delete()
            DataroomRolePermission.objects.bulk_create(
                [
                    DataroomRolePermission(role_id=role.id, permission=p, scope=s or '')
                    for p, s in default.items()
                ],
                ignore_conflicts=True,
            )

        obsolete = DataroomRole.objects.filter(organization_id=org.id, slug__in=OBSOLETE_SYSTEM_SLUGS)
        obsolete_ids = list(obsolete.values_list('id', flat=True))
        mgr = manager_by_org.get(org.id)
        if obsolete_ids and mgr:
            # Preserve custom grants merged onto manager for users still on obsolete roles
            for old_role in obsolete:
                old_grants = {
                    row.permission: row.scope or 'any'
                    for row in DataroomRolePermission.objects.filter(role_id=old_role.id)
                }
                mapped = _map_legacy_grants(old_grants)
                for perm, scope in mapped.items():
                    DataroomRolePermission.objects.update_or_create(
                        role_id=mgr.id,
                        permission=perm,
                        defaults={'scope': scope if scope != 'any' else ''},
                    )
            User.objects.filter(organization_id=org.id, organization_role_id__in=obsolete_ids).update(
                organization_role_id=mgr.id
            )
            obsolete.delete()

        # Migrate non-system custom role permissions to new codenames
        for role in DataroomRole.objects.filter(organization_id=org.id, is_system=False):
            old = list(DataroomRolePermission.objects.filter(role_id=role.id))
            if not old:
                continue
            grant_map = {row.permission: row.scope or 'any' for row in old}
            mapped = _map_legacy_grants(grant_map)
            DataroomRolePermission.objects.filter(role_id=role.id).delete()
            DataroomRolePermission.objects.bulk_create(
                [
                    DataroomRolePermission(role_id=role.id, permission=p, scope=s if s != 'any' else '')
                    for p, s in mapped.items()
                ]
            )

        SiteRolePermission.objects.filter(organization_id=org.id).delete()
        DataroomFolderRoleRule.objects.all().delete()
        DataroomCollaborator.objects.filter(dataroom__organization_id=org.id).update(dataroom_role_id=None)
        cache.delete_many([])

    AppConfiguration.objects.filter(key__in=RETIRED_GLOBAL_FEATURE_KEYS).delete()
    for key in RETIRED_GLOBAL_FEATURE_KEYS:
        cache.delete(f'app_config:{key}')


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('permissions_rbac', '0004_unify_role_labels'),
        ('datarooms', '0008_dataroomcollaborator_dataroom_role'),
        ('core', '0009_user_organization_role'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
