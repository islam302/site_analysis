"""Signal handlers for the analysis app.

Kept free of service-layer imports — handlers only perform lightweight
auditing. Cache invalidation and history updates live in the service layer.
"""
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.analysis.models import AnalysisReport

logger = logging.getLogger("apps.analysis")


@receiver(post_save, sender=AnalysisReport, dispatch_uid="analysis_report_created_log")
def log_report_created(sender, instance, created, **kwargs) -> None:
    if created:
        logger.info(
            "Analysis report created",
            extra={"report_id": str(instance.id), "user_id": str(instance.user_id)},
        )
