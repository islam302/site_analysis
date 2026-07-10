"""SSLReport: the result of a single sslyze TLS scan for a host."""
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.common.validators import validate_http_url
from apps.ssl_check.constants import ReportStatus


class SSLReport(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ssl_reports",
        null=True,
        blank=True,
        help_text="Null for anonymous submissions.",
    )
    url = models.URLField(max_length=2048, db_index=True, validators=[validate_http_url])
    host = models.CharField(max_length=255, db_index=True)
    status = models.CharField(
        max_length=10,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True, default="")

    # Synthesised grade (A+, A, B, C, F, T=untrusted) and warning flag.
    grade = models.CharField(max_length=4, blank=True, default="")
    has_warnings = models.BooleanField(default=False)
    ip_address = models.CharField(max_length=45, blank=True, default="")
    server_name = models.CharField(max_length=255, blank=True, default="")

    # Certificate.
    cert_subject = models.CharField(max_length=512, blank=True, default="")
    cert_issuer = models.CharField(max_length=512, blank=True, default="")
    cert_valid_from = models.DateTimeField(null=True, blank=True)
    cert_valid_to = models.DateTimeField(null=True, blank=True)
    cert_expires_in_days = models.IntegerField(null=True, blank=True)
    cert_is_trusted = models.BooleanField(null=True, blank=True)

    protocols = models.JSONField(default=list, blank=True)
    vulnerabilities = models.JSONField(default=dict, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "SSL report"
        verbose_name_plural = "SSL reports"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="ssl_user_created_idx"),
            models.Index(fields=["host"], name="ssl_host_idx"),
            models.Index(fields=["status"], name="ssl_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.host} [{self.grade or self.status}]"
