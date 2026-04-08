# RCE MCP — Reality Check Engine

**Zero-hallucination verification for LLM agents.**

RCE MCP is a standalone Model Context Protocol server that verifies factual claims against multiple knowledge sources, scores text for hallucinations, and validates references — before they reach your users.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Why RCE MCP?

LLMs hallucinate. Existing solutions are either **post-hoc** (check after generation) or **single-source** (only Wikidata, only web search). RCE MCP is different:

- **Upstream verification** — verify facts *before* including them in responses
- **Multi-source RAG** — Wikipedia, Wikidata, web search, local filesystem
- **HHEM scoring** — Vectara's open-source hallucination detection model (optional)
- **Zero API keys** — core functionality works without any paid service
- **Universal** — works with OpenClaw, Claude Code, Codex, Cursor, Windsurf, VS Code, any MCP client

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                    RCE MCP Server                      │
│                  (FastMCP / stdio)                     │
│                                                       │
│  Tools:                                               │
│  ├── reality_check(query, sources[])                  │
│  │   └── Parallel search → Wikipedia + Wikidata + Web │
│  ├── reality_verify(text, source_text)                │
│  │   └── HHEM-2.1-Open scoring (0.0–1.0)            │
│  ├── reality_source(url_or_path)                      │
│  │   └── Fetch URL or read file                       │
│  ├── reality_search(query, scope)                     │
│  │   └── Scoped: web / wikipedia / wikidata / local   │
│  └── rce_status()                                     │
│      └── Version, sources, HHEM status                │
│                                                       │
│  Verification Backends:                               │
│  ├── Wikipedia (MediaWiki API)          [FREE]        │
│  ├── Wikidata (Wikidata API)            [FREE]        │
│  ├── DuckDuckGo (HTML scraping)         [FREE]        │
│  ├── Local filesystem                   [FREE]        │
│  └── HHEM-2.1-Open (local model)        [OPTIONAL]    │
└──────────────────────────────────────────────────────┘
```

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

Search a specific source: `"web"`, `"wikipedia"`, `"wikidata"`, or `"local"`.

### `rce_status()`

Server health check — version, available sources, HHEM model status.

## Installation

### Option 1: uv (recommended)

```bash
# Clone
git clone https://github.com/user/rce-mcp.git
cd rce-mcp

# Install
uv sync

# Run
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

## Configuration

### OpenClaw

```bash
openclaw mcp set rce-mcp '{
  "command": "uv",
  "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"]
}'
```

Or with pip:
```bash
openclaw mcp set rce-mcp '{
  "command": "python",
  "args": ["-m", "rce_mcp.server"],
  "env": { "PYTHONPATH": "/path/to/rce-mcp/src" }
}'
```

### Claude Code

```bash
claude mcp add rce-mcp -- uv --directory /path/to/rce-mcp run rce-mcp
```

### Cursor / VS Code

Add to `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "rce-mcp": {
      "command": "uv",
      "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"]
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
      "args": ["--directory", "/path/to/rce-mcp", "run", "rce-mcp"]
    }
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RCE_TRANSPORT` | `stdio` | Transport mode: `stdio` or `streamable-http` |
| `RCE_LOCAL_DIR` | `~` | Base directory for local filesystem search |

## How It Works

### Verification Pipeline

1. **Query received** — `reality_check("Python 3.12 release date")`
2. **Parallel search** — Wikipedia + Wikidata + (optional) web, all queried concurrently
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
| Local | Codebase docs, personal notes, configs | ~50ms | Yes |
| HHEM | Scoring any text against a reference | ~100ms | Yes* |

*After initial model download

## Comparison

| Feature | RCE MCP | Strawberry | Perf MCP | Fact Checker MCP |
|---------|---------|------------|----------|-----------------|
| Approach | Upstream RAG | Post-hoc KL divergence | Multi-channel verify | Wikidata-only |
| Sources | 4 (Wiki, WD, Web, Local) | Context only | Web + NLI | Wikidata |
| API keys required | None | OpenAI | Yes (paid) | None |
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

# Test with MCP Inspector
uv run rce-mcp &  # start server in background
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
- [Strawberry Toolkit](https://github.com/hassanalabs/strawberry) by Hassana Labs — inspiration for information-theoretic approach
