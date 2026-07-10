"""factory_boy factories and WAVE fixtures for the audits app."""
import factory

from apps.audits.constants import AuditStatus, IssueType
from apps.audits.models import AccessibilityAudit, AuditIssue
from apps.users.tests.factories import UserFactory


class AccessibilityAuditFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AccessibilityAudit

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://example{n}.com")
    status = AuditStatus.PENDING


class CompletedAuditFactory(AccessibilityAuditFactory):
    status = AuditStatus.COMPLETED
    total_errors = 3
    total_alerts = 10
    total_features = 8
    total_structural = 12
    total_contrast_errors = 5
    wcag_level = None
    credits_consumed = 1


class AuditIssueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AuditIssue

    audit = factory.SubFactory(CompletedAuditFactory)
    issue_type = IssueType.ERROR
    wave_id = factory.Sequence(lambda n: f"issue_{n}")
    description = factory.Faker("sentence")
    count = 2


def fake_wave_payload(*, errors=2, contrast=0, alerts=1, features=1, structure=1) -> dict:
    """Build a WAVE-shaped response for client/service tests."""

    def category(count, item_id, desc):
        return {
            "description": desc,
            "count": count,
            "items": (
                {item_id: {"id": item_id, "description": desc, "count": count}}
                if count
                else {}
            ),
        }

    return {
        "status": {"success": True, "httpstatuscode": 200},
        "statistics": {"pageurl": "https://example.com", "creditsremaining": 100},
        "categories": {
            "error": category(errors, "alt_missing", "Missing alternative text"),
            "contrast": category(contrast, "contrast", "Very low contrast"),
            "alert": category(alerts, "redundant_alt", "Redundant alternative text"),
            "feature": category(features, "alt", "Alternative text present"),
            "structure": category(structure, "h1", "Heading level 1"),
        },
    }
