"""factory_boy factories for the analysis app."""
import factory
from django.utils import timezone

from apps.analysis.constants import ReportStatus, Strategy
from apps.analysis.models import AnalysisHistory, AnalysisReport
from apps.users.tests.factories import UserFactory


class AnalysisReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalysisReport

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://example{n}.com")
    strategy = Strategy.MOBILE
    status = ReportStatus.PENDING


class CompletedReportFactory(AnalysisReportFactory):
    status = ReportStatus.COMPLETED
    performance_score = 92
    accessibility_score = 88
    best_practices_score = 95
    seo_score = 100
    first_contentful_paint = 1.2
    largest_contentful_paint = 2.4
    total_blocking_time = 150.0
    cumulative_layout_shift = 0.02
    speed_index = 2.1
    time_to_interactive = 3.0
    raw_response = factory.LazyFunction(dict)


class AnalysisHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalysisHistory

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://example{n}.com")
    reports_count = 1
    last_analyzed_at = factory.LazyFunction(timezone.now)


def fake_pagespeed_payload(*, performance=0.92, fcp_ms=1200.0, cls=0.02) -> dict:
    """Build a minimal Lighthouse-shaped payload for parser tests."""
    return {
        "lighthouseResult": {
            "categories": {
                "performance": {"score": performance},
                "accessibility": {"score": 0.88},
                "best-practices": {"score": 0.95},
                "seo": {"score": 1.0},
            },
            "audits": {
                "first-contentful-paint": {"numericValue": fcp_ms},
                "largest-contentful-paint": {"numericValue": 2400.0},
                "total-blocking-time": {"numericValue": 150.0},
                "cumulative-layout-shift": {"numericValue": cls},
                "speed-index": {"numericValue": 2100.0},
                "interactive": {"numericValue": 3000.0},
            },
        }
    }
