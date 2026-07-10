"""Integration tests for the link checker API."""
import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.linkchecker.constants import LinkType, StatusCategory
from apps.linkchecker.models import CrawlJob
from apps.linkchecker.tests.factories import (
    CompletedCrawlJobFactory,
    LinkResultFactory,
)

pytestmark = pytest.mark.django_db


def test_submit_creates_pending_job():
    resp = APIClient().post(
        reverse("linkchecker:crawl-list"),
        {"url": "https://example.com", "max_links": 100},
        format="json",
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.data["status"] == "pending"
    assert resp.data["max_links"] == 100
    assert CrawlJob.objects.count() == 1


def test_submit_with_render_js():
    resp = APIClient().post(
        reverse("linkchecker:crawl-list"),
        {"url": "https://example.com", "render_js": True},
        format="json",
    )
    assert resp.status_code == status.HTTP_202_ACCEPTED
    assert resp.data["render_js"] is True
    assert CrawlJob.objects.get(id=resp.data["id"]).render_js is True


def test_submit_rejects_localhost():
    resp = APIClient().post(
        reverse("linkchecker:crawl-list"), {"url": "http://localhost/"}, format="json"
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_list_jobs():
    CompletedCrawlJobFactory()
    CompletedCrawlJobFactory()
    resp = APIClient().get(reverse("linkchecker:crawl-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 2


def test_retrieve_job_with_stats():
    job = CompletedCrawlJobFactory()
    resp = APIClient().get(reverse("linkchecker:crawl-detail", args=[job.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["total_broken"] == 1
    assert resp.data["total_links_found"] == 3


def test_links_endpoint_filtered_by_category():
    job = CompletedCrawlJobFactory()
    LinkResultFactory(crawl_job=job, status_category=StatusCategory.HEALTHY)
    LinkResultFactory(crawl_job=job, status_category=StatusCategory.BROKEN)
    LinkResultFactory(crawl_job=job, status_category=StatusCategory.BROKEN)

    resp = APIClient().get(
        reverse("linkchecker:crawl-links", args=[job.id]), {"status_category": "broken"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 2


def test_links_endpoint_filtered_by_type():
    job = CompletedCrawlJobFactory()
    LinkResultFactory(crawl_job=job, link_type=LinkType.INTERNAL)
    LinkResultFactory(crawl_job=job, link_type=LinkType.EXTERNAL)
    resp = APIClient().get(
        reverse("linkchecker:crawl-links", args=[job.id]), {"link_type": "external"}
    )
    assert resp.data["count"] == 1


def test_broken_shortcut():
    job = CompletedCrawlJobFactory()
    LinkResultFactory(crawl_job=job, status_category=StatusCategory.HEALTHY)
    LinkResultFactory(crawl_job=job, status_category=StatusCategory.BROKEN)
    resp = APIClient().get(reverse("linkchecker:crawl-broken", args=[job.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["status_category"] == "broken"


def test_progress_endpoint():
    job = CompletedCrawlJobFactory(total_links_found=10, total_checked=4)
    resp = APIClient().get(reverse("linkchecker:crawl-progress", args=[job.id]))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["percent"] == 40.0
    assert resp.data["total_checked"] == 4


def test_detail_not_found():
    import uuid

    resp = APIClient().get(reverse("linkchecker:crawl-detail", args=[uuid.uuid4()]))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
