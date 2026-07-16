"""Link-checker business logic (no external API — httpx + BeautifulSoup)."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction

from apps.linkchecker.constants import (
    LINK_SOURCES,
    MAX_REDIRECTS,
    CrawlStatus,
    LinkType,
    StatusCategory,
)
from apps.linkchecker.models import CrawlJob

logger = logging.getLogger("apps.linkchecker")

_SKIP_PREFIXES = ("mailto:", "tel:", "javascript:", "data:", "#")


def _headers() -> dict:
    return {"User-Agent": settings.LINKCHECKER_USER_AGENT}


def _timeouts() -> "httpx.Timeout":
    # DNS/connect 10s, read 15s (per spec); DNS shares the connect budget.
    return httpx.Timeout(connect=10.0, read=15.0, write=10.0, pool=5.0)


def _verify() -> bool:
    return settings.LINKCHECKER_VERIFY_SSL


# --------------------------------------------------------------------------- #
# Submit                                                                      #
# --------------------------------------------------------------------------- #
@transaction.atomic
def submit_crawl(
    *, url: str, crawl_depth: int = 1, max_links: int | None = None, render_js: bool = False
) -> CrawlJob:
    """Create a pending CrawlJob and dispatch the async link-check task."""
    job = CrawlJob.objects.create(
        url=url,
        crawl_depth=crawl_depth,
        max_links=max_links or settings.LINKCHECKER_MAX_LINKS,
        render_js=render_js,
        status=CrawlStatus.PENDING,
    )
    logger.info("Crawl submitted", extra={"job_id": str(job.id), "url": url})

    from apps.linkchecker.tasks import run_link_check

    transaction.on_commit(lambda: run_link_check.delay(job_id=str(job.id)))
    return job


# --------------------------------------------------------------------------- #
# Fetch + robots                                                              #
# --------------------------------------------------------------------------- #
def fetch_page_html(*, url: str) -> str:
    """GET the page HTML (following redirects). Raises httpx errors on failure."""
    with httpx.Client(
        follow_redirects=True, timeout=_timeouts(), headers=_headers(), verify=_verify()
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def render_page_html(*, url: str) -> str:
    """Render the page with a headless browser and return the post-JS HTML.

    Used for JavaScript/SPA sites where links only exist after scripts run.
    Playwright + its Chromium are optional; a clear error is raised if missing.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depends on optional install
        raise RuntimeError(
            "JS rendering requires Playwright. Install it with: "
            "pip install playwright && playwright install chromium"
        ) from exc

    from playwright.sync_api import Error as PlaywrightError

    timeout_ms = settings.LINKCHECKER_RENDER_TIMEOUT * 1000
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                context = browser.new_context(
                    user_agent=settings.LINKCHECKER_USER_AGENT,
                    ignore_https_errors=not settings.LINKCHECKER_VERIFY_SSL,
                )
                page = context.new_page()
                # ``domcontentloaded`` is reliable; ``networkidle`` can hang on
                # sites with constant background traffic (analytics/websockets).
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except PlaywrightError:
                    pass
                page.wait_for_timeout(1500)  # let late JS inject links
                return page.content()
            finally:
                browser.close()
    except PlaywrightError as exc:
        raise RuntimeError(f"Headless render failed: {exc}") from exc


