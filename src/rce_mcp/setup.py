"""First-run setup wizard for RCE MCP.

Interactively guides the user through setting API keys and verifying
connectivity for optional sources (GitHub, Context7, Stack Exchange).

Usage:
    python -m rce_mcp.setup          # interactive wizard
    python -m rce_mcp.setup --check  # non-interactive connectivity check
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__


def _detect_shell_config() -> Path | None:
    """Detect the user's shell rc file."""
    home = Path.home()
    candidates = [".bashrc", ".zshrc", ".profile", ".bash_profile"]
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        candidates.insert(0, ".zshrc")
    elif "bash" in shell:
        candidates.insert(0, ".bashrc")
    for name in candidates:
        p = home / name
        if p.is_file():
            return p
    return None


def _append_to_shell_rc(rc_path: Path, var: str, value: str) -> None:
    """Append an export line to a shell rc file."""
    marker = "# Added by rce-mcp setup"
    export_line = f'export {var}="{value}"'
    content = rc_path.read_text()

    if marker in content and var in content:
        print(f"  ✅ {var} already in {rc_path.name}")
        return

    with open(rc_path, "a") as f:
        f.write(f"\n{marker}\n{export_line}\n")
    print(f"  ✅ Added {var} to {rc_path.name}")


def _test_github(token: str) -> bool:
    """Verify a GitHub token works."""
    try:
        import httpx
        resp = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            user = resp.json().get("login", "unknown")
            print(f"  ✅ GitHub token valid (user: {user})")
            return True
        else:
            print(f"  ❌ GitHub token rejected: {resp.status_code} {resp.text[:100]}")
            return False
    except Exception as exc:
        print(f"  ❌ GitHub connection failed: {exc}")
        return False


def _test_context7(key: str) -> bool:
    """Verify a Context7 API key works."""
    try:
        import httpx
        resp = httpx.get(
            "https://context7.com/api/v1/status",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if resp.status_code == 200:
            print("  ✅ Context7 API key valid")
            return True
        else:
            print(f"  ❌ Context7 key rejected: {resp.status_code}")
            return False
    except Exception as exc:
        print(f"  ⚠️  Context7 unreachable ({exc}) — key may work later")
        return False


def _test_stackexchange(key: str) -> bool:
    """Verify a Stack Exchange key works."""
    try:
        import httpx
        resp = httpx.get(
            "https://api.stackexchange.com/2.3/info",
            params={"site": "stackoverflow", "key": key},
            timeout=10,
        )
        data = resp.json()
        if "items" in data and not data.get("error_id"):
            print(f"  ✅ Stack Exchange key valid (quota: {data.get('quota_remaining', '?')})")
            return True
        else:
            print(f"  ❌ Stack Exchange key rejected: {data.get('error_name', resp.text[:100])}")
            return False
    except Exception as exc:
        print(f"  ❌ Stack Exchange connection failed: {exc}")
        return False


def interactive_setup() -> None:
    """Run the interactive setup wizard."""
    print(f"\n{'='*60}")
    print(f"  RCE MCP Setup Wizard v{__version__}")
    print(f"{'='*60}\n")

    print("Core sources (Wikipedia, Wikidata, Web, arXiv, Local) work out of the box.")
    print("Optional sources need API keys:\n")

    rc_path = _detect_shell_config()

    # ── GitHub ───────────────────────────────────────────────────────────────
    print("── GitHub (optional — code search, issue lookup) ──")
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if gh_token:
        print(f"  Current: {gh_token[:8]}...{gh_token[-4:]}")
    choice = input("  Set GitHub token? [y/N] ").strip().lower()
    if choice == "y":
        new_token = input("  Paste token (ghp_...): ").strip()
        if new_token:
            os.environ["GITHUB_TOKEN"] = new_token
            if _test_github(new_token) and rc_path:
                _append_to_shell_rc(rc_path, "GITHUB_TOKEN", new_token)

    # ── Context7 ─────────────────────────────────────────────────────────────
    print("\n── Context7 (optional — library documentation search) ──")
    c7_key = os.environ.get("CONTEXT7_API_KEY", "")
    if c7_key:
        print(f"  Current: {c7_key[:8]}...{c7_key[-4:]}")
    choice = input("  Set Context7 API key? [y/N] ").strip().lower()
    if choice == "y":
        new_key = input("  Paste API key: ").strip()
        if new_key:
            os.environ["CONTEXT7_API_KEY"] = new_key
            if _test_context7(new_key) and rc_path:
                _append_to_shell_rc(rc_path, "CONTEXT7_API_KEY", new_key)

    # ── Stack Exchange ───────────────────────────────────────────────────────
    print("\n── Stack Exchange (optional — programming Q&A) ──")
    se_key = os.environ.get("STACKEXCHANGE_KEY", "")
    if se_key:
        print(f"  Current: {se_key[:8]}...{se_key[-4:]}")
    choice = input("  Set Stack Exchange key? [y/N] ").strip().lower()
    if choice == "y":
        new_key = input("  Paste key: ").strip()
        if new_key:
            os.environ["STACKEXCHANGE_KEY"] = new_key
            if _test_stackexchange(new_key) and rc_path:
                _append_to_shell_rc(rc_path, "STACKEXCHANGE_KEY", new_key)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Setup complete! Restart your MCP client to apply changes.")
    print(f"{'='*60}\n")


def check_connectivity() -> dict[str, Any]:
    """Non-interactive connectivity check for all configured sources."""
    from .config import get_config

    cfg = get_config()
    results: dict[str, dict[str, Any]] = {}

    # Free sources — always check
    for name, fn in [
        ("wikipedia", lambda: _ping_url("https://en.wikipedia.org/w/api.php")),
        ("wikidata", lambda: _ping_url("https://www.wikidata.org/w/api.php")),
        ("arxiv", lambda: _ping_url("https://export.arxiv.org/api/query")),
    ]:
        results[name] = {"available": fn(), "requires_key": False}

    # Key-gated sources
    if cfg.github_token:
        results["github"] = {"available": _test_github(cfg.github_token), "requires_key": True}
    else:
        results["github"] = {"available": False, "requires_key": True, "reason": "GITHUB_TOKEN not set"}

    if cfg.context7_api_key:
        results["context7"] = {"available": _test_context7(cfg.context7_api_key), "requires_key": True}
    else:
        results["context7"] = {"available": False, "requires_key": True, "reason": "CONTEXT7_API_KEY not set"}

    if cfg.stackexchange_key:
        results["stackexchange"] = {"available": _test_stackexchange(cfg.stackexchange_key), "requires_key": True}
    else:
        results["stackexchange"] = {"available": False, "requires_key": True, "reason": "STACKEXCHANGE_KEY not set"}

    return results


def _ping_url(url: str) -> bool:
    try:
        import httpx
        resp = httpx.head(url, timeout=10, follow_redirects=True)
        return resp.status_code < 500
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="RCE MCP setup wizard")
    parser.add_argument("--check", action="store_true", help="Non-interactive connectivity check")
    parser.add_argument("--json", action="store_true", help="Output as JSON (with --check)")
    args = parser.parse_args()

    if args.check:
        results = check_connectivity()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for name, info in results.items():
                status = "✅" if info["available"] else "❌"
                key_tag = " (requires key)" if info.get("requires_key") else " (free)"
                print(f"  {status} {name}{key_tag}")
                if "reason" in info:
                    print(f"       {info['reason']}")
    else:
        interactive_setup()


if __name__ == "__main__":
    main()
