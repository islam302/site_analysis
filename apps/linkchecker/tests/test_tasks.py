"""End-to-end tests for the run_link_check Celery task (respx-mocked httpx)."""
import uuid

import httpx
import pytest
import respx

from apps.linkchecker.constants import CrawlStatus
from apps.linkchecker.models import LinkResult
from apps.linkchecker.tasks import run_link_check
from apps.linkchecker.tests.factories import CrawlJobFactory

pytestmark = pytest.mark.django_db


@respx.mock
def test_run_link_check_completes_with_counts():
    job = CrawlJobFactory(url="https://example.com/")
    respx.get("https://example.com/robots.txt").mock(return_value=httpx.Response(404))
    html = '<a href="/good">g</a><a href="https://ext.com/bad">b</a><a href="/redir">r</a>'
    respx.get("https://example.com/").mock(return_value=httpx.Response(200, text=html))
    respx.head("https://example.com/good").mock(return_value=httpx.Response(200))
    respx.head("https://ext.com/bad").mock(return_value=httpx.Response(404))
    respx.head("https://example.com/redir").mock(
        return_value=httpx.Response(301, headers={"location": "https://example.com/good"})
    )

    assert run_link_check(job_id=str(job.id)) == CrawlStatus.COMPLETED

    job.refresh_from_db()
    assert job.total_links_found == 3
    assert job.total_checked == 3
    assert job.total_healthy == 1
    assert job.total_broken == 1
    assert job.total_redirects == 1
    assert job.duration_seconds is not None
    assert LinkResult.objects.filter(crawl_job=job).count() == 3


@respx.mock
def test_run_link_check_respects_robots_disallow():
    job = CrawlJobFactory(url="https://example.com/")
    respx.get("https://example.com/robots.txt").mock(
        return_value=httpx.Response(200, text="User-agent: *\nDisallow: /")
    )
    assert run_link_check(job_id=str(job.id)) == "failed"
    job.refresh_from_db()
    assert job.status == CrawlStatus.FAILED
    assert "robots" in job.error_message.lower()


@respx.mock
def test_run_link_check_uses_render_when_render_js(mocker):
    job = CrawlJobFactory(url="https://spa.example.com/", render_js=True)
    respx.get("https://spa.example.com/robots.txt").mock(return_value=httpx.Response(404))
    render = mocker.patch(
        "apps.linkchecker.tasks.render_page_html", return_value='<a href="/x">x</a>'
    )
    fetch = mocker.patch("apps.linkchecker.tasks.fetch_page_html")
    respx.head("https://spa.example.com/x").mock(return_value=httpx.Response(200))

    assert run_link_check(job_id=str(job.id)) == CrawlStatus.COMPLETED
    render.assert_called_once()
    fetch.assert_not_called()
    job.refresh_from_db()
    assert job.total_links_found == 1


def test_run_link_check_missing_job_is_safe():
    assert run_link_check(job_id=str(uuid.uuid4())) == "missing"
