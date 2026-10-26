"""Install or remove the DayZ status line in the project's .claude/settings.local.json.

Run:
    python skills/dayz-statusline/install.py            # install (idempotent)
    python skills/dayz-statusline/install.py --remove   # undo
    python skills/dayz-statusline/install.py --status

The project is $CLAUDE_PROJECT_DIR, else the nearest folder at or above the
current one that holds a .claude folder (the home folder is never taken);
with neither, it refuses and changes nothing.

Install and remove first copy settings.local.json to a free backup name
(settings.local.json.bak, then .2.bak, ...), so an older backup is never
replaced. Install records the statusLine it replaces in .claude/local-memory/,
so --remove puts that one back.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

STATUSLINE = Path(__file__).resolve().parent / "statusline.py"


def find_project_dir(start: Optional[Path] = None, home: Optional[Path] = None) -> Optional[Path]:
    """$CLAUDE_PROJECT_DIR, else the nearest folder at or above `start` holding a .claude folder.

    Stops below the home folder: ~/.claude/ is Claude Code's user config, not a
    project. None when nothing is found, so the installer refuses instead of
    creating a stray .claude/settings.local.json in a subfolder.
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    start = (start or Path.cwd()).resolve()
    home = (home or Path.home()).resolve()
    for folder in (start, *start.parents):
        if folder == home:
            break
        if (folder / ".claude").is_dir():
            return folder
    return None


PROJECT_DIR = find_project_dir()
SETTINGS_LOCAL = PROJECT_DIR / ".claude" / "settings.local.json" if PROJECT_DIR else None
RECORD = PROJECT_DIR / ".claude" / "local-memory" / "dayz-statusline.json" if PROJECT_DIR else None

OK = "[OK]   "
FAIL = "[FAIL] "
INFO = "[INFO] "

# Re-run every 10 s while the session is idle, so "Diag running" and "P: mounted"
# catch up with changes made outside Claude Code (refreshInterval, statusline docs).
REFRESH_SECONDS = 10


def our_entry() -> dict:
    # The absolute path of the interpreter running this installer, not a bare
    # "python": where "python" on PATH is only the Microsoft Store alias, a bare
    # command exits 9009 and the status line stays blank with no error.
    return {
        "type": "command",
        "command": f'"{Path(sys.executable).as_posix()}" "{STATUSLINE.as_posix()}"',
        "refreshInterval": REFRESH_SECONDS,
    }


def is_ours(entry: object) -> bool:
    """Ours if it runs a dayz-statusline/statusline.py, even from an older plugin version's path."""
    return isinstance(entry, dict) and "dayz-statusline/statusline.py" in str(entry.get("command", "")).replace("\\", "/")


def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"{FAIL} Could not read {path}: {e}", file=sys.stderr)
        print("        Fix or remove the file, then run this again. Nothing was changed.", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"{FAIL} {path} is not a JSON object. Nothing was changed.", file=sys.stderr)
        return None
    return data


def _backup(path: Path) -> Path:
    """Copy path to the first free <name>.bak, <name>.2.bak, ... and return it. Never replaces a backup."""
    backup = path.with_name(f"{path.name}.bak")
    n = 2
    while backup.exists():
        backup = path.with_name(f"{path.name}.{n}.bak")
        n += 1
    shutil.copy2(path, backup)
    return backup


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cmd_install() -> int:
    settings = _load(SETTINGS_LOCAL)
    if settings is None:
        return 1
    current = settings.get("statusLine")
    wanted = our_entry()
    if current == wanted:
        print(f"{OK} Status line already installed in {SETTINGS_LOCAL}")
        return 0
    if SETTINGS_LOCAL.exists():
        print(f"{OK} Backed up settings to {_backup(SETTINGS_LOCAL).name}")
    if current is not None and not is_ours(current):
        # Keep the user's own status line so --remove can restore it.
        _write(RECORD, {"previous": current})
        print(f"{INFO} Replacing your existing status line; --remove puts it back")
    elif current is None:
        # Nothing to restore. Overwrite any stale record left from an earlier
        # install whose statusLine was later deleted by hand, so --remove can
        # never bring back a line the user already removed.
        _write(RECORD, {"previous": None})
    settings["statusLine"] = wanted
    _write(SETTINGS_LOCAL, settings)
    print(f"{OK} Status line installed in {SETTINGS_LOCAL}")
    print("        It appears after your next message. Remove with: install.py --remove")
    return 0


def cmd_remove() -> int:
    settings = _load(SETTINGS_LOCAL)
    if settings is None:
        return 1
    current = settings.get("statusLine")
    if not is_ours(current):
        print(f"{INFO} The DayZ status line is not installed here. Nothing to remove.")
        return 0
    record = _load(RECORD)
    if record is None:
        # A corrupt record may hold the user's own status line; deleting the key
        # and the record would lose it, so stop before touching anything.
        return 1
    previous = record.get("previous")
    print(f"{OK} Backed up settings to {_backup(SETTINGS_LOCAL).name}")
    if previous is not None:
        settings["statusLine"] = previous
        msg = "restored your previous status line"
    else:
        del settings["statusLine"]
        msg = "removed the statusLine setting"
    _write(SETTINGS_LOCAL, settings)
    if RECORD.exists():
        RECORD.unlink()
    print(f"{OK} DayZ status line removed: {msg}")
    return 0


def cmd_status() -> int:
    settings = _load(SETTINGS_LOCAL)
    if settings is None:
        return 1
    current = settings.get("statusLine")
    if current == our_entry():
        print(f"{OK} Installed: {current['command']}")
    elif is_ours(current):
        print(f"{INFO} Installed from another path: {current.get('command')}. Run install.py again to update it.")
    elif current:
        shown = current.get("command") if isinstance(current, dict) else current
        print(f"{INFO} A different status line is set: {shown}")
    else:
        print(f"{INFO} No status line set in {SETTINGS_LOCAL}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Install the DayZ status line into .claude/settings.local.json.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--remove", action="store_true", help="Remove it (restores any status line it replaced)")
    group.add_argument("--status", action="store_true", help="Show what statusLine is set")
    args = parser.parse_args(argv)
    if PROJECT_DIR is None:
        print(f"{FAIL} No project found: no .claude folder at or above {Path.cwd()}.", file=sys.stderr)
        print("        Run this from your project root (the folder Claude Code was started in). Nothing was changed.",
              file=sys.stderr)
        return 1
    if args.remove:
        return cmd_remove()
    if args.status:
        return cmd_status()
    return cmd_install()


if __name__ == "__main__":
    sys.exit(main())
