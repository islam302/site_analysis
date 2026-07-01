"""AnalysisHistory: per-user rollup of how often each URL has been analyzed."""
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.common.validators import validate_http_url


class AnalysisHistory(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analysis_history",
    )
    url = models.URLField(max_length=2048, validators=[validate_http_url])
    reports_count = models.IntegerField(default=0)
    last_analyzed_at = models.DateTimeField()

    class Meta:
        verbose_name = "analysis history"
        verbose_name_plural = "analysis history"
        ordering = ["-last_analyzed_at"]
        indexes = [
            models.Index(fields=["user", "-last_analyzed_at"], name="history_user_last_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "url"], name="unique_user_url_history"),
        ]

    def __str__(self) -> str:
        return f"{self.url} x{self.reports_count}"
