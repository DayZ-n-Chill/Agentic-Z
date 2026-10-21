"""State for /dayz-init, stored per clone under <project>/.claude/local-memory/.

Two files (both gitignored with the rest of local-memory/):
  dayz-current-project.txt  the cached project root. Other DayZ skills read it
                            through cached_project_root() and refuse to run
                            until /dayz-init has written it.
  dayz-init-state.json      the setup choice disk inspection cannot derive:
                            {"last_intent": {"mod_name"}}, the active mod.

The project root is the clone (or user project) that holds workspace/ and
.server/: $CLAUDE_PROJECT_DIR when set, else the nearest folder at or above the
current directory (below the home folder) whose local-memory holds the
project cache, so skills work from a subfolder such as workspace/<mod>/; else
the current directory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

CACHE_FILENAME = "dayz-current-project.txt"
STATE_FILENAME = "dayz-init-state.json"


def find_project_dir() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    cwd = Path.cwd().resolve()
    home = Path.home().resolve()
    for folder in (cwd, *cwd.parents):
        # Stop at the home folder: ~/.claude/ is Claude Code's user config, not
        # a project, so a cache there must not capture every folder under home.
        if folder == home:
            break
        if (folder / ".claude" / "local-memory" / CACHE_FILENAME).is_file():
            return folder
    return cwd


PROJECT_DIR = find_project_dir()


def local_memory(project: Path | None = None) -> Path:
    return (project or PROJECT_DIR) / ".claude" / "local-memory"


def cached_project_root(memory_dir: Path | None = None) -> Path | None:
    """Read the project-root cache. None if the file is missing or empty."""
    cache = (memory_dir or local_memory()) / CACHE_FILENAME
    if not cache.is_file():
        return None
    text = cache.read_text(encoding="utf-8").strip()
    return Path(text) if text else None


def write_cached_project_root(path: Path, memory_dir: Path | None = None) -> None:
    cache = (memory_dir or local_memory()) / CACHE_FILENAME
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(str(path), encoding="utf-8")


def _state_path(project: Path) -> Path:
    return local_memory(project) / STATE_FILENAME


def read_state(project: Path) -> dict:
    """Load the state JSON. Empty dict if missing or unreadable."""
    path = _state_path(project)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def write_state(project: Path, data: dict) -> None:
    path = _state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def active_mod(project: Path) -> str | None:
    return read_state(project).get("last_intent", {}).get("mod_name") or None


def mod_exists(project: Path, mod_name: str) -> bool:
    """workspace/<mod> exists as a folder or a link (even a dangling one).

    Not a file check: a --no-scaffold import links a source folder that may lack
    config.cpp or $PBOPREFIX$, and it is still set up. Any existing path also
    makes /dayz-new-mod and /dayz-import-mod refuse, so the plan must skip them.
    """
    return os.path.lexists(project / "workspace" / mod_name)


def is_setup_complete(project: Path) -> bool:
    """Hub mode needs a recorded active mod that still exists in workspace/."""
    mod = active_mod(project)
    return mod is not None and mod_exists(project, mod)
