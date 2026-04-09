# RCE-MCP — Vision Document

> **Reality Check Engine** — Anti-hallucination verification server for MCP.
> This is the single source of truth for what RCE-MCP is, what it should do, and how it works.
> Rebuild from this document.

---

## What It Is

RCE-MCP is a **Model Context Protocol (MCP) server** that AI agents call before including factual claims in their responses. It searches multiple knowledge sources and verifies whether a claim is supported, contradicted, or unverifiable.

**Core promise:** "Every factual claim gets verified against real sources before it leaves the agent's context."

---

## MCP Tools Exposed

### 1. `reality_check(query, sources)` — Primary tool

Verify a factual claim against multiple knowledge sources.

**Input:**
- `query`: The claim to verify (e.g. "Python 3.12 was released in October 2023")
- `sources`: Which sources to query (defaults to `["wikipedia", "wikidata"]`)

**Output (JSON):**
```json
{
  "query": "...",
  "verified": true/false,
  "confidence": 0.0-1.0,
  "confidence_method": "hhem" | "keyword" | "heuristic",
  "results_count": 3,
  "results": [
    {
      "title": "...",
      "snippet": "...",
      "url": "https://...",
      "source": "wikipedia"
    }
  ],
  "verification_scores": {          // only when HHEM available
    "overall": 0.91,
    "label": "consistent",
    "sources_checked": 3
  }
}
```

**Verification methods (in priority order):**
1. **HHEM** — Uses HHEM-2.1-Open NLI model to score claim vs retrieved snippets. Most accurate. Requires `pip install rce-mcp[hhem]` (~2GB PyTorch).
2. **Keyword** — Checks if claim terms appear in source snippets. Weak but no extra deps.
3. **Heuristic** — Confidence based on result count/quality only. Basically useless for contradiction detection.

### 2. `reality_verify(text, source_text)` — NLI scoring

Score whether generated text is consistent with a reference source using HHEM.

