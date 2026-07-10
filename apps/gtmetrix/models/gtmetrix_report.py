"""GTmetrixReport: the result of a single GTmetrix test run."""
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.common.validators import validate_http_url
from apps.gtmetrix.constants import ReportStatus


class GTmetrixReport(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gtmetrix_reports",
        null=True,
        blank=True,
        help_text="Null for anonymous submissions.",
    )
    url = models.URLField(max_length=2048, db_index=True, validators=[validate_http_url])
    status = models.CharField(
        max_length=10,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="")

    # GTmetrix identifiers.
    test_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    report_url = models.URLField(max_length=2048, blank=True, default="")

    # Grades & scores.
    gtmetrix_grade = models.CharField(max_length=4, blank=True, default="")
    performance_score = models.IntegerField(null=True, blank=True)
    structure_score = models.IntegerField(null=True, blank=True)

    # Timing metrics (milliseconds unless noted).
    first_contentful_paint = models.FloatField(null=True, blank=True, help_text="ms")
    largest_contentful_paint = models.FloatField(null=True, blank=True, help_text="ms")
    cumulative_layout_shift = models.FloatField(null=True, blank=True, help_text="unitless")
    total_blocking_time = models.FloatField(null=True, blank=True, help_text="ms")
    time_to_interactive = models.FloatField(null=True, blank=True, help_text="ms")
    speed_index = models.FloatField(null=True, blank=True, help_text="ms")
    onload_time = models.FloatField(null=True, blank=True, help_text="ms")
    fully_loaded_time = models.FloatField(null=True, blank=True, help_text="ms")

    # Page weight.
    page_bytes = models.BigIntegerField(null=True, blank=True)
    page_requests = models.IntegerField(null=True, blank=True)

    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "GTmetrix report"
        verbose_name_plural = "GTmetrix reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="gtm_user_created_idx"),
            models.Index(fields=["status"], name="gtm_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.url} ({self.status})"
