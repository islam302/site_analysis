"""FullReport: an async job that produces a combined PDF report.

Only the job status, per-tool outcome, and the generated PDF file are stored —
never the raw analysis payloads.
"""
from django.conf import settings
from django.db import models

from apps.analysis.constants import Strategy
from apps.common.models import BaseModel
from apps.common.validators import validate_http_url
from apps.full_report.constants import FullReportStatus


def report_upload_to(instance: "FullReport", filename: str) -> str:
    return f"reports/{instance.id}/{filename}"


class FullReport(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="full_reports",
        null=True,
        blank=True,
    )
    url = models.URLField(max_length=2048, validators=[validate_http_url])
    strategy = models.CharField(max_length=10, choices=Strategy.choices, default=Strategy.MOBILE)
    lang = models.CharField(max_length=2, default="en")

    status = models.CharField(
        max_length=12,
        choices=FullReportStatus.choices,
        default=FullReportStatus.PENDING,
        db_index=True,
    )
    file = models.FileField(upload_to=report_upload_to, null=True, blank=True)
    tools_status = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "full report"
        verbose_name_plural = "full reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="fullreport_user_created_idx"),
            models.Index(fields=["status"], name="fullreport_status_idx"),
        ]

    def __str__(self) -> str:
        return f"FullReport {self.url} [{self.status}]"
