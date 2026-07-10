"""factory_boy factories and fixtures for the link checker."""
import factory

from apps.linkchecker.constants import CrawlStatus, LinkType, StatusCategory
from apps.linkchecker.models import CrawlJob, LinkResult


class CrawlJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CrawlJob

    url = factory.Sequence(lambda n: f"https://example{n}.com/")
    status = CrawlStatus.PENDING


class CompletedCrawlJobFactory(CrawlJobFactory):
    status = CrawlStatus.COMPLETED
    total_links_found = 3
    total_checked = 3
    total_healthy = 1
    total_broken = 1
    total_redirects = 1
    duration_seconds = 2.5


class LinkResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LinkResult

    crawl_job = factory.SubFactory(CompletedCrawlJobFactory)
    source_url = "https://example.com/"
    target_url = factory.Sequence(lambda n: f"https://example.com/page{n}")
    anchor_text = "link"
    link_type = LinkType.INTERNAL
    http_status = 200
    status_category = StatusCategory.HEALTHY
    response_time_ms = 120


SAMPLE_HTML = """
<html><body>
  <a href="/page1">One</a>
  <a href="/page1">Duplicate</a>
  <a href="https://external.com/x">External</a>
  <a href="mailto:a@b.com">Mail</a>
  <a href="#section">Fragment</a>
  <img src="/img.png">
  <script src="https://cdn.example.net/app.js"></script>
  <link href="/style.css" rel="stylesheet">
</body></html>
"""
