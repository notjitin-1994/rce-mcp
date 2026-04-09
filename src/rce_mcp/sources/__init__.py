"""Source backends for the Reality Check Engine."""

from __future__ import annotations

import abc
from typing import Any


class BaseSource(abc.ABC):
    """Base class for all verification sources."""

    name: str = "base"

    @abc.abstractmethod
    async def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for information matching *query*."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...


# ── Source imports (all 8) ────────────────────────────────────────────────────

from .wikipedia import WikipediaSource  # noqa: E402, F401
from .wikidata import WikidataSource  # noqa: E402, F401
from .web import WebSource  # noqa: E402, F401
from .local import LocalSource  # noqa: E402, F401
from .arxiv import ArxivSource  # noqa: E402, F401
from .github import GithubSource  # noqa: E402, F401
from .context7 import Context7Source  # noqa: E402, F401
from .stackexchange import StackExchangeSource  # noqa: E402, F401

__all__ = [
    "BaseSource",
    "WikipediaSource",
    "WikidataSource",
    "WebSource",
    "LocalSource",
    "ArxivSource",
    "GithubSource",
    "Context7Source",
    "StackExchangeSource",
]
