"""AnalysisReport: the result of a single PageSpeed Insights analysis."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.analysis.constants import ReportStatus, Strategy
from apps.common.models import BaseModel
from apps.common.validators import validate_http_url

# Scores are only populated once an analysis completes, so they are nullable
# while a report is pending or failed.
_SCORE_VALIDATORS = [MinValueValidator(0), MaxValueValidator(100)]


class AnalysisReport(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analysis_reports",
        null=True,
        blank=True,
        help_text="Null for anonymous submissions.",
    )
    url = models.URLField(max_length=2048, db_index=True, validators=[validate_http_url])
    strategy = models.CharField(max_length=10, choices=Strategy.choices, db_index=True)

    status = models.CharField(
        max_length=10,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="")

    # Lighthouse category scores (0-100).
    performance_score = models.IntegerField(null=True, blank=True, validators=_SCORE_VALIDATORS)
    accessibility_score = models.IntegerField(null=True, blank=True, validators=_SCORE_VALIDATORS)
    best_practices_score = models.IntegerField(null=True, blank=True, validators=_SCORE_VALIDATORS)
    seo_score = models.IntegerField(null=True, blank=True, validators=_SCORE_VALIDATORS)

    # Core Web Vitals & timing metrics.
    first_contentful_paint = models.FloatField(null=True, blank=True, help_text="seconds")
    largest_contentful_paint = models.FloatField(null=True, blank=True, help_text="seconds")
    total_blocking_time = models.FloatField(null=True, blank=True, help_text="milliseconds")
    cumulative_layout_shift = models.FloatField(null=True, blank=True, help_text="unitless")
    speed_index = models.FloatField(null=True, blank=True, help_text="seconds")
    time_to_interactive = models.FloatField(null=True, blank=True, help_text="seconds")

    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "analysis report"
        verbose_name_plural = "analysis reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="report_user_created_idx"),
            models.Index(fields=["url", "strategy"], name="report_url_strategy_idx"),
            models.Index(fields=["status"], name="report_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(performance_score__isnull=True)
                    | (models.Q(performance_score__gte=0) & models.Q(performance_score__lte=100))
                ),
                name="report_performance_score_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.url} [{self.strategy}] ({self.status})"
