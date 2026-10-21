"""Install or remove the DayZ status line in the project's .claude/settings.local.json.

Run:
    python .claude/skills/dayz-statusline/install.py            # install (idempotent)
    python .claude/skills/dayz-statusline/install.py --remove   # undo
    python .claude/skills/dayz-statusline/install.py --status

Install backs up settings.local.json to settings.local.json.bak first and
records the statusLine it replaces in .claude/local-memory/, so --remove puts
that one back.
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

# Project dir: where Claude Code was started, as /dayz-scope-mod resolves it.
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
SETTINGS_LOCAL = PROJECT_DIR / ".claude" / "settings.local.json"
RECORD = PROJECT_DIR / ".claude" / "local-memory" / "dayz-statusline.json"

OK = "[OK]   "
FAIL = "[FAIL] "
INFO = "[INFO] "

# Re-run every 10 s while the session is idle, so "Diag running" and "P: mounted"
# catch up with changes made outside Claude Code (refreshInterval, statusline docs).
REFRESH_SECONDS = 10


def our_entry() -> dict:
    return {
        "type": "command",
        "command": f'python "{STATUSLINE.as_posix()}"',
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
        shutil.copy2(SETTINGS_LOCAL, SETTINGS_LOCAL.with_name(SETTINGS_LOCAL.name + ".bak"))
        print(f"{OK} Backed up settings to {SETTINGS_LOCAL.name}.bak")
    if current is not None and not is_ours(current):
        # Keep the user's own status line so --remove can restore it.
        _write(RECORD, {"previous": current})
        print(f"{INFO} Replacing your existing status line; --remove puts it back")
    elif current is None and not RECORD.exists():
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
    record = _load(RECORD) if RECORD.exists() else {}
    previous = (record or {}).get("previous")
    shutil.copy2(SETTINGS_LOCAL, SETTINGS_LOCAL.with_name(SETTINGS_LOCAL.name + ".bak"))
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
        print(f"{INFO} A different status line is set: {current.get('command')}")
    else:
        print(f"{INFO} No status line set in {SETTINGS_LOCAL}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Install the DayZ status line into .claude/settings.local.json.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--remove", action="store_true", help="Remove it (restores any status line it replaced)")
    group.add_argument("--status", action="store_true", help="Show what statusLine is set")
    args = parser.parse_args(argv)
    if args.remove:
        return cmd_remove()
    if args.status:
        return cmd_status()
    return cmd_install()


if __name__ == "__main__":
    sys.exit(main())
