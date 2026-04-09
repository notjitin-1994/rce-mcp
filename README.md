# RCE MCP — Reality Check Engine

**Zero-hallucination verification for LLM agents.**

RCE MCP is a standalone Model Context Protocol server that verifies factual claims against multiple knowledge sources, scores text for hallucinations, and validates references — before they reach your users.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Why RCE MCP?

LLMs hallucinate. Existing solutions are either **post-hoc** (check after generation) or **single-source** (only Wikidata, only web search). RCE MCP is different:

- **Upstream verification** — verify facts *before* including them in responses
- **Multi-source RAG** — 8 knowledge sources (5 free, 3 optional with API keys)
- **HHEM scoring** — Vectara's open-source hallucination detection model (optional)
- **Zero-config core** — core functionality works without any paid service
- **Universal** — works with OpenClaw, Claude Code, Codex, Cursor, Windsurf, VS Code, any MCP client

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      RCE MCP Server                           │
│                    (FastMCP / stdio)                          │
│                                                              │
│  Tools:                                                      │
│  ├── reality_check(query, sources[])                         │
│  │   └── Parallel search → all configured sources            │
│  ├── reality_verify(text, source_text)                       │
│  │   └── HHEM-2.1-Open scoring (0.0–1.0)                    │
│  ├── reality_source(url_or_path)                             │
│  │   └── Fetch URL or read file                              │
│  ├── reality_search(query, scope)                            │
│  │   └── Scoped search across any source                     │
│  └── rce_status()                                            │
│      └── Version, sources, HHEM status                       │
│                                                              │
│  Verification Backends:                                      │
│  ├── Wikipedia (MediaWiki API)              [FREE]           │
│  ├── Wikidata (Wikidata API)                [FREE]           │
│  ├── DuckDuckGo (HTML scraping)             [FREE]           │
│  ├── arXiv (Atom API)                       [FREE]           │
│  ├── Local filesystem                      [FREE]           │
│  ├── GitHub (REST API)              [GITHUB_TOKEN]           │
│  ├── Context7 (API)              [CONTEXT7_API_KEY]          │
│  ├── Stack Exchange (API)        [STACKEXCHANGE_KEY]         │
│  └── HHEM-2.1-Open (local model)             [OPTIONAL]      │
└──────────────────────────────────────────────────────────────┘
```

## Knowledge Sources

| Source | Best For | API Key | Free Tier |
|--------|----------|---------|-----------|
| **Wikipedia** | General knowledge, dates, biographies | None | Unlimited |
| **Wikidata** | Structured facts, entity properties | None | Unlimited |
| **DuckDuckGo** | Current events, recent info, general web | None | Unlimited |
| **arXiv** | Academic papers, research, citations | None | Unlimited |
| **Local** | Codebase docs, personal notes, configs | None | Unlimited |
| **GitHub** | Code search, issues, repositories | `GITHUB_TOKEN` | 5,000 req/hr |
| **Context7** | Library/framework documentation | `CONTEXT7_API_KEY` | Varies |
| **Stack Exchange** | Programming Q&A (Stack Overflow, etc.) | `STACKEXCHANGE_KEY` | Higher limits |

## Tools Reference

### `reality_check(query, sources?)`

**Primary tool.** Verify a factual claim against multiple knowledge sources.

```json
// Input
{ "query": "Python 3.12 was released in October 2023" }

// Output
{
  "query": "Python 3.12 was released in October 2023",
  "verified": true,
  "confidence": 0.6,
  "results_count": 3,
  "results": [
    {
      "title": "Python 3.12",
      "snippet": "Python 3.12 was released on October 2, 2023...",
      "url": "https://en.wikipedia.org/wiki/Python_(programming_language)",
      "source": "wikipedia"
    }
  ]
}
```

### `reality_verify(text, source_text)`

Score whether generated text is consistent with source material using HHEM-2.1-Open.

```json
// Input
{ "text": "The capital of France is Paris", "source_text": "The capital of France is Berlin" }

// Output
{ "score": 0.011, "label": "hallucinated", "available": true, "error": null }
```

### `reality_source(url_or_path)`

Fetch and validate a URL or local file.

### `reality_search(query, scope)`

Search a specific source: `"web"`, `"wikipedia"`, `"wikidata"`, `"local"`, `"arxiv"`, `"github"`, `"context7"`, or `"stackexchange"`.

### `rce_status()`

Server health check — version, available sources, HHEM model status.

## Installation

### Option 1: uv (recommended)

```bash
git clone https://github.com/user/rce-mcp.git
cd rce-mcp
uv sync
uv run rce-mcp
```

### Option 2: pip

```bash
pip install mcp[cli] httpx beautifulsoup4
# For HHEM scoring (optional):
pip install transformers torch

# Run
python -m rce_mcp.server
```

### Option 3: Docker

```bash
docker build -t rce-mcp .
docker run -i --rm rce-mcp
```

### HHEM Scoring (Optional)

The hallucination scoring model requires PyTorch and Transformers:

```bash
# With pip
pip install rce-mcp[hhem]

# With uv
uv sync --extra hhem
```

The model (~1.8 GB) is downloaded from HuggingFace on first use and cached locally. It lazy-loads — server startup is not affected.

## API Key Setup

Three optional sources require API keys for access:

### Quick Setup (interactive)

```bash
python -m rce_mcp.setup
```

### Manual Setup

Set environment variables before starting the server:

```bash
# GitHub (for code search, issue lookup)
export GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"