def is_allowed_by_robots(*, url: str) -> bool:
    """Return True if robots.txt permits crawling ``url`` (fail-open)."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = robotparser.RobotFileParser()
    try:
        with httpx.Client(timeout=_timeouts(), headers=_headers(), verify=_verify()) as client:
            resp = client.get(robots_url)
        if resp.status_code >= 400:
            return True  # no robots.txt -> allowed
        parser.parse(resp.text.splitlines())
    except httpx.HTTPError:
        return True  # can't fetch robots -> don't block
    return parser.can_fetch(settings.LINKCHECKER_USER_AGENT, url)


# --------------------------------------------------------------------------- #
# Extract                                                                     #
# --------------------------------------------------------------------------- #
def extract_links(*, html_content: str, base_url: str) -> list[dict]:
    """Extract, resolve, de-duplicate and classify links from a page.

    Pulls URLs from ``<a href>``, ``<img src>``, ``<script src>`` and
    ``<link href>``. Relative URLs are resolved against ``base_url``; only
    http(s) URLs are kept; each destination appears once.
    """
    soup = BeautifulSoup(html_content, "lxml")
    base_host = urlparse(base_url).netloc.lower()

    seen: set[str] = set()
    results: list[dict] = []
    for tag_name, attr in LINK_SOURCES:
        for tag in soup.find_all(tag_name):
            raw = (tag.get(attr) or "").strip()
            if not raw or raw.lower().startswith(_SKIP_PREFIXES):
                continue

            target = urljoin(base_url, raw)
            parsed = urlparse(target)
            if parsed.scheme not in ("http", "https"):
                continue

            target = target.split("#", 1)[0]  # drop fragment
            if target in seen:
                continue
            seen.add(target)

            host = parsed.netloc.lower()
            is_internal = host == base_host or host.endswith("." + base_host)
            anchor = ""
            if tag_name == "a":
                anchor = (tag.get_text() or "").strip()[:500]

            results.append(
                {
                    "source_url": base_url,
                    "target_url": target,
                    "anchor_text": anchor,
                    "link_type": LinkType.INTERNAL if is_internal else LinkType.EXTERNAL,
                }
            )
    return results


# --------------------------------------------------------------------------- #
# Check a single link                                                         #
# --------------------------------------------------------------------------- #
def _classify(status: int | None, redirected: bool) -> str:
    if status is None:
        return StatusCategory.ERROR
    if 400 <= status < 600:
        return StatusCategory.BROKEN
    if redirected:
        return StatusCategory.REDIRECT
    if 200 <= status < 300:
        return StatusCategory.HEALTHY
    return StatusCategory.ERROR


def check_single_link(*, url: str, timeout: int | None = None) -> dict:
    """Check one URL's health.

    Sends a HEAD request (falling back to GET on 405), follows redirects
    manually to record the final URL, and classifies the outcome. Never raises —
    timeouts and connection/DNS errors are returned as categorised results.
    """
    start = time.monotonic()
    try:
        with httpx.Client(
            follow_redirects=False, timeout=_timeouts(), headers=_headers(), verify=_verify()
        ) as client:
            current = url
            status = None
            redirected = False
            for _ in range(MAX_REDIRECTS + 1):
                response = client.head(current)
                if response.status_code == 405:
                    response = client.get(current)
                status = response.status_code
                if 300 <= status < 400:
                    location = response.headers.get("location")
                    if not location:
                        break
                    current = urljoin(current, location)
                    redirected = True
                    continue
                break

        elapsed = int((time.monotonic() - start) * 1000)
        return {
            "http_status": status,
            "response_time_ms": elapsed,
            "status_category": _classify(status, redirected),
            "redirect_url": current if redirected else "",
            "error_detail": "",
        }
    except httpx.TimeoutException as exc:
        return {
            "http_status": None,
            "response_time_ms": int((time.monotonic() - start) * 1000),
            "status_category": StatusCategory.TIMEOUT,
            "redirect_url": "",
            "error_detail": (str(exc) or "Request timed out")[:500],
        }
    except httpx.HTTPError as exc:  # connection refused, DNS failure, etc.
        return {
            "http_status": None,
            "response_time_ms": int((time.monotonic() - start) * 1000),
            "status_category": StatusCategory.ERROR,
            "redirect_url": "",
            "error_detail": (str(exc) or "Connection error")[:500],
        }


def quick_link_check(*, url: str, max_links: int = 100) -> dict:
    """Fetch a page, check up to ``max_links`` links, and return a summary.

    A lightweight, non-persisting variant used by the combined full report.
    """
    html = fetch_page_html(url=url)
    links = extract_links(html_content=html, base_url=url)[:max_links]

    counts = {c: 0 for c in StatusCategory.values}
    broken_sample: list[dict] = []
    with ThreadPoolExecutor(max_workers=settings.LINKCHECKER_MAX_WORKERS) as pool:
        futures = {pool.submit(check_single_link, url=link["target_url"]): link for link in links}
        for future in as_completed(futures):
            link = futures[future]
            outcome = future.result()
            category = outcome["status_category"]
            counts[category] = counts.get(category, 0) + 1
            if category == StatusCategory.BROKEN and len(broken_sample) < 15:
                broken_sample.append(
                    {"target_url": link["target_url"], "http_status": outcome["http_status"]}
                )

    return {
        "total_links": len(links),
        "healthy": counts[StatusCategory.HEALTHY],
        "broken": counts[StatusCategory.BROKEN],
        "redirects": counts[StatusCategory.REDIRECT],
        "timeouts": counts[StatusCategory.TIMEOUT],
        "errors": counts[StatusCategory.ERROR],
        "broken_links": broken_sample,
    }
