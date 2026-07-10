"""AccessibilityAudit: the result of a single WAVE accessibility check."""
from django.conf import settings
from django.db import models

from apps.audits.constants import AuditStatus
from apps.common.models import BaseModel
from apps.common.validators import validate_http_url


class AccessibilityAudit(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accessibility_audits",
        null=True,
        blank=True,
        help_text="Null for anonymous audits (no credit charged).",
    )
    url = models.URLField(max_length=2048, db_index=True, validators=[validate_http_url])
    status = models.CharField(
        max_length=10,
        choices=AuditStatus.choices,
        default=AuditStatus.PENDING,
        db_index=True,
    )

    total_errors = models.IntegerField(default=0)
    total_alerts = models.IntegerField(default=0)
    total_features = models.IntegerField(default=0)
    total_structural = models.IntegerField(default=0)
    total_contrast_errors = models.IntegerField(default=0)

    wcag_level = models.CharField(
        max_length=3,
        null=True,
        blank=True,
        help_text="Estimated WCAG conformance: A / AA / AAA, or null if it fails.",
    )
    raw_response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default="")
    credits_consumed = models.IntegerField(default=0)

    class Meta:
        verbose_name = "accessibility audit"
        verbose_name_plural = "accessibility audits"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="audit_user_created_idx"),
            models.Index(fields=["url"], name="audit_url_idx"),
            models.Index(fields=["status"], name="audit_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.url} ({self.status})"
