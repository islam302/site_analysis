"""Signal handlers for the ssl_check app (lightweight auditing only)."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.ssl_check.models import SSLReport

logger = logging.getLogger("apps.ssl_check")


@receiver(post_save, sender=SSLReport, dispatch_uid="ssl_report_created")
def log_report_created(sender, instance, created, **kwargs) -> None:
    if created:
        logger.info(
            "SSL report created",
            extra={"report_id": str(instance.id), "host": instance.host},
        )