# Context7 (for library documentation)
export CONTEXT7_API_KEY="YOUR_CONTEXT7_API_KEY_HERE"

# Stack Exchange (for programming Q&A)
export STACKEXCHANGE_KEY="YOUR_STACKEXCHANGE_KEY_HERE"
```

See [API_KEYS.md](API_KEYS.md) for detailed setup instructions for each key.

## Configuration

### OpenClaw

```bash
openclaw mcp set rce-mcp '{
  "command": "uv",
  "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"],
  "env": {
    "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN_HERE",
    "CONTEXT7_API_KEY": "YOUR_CONTEXT7_API_KEY_HERE",
    "STACKEXCHANGE_KEY": "YOUR_STACKEXCHANGE_KEY_HERE"
  }
}'
```

### Claude Code

```bash
claude mcp add rce-mcp -- \
  env GITHUB_TOKEN=YOUR_GITHUB_TOKEN_HERE \
  env CONTEXT7_API_KEY=YOUR_CONTEXT7_API_KEY_HERE \
  -- uv --directory /path/to/rce-mcp run rce-mcp
```

### Cursor / VS Code

Add to `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "rce-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"],
      "env": {
        "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN_HERE",
        "CONTEXT7_API_KEY": "YOUR_CONTEXT7_API_KEY_HERE",
        "STACKEXCHANGE_KEY": "YOUR_STACKEXCHANGE_KEY_HERE"
      }
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "rce-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"],
      "env": {
        "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN_HERE",
        "CONTEXT7_API_KEY": "YOUR_CONTEXT7_API_KEY_HERE",
        "STACKEXCHANGE_KEY": "YOUR_STACKEXCHANGE_KEY_HERE"
      }
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RCE_TRANSPORT` | `stdio` | Transport mode: `stdio` or `streamable-http` |
| `RCE_LOCAL_DIR` | `~` | Base directory for local filesystem search |
| `GITHUB_TOKEN` | *(none)* | GitHub Personal Access Token |
| `CONTEXT7_API_KEY` | *(none)* | Context7 API key |
| `STACKEXCHANGE_KEY` | *(none)* | Stack Exchange API key |
| `RCE_ARXIV_MAX_RESULTS` | `5` | Max results from arXiv search |
| `RCE_WEB_TIMEOUT` | `15` | HTTP timeout in seconds |

## How It Works

### Verification Pipeline

1. **Query received** — `reality_check("Python 3.12 release date")`
2. **Parallel search** — All configured sources queried concurrently
3. **Evidence collection** — Titles, snippets, URLs, entity claims gathered
4. **Confidence scoring** — Multiple sources agreeing → higher confidence
5. **Structured response** — JSON with facts, sources, and confidence level

### HHEM Scoring

Based on [Vectara's HHEM-2.1-Open](https://huggingface.co/vectara/hallucination_evaluation_model):

- Input: (premise, hypothesis) pairs
- Output: Score 0.0–1.0 where 1.0 = fully supported by source
- Detects "factual but hallucinated" — e.g., answer is true in world knowledge but contradicts the provided source
- Based on T5-base architecture, fine-tuned for NLI (Natural Language Inference)

### Source Priority

| Source | Best For | Latency | Offline |
|--------|----------|---------|---------|
| Wikipedia | General knowledge, dates, biographies | ~200ms | No |
| Wikidata | Structured facts, entity properties | ~300ms | No |
| Web (DDG) | Current events, recent information | ~1s | No |
| arXiv | Academic papers, research | ~500ms | No |
| Local | Codebase docs, personal notes, configs | ~50ms | Yes |
| GitHub | Code search, issues, repos | ~300ms | No |
| Context7 | Library documentation | ~400ms | No |
| Stack Exchange | Programming Q&A | ~300ms | No |
| HHEM | Scoring any text against a reference | ~100ms | Yes* |

\*After initial model download

## Comparison

| Feature | RCE MCP | Strawberry | Perf MCP | Fact Checker MCP |
|---------|---------|------------|----------|-----------------|
| Approach | Upstream RAG | Post-hoc KL divergence | Multi-channel verify | Wikidata-only |
| Sources | 8 (5 free + 3 optional) | Context only | Web + NLI | Wikidata |
| API keys required | None (3 optional) | OpenAI | Yes (paid) | None |
| Local scoring | Yes (HHEM) | No | No | No |
| Standalone MCP | Yes | Yes | Yes | Yes |
| Cost | Free | API costs | $19/mo | Free |
| Open source | MIT | MIT | MIT | MIT |

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Run server
uv run rce-mcp

# Run setup wizard
uv run rce-setup

# Check source connectivity
uv run rce-setup --check

# Test with MCP Inspector
uv run rce-mcp &
npx -y @modelcontextprotocol/inspector
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [HHEM-2.1-Open](https://huggingface.co/vectara/hallucination_evaluation_model) by Vectara — open-source hallucination detection
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) by Anthropic
- [arXiv API](https://info.arxiv.org/help/api/index.html) — free academic paper search
- [Stack Exchange API](https://api.stackexchange.com/) — programming Q&A
