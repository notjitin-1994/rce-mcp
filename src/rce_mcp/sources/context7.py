"""Context7 source — search library/framework documentation via Context7 API.

Requires: CONTEXT7_API_KEY environment variable.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

CONTEXT7_API = "https://context7.com/api/v1"


class Context7Source:
    """Search Context7 for library documentation — requires API key."""

    name = "context7"

    def __init__(self, timeout: float | None = None) -> None:
        cfg = get_config()
        self._timeout = timeout or cfg.web_timeout
        self._api_key = cfg.context7_api_key
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self._api_key}" if self._api_key else "",
                "User-Agent": "RCE-MCP/1.0 (https://github.com/user/rce-mcp)",
            },
            timeout=self._timeout,
            follow_redirects=True,
        )

    @property
    def available(self) -> bool:
        return self._api_key is not None

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search Context7 documentation for *query*."""
        if not self._api_key:
            logger.debug("Context7 skipped: no API key configured")
            return []

        params = {"q": query, "limit": min(limit, 10)}
        try:
            resp = await self._client.get(
                f"{CONTEXT7_API}/search",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Context7 search failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("results", [])[:limit]:
            results.append(
                {
                    "title": item.get("title", "Untitled")[:300],
                    "snippet": item.get("content", "")[:500],
                    "url": item.get("url", ""),
                    "source": "context7",
                    "library": item.get("library", ""),
                    "version": item.get("version", ""),
                }
            )

        return results
