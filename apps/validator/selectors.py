"""Read-only, user-scoped queries for the validator.

Every selector is scoped to ``user`` so one user can never read another's jobs.
"""
from __future__ import annotations

import uuid

from django.db.models import QuerySet

from apps.validator.exceptions import ValidationJobNotFoundError
from apps.validator.models import SchemaIssue, SchemaItem, ValidationJob


def get_jobs(*, user) -> QuerySet[ValidationJob]:
    """Return the user's validation jobs, newest first."""
    return ValidationJob.objects.filter(user=user).order_by("-created_at")


def get_job_detail(*, user, job_id: uuid.UUID | str) -> ValidationJob:
    """Return one of the user's jobs (schemas + issues prefetched) or raise 404."""
    try:
        return (
            ValidationJob.objects.prefetch_related("schemas__issues")
            .get(user=user, id=job_id)
        )
    except (ValidationJob.DoesNotExist, ValueError, TypeError):
        raise ValidationJobNotFoundError(extra={"job_id": str(job_id)})


def get_schemas(*, user, job_id: uuid.UUID | str) -> QuerySet[SchemaItem]:
    """Return the schema items for one of the user's jobs (ownership enforced)."""
    get_job_detail(user=user, job_id=job_id)
    return (
        SchemaItem.objects.filter(job_id=job_id)
        .prefetch_related("issues")
        .order_by("schema_type")
    )


def get_issues(*, user, job_id: uuid.UUID | str) -> QuerySet[SchemaIssue]:
    """Return every issue across a job's schemas (ownership enforced)."""
    get_job_detail(user=user, job_id=job_id)
    return SchemaIssue.objects.filter(schema_item__job_id=job_id).order_by(
        "severity", "field"
    )
