"""AuditIssue: one WAVE issue type found during an audit (with its count)."""
from django.db import models

from apps.audits.constants import IssueType
from apps.common.models import BaseModel


class AuditIssue(BaseModel):
    audit = models.ForeignKey(
        "audits.AccessibilityAudit",
        on_delete=models.CASCADE,
        related_name="issues",
    )
    issue_type = models.CharField(max_length=12, choices=IssueType.choices, db_index=True)
    wave_id = models.CharField(max_length=100, help_text="WAVE item id, e.g. 'alt_missing'.")
    description = models.TextField(blank=True, default="")
    count = models.IntegerField(default=0)
    wcag_reference = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Related WCAG success criterion, e.g. '1.1.1'.",
    )

    class Meta:
        verbose_name = "audit issue"
        verbose_name_plural = "audit issues"
        ordering = ["issue_type", "-count"]
        indexes = [
            models.Index(fields=["audit", "issue_type"], name="issue_audit_type_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.issue_type}] {self.wave_id} x{self.count}"
