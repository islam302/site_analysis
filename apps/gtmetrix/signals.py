"""Signal handlers for the GTmetrix app (lightweight auditing only)."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.gtmetrix.models import GTmetrixReport

logger = logging.getLogger("apps.gtmetrix")


@receiver(post_save, sender=GTmetrixReport, dispatch_uid="gtmetrix_report_created")
def log_report_created(sender, instance, created, **kwargs) -> None:
    if created:
        logger.info(
            "GTmetrix report created",
            extra={"report_id": str(instance.id), "user_id": str(instance.user_id)},
        )