**Input:**
- `text`: The hypothesis (e.g. an LLM's answer)
- `source_text`: The reference/ground truth

**Output:**
```json
{
  "score": 0.91,
  "label": "consistent",
  "available": true
}
```

### 3. `reality_source(url_or_path)` — Source validation

Fetch a URL or read a local file. Extracts readable text from HTML.

### 4. `reality_search(query, scope)` — Scoped search

Search a single source. Scopes: `web`, `wikipedia`, `wikidata`, `local`, `arxiv`, `github`, `context7`, `stackexchange`.

### 5. `rce_status()` — Server status

Returns version, available sources, HHEM model status, transport mode.

---

## Knowledge Sources

| Source | API | Auth Required | Status in v0.2.0 | Notes |
|--------|-----|---------------|-------------------|-------|
| **Wikipedia** | MediaWiki API | No | ✅ Working | Primary workhorse. Does 90%+ of verification. |
| **Wikidata** | wbsearchentities | No | ⚠️ Fragile | Only works with entity names, not natural language. Needs cascading fallback (try full query → individual proper nouns → original). |
| **Web** | DuckDuckGo HTML scraping | No | ❌ Broken | Rate-limits immediately in automated contexts. Consider Brave Search API or SerpAPI replacement. |
| **ArXiv** | ArXiv API | No | ✅ Working | Good for academic/scientific claims. |
| **Local** | Filesystem (os.walk) | No | ✅ Working | Searches local files. Wrap in `asyncio.to_thread`. |
| **GitHub** | GitHub REST API v3 | Yes (token) | ⚠️ No key | Auth prefix: `token` (GitHub convention, not `Bearer`). |
| **Context7** | Context7 API | Yes (key) | ⚠️ No key | For library/framework documentation. |
| **Stack Exchange** | SE API v2.1 | Optional (key) | ⚠️ No key | **Must use `filter=withbody`** parameter — without it, API strips answer body content. Key gives higher rate limits (no key = 300 req/day). |

---

## API Keys & Configuration

### Environment Variables

| Variable | Source | Required | Notes |
|----------|--------|----------|-------|
| `GITHUB_TOKEN` | GitHub PAT | For GitHub source | Prefix: `token` (not `Bearer`). Scopes needed: `repo`, `read:org` |
| `CONTEXT7_API_KEY` | Context7 | For Context7 source | Register at context7.com |
| `STACKEXCHANGE_KEY` | Stack Exchange | Optional (higher rate limit) | No key = 300 req/day. Get from stackapps.com |
| `RCE_TRANSPORT` | — | No | `stdio` (default) or `streamable-http` |
| `RCE_LOCAL_DIR` | — | No | Base dir for local search (default: `~`) |
| `RCE_WEB_TIMEOUT` | — | No | HTTP timeout in seconds (default: `15`) |
| `RCE_ARXIV_MAX_RESULTS` | — | No | Max arXiv results (default: `5`) |

### Current API Key Status (as of 2026-04-09)

```
GITHUB_TOKEN:       NOT CONFIGURED
CONTEXT7_API_KEY:   NOT CONFIGURED
STACKEXCHANGE_KEY:  NOT CONFIGURED
```

**None of the API keys are currently set.** Only the no-auth sources (Wikipedia, Wikidata, ArXiv, Local) work out of the box.

---

## HHEM (Hallucination Detection Model)

**Model:** HHEM-2.1-Open by Vectara
**Purpose:** Natural Language Inference — scores whether a claim is consistent with source text
**Score range:** 0.0 (fully hallucinated) → 1.0 (fully supported)
**Install:** `pip install rce-mcp[hhem]` (~2GB PyTorch + transformers)

### Critical Implementation Details

1. **Must run in thread pool** — `model.predict()` is synchronous CPU-bound. Use `asyncio.to_thread()` or it blocks the event loop.
2. **Serialize inference** — Use `asyncio.Semaphore(1)` to prevent concurrent inference calls (model is not thread-safe).
3. **Lazy load with lock** — Use `asyncio.Lock` for thread-safe lazy model initialization.
4. **Timeout** — Add 30s timeout to prevent indefinite hangs.
5. **Eval results:** 90% accuracy at threshold 0.5 (consistent avg=0.911, hallucinated avg=0.183, 3/15 false negatives on subtle paraphrases).

---

## Known Issues from v0.2.0 Eval

These must be fixed in the rebuild:

### 🔴 Critical

1. **False claim detection doesn't work without HHEM** — Keyword heuristic can't catch "Bitcoin was created by Vitalik Buterin" because both terms appear in source text. The tool returns `verified: true` for false claims. **This is the #1 problem.**

2. **No caching** — Same query hits Wikipedia every single time. Add in-memory or disk cache with TTL.

3. **Web source (DDG) is non-functional** — Rate-limits immediately. Replace with Brave Search API or make it gracefully degrade.

### 🟡 Important

4. **Confidence is misleading** — `confidence_method: "heuristic"` just means "we found results." Rename or remove until real verification exists.

5. **No result deduplication** — Same Wikipedia article can appear multiple times from different queries.

6. **Resource leaks** — httpx clients must be properly closed on shutdown.

### 🟢 Nice to Have

7. **Batch verification** — Verify multiple claims in one call.
8. **Configurable HHEM threshold** — Allow users to set their own consistency threshold.
9. **Source priority/weighting** — Wikipedia > ArXiv > Wikidata > Web, etc.
10. **Streaming results** — Return sources as they arrive, not all at once.

---

## Architecture Notes

- **Package name:** `rce-mcp` (PyPI)
- **Import name:** `rce_mcp`
- **Python:** >=3.11
- **Build:** hatchling
- **Entry points:** `rce-mcp` (server), `rce-setup` (config wizard)
- **MCP framework:** `mcp[cli]>=1.0.0` (FastMCP)
- **HTTP client:** httpx (async)
- **Transport:** stdio (default), streamable-http
- **Git:** `git@github.com:notjitin-1994/rce-mcp.git`
- **License:** MIT

---

## What "Done" Looks Like

A normal user installs `pip install rce-mcp`, adds it to their Claude Code / Cursor config, and every factual claim in their agent's responses is automatically verified against real sources with meaningful confidence scores. False claims are caught and flagged. The tool is fast (<5s for single-source), reliable, and doesn't require a GPU or 2GB of PyTorch to work.

---

*Document created: 2026-04-09*
*Author: Astra (from v0.2.0 post-mortem)*
