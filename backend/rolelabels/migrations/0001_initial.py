# Generated manually for rolelabels app

import core.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0008_alter_user_language'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='RoleLabel',
            fields=[
                ('id', core.fields.ULIDField(default=core.fields.generate_ulid, editable=False, max_length=26, primary_key=True, serialize=False, unique=True, validators=[core.fields.validate_ulid])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_labels', to='core.organization')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='UserRoleLabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role_label', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='user_assignments', to='rolelabels.rolelabel')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='role_label_assignment', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name='rolelabel',
            constraint=models.UniqueConstraint(Lower('name'), models.F('organization'), name='rolelabels_rolelabel_org_name_ci_unique'),
        ),
    ]
