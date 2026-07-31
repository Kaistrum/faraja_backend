from django.db import migrations

INFRASTRUCTURE_LABELS = {
    'residential': 'Residential',
    'commercial': 'Commercial',
    'government': 'Government',
    'utility': 'Utility',
    'transport': 'Transport & Communication',
    'community': 'Community',
    'recreation': 'Public Recreation',
    'other': 'Other',
}

CRISIS_LABELS = {
    'earthquake': 'Earthquake',
    'flood': 'Flood',
    'tsunami': 'Tsunami',
    'cyclone': 'Cyclone/Hurricane',
    'wildfire': 'Wildfire',
    'explosion': 'Explosion',
    'conflict': 'Conflict',
    'civil_unrest': 'Civil Unrest',
    'chemical': 'Chemical Incident',
    'other': 'Other',
}


def build_description(infra, crisis):
    infra_label = INFRASTRUCTURE_LABELS.get(infra) if infra else None
    crisis_label = CRISIS_LABELS.get(crisis) if crisis else None
    if infra_label and crisis_label:
        return f"{infra_label} site affected by {crisis_label.lower()}"
    if infra_label:
        return f"{infra_label} structure"
    if crisis_label:
        return f"Site affected by {crisis_label.lower()}"
    return "Affected site"


def fix_location_descriptions(apps, schema_editor):
    CrisisReport = apps.get_model('api', 'CrisisReport')
    FinalCrisisReport = apps.get_model('api', 'FinalCrisisReport')

    for model in (CrisisReport, FinalCrisisReport):
        objs = []
        for obj in model.objects.all().iterator():
            new_desc = build_description(obj.infrastructure_type, obj.nature_of_crisis)
            if obj.location_description != new_desc:
                obj.location_description = new_desc
                objs.append(obj)
        if objs:
            model.objects.bulk_update(objs, ['location_description'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_backfill_lat_lon'),
    ]

    operations = [
        migrations.RunPython(fix_location_descriptions, migrations.RunPython.noop),
    ]
