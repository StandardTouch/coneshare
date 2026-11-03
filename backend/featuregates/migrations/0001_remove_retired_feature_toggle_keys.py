from django.db import migrations

RETIRED_KEYS = ('MCP_ENABLED', 'API_KEYS_ENABLED', 'AUTOMATION_ENABLED')


def delete_retired_toggle_rows(apps, schema_editor):
    AppConfiguration = apps.get_model('core', 'AppConfiguration')
    AppConfiguration.objects.filter(key__in=RETIRED_KEYS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_alter_user_language'),
    ]

    operations = [
        migrations.RunPython(delete_retired_toggle_rows, migrations.RunPython.noop),
    ]
