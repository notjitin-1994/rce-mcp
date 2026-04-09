"""RCE MCP Server — Reality Check Engine for anti-hallucination verification.

Exposes tools for multi-source fact verification, hallucination scoring,
source validation, and scoped search via the Model Context Protocol.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from . import __version__
from .config import get_config
from .hhem import hhem_status, is_hhem_available, score_hallucination
from .sources import (
    ArxivSource,
    BaseSource,
    Context7Source,
    GithubSource,
    LocalSource,
    StackExchangeSource,
    WebSource,
    WikidataSource,
    WikipediaSource,
)
from .utils import confidence_from_sources, strip_html, truncate

logger = logging.getLogger("rce-mcp")

# ── MCP Server ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    "RCE MCP",
    instructions=(
        "Reality Check Engine — verify facts, score hallucinations, and validate "
        "sources before including claims in responses. Call `reality_check` for "
        "any factual claim. Call `reality_verify` to score text against a source."
    ),
)


# ── Source instances (lazy-initialized) ──────────────────────────────────────

_sources: dict[str, Any] | None = None


def _build_sources() -> dict[str, BaseSource]:
    """Build all available source backends from config."""
    cfg = get_config()
    return {
        "wikipedia": WikipediaSource(),
        "wikidata": WikidataSource(),
        "web": WebSource(),
        "local": LocalSource(),
        "arxiv": ArxivSource(),
        "github": GithubSource(),
        "context7": Context7Source(),
        "stackexchange": StackExchangeSource(),
    }


async def _get_sources() -> dict[str, Any]:
    """Lazy-initialize all source backends."""
    global _sources
    if _sources is None:
        _sources = _build_sources()
    return _sources


async def _close_sources() -> None:
    """Shut down source clients."""
    global _sources
    if _sources:
        for src in _sources.values():
            try:
                await src.close()
            except Exception:
                pass
        _sources = None


# ── Tool: reality_check ─────────────────────────────────────────────────────

@mcp.tool()
async def reality_check(
    query: str,
    sources: Optional[list[str]] = None,
) -> str:
    """Verify a factual claim or question against multiple knowledge sources.

    Searches across multiple knowledge sources — Wikipedia, Wikidata, ArXiv,
    GitHub, Stack Exchange, Context7, web, and local filesystem — to find
    evidence supporting or contradicting the claim. Returns verified facts
    with confidence scores and source URLs.

    Args:
        query: The factual claim or question to verify (e.g. "Python 3.12 was released in October 2023").
        sources: Which sources to query. Options: ["wikipedia", "wikidata", "web", "arxiv", "github",
                 "context7", "stackexchange", "local"].
                 Defaults to ["wikipedia", "wikidata"].

    Returns:
        JSON with verified facts, confidence score, and source URLs.
    """
    if sources is None:
        sources = ["wikipedia", "wikidata"]

    src_map = await _get_sources()
    all_results: list[dict[str, Any]] = []
    errors: list[str] = []
    auth_warnings: list[str] = []

    tasks = []
    source_names = []
    for s in sources:
        if s in src_map:
            src = src_map[s]
            # Check if source is available (has required auth configured)
            if hasattr(src, "available") and not src.available:
                auth_warnings.append(f"{s}: not configured (missing API key or credentials)")
                continue
            tasks.append(src.search(query, limit=3))
            source_names.append(s)

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for name, result in zip(source_names, results):
            if isinstance(result, Exception):
                err_msg = str(result)
                errors.append(f"{name}: {err_msg}")
                logger.warning("Source %s failed: %s", name, result)
                # Detect auth-specific errors (401/403) and surface them
                if any(code in err_msg for code in ("401", "403", "Unauthorized", "Forbidden", "authentication")):
                    auth_warnings.append(f"{name}: authentication error — {err_msg}")
            elif isinstance(result, list):
                all_results.extend(result)

    confidence = confidence_from_sources(all_results, query=query)

    response: dict[str, Any] = {
        "query": query,
        "verified": confidence >= 0.3,
        "confidence": confidence,
        "results_count": len(all_results),
        "results": all_results,
    }
    if errors:
        response["errors"] = errors
    if auth_warnings:
        response["auth_warnings"] = auth_warnings

    return json.dumps(response, ensure_ascii=False, indent=2)


# ── Tool: reality_verify ────────────────────────────────────────────────────

@mcp.tool()
async def reality_verify(
    text: str,
    source_text: str,
) -> str:
    """Score whether *text* is factually consistent with *source_text*.

    Uses HHEM-2.1-Open (Vectara's hallucination evaluation model) to produce
    a consistency score between 0.0 (fully hallucinated) and 1.0 (fully supported).

    Requires: pip install rce-mcp[hhem]

    Args:
        text: The generated text / hypothesis to evaluate (e.g. an LLM's answer).
        source_text: The reference text / premise (e.g. retrieved documents).

    Returns:
        JSON with score (0.0-1.0), label, and availability status.
    """
    result = await score_hallucination(source_text, text)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Tool: reality_source ────────────────────────────────────────────────────

@mcp.tool()
async def reality_source(
    url_or_path: str,
) -> str:
    """Fetch and validate a specific source (URL or local file path).

    For URLs: fetches the page and extracts readable text.
    For file paths: reads the file content.
    Returns content snippet and metadata.

    Args:
        url_or_path: An HTTP(S) URL or a local file path.

    Returns:
        JSON with content snippet, metadata, and validation status.
    """
    if url_or_path.startswith(("http://", "https://")):
        return await _fetch_url(url_or_path)
    else:
        return await _read_file(url_or_path)


async def _fetch_url(url: str) -> str:
    """Fetch a URL and extract readable text."""
    import httpx

    headers = {"User-Agent": "RCE-MCP/1.0 (https://github.com/notjitin-1994/rce-mcp)"}
    try:
        async with httpx.AsyncClient(
            headers=headers, timeout=15.0, follow_redirects=True
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "unknown")
        raw_text = resp.text
        clean_text = strip_html(raw_text) if "text/html" in content_type else raw_text

        return json.dumps(
            {
                "valid": True,
                "url": url,
                "content_type": content_type,
                "content_length": len(raw_text),
                "snippet": truncate(clean_text, 2000),
                "status": "ok",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps(
            {
                "valid": False,
                "url": url,
                "error": str(exc),
                "status": "fetch_failed",
            },
            ensure_ascii=False,
            indent=2,
        )


async def _read_file(path: str) -> str:
    """Read a local file."""
    from pathlib import Path

    fpath = Path(path).expanduser().resolve()
    try:
        if not fpath.is_file():
            return json.dumps(
                {"valid": False, "path": str(fpath), "error": "File not found", "status": "not_found"},
                indent=2,
            )
        if fpath.stat().st_size > 1_048_576:  # 1 MB
            return json.dumps(
                {"valid": False, "path": str(fpath), "error": "File too large (max 1 MB)", "status": "too_large"},
                indent=2,
            )
        content = fpath.read_text(encoding="utf-8", errors="ignore")
        return json.dumps(
            {
                "valid": True,
                "path": str(fpath),
                "content_length": len(content),
                "snippet": truncate(content, 2000),
                "status": "ok",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps(
            {"valid": False, "path": str(fpath), "error": str(exc), "status": "read_failed"},
            ensure_ascii=False,
            indent=2,
        )


# ── Tool: reality_search ────────────────────────────────────────────────────

@mcp.tool()
async def reality_search(
    query: str,
    scope: str = "wikipedia",
) -> str:
    """Search a specific knowledge source for information.

    Args:
        query: The search query.
        scope: Which source to search. Options: "web", "wikipedia", "wikidata", "local",
               "arxiv", "github", "context7", "stackexchange".

    Returns:
        JSON with search results including titles, snippets, and URLs.
    """
    valid_scopes = {
        "web", "wikipedia", "wikidata", "local",
        "arxiv", "github", "context7", "stackexchange",
    }
    if scope not in valid_scopes:
        return json.dumps(
            {
                "error": f"Invalid scope '{scope}'. Must be one of: {', '.join(sorted(valid_scopes))}",
                "results": [],
            },
            indent=2,
        )

    src_map = await _get_sources()
    source = src_map.get(scope)
    if source is None:
        return json.dumps(
            {"error": f"Source '{scope}' not available", "results": []},
            indent=2,
        )

    try:
        results = await source.search(query, limit=5)
        return json.dumps(
            {"query": query, "scope": scope, "results_count": len(results), "results": results},
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps(
            {"query": query, "scope": scope, "error": str(exc), "results": []},
            indent=2,
        )


# ── Tool: rce_status ────────────────────────────────────────────────────────

@mcp.tool()
async def rce_status() -> str:
    """Get RCE MCP server status: version, available sources, HHEM model status.

    Returns:
        JSON with server status information.
    """
    cfg = get_config()

    # Build source availability list
    all_sources = _build_sources()
    source_status = []
    for name, src in all_sources.items():
        available = True
        if hasattr(src, "available"):
            available = src.available
        source_status.append({"name": name, "available": available})

    return json.dumps(
        {
            "name": "RCE MCP",
            "version": __version__,
            "description": "Reality Check Engine — Anti-hallucination verification server",
            "sources": source_status,
            "hhem": hhem_status(),
            "transport": cfg.transport,
        },
        indent=2,
    )


# ── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    """Run the RCE MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    logger.info("RCE MCP v%s starting...", __version__)

    cfg = get_config()
    logger.info("Transport: %s", cfg.transport)

    try:
        if cfg.transport == "streamable-http":
            mcp.run(transport="streamable-http")
        else:
            mcp.run(transport="stdio")
    finally:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_close_sources())
            else:
                loop.run_until_complete(_close_sources())
        except Exception:
            pass


if __name__ == "__main__":
    main()
