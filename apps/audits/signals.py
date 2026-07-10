"""Signal handlers for the audits app (lightweight auditing only)."""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.audits.models import AccessibilityAudit

logger = logging.getLogger("apps.audits")


@receiver(post_save, sender=AccessibilityAudit, dispatch_uid="audit_created_log")
def log_audit_created(sender, instance, created, **kwargs) -> None:
    if created:
        logger.info(
            "Accessibility audit created",
            extra={"audit_id": str(instance.id), "user_id": str(instance.user_id)},
        )
