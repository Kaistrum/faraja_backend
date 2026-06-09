from django.db import migrations


def noop(apps, schema_editor):
    # Placeholder migration: model changed in code; run `makemigrations` locally
    return


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(noop),
    ]
