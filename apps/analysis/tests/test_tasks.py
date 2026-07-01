"""Tests for the analysis Celery task (runs eagerly under test settings)."""
import pytest

from apps.analysis.constants import ReportStatus
from apps.analysis.tasks import run_pagespeed_analysis
from apps.analysis.tests.factories import AnalysisReportFactory, fake_pagespeed_payload

pytestmark = pytest.mark.django_db


def test_run_pagespeed_analysis_completes_report(mocker):
    report = AnalysisReportFactory(status=ReportStatus.PENDING)
    mocker.patch(
        "apps.analysis.services.analysis_service.fetch_pagespeed",
        return_value=fake_pagespeed_payload(),
    )
    result_status = run_pagespeed_analysis(report_id=str(report.id))

    assert result_status == ReportStatus.COMPLETED
    report.refresh_from_db()
    assert report.performance_score == 92


def test_run_pagespeed_analysis_missing_report_is_safe():
    import uuid

    assert run_pagespeed_analysis(report_id=str(uuid.uuid4())) == "missing"
