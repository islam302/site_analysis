"""Tests for analysis selectors."""
import uuid

import pytest
from django.core.cache import cache

from apps.analysis.constants import HISTORY_CACHE_KEY, Strategy
from apps.analysis.exceptions import ReportNotFoundError
from apps.analysis.selectors import (
    get_analysis_history,
    get_report_detail,
    get_user_reports,
    invalidate_history_cache,
)
from apps.analysis.tests.factories import AnalysisHistoryFactory, AnalysisReportFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_get_user_reports_only_returns_own_reports():
    user = UserFactory()
    AnalysisReportFactory(user=user)
    AnalysisReportFactory()  # someone else's
    assert get_user_reports(user=user).count() == 1


def test_get_user_reports_applies_filters():
    user = UserFactory()
    AnalysisReportFactory(user=user, strategy=Strategy.MOBILE)
    AnalysisReportFactory(user=user, strategy=Strategy.DESKTOP)
    qs = get_user_reports(user=user, filters={"strategy": Strategy.DESKTOP})
    assert qs.count() == 1


def test_get_report_detail_found():
    report = AnalysisReportFactory()
    assert get_report_detail(user=report.user, report_id=report.id) == report


def test_get_report_detail_not_found():
    user = UserFactory()
    with pytest.raises(ReportNotFoundError):
        get_report_detail(user=user, report_id=uuid.uuid4())


def test_get_report_detail_other_users_report_not_found():
    report = AnalysisReportFactory()
    other = UserFactory()
    with pytest.raises(ReportNotFoundError):
        get_report_detail(user=other, report_id=report.id)


def test_get_analysis_history_is_cached():
    user = UserFactory()
    AnalysisHistoryFactory(user=user)

    first = get_analysis_history(user=user)
    assert len(first) == 1

    # The cache now holds the value directly.
    assert cache.get(HISTORY_CACHE_KEY.format(user_id=user.id)) is not None

    # Adding a row should NOT appear until the cache is invalidated.
    AnalysisHistoryFactory(user=user)
    assert len(get_analysis_history(user=user)) == 1

    invalidate_history_cache(user_id=user.id)
    assert len(get_analysis_history(user=user)) == 2
