"""Models for structured-data (Schema.org) validation.

A :class:`ValidationJob` is the async job for one URL. Each structured-data
object found on the page becomes a :class:`SchemaItem`, and every problem found
while validating it against the Schema.org rules becomes a :class:`SchemaIssue`.
"""
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.common.validators import validate_http_url
from apps.validator.constants import IssueSeverity, SchemaFormat, ValidationStatus


class ValidationJob(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="validation_jobs",
    )
    url = models.URLField(max_length=2048, db_index=True, validators=[validate_http_url])
    status = models.CharField(
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.PENDING,
        db_index=True,
    )

    total_schemas_found = models.IntegerField(default=0)
    total_errors = models.IntegerField(default=0)
    total_warnings = models.IntegerField(default=0)

    has_json_ld = models.BooleanField(default=False)
    has_microdata = models.BooleanField(default=False)
    has_rdfa = models.BooleanField(default=False)

    error_message = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "validation job"
        verbose_name_plural = "validation jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="val_user_created_idx"),
            models.Index(fields=["status", "-created_at"], name="val_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Validation {self.url} [{self.status}]"


class SchemaItem(BaseModel):
    job = models.ForeignKey(ValidationJob, on_delete=models.CASCADE, related_name="schemas")
    schema_type = models.CharField(max_length=100, db_index=True)
    format = models.CharField(max_length=10, choices=SchemaFormat.choices, db_index=True)
    raw_data = models.JSONField(default=dict)
    is_valid = models.BooleanField(default=False, db_index=True)
    google_rich_result_eligible = models.BooleanField(default=False)

    class Meta:
        verbose_name = "schema item"
        verbose_name_plural = "schema items"
        ordering = ["schema_type"]
        indexes = [
            models.Index(fields=["job", "schema_type"], name="schema_job_type_idx"),
            models.Index(fields=["job", "format"], name="schema_job_format_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.schema_type} ({self.format})"


class SchemaIssue(BaseModel):
    schema_item = models.ForeignKey(
        SchemaItem, on_delete=models.CASCADE, related_name="issues"
    )
    severity = models.CharField(
        max_length=10, choices=IssueSeverity.choices, db_index=True
    )
    field = models.CharField(max_length=200, blank=True, default="")
    message = models.TextField()
    suggestion = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = "schema issue"
        verbose_name_plural = "schema issues"
        ordering = ["severity", "field"]
        indexes = [
            models.Index(fields=["schema_item", "severity"], name="issue_item_sev_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.field}: {self.message[:50]}"
