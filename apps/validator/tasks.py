"""Celery task that runs structured-data validation for a ValidationJob."""
from __future__ import annotations

import logging

from celery import shared_task

from apps.validator.services.validation_service import process_validation

logger = logging.getLogger("apps.validator")


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def process_validation_task(self, job_id: str) -> str:
    """Process a ValidationJob end to end. Receives only a primitive id."""
    logger.info("process_validation_task received", extra={"job_id": job_id})
    return process_validation(job_id=job_id)
