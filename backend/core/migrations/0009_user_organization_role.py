import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('permissions_rbac', '0003_remove_legacy_rbac_toggles'),
        ('core', '0008_alter_user_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='organization_role',
            field=models.ForeignKey(
                blank=True,
                help_text='Default organization role (permissions template for dataroom access and site actions).',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='organization_members',
                to='permissions_rbac.dataroomrole',
            ),
        ),
    ]
