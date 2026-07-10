"""Tests for the combined full-report: service, PDF builder, task, and API."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.analysis.tests.factories import fake_pagespeed_payload
from apps.audits.tests.factories import fake_wave_payload
from apps.full_report.constants import FullReportStatus
from apps.full_report.models import FullReport
from apps.full_report.services import build_report_pdf, run_full_report
from apps.full_report.tasks import run_full_report_task
from apps.gtmetrix.tests.factories import fake_gtmetrix_result
from apps.ssl_check.tests.factories import fake_ssl_scan_result

pytestmark = pytest.mark.django_db


def _mock_all(mocker, *, wave_ok=True, gtmetrix_ok=True):
    mocker.patch(
        "apps.full_report.services.full_report_service.fetch_pagespeed",
        return_value=fake_pagespeed_payload(),
    )
    mocker.patch(
        "apps.full_report.services.full_report_service.run_gtmetrix_test",
        return_value=fake_gtmetrix_result() if gtmetrix_ok else None,
        side_effect=None if gtmetrix_ok else RuntimeError("gtmetrix down"),
    )
    mocker.patch(
        "apps.full_report.services.full_report_service.fetch_wave",
        return_value=fake_wave_payload(errors=2, contrast=1) if wave_ok else None,
        side_effect=None if wave_ok else RuntimeError("wave down"),
    )
    mocker.patch(
        "apps.full_report.services.full_report_service.run_ssl_scan",
        return_value=fake_ssl_scan_result("A+"),
    )


# --- service + PDF (concurrent, no storage) ---------------------------------
def test_run_full_report_all_ok(mocker):
    _mock_all(mocker)
    report = run_full_report(url="https://example.com", strategy="mobile")
    assert report["pagespeed"]["status"] == "ok"
    assert report["gtmetrix"]["status"] == "ok"
    assert report["accessibility"]["status"] == "ok"
    assert report["ssl"]["status"] == "ok"
    assert report["ssl"]["data"]["grade"] == "A+"
    assert report["pagespeed"]["data"]["performance_score"] == 92


def test_run_full_report_partial_failure(mocker):
    _mock_all(mocker, wave_ok=False)
    report = run_full_report(url="https://example.com", strategy="desktop")
    assert report["pagespeed"]["status"] == "ok"
    assert report["accessibility"]["status"] == "failed"
    assert "wave down" in report["accessibility"]["error"]


def test_build_report_pdf_english(mocker):
    _mock_all(mocker)
    report = run_full_report(url="https://example.com", strategy="mobile")
    pdf = build_report_pdf(report, lang="en")
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000


def test_build_report_pdf_arabic(mocker):
    _mock_all(mocker)
    report = run_full_report(url="https://example.com", strategy="mobile")
    pdf = build_report_pdf(report, lang="ar")
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000


# --- async task -------------------------------------------------------------
def test_task_completes_and_saves_pdf(mocker, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _mock_all(mocker)
    job = FullReport.objects.create(url="https://example.com", strategy="mobile", lang="en")

    result_status = run_full_report_task(report_id=str(job.id))

    job.refresh_from_db()
    assert result_status == FullReportStatus.COMPLETED
    assert job.status == FullReportStatus.COMPLETED
    assert job.file.name.endswith(".pdf")
    assert job.tools_status["pagespeed"] == "ok"
    assert job.tools_status["ssl"] == "ok"
    with job.file.open("rb") as f:
        assert f.read(4) == b"%PDF"


def test_task_arabic(mocker, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _mock_all(mocker)
    job = FullReport.objects.create(url="https://example.com", strategy="mobile", lang="ar")
    run_full_report_task(report_id=str(job.id))
    job.refresh_from_db()
    assert job.status == FullReportStatus.COMPLETED
    assert job.file.name.endswith("-ar.pdf")


def test_task_missing_report_is_safe():
    import uuid

    assert run_full_report_task(report_id=str(uuid.uuid4())) == "missing"


# --- API (async) ------------------------------------------------------------
def test_create_returns_202_with_status_url(mocker):
    _mock_all(mocker)  # on_commit won't fire in the test transaction, so it stays pending
    resp = APIClient().post(
        reverse("full_report:run"),
        {"url": "https://example.com", "strategy": "mobile"},
        format="json",
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.data["status"] == "pending"
    assert "id" in resp.data
    assert resp.data["status_url"].endswith(f"/{resp.data['id']}/")


def test_detail_pending_then_completed(mocker, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    _mock_all(mocker)
    job = FullReport.objects.create(url="https://example.com", strategy="mobile", lang="en")
    client = APIClient()

    # Pending: no download url yet.
    resp = client.get(reverse("full_report:detail", args=[job.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["status"] == "pending"
    assert resp.data["download_url"] is None

    # Process it, then poll again.
    run_full_report_task(report_id=str(job.id))
    resp = client.get(reverse("full_report:detail", args=[job.id]))
    assert resp.data["status"] == "completed"
    assert resp.data["download_url"].endswith(".pdf")
    assert resp.data["download_url"].startswith("http")


def test_create_validates_url():
    resp = APIClient().post(reverse("full_report:run"), {"url": "not-a-url"}, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
