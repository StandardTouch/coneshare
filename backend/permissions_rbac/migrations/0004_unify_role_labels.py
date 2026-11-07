from django.db import migrations
from django.utils.text import slugify


def _unique_slug(DataroomRole, organization_id, base_slug):
    slug = (base_slug or 'custom')[:32]
    if not DataroomRole.objects.filter(organization_id=organization_id, slug=slug).exists():
        return slug
    n = 2
    while True:
        suffix = f'-{n}'
        candidate = f'{slug[: max(1, 32 - len(suffix))]}{suffix}'
        if not DataroomRole.objects.filter(organization_id=organization_id, slug=candidate).exists():
            return candidate
        n += 1


def migrate_role_labels_to_rbac(apps, schema_editor):
    RoleLabel = apps.get_model('rolelabels', 'RoleLabel')
    UserRoleLabel = apps.get_model('rolelabels', 'UserRoleLabel')
    DataroomRole = apps.get_model('permissions_rbac', 'DataroomRole')
    User = apps.get_model('core', 'User')

    label_to_role = {}
    for label in RoleLabel.objects.all().iterator():
        existing = DataroomRole.objects.filter(
            organization_id=label.organization_id,
            name__iexact=label.name,
        ).first()
        if existing:
            role = existing
        else:
            slug = _unique_slug(DataroomRole, label.organization_id, slugify(label.name))
            role = DataroomRole.objects.create(
                organization_id=label.organization_id,
                slug=slug,
                name=label.name,
                description=label.description or '',
                is_system=False,
            )
        label_to_role[label.id] = role

    for assignment in UserRoleLabel.objects.select_related('user', 'role_label').iterator():
        role = label_to_role.get(assignment.role_label_id)
        if not role:
            continue
        user = assignment.user
        if user.role == 'admin':
            continue
        User.objects.filter(pk=user.pk).update(organization_role_id=role.id)

    viewer_assignments = (
        User.objects.filter(role='member', organization_role__isnull=True)
        .values_list('organization_id', flat=True)
        .distinct()
    )
    for org_id in viewer_assignments:
        viewer = DataroomRole.objects.filter(organization_id=org_id, slug='viewer', is_system=True).first()
        if not viewer:
            continue
        User.objects.filter(organization_id=org_id, role='member', organization_role__isnull=True).update(
            organization_role_id=viewer.id
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('permissions_rbac', '0003_remove_legacy_rbac_toggles'),
        ('rolelabels', '0001_initial'),
        ('core', '0009_user_organization_role'),
    ]

    operations = [
        migrations.RunPython(migrate_role_labels_to_rbac, noop_reverse),
    ]
