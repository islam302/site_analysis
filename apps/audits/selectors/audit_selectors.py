"""Read-only queries for accessibility audits."""
from __future__ import annotations

import uuid

from django.db.models import QuerySet

from apps.audits.exceptions import AuditNotFoundError
from apps.audits.models import AccessibilityAudit, AuditIssue


def get_user_audits(*, user) -> QuerySet[AccessibilityAudit]:
    """Return the user's audits, newest first, with issue counts annotated."""
    return AccessibilityAudit.objects.filter(user=user).order_by("-created_at")


def get_audit_by_id(*, audit_id: uuid.UUID | str) -> AccessibilityAudit:
    """Return any audit by id (public read by UUID) or raise not-found."""
    try:
        return AccessibilityAudit.objects.prefetch_related("issues").get(id=audit_id)
    except (AccessibilityAudit.DoesNotExist, ValueError, TypeError):
        raise AuditNotFoundError(extra={"audit_id": str(audit_id)})


def get_audit_issues(
    *, audit_id: uuid.UUID | str, issue_type: str | None = None
) -> QuerySet[AuditIssue]:
    """Return the issues for an audit (public by id), optionally filtered."""
    # Validate existence first for a clean 404.
    get_audit_by_id(audit_id=audit_id)
    qs = AuditIssue.objects.filter(audit_id=audit_id).order_by("issue_type", "-count")
    if issue_type:
        qs = qs.filter(issue_type=issue_type)
    return qs
