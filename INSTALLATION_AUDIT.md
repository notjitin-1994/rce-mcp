# Installation Audit

This document provides a comprehensive audit of RCE MCP's installation, dependencies, configuration, and security posture.

## Overview

| Item | Value |
|------|-------|
| Package | `rce-mcp` |
| Version | 0.2.0 |
| Python | >= 3.11 |
| License | MIT |
| Entry points | `rce-mcp`, `rce-setup` |

## Dependencies

### Core (Required)

| Package | Version | Purpose |
|---------|---------|---------|
| `mcp[cli]` | >= 1.0.0 | MCP SDK and CLI transport |
| `httpx` | >= 0.25.0 | Async HTTP client (all API calls) |
| `beautifulsoup4` | >= 4.12.0 | HTML parsing (fallback) |

### Optional — HHEM Scoring

| Package | Version | Purpose |
|---------|---------|---------|
| `transformers` | >= 4.44.0, < 5.0.0 | Model loading (HHEM) |
| `torch` | >= 2.0.0 | ML inference backend |
| `tokenizers` | >= 0.20.0 | Tokenization |
| `safetensors` | >= 0.4.0 | Safe model serialization |
| `sentencepiece` | >= 0.2.0 | Tokenizer backend |
| `regex` | >= 2024.0.0 | Extended regex |
| `numpy` | >= 1.26.0 | Numerical operations |

### Dev

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | latest | Test framework |
| `pytest-asyncio` | latest | Async test support |

## Entry Points

| Command | Module | Function | Purpose |
|---------|--------|----------|---------|
| `rce-mcp` | `rce_mcp.server` | `main()` | Start MCP server |
| `rce-setup` | `rce_mcp.setup` | `main()` | Interactive setup wizard |

## Security Audit

### ✅ No Hardcoded Secrets

All API keys are read exclusively from environment variables:

| Variable | Source | Status |
|----------|--------|--------|
| `GITHUB_TOKEN` | Environment | ✅ No defaults, no hardcoded values |
| `CONTEXT7_API_KEY` | Environment | ✅ No defaults, no hardcoded values |
| `STACKEXCHANGE_KEY` | Environment | ✅ No defaults, no hardcoded values |
| `RCE_TRANSPORT` | Environment | ✅ Default is safe (`stdio`) |
| `RCE_LOCAL_DIR` | Environment | ✅ Default is `~` (user home) |

### ✅ No Network Exposure

- Default transport is `stdio` (stdin/stdout) — no network listener
- `streamable-http` mode must be explicitly enabled via `RCE_TRANSPORT`
- No incoming ports, no open sockets in default mode

### ✅ No Telemetry

- No analytics, tracking, or phone-home behavior
- No usage data collection
- No external connections except to configured knowledge source APIs

### ✅ Minimal Permissions

- Only reads environment variables (no writes)
- Local source only reads files within `RCE_LOCAL_DIR`
- File reads are capped at 1 MB
- Directory scanning is capped at 500 files
- No file writes anywhere

### ✅ Safe Defaults

- CPU-only for HHEM (no GPU auto-detection)
- Rate-limiting friendly (delays between API calls)
- Graceful degradation (sources fail silently, others continue)
- Local source skips `.git`, `node_modules`, `.venv`, etc.

## Source Connectivity

| Source | Endpoint | Auth Required | Timeout |
|--------|----------|---------------|---------|
| Wikipedia | `en.wikipedia.org/w/api.php` | No | 15s |
| Wikidata | `www.wikidata.org/w/api.php` | No | 15s |
| DuckDuckGo | `html.duckduckgo.com/html/` | No | 15s |
| arXiv | `export.arxiv.org/api/query` | No | 15s |
| Local | Filesystem | No | N/A |
| GitHub | `api.github.com` | `GITHUB_TOKEN` | 15s |
| Context7 | `context7.com/api/v1` | `CONTEXT7_API_KEY` | 15s |
| Stack Exchange | `api.stackexchange.com/2.3` | Optional key | 15s |

## File Structure

```
rce-mcp/
├── pyproject.toml              # Package config, deps, entry points
├── README.md                   # Documentation
├── API_KEYS.md                 # API key setup guide
├── STACKEXCHANGE_SETUP.md      # Stack Exchange detailed setup
├── INSTALLATION_AUDIT.md       # This file
├── LICENSE                     # MIT license
├── src/
│   └── rce_mcp/
│       ├── __init__.py         # Version metadata
│       ├── config.py           # Centralized config (env vars only)
│       ├── server.py           # MCP server, tool definitions
│       ├── setup.py            # Interactive setup wizard
│       ├── utils.py            # Text processing utilities
│       ├── hhem.py             # HHEM hallucination scoring
│       └── sources/
│           ├── __init__.py     # Source registry (8 sources)
│           ├── wikipedia.py    # Wikipedia API
│           ├── wikidata.py     # Wikidata API
│           ├── web.py          # DuckDuckGo search
│           ├── arxiv.py        # arXiv paper search
│           ├── local.py        # Filesystem search
│           ├── github.py       # GitHub code/issue search
│           ├── context7.py     # Context7 docs search
│           └── stackexchange.py # Stack Exchange Q&A
└── tests/
    └── ...                     # Test files (to be added)
```

## Installation Verification

After installing, run these checks:

```bash
# 1. Verify package installed
python -c "import rce_mcp; print(f'RCE MCP v{rce_mcp.__version__}')"

# 2. Check entry points
which rce-mcp
which rce-setup

# 3. Run connectivity check
rce-setup --check

# 4. Verify HHEM availability (optional)
python -c "from rce_mcp.hhem import is_hhem_available; print(f'HHEM: {is_hhem_available()}')"

# 5. Run tests
pytest
```

## Known Limitations

1. **DuckDuckGo scraping** — relies on HTML structure that may change. Not an official API.
2. **HHEM model size** — ~1.8 GB download on first use. CPU-only inference.
3. **GitHub rate limits** — 5,000 req/hr with token. Code search requires 2+ char queries.
4. **Stack Exchange** — 300 req/day without key. Search quality varies by site.
5. **Local source** — simple substring matching, no full-text search index.

## Checklist for New Installations

- [ ] Python 3.11+ installed
- [ ] `uv` or `pip` available
- [ ] Core dependencies installed (`mcp[cli] httpx beautifulsoup4`)
- [ ] Server starts: `rce-mcp` or `python -m rce_mcp.server`
- [ ] Free sources work (Wikipedia, Wikidata, Web, arXiv)
- [ ] (Optional) HHEM installed and model loads
- [ ] (Optional) `GITHUB_TOKEN` set and verified
- [ ] (Optional) `CONTEXT7_API_KEY` set and verified
- [ ] (Optional) `STACKEXCHANGE_KEY` set and verified
- [ ] MCP client configured and can reach server
- [ ] `rce_status()` returns expected sources
