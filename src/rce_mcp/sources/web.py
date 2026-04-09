"""Web search source — DuckDuckGo HTML scraping (no API key needed)."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import unquote

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

DDG_URL = "https://html.duckduckgo.com/html/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
}


class WebSource(BaseSource):
    """DuckDuckGo web search — no API key required."""

    name = "web"

    def __init__(self, timeout: float | None = None) -> None:
        cfg = get_config()
        self._timeout = timeout or cfg.web_timeout
        self._client = httpx.AsyncClient(
            headers=HEADERS, timeout=self._timeout, follow_redirects=True
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search DuckDuckGo and parse HTML results."""
        try:
            resp = await self._client.get(DDG_URL, params={"q": query})
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("DuckDuckGo search failed: %s", exc)
            return []

        return self._parse_ddg_html(resp.text, limit)

    @staticmethod
    def _parse_ddg_html(html: str, limit: int = 5) -> list[dict[str, Any]]:
        """Parse DDG HTML using regex."""
        results: list[dict[str, Any]] = []

        link_pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]*)"',
            re.DOTALL,
        )
        links = link_pattern.findall(html)

        snippet_pattern = re.compile(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        snippets = snippet_pattern.findall(html)

        title_pattern = re.compile(
            r'class="result__a"[^>]*>(.*?)</a>',
            re.DOTALL,
        )
        titles = title_pattern.findall(html)

        def clean(text: str) -> str:
            return re.sub(r"<[^>]+>", "", text).strip()

        for i, link in enumerate(links[:limit]):
            match = re.search(r"uddg=([^&]+)", link)
            if match:
                url = unquote(match.group(1))
            else:
                url = link
                if url.startswith("//"):
                    url = "https:" + url

            title = clean(titles[i]) if i < len(titles) else url
            snippet = clean(snippets[i]) if i < len(snippets) else ""

            if url:
                results.append(
                    {
                        "title": title[:200],
                        "snippet": snippet[:500],
                        "url": url,
                        "source": "web",
                    }
                )

        return results
