"""Lift the active DayZ mod scope. Thin wrapper around dayz-scope-mod --clear.

Run:
    python .claude/skills/dayz-scope-clear/clear.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "dayz-scope-mod"))

from scope import cmd_clear  # noqa: E402


if __name__ == "__main__":
    sys.exit(cmd_clear())
