"""
Django signals for automatic CrisisReport processing.
When a new CrisisReport is created, automatically check for duplicates
and create a FinalCrisisReport if it's not a duplicate.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import CrisisReport, FinalCrisisReport, is_duplicate_report


@receiver(post_save, sender=CrisisReport)
def process_crisis_report(sender, instance, created, **kwargs):
    """
    Signal handler: When a CrisisReport is created, check for duplicates.
    If not a duplicate, automatically create a FinalCrisisReport for dashboard use.
    """
    if not created:
        # Only process newly created reports
        return
    
    # Check for duplicates
    is_duplicate, matched_report_id, reason = is_duplicate_report(instance)
    
    if is_duplicate:
        # Log duplicate but don't create FinalCrisisReport
        print(f"[DUPLICATE] Report {instance.report_id}: {reason}")
        # Optionally: update instance to mark as duplicate
        # instance.is_duplicate = True
        # instance.save(update_fields=['is_duplicate'])
        return
    
    # Not a duplicate - create FinalCrisisReport
    try:
        final_report = FinalCrisisReport.objects.create(
            client_id=instance.client_id,
            original_report_id=instance.report_id,
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
            raw_payload=instance.raw_payload,
        )
        print(f"[SUCCESS] Created FinalCrisisReport {final_report.report_id} from {instance.report_id}")
    except Exception as e:
        print(f"[ERROR] Failed to create FinalCrisisReport for {instance.report_id}: {str(e)}")
