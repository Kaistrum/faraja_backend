from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import CrisisReport, FinalCrisisReport, is_duplicate_report


@receiver(post_save, sender=CrisisReport)
def process_crisis_report(sender, instance, created, **kwargs):
    if not created:
        return

    is_duplicate, matched_report_id, reason = is_duplicate_report(instance)

    if is_duplicate:
        print(f"[DUPLICATE] Report {instance.report_id}: {reason}")
        return

    _, was_created = FinalCrisisReport.objects.get_or_create(
        original_report_id=instance.report_id,
        defaults=dict(
            client_id=instance.client_id,
            location=instance.location,
            location_description=instance.location_description,
            building_footprint_id=instance.building_footprint_id,
            submitted_at=instance.submitted_at,
            processed_at=timezone.now(),
            infrastructure_type=instance.infrastructure_type,
            nature_of_crisis=instance.nature_of_crisis,
            debris=instance.debris,
            affected_units=instance.affected_units,
            damage_level=instance.damage_level,
            photo_url=instance.photo_url,
            ai_damage_level=instance.ai_damage_level,
            ai_disaster_type=instance.ai_disaster_type,
            ai_informativeness=instance.ai_informativeness,
            ai_humanitarian_category=instance.ai_humanitarian_category,
            ai_damage_severity=instance.ai_damage_severity,
        ),
    )

    if not was_created:
        print(f"[DUPLICATE] FinalCrisisReport already exists for {instance.report_id}")
