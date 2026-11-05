from django.db import migrations


def seed_roles_and_collaborators(apps, schema_editor):
    Organization = apps.get_model('core', 'Organization')
    DataroomCollaborator = apps.get_model('datarooms', 'DataroomCollaborator')
    DataroomRole = apps.get_model('permissions_rbac', 'DataroomRole')
    DataroomRolePermission = apps.get_model('permissions_rbac', 'DataroomRolePermission')
    SiteRolePermission = apps.get_model('permissions_rbac', 'SiteRolePermission')

    from permissions_rbac.catalogue import (
        DEFAULT_SITE_ROLE_GRANTS,
        SYSTEM_ROLE_SLUGS,
        default_grants_for_role_slug,
    )
    from permissions_rbac.seed import ROLE_DISPLAY_NAMES

    for org in Organization.objects.all().iterator():
        roles_by_slug = {}
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
            roles_by_slug[slug] = role
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

        for site_role, grants in DEFAULT_SITE_ROLE_GRANTS.items():
            for permission in grants:
                SiteRolePermission.objects.get_or_create(
                    organization_id=org.id,
                    site_role=site_role,
                    permission=permission,
                )

        editor_role = roles_by_slug.get('editor')
        if editor_role:
            DataroomCollaborator.objects.filter(
                dataroom__organization_id=org.id,
                dataroom_role__isnull=True,
            ).update(dataroom_role_id=editor_role.id)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('permissions_rbac', '0001_initial'),
        ('datarooms', '0008_dataroomcollaborator_dataroom_role'),
    ]

    operations = [
        migrations.RunPython(seed_roles_and_collaborators, noop_reverse),
    ]
