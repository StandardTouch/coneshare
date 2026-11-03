from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('esign', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='signaturerequest',
            name='original_document_hash',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
