"""dayz-init Step 6: print the hub status block for this clone.

Usage:
    python .claude/skills/dayz-init/hub_status.py
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
from skill_helpers import strip_cpp_comments  # noqa: E402
from state import PROJECT_DIR, active_mod  # noqa: E402

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
    # requiredAddons entries of the active mod that vanilla (DZ_*) does not provide.
    needs: list[str] = field(default_factory=list)


def _test_servers(server_dir: Path) -> list[str]:
    """Instances made by /dayz-add-server. The `<instance>-behavior` copies that
    /dayz-gate behavior rebuilds on every run, folders without a serverDZ.cfg and
    the shared `!` folders are not test servers."""
    if not server_dir.is_dir():
        return []
    return sorted(
        p.name for p in server_dir.iterdir()
        if p.is_dir() and not p.name.startswith("!") and not p.name.endswith("-behavior")
        and (p / "serverDZ.cfg").is_file()
    )


def _non_vanilla_addons(config: Path) -> list[str]:
    """requiredAddons[] names in config.cpp that are not vanilla DZ_* patches."""
    if not config.is_file():
        return []
    text = strip_cpp_comments(config.read_text(encoding="utf-8", errors="replace"))
    names: list[str] = []
    for block in re.findall(r"requiredAddons\s*\[\]\s*=\s*\{([^}]*)\}", text):
        for name in re.findall(r'"([^"]+)"', block):
            if not name.lower().startswith("dz_") and name not in names:
                names.append(name)
    return names


def launch_needs(mod_dir: Path) -> list[str]:
    """Non-vanilla requiredAddons a launch of this mod folder must get from --deps.

    Empty for a prebuilt bundle (Addons/*.pbo), whose own PBOs may provide them,
    the same exception /dayz-gate ingame makes.
    """
    addons = mod_dir / "Addons"
    if addons.is_dir() and any(addons.glob("*.pbo")):
        return []
    return _non_vanilla_addons(mod_dir / "config.cpp")


def needs_message(mod: str, needs: list[str]) -> str:
    return (
        f"{mod}'s config.cpp requires non-vanilla addons {', '.join(needs)} but no --deps were given. "
        "Pass the @mods under P:\\Mods\\ that provide them, in load order (for example --deps CF); "
        "without them the mod fails to load in game."
    )


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
    return Status(
        project=project,
        mod=mod,
        pbo_age_minutes=pbo_age,
        servers=_test_servers(project / ".server"),
        diag_running=_diag_running(),
        voyage_key=_voyage_key_set(project / ".env"),
        search_index=SEARCH_INDEX.is_dir(),
        needs=launch_needs(project / "workspace" / mod) if mod else [],  # same rule launch applies
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
    lines = [
        f"/dayz-init: {s.mod or '(no active mod)'}",
        f"Project: {s.project}",
        f"PBO:     {'built ' + str(s.pbo_age_minutes) + 'm ago' if s.pbo_age_minutes is not None else 'not built yet'}",
        f"Servers: {', '.join(s.servers) if s.servers else 'none'}",
        f"Diag:    {'running' if s.diag_running else 'not running'}",
        f"Search:  {search}",
    ]
    if s.needs:
        lines.append(f"Needs:   {', '.join(s.needs)} (not vanilla; pass the @mods that provide them as --deps)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(
        description="Print the /dayz-init status: active mod, PBO age, test servers, DayZ Diag and search. "
                    "Takes no options.",
    ).parse_args(argv)
    print(render_status(gather_status(PROJECT_DIR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
