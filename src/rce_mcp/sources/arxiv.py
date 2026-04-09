"""arXiv source — search academic papers via the arXiv API (free, no key)."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import quote

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

ARXIV_API = "https://export.arxiv.org/api/query"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivSource:
    """Search arXiv for academic papers — no API key required."""

    name = "arxiv"

    def __init__(self, timeout: float | None = None) -> None:
        cfg = get_config()
        self._timeout = timeout or cfg.web_timeout
        self._max_results = cfg.arxiv_max_results
        self._client = httpx.AsyncClient(
            headers={"User-Agent": "RCE-MCP/1.0 (https://github.com/notjitin-1994/rce-mcp)"},
            timeout=self._timeout,
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search arXiv for papers matching *query*."""
        limit = min(limit, self._max_results)
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
        try:
            resp = await self._client.get(ARXIV_API, params=params)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("arXiv search failed: %s", exc)
            return []

        return self._parse_atom(resp.text, limit)

    @staticmethod
    def _parse_atom(xml_text: str, limit: int) -> list[dict[str, Any]]:
        """Parse arXiv Atom XML response."""
        results: list[dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        for entry in root.findall("atom:entry", ATOM_NS)[:limit]:
            title_el = entry.find("atom:title", ATOM_NS)
            summary_el = entry.find("atom:summary", ATOM_NS)
            id_el = entry.find("atom:id", ATOM_NS)

            title = _clean_xml(title_el.text) if title_el is not None else "Unknown"
            summary = _clean_xml(summary_el.text) if summary_el is not None else ""
            arxiv_id = _extract_arxiv_id(id_el.text if id_el is not None else "")

            results.append(
                {
                    "title": title[:300],
                    "snippet": summary[:500].strip(),
                    "url": id_el.text if id_el is not None else f"https://arxiv.org/abs/{arxiv_id}",
                    "source": "arxiv",
                    "arxiv_id": arxiv_id,
                }
            )

        return results


def _clean_xml(text: str) -> str:
    """Collapse whitespace in XML text content."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_arxiv_id(url: str) -> str:
    """Extract arXiv ID from a URL or identifier string."""
    match = re.search(r"(\d{4}\.\d{4,5}(v\d+)?)", url)
    return match.group(1) if match else url.split("/")[-1]
