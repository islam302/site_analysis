"""Orchestration for structured-data validation: submit + process."""
from __future__ import annotations

import logging

import httpx
from django.db import transaction

from apps.validator.constants import (
    FETCH_TIMEOUT,
    DEFAULT_USER_AGENT,
    IssueSeverity,
    SchemaFormat,
    ValidationStatus,
)
from apps.validator.exceptions import PageFetchError
from apps.validator.models import SchemaIssue, SchemaItem, ValidationJob
from apps.validator.services.extractor_service import (
    extract_json_ld,
    extract_microdata,
    extract_rdfa,
)
from apps.validator.services.schema_validator_service import resolve_type, validate_schema

logger = logging.getLogger("apps.validator")


@transaction.atomic
def submit_validation(*, user, url: str) -> ValidationJob:
    """Create a pending ValidationJob and dispatch the async processing task."""
    job = ValidationJob.objects.create(user=user, url=url, status=ValidationStatus.PENDING)
    logger.info("Validation submitted", extra={"job_id": str(job.id), "url": url})

    from apps.validator.tasks import process_validation_task

    transaction.on_commit(lambda: process_validation_task.delay(job_id=str(job.id)))
    return job


def fetch_page(*, url: str) -> str:
    """GET the page HTML with a proper UA and a 15s timeout (follows redirects)."""
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text
    except httpx.HTTPError as exc:
        raise PageFetchError(
            message=f"Could not fetch the page: {exc}", extra={"url": url}
        ) from exc


def quick_schema_check(*, url: str, max_items: int = 15) -> dict:
    """Fetch a page, validate its structured data, and return a summary.

    A lightweight, non-persisting variant used by the combined full report.
    Reuses the same extractors and validation engine as the async job.
    """
    html = fetch_page(url=url)
    json_ld = extract_json_ld(html_content=html)
    microdata = extract_microdata(html_content=html)
    rdfa = extract_rdfa(html_content=html)

    blocks = (
        (SchemaFormat.JSON_LD, json_ld),
        (SchemaFormat.MICRODATA, microdata),
        (SchemaFormat.RDFA, rdfa),
    )

    schemas: list[dict] = []
    issues: list[dict] = []
    total_errors = 0
    total_warnings = 0
    valid = 0
    rich = 0

    for fmt, extracted in blocks:
        for data in extracted:
            schema_type = resolve_type(data)
            result = validate_schema(schema_type=schema_type, data=data)
            errors = sum(1 for i in result["issues"] if i["severity"] == IssueSeverity.ERROR)
            warnings = sum(1 for i in result["issues"] if i["severity"] == IssueSeverity.WARNING)
            total_errors += errors
            total_warnings += warnings
            if result["is_valid"]:
                valid += 1
            if result["google_rich_result_eligible"]:
                rich += 1
            if len(schemas) < max_items:
                schemas.append(
                    {
                        "schema_type": result["schema_type"],
                        "format": fmt,
                        "is_valid": result["is_valid"],
                        "errors": errors,
                        "warnings": warnings,
                        "rich": result["google_rich_result_eligible"],
                    }
                )
            for issue in result["issues"]:
                if issue["severity"] == IssueSeverity.INFO or len(issues) >= max_items:
                    continue
                issues.append(
                    {
                        "schema_type": result["schema_type"],
                        "severity": issue["severity"],
                        "field": issue["field"],
                        "message": issue["message"],
                    }
                )

    total = sum(len(items) for _, items in blocks)
    return {
        "total_schemas": total,
        "valid_schemas": valid,
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "rich_result_eligible": rich,
        "has_json_ld": len(json_ld) > 0,
        "has_microdata": len(microdata) > 0,
        "has_rdfa": len(rdfa) > 0,
        "schemas": schemas,
        "issues": issues,
    }


def process_validation(*, job_id: str) -> str:
    """Fetch the page, extract all structured data, validate it, and save results.

    Idempotent-ish: re-running clears prior schema items for the job first.
    Returns the final job status string.
    """
    try:
        job = ValidationJob.objects.get(id=job_id)
    except ValidationJob.DoesNotExist:
        logger.warning("ValidationJob missing; skipping (%s)", job_id)
        return "missing"

    job.status = ValidationStatus.PROCESSING
    job.save(update_fields=["status", "updated_at"])
    logger.info("Validation processing", extra={"job_id": job_id, "url": job.url})

    try:
        html = fetch_page(url=job.url)

        json_ld = extract_json_ld(html_content=html)
        microdata = extract_microdata(html_content=html)
        rdfa = extract_rdfa(html_content=html)

        blocks = (
            (SchemaFormat.JSON_LD, json_ld),
            (SchemaFormat.MICRODATA, microdata),
            (SchemaFormat.RDFA, rdfa),
        )

        items_to_create: list[SchemaItem] = []
        issues_to_create: list[SchemaIssue] = []
        total_errors = 0
        total_warnings = 0

        for fmt, extracted in blocks:
            for data in extracted:
                schema_type = resolve_type(data)
                result = validate_schema(schema_type=schema_type, data=data)
                item = SchemaItem(
                    job=job,
                    schema_type=result["schema_type"],
                    format=fmt,
                    raw_data=data,
                    is_valid=result["is_valid"],
                    google_rich_result_eligible=result["google_rich_result_eligible"],
                )
                items_to_create.append(item)
                for issue in result["issues"]:
                    issues_to_create.append(SchemaIssue(schema_item=item, **issue))
                    if issue["severity"] == IssueSeverity.ERROR:
                        total_errors += 1
                    elif issue["severity"] == IssueSeverity.WARNING:
                        total_warnings += 1

        with transaction.atomic():
            # Replace any prior results (safe on re-run).
            SchemaItem.objects.filter(job=job).delete()
            SchemaItem.objects.bulk_create(items_to_create, batch_size=500)
            SchemaIssue.objects.bulk_create(issues_to_create, batch_size=1000)

            job.total_schemas_found = len(items_to_create)
            job.total_errors = total_errors
            job.total_warnings = total_warnings
            job.has_json_ld = len(json_ld) > 0
            job.has_microdata = len(microdata) > 0
            job.has_rdfa = len(rdfa) > 0
            job.status = ValidationStatus.COMPLETED
            job.error_message = None
            job.save()
    except Exception as exc:  # noqa: BLE001 - record failure on the job, don't crash worker
        job.status = ValidationStatus.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        logger.warning("Validation failed: %s (job %s)", exc, job_id)
        return ValidationStatus.FAILED

    logger.info(
        "Validation completed",
        extra={
            "job_id": job_id,
            "schemas": job.total_schemas_found,
            "errors": job.total_errors,
        },
    )
    return job.status
