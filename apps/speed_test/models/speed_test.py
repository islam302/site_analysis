"""SpeedTest: a combined run of Google PageSpeed + GTmetrix for one URL."""
from django.conf import settings
from django.db import models

from apps.analysis.constants import Strategy
from apps.common.models import BaseModel
from apps.common.validators import validate_http_url


class SpeedTest(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="speed_tests",
        null=True,
        blank=True,
    )
    url = models.URLField(max_length=2048, db_index=True, validators=[validate_http_url])
    strategy = models.CharField(max_length=10, choices=Strategy.choices, default=Strategy.MOBILE)

    google_report = models.ForeignKey(
        "analysis.AnalysisReport",
        on_delete=models.SET_NULL,
        related_name="speed_tests",
        null=True,
        blank=True,
    )
    gtmetrix_report = models.ForeignKey(
        "gtmetrix.GTmetrixReport",
        on_delete=models.SET_NULL,
        related_name="speed_tests",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "speed test"
        verbose_name_plural = "speed tests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="speedtest_user_created_idx"),
        ]

    def __str__(self) -> str:
        return f"SpeedTest {self.url} [{self.combined_status}]"

    @property
    def combined_status(self) -> str:
        """Roll the two sub-report statuses into one overall status.

        completed  -> both finished successfully
        failed     -> both failed
        pending    -> neither has finished yet
        partial    -> anything else (one done, or one succeeded / one failed)
        """
        google = getattr(self.google_report, "status", None) or "pending"
        gtmetrix = getattr(self.gtmetrix_report, "status", None) or "pending"

        if google == "completed" and gtmetrix == "completed":
            return "completed"
        if google == "failed" and gtmetrix == "failed":
            return "failed"
        if google == "pending" and gtmetrix == "pending":
            return "pending"
        return "partial"
