"""GitHub source — search code, issues, and repos via GitHub REST API.

Requires: GITHUB_TOKEN environment variable.
Uses unauthenticated search with token for higher rate limits.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import get_config

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GithubSource:
    """Search GitHub — code, issues, repositories — requires personal access token."""

    name = "github"

    def __init__(self, timeout: float | None = None) -> None:
        cfg = get_config()
        self._timeout = timeout or cfg.web_timeout
        self._token = cfg.github_token
        self._headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "RCE-MCP/1.0 (https://github.com/notjitin-1994/rce-mcp)",
        }
        if self._token:
            self._headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.AsyncClient(
            headers=self._headers,
            timeout=self._timeout,
            follow_redirects=True,
        )

    @property
    def available(self) -> bool:
        return self._token is not None

    async def close(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search GitHub (code, issues, repos) for *query*.

        Tries code search first, falls back to issues if no results.
        """
        if not self._token:
            logger.debug("GitHub skipped: no token configured")
            return []

        results = await self._search_code(query, limit)
        if not results:
            results = await self._search_issues(query, limit)
        return results

    async def _search_code(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Search GitHub code."""
        params = {"q": query, "per_page": min(limit, 10)}
        try:
            resp = await self._client.get(
                f"{GITHUB_API}/search/code",
                params=params,
            )
            if resp.status_code == 422:
                # Code search requires at least 2 characters
                return []
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("GitHub code search failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("items", [])[:limit]:
            results.append(
                {
                    "title": item.get("name", "unknown"),
                    "snippet": self._truncate(item.get("text_matches", [{}])[0].get("fragment", ""), 500),
                    "url": item.get("html_url", ""),
                    "source": "github",
                    "repo": item.get("repository", {}).get("full_name", ""),
                    "path": item.get("path", ""),
                }
            )
        return results

    async def _search_issues(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Search GitHub issues and PRs."""
        params = {"q": query, "per_page": min(limit, 10)}
        try:
            resp = await self._client.get(
                f"{GITHUB_API}/search/issues",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("GitHub issue search failed: %s", exc)
            return []

        results: list[dict[str, Any]] = []
        for item in data.get("items", [])[:limit]:
            results.append(
                {
                    "title": item.get("title", "unknown")[:300],
                    "snippet": item.get("body", "")[:500].replace("\n", " "),
                    "url": item.get("html_url", ""),
                    "source": "github",
                    "repo": item.get("repository_url", "").split("/")[-1],
                    "type": "pull_request" if item.get("pull_request") else "issue",
                    "state": item.get("state", ""),
                }
            )
        return results

    @staticmethod
    def _truncate(text: str, max_chars: int = 500) -> str:
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1] + "…"
