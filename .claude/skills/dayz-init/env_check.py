"""Environment detection for /dayz-init.

Categorizes each prereq as: OK (nothing to do), AUTOFIX (we can fix it),
HARD_STOP (user has to act). Returns EnvIssue objects with optional
steam:// links and human-readable messages.
"""
from __future__ import annotations

import os
import shutil
import sys
import winreg
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Severity(Enum):
    AUTOFIX = "autofix"
    HARD_STOP = "hard_stop"


@dataclass
class EnvIssue:
    name: str
    severity: Severity
    message: str
    fix_link: str | None = None


def check_python() -> EnvIssue | None:
    """Confirm Python 3.8+. Currently running interpreter == answer."""
    if sys.version_info < (3, 8):
        return EnvIssue(
            name="python",
            severity=Severity.HARD_STOP,
            message=f"Python 3.8+ required, found {sys.version.split()[0]}",
            fix_link="https://www.python.org/downloads/",
        )
    return None


def _p_drive_mounted() -> bool:
    return Path("P:\\").exists()


def check_p_drive() -> EnvIssue | None:
    if _p_drive_mounted():
        return None
    return EnvIssue(
        name="p_drive",
        severity=Severity.AUTOFIX,
        message="P:\\ is not mounted (will mount via subst)",
    )


def _dayz_tools_installed() -> bool:
    """Check Steam app 830640 install via registry. Returns False on any error."""
    try:
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Bohemia Interactive\DayZ Tools",
        ):
            return True
    except OSError:
        return False


def check_dayz_tools() -> EnvIssue | None:
    if _dayz_tools_installed():
        return None
    return EnvIssue(
        name="dayz_tools",
        severity=Severity.HARD_STOP,
        message="DayZ Tools is not installed (Steam, free)",
        fix_link="steam://install/830640",
    )


def check_vanilla_data() -> EnvIssue | None:
    """Vanilla data extracted to P:\\ implies P:\\scripts\\3_Game exists."""
    marker = Path("P:\\scripts\\3_Game")
    if marker.is_dir():
        return None
    return EnvIssue(
        name="vanilla_data",
        severity=Severity.HARD_STOP,
        message=(
            "Vanilla data is not extracted to P:\\.\n"
            "  Open DayZ Tools, then: Tools menu, Extract Game Data."
        ),
    )


def check_mods_junction() -> EnvIssue | None:
    """P:\\Mods\\ should junction to <DayZ install>\\!Workshop\\."""
    if Path("P:\\Mods").exists():
        return None
    return EnvIssue(
        name="mods_junction",
        severity=Severity.AUTOFIX,
        message="P:\\Mods\\ junction to !Workshop missing (will create)",
    )


def run_all() -> list[EnvIssue]:
    """Run every check, return non-None issues in declaration order."""
    checks = [
        check_python,
        check_p_drive,
        check_dayz_tools,
        check_vanilla_data,
        check_mods_junction,
    ]
    return [issue for check in checks if (issue := check()) is not None]


def classify(
    issues: list[EnvIssue],
) -> tuple[list[EnvIssue], list[EnvIssue]]:
    """Split issues into (autofixable, hard_stop) preserving order within each."""
    autofix = [i for i in issues if i.severity == Severity.AUTOFIX]
    hard_stop = [i for i in issues if i.severity == Severity.HARD_STOP]
    return autofix, hard_stop
