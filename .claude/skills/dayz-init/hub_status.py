"""dayz-init Step 6: print the hub status block for this clone.

Usage:
    python .claude/skills/dayz-init/hub_status.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from state import PROJECT_DIR, active_mod

SEARCH_INDEX = Path.home() / ".claude" / "dayz-search-index" / "lancedb"


@dataclass
class Status:
    project: Path
    mod: str | None
    pbo_age_minutes: int | None
    servers: list[str]
    diag_running: bool
    voyage_key: bool
    search_index: bool


def _voyage_key_set(env_file: Path) -> bool:
    """The dayz-rag MCP server reads VOYAGE_API_KEY from the environment or the project .env."""
    if os.environ.get("VOYAGE_API_KEY", "").strip():
        return True
    if not env_file.is_file():
        return False
    for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "VOYAGE_API_KEY" and value.strip():
            return True
    return False


def _diag_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq DayZDiag_x64.exe"], text=True, stderr=subprocess.DEVNULL
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    return "DayZDiag_x64.exe" in out


def gather_status(project: Path, mods_root: Path = Path("P:\\Mods")) -> Status:
    mod = active_mod(project)
    pbo_age = None
    if mod:
        pbo = mods_root / f"@{mod}" / "Addons" / f"{mod}.pbo"
        if pbo.is_file():
            pbo_age = int((time.time() - pbo.stat().st_mtime) / 60)
    server_dir = project / ".server"
    servers = sorted(
        p.name for p in server_dir.iterdir() if p.is_dir() and not p.name.startswith("!")
    ) if server_dir.is_dir() else []
    return Status(
        project=project,
        mod=mod,
        pbo_age_minutes=pbo_age,
        servers=servers,
        diag_running=_diag_running(),
        voyage_key=_voyage_key_set(project / ".env"),
        search_index=SEARCH_INDEX.is_dir(),
    )


def render_status(s: Status) -> str:
    if s.search_index and s.voyage_key:
        search = "ready"
    elif s.search_index:
        search = "index installed, VOYAGE_API_KEY missing from .env"
    elif s.voyage_key:
        search = "VOYAGE_API_KEY set, index not installed"
    else:
        search = "not set up"
    return "\n".join([
        f"/dayz-init: {s.mod or '(no active mod)'}",
        f"Project: {s.project}",
        f"PBO:     {'built ' + str(s.pbo_age_minutes) + 'm ago' if s.pbo_age_minutes is not None else 'not built yet'}",
        f"Servers: {', '.join(s.servers) if s.servers else 'none'}",
        f"Diag:    {'running' if s.diag_running else 'not running'}",
        f"Search:  {search}",
    ])


def main() -> int:
    print(render_status(gather_status(PROJECT_DIR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
