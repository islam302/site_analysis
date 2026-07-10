"""Tests for link-checker services (extract_links + check_single_link via respx)."""
import httpx
import pytest
import respx

from apps.linkchecker.constants import LinkType, StatusCategory
from apps.linkchecker.services import check_single_link, extract_links
from apps.linkchecker.tests.factories import SAMPLE_HTML


# --- extract_links (no network) --------------------------------------------
def test_extract_links_dedupes_and_classifies():
    links = extract_links(html_content=SAMPLE_HTML, base_url="https://example.com/")
    targets = {link["target_url"] for link in links}

    # Relative resolved, fragment/mailto skipped, duplicate collapsed.
    assert "https://example.com/page1" in targets
    assert "https://example.com/img.png" in targets
    assert "https://example.com/style.css" in targets
    assert "https://external.com/x" in targets
    assert "https://cdn.example.net/app.js" in targets
    assert len(links) == 5  # page1 (deduped), img, style, external, cdn

    by_target = {link["target_url"]: link for link in links}
    assert by_target["https://example.com/page1"]["link_type"] == LinkType.INTERNAL
    assert by_target["https://example.com/page1"]["anchor_text"] == "One"
    assert by_target["https://external.com/x"]["link_type"] == LinkType.EXTERNAL


def test_extract_links_skips_non_http_schemes():
    html = '<a href="mailto:x@y.com">m</a><a href="javascript:void(0)">j</a>'
    assert extract_links(html_content=html, base_url="https://example.com/") == []


# --- check_single_link (respx) ---------------------------------------------
@respx.mock
def test_check_healthy():
    respx.head("https://example.com/ok").mock(return_value=httpx.Response(200))
    result = check_single_link(url="https://example.com/ok")
    assert result["status_category"] == StatusCategory.HEALTHY
    assert result["http_status"] == 200
    assert result["response_time_ms"] is not None


@respx.mock
def test_check_broken_404():
    respx.head("https://example.com/missing").mock(return_value=httpx.Response(404))
    result = check_single_link(url="https://example.com/missing")
    assert result["status_category"] == StatusCategory.BROKEN
    assert result["http_status"] == 404


@respx.mock
def test_check_broken_500():
    respx.head("https://example.com/boom").mock(return_value=httpx.Response(500))
    result = check_single_link(url="https://example.com/boom")
    assert result["status_category"] == StatusCategory.BROKEN


@respx.mock
def test_check_redirect_chain():
    respx.head("https://example.com/old").mock(
        return_value=httpx.Response(301, headers={"location": "https://example.com/new"})
    )
    respx.head("https://example.com/new").mock(return_value=httpx.Response(200))
    result = check_single_link(url="https://example.com/old")
    assert result["status_category"] == StatusCategory.REDIRECT
    assert result["redirect_url"] == "https://example.com/new"


@respx.mock
def test_check_head_405_falls_back_to_get():
    respx.head("https://example.com/nohead").mock(return_value=httpx.Response(405))
    respx.get("https://example.com/nohead").mock(return_value=httpx.Response(200))
    result = check_single_link(url="https://example.com/nohead")
    assert result["status_category"] == StatusCategory.HEALTHY


@respx.mock
def test_check_timeout():
    respx.head("https://example.com/slow").mock(side_effect=httpx.ConnectTimeout("timed out"))
    result = check_single_link(url="https://example.com/slow")
    assert result["status_category"] == StatusCategory.TIMEOUT
    assert result["http_status"] is None


@respx.mock
def test_check_connection_error():
    respx.head("https://example.com/down").mock(side_effect=httpx.ConnectError("refused"))
    result = check_single_link(url="https://example.com/down")
    assert result["status_category"] == StatusCategory.ERROR
    assert "refused" in result["error_detail"]
