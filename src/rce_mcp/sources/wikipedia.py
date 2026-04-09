"""Wikipedia source — search and extract via MediaWiki API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "RCE-MCP/1.0 (https://github.com/notjitin-1994/rce-mcp)"}


class WikipediaSource(BaseSource):
    """Search Wikipedia and extract article summaries."""

    name = "wikipedia"

    def __init__(self, timeout: float | None = None) -> None:
        cfg = get_config()
        self._timeout = timeout or cfg.web_timeout
        self._client = httpx.AsyncClient(
            headers=HEADERS, timeout=self._timeout, follow_redirects=True
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        """Search Wikipedia for articles matching *query*."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": min(limit, 10),
            "utf8": 1,
        }
        try:
            resp = await self._client.get(WIKIPEDIA_API, params=params)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Wikipedia search failed: %s", exc)
            return []

        hits = data.get("query", {}).get("search", [])
        if not hits:
            return []

        # Fetch extracts for found page IDs
        page_ids = "|".join(str(h["pageid"]) for h in hits)
        extract_params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "pageids": page_ids,
            "format": "json",
        }
        try:
            resp2 = await self._client.get(WIKIPEDIA_API, params=extract_params)
            resp2.raise_for_status()
            pages = resp2.json().get("query", {}).get("pages", {})
        except Exception as exc:
            logger.warning("Wikipedia extract failed: %s", exc)
            pages = {}

        results: list[dict[str, Any]] = []
        for hit in hits:
            pid = str(hit["pageid"])
            page = pages.get(pid, {})
            title = hit.get("title", "")
            snippet = hit.get("snippet", "")
            clean_snippet = (
                snippet.replace("<span class=\"searchmatch\">", "")
                .replace("</span>", "")
            )
            extract = page.get("extract", "")
            results.append(
                {
                    "title": title,
                    "snippet": extract[:500] if extract else clean_snippet,
                    "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "source": "wikipedia",
                    "page_id": pid,
                }
            )
        return results

    async def get_article(self, title: str) -> dict[str, Any] | None:
        """Fetch a single Wikipedia article by title."""
        params = {
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": title,
            "format": "json",
        }
        try:
            resp = await self._client.get(WIKIPEDIA_API, params=params)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for _pid, page in pages.items():
                if "missing" not in page:
                    return {
                        "title": page.get("title", title),
                        "snippet": page.get("extract", "")[:1000],
                        "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        "source": "wikipedia",
                    }
        except Exception as exc:
            logger.warning("Wikipedia get_article failed: %s", exc)
        return None
