"""Tests for the WAVE client parsing and the audit service (credit-gated)."""
import pytest

from apps.audits.constants import AuditStatus
from apps.audits.exceptions import WaveAPIError
from apps.audits.models import AccessibilityAudit, AuditIssue
from apps.audits.services import run_accessibility_audit
from apps.audits.services.wave_client import parse_wave
from apps.audits.tests.factories import fake_wave_payload
from apps.credits.exceptions import InsufficientCreditsError
from apps.credits.models import CreditTransaction
from apps.credits.tests.factories import set_balance
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


# --- parser -----------------------------------------------------------------
def test_parse_wave_totals_and_issues():
    parsed = parse_wave(fake_wave_payload(errors=2, contrast=3, alerts=1, features=1, structure=1))
    assert parsed["totals"]["total_errors"] == 2
    assert parsed["totals"]["total_contrast_errors"] == 3
    assert parsed["totals"]["total_structural"] == 1
    # errors present -> fails WCAG
    assert parsed["wcag_level"] is None
    types = {i["issue_type"] for i in parsed["issues"]}
    assert "error" in types and "structural" in types


def test_parse_wave_clean_page_is_aa():
    parsed = parse_wave(fake_wave_payload(errors=0, contrast=0))
    assert parsed["wcag_level"] == "AA"


def test_parse_wave_only_contrast_is_a():
    parsed = parse_wave(fake_wave_payload(errors=0, contrast=4))
    assert parsed["wcag_level"] == "A"


# --- run audit --------------------------------------------------------------
def test_run_audit_success_deducts_one_credit(mocker):
    user = UserFactory()
    set_balance(user, 5)
    mocker.patch(
        "apps.audits.services.audit_service.fetch_wave",
        return_value=fake_wave_payload(errors=2, contrast=1),
    )

    audit = run_accessibility_audit(user=user, url="https://example.com")

    assert audit.status == AuditStatus.COMPLETED
    assert audit.total_errors == 2
    assert audit.credits_consumed == 1
    assert AuditIssue.objects.filter(audit=audit).count() >= 1

    user.credit_balance.refresh_from_db()
    assert user.credit_balance.balance == 4
    assert CreditTransaction.objects.filter(user=user, transaction_type="usage").count() == 1


def test_run_audit_anonymous_skips_credits(mocker):
    from django.contrib.auth.models import AnonymousUser

    mocker.patch(
        "apps.audits.services.audit_service.fetch_wave",
        return_value=fake_wave_payload(errors=1),
    )
    audit = run_accessibility_audit(user=AnonymousUser(), url="https://example.com")

    assert audit.status == AuditStatus.COMPLETED
    assert audit.user_id is None
    assert audit.credits_consumed == 0


def test_run_audit_zero_credits_raises_before_calling_wave(mocker):
    user = UserFactory()  # balance 0
    wave = mocker.patch("apps.audits.services.audit_service.fetch_wave")

    with pytest.raises(InsufficientCreditsError):
        run_accessibility_audit(user=user, url="https://example.com")

    wave.assert_not_called()
    assert not AccessibilityAudit.objects.filter(user=user).exists()


def test_run_audit_wave_failure_marks_failed_and_keeps_credits(mocker):
    user = UserFactory()
    set_balance(user, 3)
    mocker.patch(
        "apps.audits.services.audit_service.fetch_wave",
        side_effect=WaveAPIError("WAVE down"),
    )

    with pytest.raises(WaveAPIError):
        run_accessibility_audit(user=user, url="https://example.com")

    audit = AccessibilityAudit.objects.get(user=user)
    assert audit.status == AuditStatus.FAILED
    assert audit.credits_consumed == 0
    # No credit spent on failure.
    user.credit_balance.refresh_from_db()
    assert user.credit_balance.balance == 3
    assert not CreditTransaction.objects.filter(user=user).exists()
