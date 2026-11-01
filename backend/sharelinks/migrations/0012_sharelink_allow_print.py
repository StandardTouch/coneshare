from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sharelinks', '0011_add_scroll_percentage_to_pageview'),
    ]

    operations = [
        migrations.AddField(
            model_name='sharelink',
            name='allow_print',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='sharelinktemplate',
            name='allow_print',
            field=models.BooleanField(default=True),
        ),
    ]
