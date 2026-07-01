"""Pure utility helpers with no Django model dependencies."""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Return a canonical form of ``url`` for de-duplication.

    Lowercases the scheme/host, drops fragments, and removes a trailing slash
    from non-root paths so ``https://a.com/x`` and ``https://a.com/x/`` collapse.
    """
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))


def truncate(text: str, length: int = 200, suffix: str = "…") -> str:
    """Truncate ``text`` to ``length`` characters, appending ``suffix`` if cut."""
    text = (text or "").strip()
    if len(text) <= length:
        return text
    return text[: length - len(suffix)].rstrip() + suffix
