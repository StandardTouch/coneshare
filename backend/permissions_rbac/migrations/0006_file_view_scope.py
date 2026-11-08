"""Set explicit any scope on existing file_view grants."""
from django.db import migrations

from permissions_rbac.catalogue import PERM_FILE_VIEW, SCOPE_ANY


def forwards(apps, schema_editor):
    DataroomRolePermission = apps.get_model('permissions_rbac', 'DataroomRolePermission')
    DataroomRolePermission.objects.filter(permission=PERM_FILE_VIEW).exclude(scope=SCOPE_ANY).update(
        scope=SCOPE_ANY
    )


def backwards(apps, schema_editor):
    DataroomRolePermission = apps.get_model('permissions_rbac', 'DataroomRolePermission')
    DataroomRolePermission.objects.filter(permission=PERM_FILE_VIEW, scope=SCOPE_ANY).update(scope='')


class Migration(migrations.Migration):

    dependencies = [
        ('permissions_rbac', '0005_rbac_redesign'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
