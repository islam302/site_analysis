"""factory_boy factories and fixtures for the GTmetrix app."""
import factory

from apps.gtmetrix.constants import ReportStatus
from apps.gtmetrix.models import GTmetrixReport
from apps.users.tests.factories import UserFactory


class GTmetrixReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GTmetrixReport

    user = factory.SubFactory(UserFactory)
    url = factory.Sequence(lambda n: f"https://example{n}.com")
    status = ReportStatus.PENDING


class CompletedGTmetrixReportFactory(GTmetrixReportFactory):
    status = ReportStatus.COMPLETED
    test_id = "test_abc"
    gtmetrix_grade = "A"
    performance_score = 95
    structure_score = 92
    first_contentful_paint = 800.0
    largest_contentful_paint = 1200.0
    cumulative_layout_shift = 0.01
    total_blocking_time = 50.0
    fully_loaded_time = 2500.0
    page_bytes = 1048576
    page_requests = 42


def fake_gtmetrix_result() -> dict:
    """Shape returned by ``run_gtmetrix_test`` (for mocking the service)."""
    return {
        "test_id": "test_abc",
        "metrics": {
            "gtmetrix_grade": "A",
            "performance_score": 95,
            "structure_score": 92,
            "first_contentful_paint": 800.0,
            "largest_contentful_paint": 1200.0,
            "cumulative_layout_shift": 0.01,
            "total_blocking_time": 50.0,
            "time_to_interactive": 1500.0,
            "speed_index": 1100.0,
            "onload_time": 1800.0,
            "fully_loaded_time": 2500.0,
            "page_bytes": 1048576,
            "page_requests": 42,
            "report_url": "https://gtmetrix.com/reports/example/abc/",
        },
        "raw": {"data": {"id": "report_abc", "type": "report"}},
    }


def fake_report_json() -> dict:
    """A GTmetrix report resource payload (for parser tests)."""
    return {
        "data": {
            "type": "report",
            "id": "report_abc",
            "attributes": {
                "gtmetrix_grade": "A",
                "performance_score": 95,
                "structure_score": 92,
                "first_contentful_paint": 800.0,
                "largest_contentful_paint": 1200.0,
                "cumulative_layout_shift": 0.01,
                "total_blocking_time": 50.0,
                "time_to_interactive": 1500.0,
                "speed_index": 1100.0,
                "onload_time": 1800.0,
                "fully_loaded_time": 2500.0,
                "page_bytes": 1048576,
                "page_requests": 42,
            },
            "links": {"report_pdf": "https://gtmetrix.com/api/2.0/reports/report_abc.pdf"},
        }
    }
