from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_alter_crisisreport_location_and_more'),
    ]

    operations = [
        # CrisisReport
        migrations.RemoveField(
            model_name='crisisreport',
            name='raw_payload',
        ),
        migrations.AddField(
            model_name='crisisreport',
            name='lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='crisisreport',
            name='lon',
            field=models.FloatField(blank=True, null=True),
        ),
        # FinalCrisisReport
        migrations.RemoveField(
            model_name='finalcrisisreport',
            name='raw_payload',
        ),
        migrations.AddField(
            model_name='finalcrisisreport',
            name='lat',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='finalcrisisreport',
            name='lon',
            field=models.FloatField(blank=True, null=True),
        ),
    ]
