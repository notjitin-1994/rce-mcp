"""Text extraction, HTML stripping, and shared utilities."""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import Optional

logger = logging.getLogger(__name__)


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML→plain-text extractor. No external deps needed for basics."""

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr"):
            self._pieces.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._pieces.append(data)

    def get_text(self) -> str:
        raw = "".join(self._pieces)
        # Collapse whitespace
        return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", raw)).strip()


def strip_html(html: str) -> str:
    """Strip HTML tags and return readable plain text."""
    extractor = _HTMLTextExtractor()
    try:
        extractor.feed(html)
        return extractor.get_text()
    except Exception:
        # Fallback: aggressive regex strip
        return re.sub(r"<[^>]+>", " ", html)


def truncate(text: str, max_chars: int = 2000) -> str:
    """Truncate text to max_chars, appending '…' if truncated."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "…"


def confidence_from_sources(results: list[dict], query: str = "") -> float:
    """Compute a rough confidence score from multiple source results.

    Uses a simple heuristic:
    - Each source that returns a result contributes 0.25
    - Multiple agreeing sources boost confidence
    - Query term overlap in result snippets provides an additional boost
    - Max 1.0

    This is intentionally simple — the HHEM model provides proper scoring.
    """
    if not results:
        return 0.0
    base = min(len(results) * 0.3, 0.7)
    # Bonus for multiple sources agreeing
    if len(results) >= 2:
        base += 0.15
    if len(results) >= 3:
        base += 0.15

    # Query-term overlap boost: check if query words appear in snippets
    if query:
        query_words = set(re.findall(r"\b\w{3,}\b", query.lower()))
        if query_words:
            match_count = 0
            for result in results:
                snippet = result.get("snippet", "").lower()
                title = result.get("title", "").lower()
                text = f"{title} {snippet}"
                if any(word in text for word in query_words):
                    match_count += 1
            # Boost up to +0.2 based on fraction of results matching query terms
            overlap_ratio = match_count / len(results)
            base += 0.2 * overlap_ratio

    return min(round(base, 2), 1.0)
