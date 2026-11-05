from django.db import migrations

LEGACY_APP_CONFIG_KEYS = (
    'COLLABORATORS_OWN_DELETE_ONLY',
    'DATAROOM_CREATE_ADMIN_ONLY',
)


def remove_legacy_toggles_and_reseed_rbac(apps, schema_editor):
    from django.core.cache import cache

    AppConfiguration = apps.get_model('core', 'AppConfiguration')
    AppConfiguration.objects.filter(key__in=LEGACY_APP_CONFIG_KEYS).delete()
    for key in LEGACY_APP_CONFIG_KEYS:
        cache.delete(f'app_config:{key}')

    Organization = apps.get_model('core', 'Organization')
    DataroomRole = apps.get_model('permissions_rbac', 'DataroomRole')
    DataroomRolePermission = apps.get_model('permissions_rbac', 'DataroomRolePermission')
    SiteRolePermission = apps.get_model('permissions_rbac', 'SiteRolePermission')

    from permissions_rbac.catalogue import (
        DEFAULT_SITE_ROLE_GRANTS,
        PERM_CREATE_DATAROOM,
        SYSTEM_ROLE_SLUGS,
        default_grants_for_role_slug,
    )
    from permissions_rbac.seed import ROLE_DISPLAY_NAMES
    from permissions_rbac.services import invalidate_organization_rbac_cache

    for org in Organization.objects.all().iterator():
        for slug in SYSTEM_ROLE_SLUGS:
            role, _ = DataroomRole.objects.get_or_create(
                organization_id=org.id,
                slug=slug,
                defaults={
                    'name': ROLE_DISPLAY_NAMES[slug],
                    'description': '',
                    'is_system': True,
                },
            )
            DataroomRolePermission.objects.filter(role=role).delete()
            grant_rows = []
            for permission, scope in default_grants_for_role_slug(slug).items():
                grant_rows.append(
                    DataroomRolePermission(
                        role=role,
                        permission=permission,
                        scope=scope or '',
                    )
                )
            if grant_rows:
                DataroomRolePermission.objects.bulk_create(grant_rows, ignore_conflicts=True)

        SiteRolePermission.objects.filter(
            organization_id=org.id,
            site_role='member',
            permission=PERM_CREATE_DATAROOM,
        ).delete()
        for site_role, grants in DEFAULT_SITE_ROLE_GRANTS.items():
            for permission in grants:
                SiteRolePermission.objects.get_or_create(
                    organization_id=org.id,
                    site_role=site_role,
                    permission=permission,
                )

        invalidate_organization_rbac_cache(str(org.id))


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('permissions_rbac', '0002_seed_default_roles'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(remove_legacy_toggles_and_reseed_rbac, noop_reverse),
    ]
