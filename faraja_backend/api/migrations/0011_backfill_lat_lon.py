from django.db import migrations


def backfill_lat_lon(apps, schema_editor):
    CrisisReport = apps.get_model('api', 'CrisisReport')
    FinalCrisisReport = apps.get_model('api', 'FinalCrisisReport')

    for model in (CrisisReport, FinalCrisisReport):
        objs = []
        for obj in model.objects.filter(location__isnull=False, lat__isnull=True).iterator():
            obj.lat = obj.location.y
            obj.lon = obj.location.x
            objs.append(obj)
        if objs:
            model.objects.bulk_update(objs, ['lat', 'lon'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0010_add_lat_lon_remove_raw_payload'),
    ]

    operations = [
        migrations.RunPython(backfill_lat_lon, migrations.RunPython.noop),
    ]
