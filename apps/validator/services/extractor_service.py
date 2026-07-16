"""Extract structured data (JSON-LD, Microdata, RDFa) from raw HTML.

Pure parsing — no network, no validation. Each extractor returns a flat list of
plain dicts, one per top-level structured-data object, in a normalised shape
(``@type`` as a short type name, properties keyed by name). Nested objects are
represented as nested dicts.
"""
from __future__ import annotations

import json

from bs4 import BeautifulSoup, Tag

from apps.validator.constants import PARSE_ERROR_KEY

# Microdata: tag -> attribute that carries the property value.
_MICRODATA_VALUE_ATTRS = {
    "meta": "content",
    "a": "href",
    "link": "href",
    "area": "href",
    "img": "src",
    "audio": "src",
    "video": "src",
    "source": "src",
    "iframe": "src",
    "embed": "src",
    "track": "src",
    "object": "data",
    "data": "value",
    "time": "datetime",
}


def _soup(html_content: str) -> BeautifulSoup:
    return BeautifulSoup(html_content or "", "lxml")


def _short_type(itemtype: str | None) -> str | None:
    """Reduce ``https://schema.org/Product`` (or a space-separated list) to ``Product``."""
    if not itemtype:
        return None
    first = itemtype.split()[0] if itemtype.split() else itemtype
    return first.rstrip("/").split("/")[-1].split("#")[-1] or None


def _assign(obj: dict, name: str, value) -> None:
    """Set ``obj[name] = value``; if the key repeats, collect into a list."""
    if name in obj:
        existing = obj[name]
        if isinstance(existing, list):
            existing.append(value)
        else:
            obj[name] = [existing, value]
    else:
        obj[name] = value


# --------------------------------------------------------------------------- #
# JSON-LD                                                                     #
# --------------------------------------------------------------------------- #
def _flatten_json_ld(parsed) -> list[dict]:
    """Flatten a parsed JSON-LD value into a list of object dicts.

    Handles a single object, a top-level array of objects, and ``@graph``
    containers (recursively).
    """
    out: list[dict] = []
    if isinstance(parsed, list):
        for entry in parsed:
            out.extend(_flatten_json_ld(entry))
    elif isinstance(parsed, dict):
        graph = parsed.get("@graph")
        if isinstance(graph, list):
            for entry in graph:
                out.extend(_flatten_json_ld(entry))
            # A node carrying both @graph and its own @type is rare; keep the
            # node too so nothing is silently dropped.
            if parsed.get("@type"):
                node = {k: v for k, v in parsed.items() if k != "@graph"}
                out.append(node)
        else:
            out.append(parsed)
    return out


def extract_json_ld(*, html_content: str) -> list[dict]:
    """Return every JSON-LD object from ``<script type="application/ld+json">``.

    Single objects, arrays and ``@graph`` containers are all flattened to one
    object per list entry. A block whose JSON does not parse yields a single
    marker dict ``{"@parseError": "<reason>"}`` so the failure is not lost.
    """
    items: list[dict] = []
    for script in _soup(html_content).find_all("script", attrs={"type": "application/ld+json"}):
        raw = (script.string or script.get_text() or "").strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            items.append({PARSE_ERROR_KEY: str(exc)})
            continue
        items.extend(_flatten_json_ld(parsed))
    return items


# --------------------------------------------------------------------------- #
# Microdata                                                                   #
# --------------------------------------------------------------------------- #
def _nearest_scope(tag: Tag) -> Tag | None:
    """Return the closest ancestor element carrying ``itemscope`` (or None)."""
    parent = tag.parent
    while parent is not None and isinstance(parent, Tag):
        if parent.has_attr("itemscope"):
            return parent
        parent = parent.parent
    return None


def _microdata_value(tag: Tag):
    attr = _MICRODATA_VALUE_ATTRS.get(tag.name)
    if attr and tag.has_attr(attr):
        return (tag.get(attr) or "").strip()
    if tag.has_attr("content"):
        return (tag.get("content") or "").strip()
    return tag.get_text(strip=True)


def _parse_microdata_item(scope: Tag) -> dict:
    """Build a dict for one itemscope element and its direct properties."""
    obj: dict = {}
    type_name = _short_type(scope.get("itemtype"))
    if type_name:
        obj["@type"] = type_name

    for prop in scope.find_all(attrs={"itemprop": True}):
        # Only properties whose nearest itemscope ancestor is *this* scope.
        if _nearest_scope(prop) is not scope:
            continue
        names = (prop.get("itemprop") or "").split()
        value = _parse_microdata_item(prop) if prop.has_attr("itemscope") else _microdata_value(prop)
        for name in names:
            _assign(obj, name, value)
    return obj


def extract_microdata(*, html_content: str) -> list[dict]:
    """Return top-level Microdata items (elements with itemscope + itemtype)."""
    soup = _soup(html_content)
    items: list[dict] = []
    for scope in soup.find_all(attrs={"itemscope": True}):
        if _nearest_scope(scope) is not None:
            continue  # nested item; captured within its parent
        items.append(_parse_microdata_item(scope))
    return items


# --------------------------------------------------------------------------- #
# RDFa                                                                        #
# --------------------------------------------------------------------------- #
def _nearest_typeof(tag: Tag) -> Tag | None:
    parent = tag.parent
    while parent is not None and isinstance(parent, Tag):
        if parent.has_attr("typeof"):
            return parent
        parent = parent.parent
    return None


def _rdfa_value(tag: Tag):
    if tag.has_attr("content"):
        return (tag.get("content") or "").strip()
    for attr in ("resource", "href", "src"):
        if tag.has_attr(attr):
            return (tag.get(attr) or "").strip()
    if tag.name == "time" and tag.has_attr("datetime"):
        return (tag.get("datetime") or "").strip()
    return tag.get_text(strip=True)


def _parse_rdfa_item(scope: Tag) -> dict:
    obj: dict = {}
    type_name = _short_type(scope.get("typeof"))
    if type_name:
        obj["@type"] = type_name

    for prop in scope.find_all(attrs={"property": True}):
        if _nearest_typeof(prop) is not scope:
            continue
        names = (prop.get("property") or "").split()
        # An element that itself opens a new typeof is a nested object.
        value = _parse_rdfa_item(prop) if prop.has_attr("typeof") else _rdfa_value(prop)
        for name in names:
            _assign(obj, _short_type(name) or name, value)
    return obj


def extract_rdfa(*, html_content: str) -> list[dict]:
    """Return top-level RDFa items (elements with a ``typeof`` attribute)."""
    soup = _soup(html_content)
    items: list[dict] = []
    for scope in soup.find_all(attrs={"typeof": True}):
        if _nearest_typeof(scope) is not None:
            continue
        items.append(_parse_rdfa_item(scope))
    return items
