"""State management for /dayz-init.

Two stores:
  1. ~/.claude/local-memory/dayz-current-project.txt  - the cached project path
  2. <project>/.agentic-z/state.json                  - per-project wizard state

Setup completion is derived from disk markers, not the state file.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CACHE_FILENAME = "dayz-current-project.txt"
STATE_DIR_NAME = ".agentic-z"
STATE_FILE_NAME = "state.json"
PROJECT_ENV_VAR = "DAYZ_PROJECT"


def _claude_home(home: Path | None = None) -> Path:
    if home is not None:
        return home
    return Path.home() / ".claude" / "local-memory"


def project_root_from_cwd(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default: cwd) looking for a project marker.

    `.agentic-z/state.json` wins over a bare `workspace/` directory, which is a
    weaker signal that unrelated repos can match.
    """
    origin = (start or Path.cwd()).resolve()
    candidates = [origin, *origin.parents]
    for d in candidates:
        if (d / STATE_DIR_NAME / STATE_FILE_NAME).is_file():
            return d
    for d in candidates:
        if (d / "workspace").is_dir():
            return d
    return None


def cached_project_root(home: Path | None = None) -> Path | None:
    """Resolve the project root: DAYZ_PROJECT, then cwd, then the cache file.

    The cache is machine-wide (one project for the whole install), so it is the
    last resort - otherwise the project you set up last hijacks every other
    project you open.
    """
    env = os.environ.get(PROJECT_ENV_VAR, "").strip()
    if env:
        return Path(env)

    from_cwd = project_root_from_cwd()
    if from_cwd is not None:
        return from_cwd

    cache = _claude_home(home) / CACHE_FILENAME
    if not cache.is_file():
        return None
    text = cache.read_text(encoding="utf-8").strip()
    return Path(text) if text else None


def write_cached_project_root(path: Path, home: Path | None = None) -> None:
    """Write the project-root cache, creating parent dirs as needed."""
    cache = _claude_home(home) / CACHE_FILENAME
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(str(path), encoding="utf-8")


def is_setup_complete(project: Path) -> bool:
    """Required markers for hub mode: scaffolded mod + state file."""
    has_pboprefix = (project / "$PBOPREFIX$").is_file()
    has_config = (project / "config.cpp").is_file()
    has_state = (project / STATE_DIR_NAME / STATE_FILE_NAME).is_file()
    return has_pboprefix and has_config and has_state


def _state_path(project: Path) -> Path:
    return project / STATE_DIR_NAME / STATE_FILE_NAME


def read_state(project: Path) -> dict:
    """Load <project>/.agentic-z/state.json. Empty dict if missing."""
    path = _state_path(project)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_state(project: Path, data: dict) -> None:
    """Write JSON state, creating .agentic-z/ if needed."""
    path = _state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
