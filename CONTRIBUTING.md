# Contributing to RCE MCP

Thanks for your interest in contributing! This guide covers the basics.

## Setup

```bash
# Clone the repo
git clone https://github.com/notjitin-1994/rce-mcp.git
cd rce-mcp

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Development Workflow

1. **Fork** the repo and create a feature branch from `main`
2. **Make changes** — keep them focused and atomic
3. **Test** your changes: `pytest`
4. **Lint** your code: `ruff check src/` and `ruff format --check src/`
5. **Commit** with clear messages (conventional commits preferred: `feat:`, `fix:`, `docs:`, etc.)
6. **Push** to your fork and open a Pull Request

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_utils.py
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Check for issues
ruff check src/

# Auto-fix what can be fixed
ruff check --fix src/

# Format code
ruff format src/
```

## Project Structure

```
src/rce_mcp/
├── server.py       # MCP server, tool definitions
├── utils.py        # Shared utilities (confidence scoring, HTML stripping)
├── config.py       # Configuration management
├── hhem.py         # HHEM hallucination scoring integration
├── setup.py        # First-run setup wizard
├── __init__.py     # Package metadata
└── sources/        # Source backends
    ├── arxiv.py
    ├── context7.py
    ├── github.py
    ├── local.py
    ├── stackexchange.py
    ├── web.py
    ├── wikidata.py
    └── wikipedia.py
```

## Pull Request Guidelines

- **One logical change per PR** — don't bundle unrelated fixes
- **Include tests** for new features or bug fixes
- **Update docs** if behavior changes (docstrings, README, etc.)
- **Keep PRs small** — easier to review, easier to revert
- **Write clear descriptions** — explain *why*, not just *what*
- **Pass CI** — your PR must pass linting and tests before merge

## Adding a New Source

1. Create `src/rce_mcp/sources/your_source.py` implementing the `BaseSource` interface
2. Register it in `_build_sources()` in `server.py`
3. Add it to the `reality_search` valid scopes and `reality_check` docs
4. Add configuration options to `config.py` if needed
5. Write tests in `tests/`

## Reporting Issues

When reporting bugs, please include:

- **Python version** (`python --version`)
- **OS** and version
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Relevant logs** (enable with `RUST_LOG=debug` or Python logging)

## Questions?

Open a [Discussion](https://github.com/notjitin-1994/rce-mcp/discussions) on GitHub.
