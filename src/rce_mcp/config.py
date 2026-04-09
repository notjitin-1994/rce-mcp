"""Centralized configuration for RCE MCP.

All API keys and settings are read from environment variables.
No keys are ever hardcoded.

Required environment variables (for sources that need them):
  GITHUB_TOKEN          — GitHub Personal Access Token (for GitHub source)
  CONTEXT7_API_KEY      — Context7 API key (for Context7 source)
  STACKEXCHANGE_KEY     — Stack Exchange API key (for Stack Exchange source)

Optional environment variables:
  RCE_TRANSPORT         — Transport mode: "stdio" or "streamable-http" (default: "stdio")
  RCE_LOCAL_DIR         — Base directory for local filesystem search (default: "~")
  RCE_ARXIV_MAX_RESULTS — Max results from arXiv (default: 5)
  RCE_WEB_TIMEOUT       — HTTP timeout in seconds (default: 15)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class RCEConfig:
    """Immutable runtime configuration, sourced entirely from environment variables."""

    # ── Transport ────────────────────────────────────────────────────────────
    transport: str = field(
        default_factory=lambda: os.environ.get("RCE_TRANSPORT", "stdio")
    )

    # ── Local filesystem ─────────────────────────────────────────────────────
    local_dir: str = field(
        default_factory=lambda: os.path.expanduser(
            os.environ.get("RCE_LOCAL_DIR", "~")
        )
    )

    # ── API keys (None when not set — source will skip itself) ───────────────
    github_token: Optional[str] = field(
        default_factory=lambda: os.environ.get("GITHUB_TOKEN") or None
    )
    context7_api_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("CONTEXT7_API_KEY") or None
    )
    stackexchange_key: Optional[str] = field(
        default_factory=lambda: os.environ.get("STACKEXCHANGE_KEY") or None
    )

    # ── Tuning ───────────────────────────────────────────────────────────────
    arxiv_max_results: int = field(
        default_factory=lambda: int(
            os.environ.get("RCE_ARXIV_MAX_RESULTS", "5")
        )
    )
    web_timeout: float = field(
        default_factory=lambda: float(
            os.environ.get("RCE_WEB_TIMEOUT", "15")
        )
    )

    # ── Computed helpers ─────────────────────────────────────────────────────
    @property
    def has_github(self) -> bool:
        return self.github_token is not None

    @property
    def has_context7(self) -> bool:
        return self.context7_api_key is not None

    @property
    def has_stackexchange(self) -> bool:
        return self.stackexchange_key is not None


# ── Module-level singleton ────────────────────────────────────────────────────

_config: Optional[RCEConfig] = None


def get_config() -> RCEConfig:
    """Return the global config singleton (created once, reads env vars)."""
    global _config
    if _config is None:
        _config = RCEConfig()
    return _config


def reset_config() -> None:
    """Reset the config singleton (useful for tests)."""
    global _config
    _config = None
