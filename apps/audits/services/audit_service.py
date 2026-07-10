"""Accessibility audit business logic.

An audit is synchronous (WAVE returns the full report in one call):
1. Pre-flight the credit balance (fast fail on zero).
2. Call WAVE (outside any DB transaction/lock).
3. On success, in a single atomic block: deduct one credit (row-locked),
   persist totals + issues, mark completed.
4. On WAVE failure, mark the audit failed and consume **no** credit.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.db.models import Avg, Count, Sum

from apps.audits.constants import AUDIT_CREDIT_COST, AuditStatus
from apps.audits.models import AccessibilityAudit, AuditIssue
from apps.audits.services.wave_client import fetch_wave, parse_wave
from apps.credits.services import check_balance, deduct_credit

logger = logging.getLogger("apps.audits")


def run_accessibility_audit(*, user, url: str) -> AccessibilityAudit:
    """Run a WAVE audit for ``url``.

    Authenticated users are credit-gated (one credit per audit); anonymous users
    (``user`` is ``AnonymousUser``/None) run without credits and ``user=None``.

    Raises:
        InsufficientCreditsError: an authenticated user has no credits.
        WaveAPIError / WaveConfigError: the WAVE call failed (no credit spent).
    """
    account = user if getattr(user, "is_authenticated", False) else None

    # 1. Pre-flight credit check for authenticated users only.
    if account is not None:
        check_balance(user=account, required=AUDIT_CREDIT_COST)

    audit = AccessibilityAudit.objects.create(
        user=account, url=url, status=AuditStatus.PENDING
    )

    # 2. Call WAVE outside any transaction so we never hold a lock over HTTP.
    try:
        raw = fetch_wave(url=url)
    except Exception as exc:  # noqa: BLE001 - persist failure, no credit charged
        audit.status = AuditStatus.FAILED
        audit.error_message = str(exc)
        audit.save(update_fields=["status", "error_message", "updated_at"])
        logger.warning("Audit failed (WAVE): %s (audit %s)", str(exc), str(audit.id))
        raise

    parsed = parse_wave(raw)

    # 3. Deduct (authenticated only) + persist atomically. If the balance raced
    #    to zero since the pre-flight check, deduct_credit raises and the whole
    #    block rolls back; we then mark the audit failed (WAVE already ran, but
    #    no credit charged).
    try:
        with transaction.atomic():
            credits_consumed = 0
            if account is not None:
                deduct_credit(
                    user=account,
                    amount=AUDIT_CREDIT_COST,
                    description=f"Accessibility audit: {url}",
                )
                credits_consumed = AUDIT_CREDIT_COST

            for field, value in parsed["totals"].items():
                setattr(audit, field, value)
            audit.wcag_level = parsed["wcag_level"]
            audit.raw_response = raw
            audit.status = AuditStatus.COMPLETED
            audit.error_message = ""
            audit.credits_consumed = credits_consumed
            audit.save()

            AuditIssue.objects.bulk_create(
                [AuditIssue(audit=audit, **issue) for issue in parsed["issues"]]
            )
    except Exception as exc:  # noqa: BLE001
        audit.refresh_from_db()
        audit.status = AuditStatus.FAILED
        audit.error_message = str(exc)
        audit.credits_consumed = 0
        audit.save(update_fields=["status", "error_message", "credits_consumed", "updated_at"])
        logger.warning("Audit finalize failed: %s (audit %s)", str(exc), str(audit.id))
        raise

    logger.info(
        "Audit completed",
        extra={"audit_id": str(audit.id), "errors": audit.total_errors},
    )
    return audit


def get_audit_summary(*, user) -> dict:
    """Return aggregate audit stats for a user.

    Includes total audits, averaged error counts, and the most common issue
    types across all of the user's completed audits.
    """
    audits = AccessibilityAudit.objects.filter(user=user, status=AuditStatus.COMPLETED)
    agg = audits.aggregate(
        total_audits=Count("id"),
        avg_errors=Avg("total_errors"),
        avg_contrast_errors=Avg("total_contrast_errors"),
        total_errors=Sum("total_errors"),
    )

    top_issues = list(
        AuditIssue.objects.filter(audit__user=user)
        .values("wave_id", "issue_type")
        .annotate(occurrences=Count("id"), total_count=Sum("count"))
        .order_by("-total_count")[:10]
    )

    return {
        "total_audits": agg["total_audits"] or 0,
        "avg_errors": round(agg["avg_errors"] or 0, 2),
        "avg_contrast_errors": round(agg["avg_contrast_errors"] or 0, 2),
        "total_errors": agg["total_errors"] or 0,
        "most_common_issues": top_issues,
    }
