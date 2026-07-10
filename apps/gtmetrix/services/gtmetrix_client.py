"""Client for the GTmetrix API 2.0 (https://gtmetrix.com/api/2.0/).

GTmetrix runs tests asynchronously: you POST a test, poll it until it reaches
the ``completed`` state, then fetch the resulting report. Auth is HTTP Basic
with the API key as the username and an empty password. This module performs
the HTTP + polling + parsing; the service layer persists results.
"""
from __future__ import annotations

import logging
import time

import requests
from django.conf import settings

from apps.gtmetrix.constants import (
    REPORT_ATTR_TO_FIELD,
    TEST_STATE_COMPLETED,
    TEST_STATE_ERROR,
)
from apps.gtmetrix.exceptions import (
    GTmetrixAPIError,
    GTmetrixClientError,
    GTmetrixConfigError,
    GTmetrixTimeoutError,
)

logger = logging.getLogger("apps.gtmetrix")

_JSON_API = "application/vnd.api+json"


def _auth() -> tuple[str, str]:
    if not settings.GTMETRIX_API_KEY:
        raise GTmetrixConfigError()
    return (settings.GTMETRIX_API_KEY, "")


def _url(path: str) -> str:
    return settings.GTMETRIX_BASE_URL.rstrip("/") + "/" + path.lstrip("/")


def _request(method: str, path: str, **kwargs) -> dict:
    try:
        resp = requests.request(
            method,
            _url(path),
            auth=_auth(),
            headers={"Content-Type": _JSON_API, "Accept": _JSON_API},
            timeout=settings.GTMETRIX_REQUEST_TIMEOUT,
            **kwargs,
        )
        resp.raise_for_status()
        return resp.json() if resp.content else {}
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        # GTmetrix returns JSON:API errors: {"errors": [{"title": .., "detail": ..}]}
        title = ""
        try:
            errors = exc.response.json().get("errors", []) if exc.response is not None else []
            if errors:
                title = errors[0].get("detail") or errors[0].get("title") or ""
        except ValueError:
            title = ""
        logger.warning(
            "GTmetrix HTTP %s: %s", code, title or "(no detail)", extra={"path": path}
        )
        message = f"GTmetrix error {code}" + (f": {title}" if title else "")
        # 4xx (except 429 rate limit) is a client error — not worth retrying.
        if code is not None and 400 <= code < 500 and code != 429:
            raise GTmetrixClientError(message, extra={"status_code": code})
        raise GTmetrixAPIError(message, extra={"status_code": code})
    except (requests.RequestException, ValueError) as exc:
        logger.warning("GTmetrix request failed", extra={"path": path, "error": str(exc)})
        raise GTmetrixAPIError(extra={"error": str(exc)})


def start_test(*, url: str) -> str:
    """Queue a GTmetrix test for ``url`` and return the test id."""
    payload = {"data": {"type": "test", "attributes": {"url": url}}}
    data = _request("POST", "tests", json=payload)
    test_id = data.get("data", {}).get("id")
    if not test_id:
        raise GTmetrixAPIError("GTmetrix did not return a test id.", extra={"response": data})
    return test_id


def get_test(*, test_id: str) -> dict:
    """Return the raw test resource JSON."""
    return _request("GET", f"tests/{test_id}")


def get_report(*, report_id: str) -> dict:
    """Return the raw report resource JSON."""
    return _request("GET", f"reports/{report_id}")


def _report_id_from_test(test_json: dict) -> str | None:
    data = test_json.get("data", {})
    # Preferred: an explicit report relationship/link once completed.
    rel = data.get("relationships", {}).get("report", {}).get("data") or {}
    if rel.get("id"):
        return rel["id"]
    report_link = data.get("links", {}).get("report")
    if report_link:
        return report_link.rstrip("/").rsplit("/", 1)[-1]
    return None


def parse_report(report_json: dict) -> dict:
    """Flatten a GTmetrix report resource into our model field schema."""
    data = report_json.get("data", {})
    attrs = data.get("attributes", {})
    parsed: dict = {}
    for api_key, field in REPORT_ATTR_TO_FIELD.items():
        parsed[field] = attrs.get(api_key)
    links = data.get("links", {})
    parsed["report_url"] = links.get("report_pdf") or attrs.get("report_url", "") or ""
    return parsed


def poll_and_fetch(*, test_id: str) -> dict:
    """Poll an existing test to completion and return parsed metrics.

    Separated from :func:`start_test` so callers can persist ``test_id`` first
    and, on retry, resume polling the *same* test instead of starting a new one
    (which would spend another GTmetrix API credit).

    Returns a dict with keys: ``test_id``, ``metrics`` (model fields), ``raw``.

    Raises:
        GTmetrixAPIError: API failure or the test errored.
        GTmetrixTimeoutError: the test did not complete within the budget.
    """
    deadline = time.monotonic() + settings.GTMETRIX_POLL_MAX_SECONDS
    interval = max(settings.GTMETRIX_POLL_INTERVAL, 0)

    while True:
        test_json = get_test(test_id=test_id)
        state = test_json.get("data", {}).get("attributes", {}).get("state")

        if state == TEST_STATE_COMPLETED:
            break
        if state == TEST_STATE_ERROR:
            error = test_json.get("data", {}).get("attributes", {}).get("error", "")
            raise GTmetrixAPIError("GTmetrix test errored.", extra={"error": error})
        if time.monotonic() >= deadline:
            raise GTmetrixTimeoutError(extra={"test_id": test_id, "last_state": state})
        time.sleep(interval)

    report_id = _report_id_from_test(test_json) or test_id
    report_json = get_report(report_id=report_id)
    return {"test_id": test_id, "metrics": parse_report(report_json), "raw": report_json}


def run_gtmetrix_test(*, url: str) -> dict:
    """Convenience wrapper: start a test then poll it to completion."""
    test_id = start_test(url=url)
    logger.info("GTmetrix test queued", extra={"test_id": test_id, "url": url})
    return poll_and_fetch(test_id=test_id)
