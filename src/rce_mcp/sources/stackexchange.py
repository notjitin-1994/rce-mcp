"""Stack Exchange source — search programming Q&A via Stack Exchange API.

Requires: STACKEXCHANGE_KEY environment variable (higher rate limits).
Works without a key but with stricter rate limits.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

SE_API = "https://api.stackexchange.com/2.3"


class StackExchangeSource:
    """Search Stack Exchange sites (default: Stack Overflow) for Q&A."""

    name = "stackexchange"

    def __init__(self, timeout: float | None = None, site: str = "stackoverflow") -> None:
        cfg = get_config()
        self._timeout = timeout or cfg.web_timeout
        self._key = cfg.stackexchange_key
        self._site = site
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "RCE-MCP/1.0 (https://github.com/notjitin-1994/rce-mcp)"},
            timeout=self._timeout,
            follow_redirects=True,
        )

    @property
    def available(self) -> bool:
        return True  # Works without key, just lower rate limits

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search Stack Exchange for questions matching *query*."""
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": query,
            "site": self._site,
            "accepted": True,
            "answers": 1,
            "pagesize": min(limit, 10),
        }
        if self._key:
            params["key"] = self._key

        try:
            resp = await self._client.get(
                f"{SE_API}/search/advanced",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Stack Exchange search failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("items", [])[:limit]:
            # Strip HTML tags from body
            body = _strip_html(item.get("body", ""))

            results.append(
                {
                    "title": item.get("title", "unknown")[:300],
                    "snippet": body[:500],
                    "url": item.get("link", ""),
                    "source": "stackexchange",
                    "site": self._site,
                    "tags": item.get("tags", []),
                    "score": item.get("score", 0),
                    "answer_count": item.get("answer_count", 0),
                    "is_answered": item.get("is_answered", False),
                }
            )

        return results


def _strip_html(html: str) -> str:
    """Simple HTML tag stripping."""
    import re
    return re.sub(r"<[^>]+>", "", html).strip()
