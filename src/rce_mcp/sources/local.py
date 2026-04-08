"""Local filesystem search source."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from . import BaseSource

logger = logging.getLogger(__name__)

# Extensions considered text-searchable
TEXT_EXTENSIONS = frozenset(
    ".txt .md .rst .csv .json .yaml .yml .toml .xml .html .css .js .ts .tsx .jsx "
    ".py .rb .go .rs .java .c .cpp .h .hpp .cs .php .sh .bash .zsh .fish "
    ".cfg .ini .conf .env .log .sql .r .lua .vim .el .org .tex .bib".split()
)

# Directories to skip
SKIP_DIRS = frozenset(
    [
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        "dist",
        "build",
        ".next",
        ".cache",
    ]
)

# Max file size to read (1 MB)
MAX_FILE_SIZE = 1_048_576


class LocalSource(BaseSource):
    """Search local filesystem for text files matching a query."""

    name = "local"

    def __init__(self, base_dir: str | None = None) -> None:
        self._base_dir = Path(base_dir or os.environ.get("RCE_LOCAL_DIR", os.path.expanduser("~")))
        if not self._base_dir.is_dir():
            logger.warning("Local search base dir does not exist: %s", self._base_dir)

    async def close(self) -> None:
        pass

    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search local text files for *query* substring (case-insensitive)."""
        if not self._base_dir.is_dir():
            return []

        query_lower = query.lower()
        results: list[dict[str, Any]] = []
        files_searched = 0
        max_files = 500  # Safety limit

        try:
            for root, dirs, files in os.walk(self._base_dir):
                # Skip unwanted directories
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

                for fname in files:
                    files_searched += 1
                    if files_searched > max_files:
                        break

                    ext = os.path.splitext(fname)[1].lower()
                    if ext not in TEXT_EXTENSIONS:
                        continue

                    fpath = Path(root) / fname

                    # Skip large files
                    try:
                        if fpath.stat().st_size > MAX_FILE_SIZE:
                            continue
                    except OSError:
                        continue

                    try:
                        content = fpath.read_text(encoding="utf-8", errors="ignore")
                    except (OSError, UnicodeDecodeError):
                        continue

                    # Simple substring search
                    if query_lower in content.lower():
                        # Extract surrounding context
                        idx = content.lower().find(query_lower)
                        start = max(0, idx - 150)
                        end = min(len(content), idx + len(query) + 150)
                        snippet = content[start:end].replace("\n", " ").strip()

                        rel_path = str(fpath.relative_to(self._base_dir))
                        results.append(
                            {
                                "title": fname,
                                "snippet": f"…{snippet}…" if (start > 0 or end < len(content)) else snippet,
                                "url": str(fpath),
                                "source": "local",
                                "relative_path": rel_path,
                            }
                        )

                        if len(results) >= limit:
                            return results

                if files_searched > max_files or len(results) >= limit:
                    break

        except PermissionError:
            logger.warning("Permission denied scanning: %s", self._base_dir)

        return results
