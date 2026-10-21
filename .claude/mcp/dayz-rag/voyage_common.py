"""Voyage helpers shared by the dayz-rag MCP server and the /dayz-search-index indexer.

Both import this file by path (it sits next to server.py), so the .env lookup,
the API-key check and the retry rule are the same for searching and indexing.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path

# Repo root in a clone, plugin root when installed as a plugin (this file is
# <root>/.claude/mcp/dayz-rag/voyage_common.py). Its .env is read as well as the
# working directory's, since a plugin's server may not start in the repo.
REPO_ROOT = Path(__file__).resolve().parents[3]

# voyageai.error classes worth retrying: rate limits, timeouts, dropped
# connections and server-side faults. Auth and bad-request errors are not.
TRANSIENT_ERROR_NAMES = (
    "RateLimitError",
    "Timeout",
    "APIConnectionError",
    "TryAgain",
    "ServiceUnavailableError",
    "ServerError",
)


def dotenv_paths() -> list[Path]:
    """.env files to load, in priority order: the nearest one at or above the
    working directory, then the one at REPO_ROOT. Duplicates are dropped."""
    paths: list[Path] = []
    cwd = Path.cwd()
    for d in (cwd, *cwd.parents):
        if (d / ".env").is_file():
            paths.append(d / ".env")
            break
    root_env = REPO_ROOT / ".env"
    if root_env.is_file() and all(os.path.normcase(str(p)) != os.path.normcase(str(root_env)) for p in paths):
        paths.append(root_env)
    return paths


def load_api_key() -> str:
    """Load the .env files from dotenv_paths() and return VOYAGE_API_KEY.

    load_dotenv never overrides a variable that is already set, so the process
    environment wins, then the working-directory .env, then REPO_ROOT's.
    Raises RuntimeError when no key is found.
    """
    try:
        from dotenv import load_dotenv

        for env_path in dotenv_paths():
            load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv is optional: a key in the environment still works
    key = os.environ.get("VOYAGE_API_KEY", "").strip()
    # Accept a pasted `export VOYAGE_API_KEY="..."` value.
    if key.startswith("export "):
        key = key.split("=", 1)[-1].strip().strip('"').strip("'")
    if not key:
        raise RuntimeError(
            "VOYAGE_API_KEY not set. Add VOYAGE_API_KEY=pa-xxxxxxxx to .env at the repo root "
            "(or set it in the environment). Get a key at https://dash.voyageai.com"
        )
    return key


def is_transient(exc: BaseException) -> bool:
    """True when exc is a voyageai error class that is worth retrying."""
    verr = importlib.import_module("voyageai.error")
    classes = tuple(getattr(verr, name) for name in TRANSIENT_ERROR_NAMES)  # all present since voyageai 0.2.3
    return isinstance(exc, classes)
