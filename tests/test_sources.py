"""Tests for RCE MCP sources."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from rce_mcp.sources.wikipedia import WikipediaSource
from rce_mcp.sources.wikidata import WikidataSource
from rce_mcp.sources.web import WebSource
from rce_mcp.sources.local import LocalSource


@pytest.mark.asyncio
async def test_wikipedia_search():
    src = WikipediaSource()
    try:
        results = await src.search("Eiffel Tower", limit=2)
        assert len(results) > 0
        assert results[0]["source"] == "wikipedia"
        assert "url" in results[0]
        assert results[0]["url"].startswith("https://en.wikipedia.org/")
    finally:
        await src.close()


@pytest.mark.asyncio
async def test_wikidata_search():
    src = WikidataSource()
    try:
        results = await src.search("Eiffel Tower", limit=2)
        assert len(results) > 0
        assert results[0]["source"] == "wikidata"
        assert "entity_id" in results[0]
    finally:
        await src.close()


@pytest.mark.asyncio
async def test_web_search():
    src = WebSource()
    try:
        results = await src.search("OpenAI", limit=3)
        assert len(results) > 0
        assert results[0]["source"] == "web"
        assert "url" in results[0]
        assert results[0]["url"].startswith("http")
    finally:
        await src.close()


@pytest.mark.asyncio
async def test_local_search():
    src = LocalSource(base_dir="/etc")
    results = await src.search("hostname", limit=2)
    # May or may not find something depending on system
    assert isinstance(results, list)
    for r in results:
        assert r["source"] == "local"


@pytest.mark.asyncio
async def test_local_search_missing_dir():
    src = LocalSource(base_dir="/nonexistent/path/that/does/not/exist")
    results = await src.search("test", limit=2)
    assert results == []


@pytest.mark.asyncio
async def test_web_search_empty():
    src = WebSource()
    try:
        results = await src.search("", limit=3)
        # DDG may return results even for empty queries
        assert isinstance(results, list)
    finally:
        await src.close()
