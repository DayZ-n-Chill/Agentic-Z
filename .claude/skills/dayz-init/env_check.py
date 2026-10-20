"""Environment checks for /dayz-init.

Each check returns None (fine) or an EnvIssue:
  AUTOFIX    /dayz-init fixes it itself (mount P:\\, create the P:\\Mods junction)
  HARD_STOP  the user has to act (install DayZ Tools, extract game data, ...)

Paths are resolved with the shared dayz-preflight resolvers so this check and
every other DayZ skill agree on where things live. Checks that read P:\\ are
skipped while P:\\ is unmounted; re-run after mounting to see them.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
from skill_helpers import preflight  # noqa: E402

P_MODS = Path("P:\\Mods")


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
    if sys.version_info < (3, 10):
        return EnvIssue(
            name="python",
            severity=Severity.HARD_STOP,
            message=f"Python 3.10+ required, found {sys.version.split()[0]}",
            fix_link="https://www.python.org/downloads/",
        )
    return None


def p_drive_mounted() -> bool:
    """Check P:\\ via the logical-drive bitmask (no disk I/O, no popup risk)."""
    if sys.platform != "win32":
        return False
    import ctypes

    return bool(ctypes.windll.kernel32.GetLogicalDrives() & (1 << 15))  # bit 15 = P


def check_p_drive() -> EnvIssue | None:
    if p_drive_mounted():
        return None
    return EnvIssue(
        name="p_drive",
        severity=Severity.AUTOFIX,
        message="P:\\ is not mounted (will mount with /dayz-workdrive)",
    )


def check_dayz_tools() -> EnvIssue | None:
    if preflight.find_dayz_tools() is not None:
        return None
    return EnvIssue(
        name="dayz_tools",
        severity=Severity.HARD_STOP,
        message="DayZ Tools not found (free on Steam; set DAYZ_TOOLS_PATH if installed elsewhere)",
        fix_link="steam://install/830640",
    )


def check_vanilla_data() -> EnvIssue | None:
    if not p_drive_mounted() or preflight.find_vanilla_data() is not None:
        return None
    return EnvIssue(
        name="vanilla_data",
        severity=Severity.HARD_STOP,
        message="Vanilla game data is not extracted to P:\\ (DayZ Tools > Tools > Extract Game Data)",
    )


def check_mods_junction() -> EnvIssue | None:
    """P:\\Mods\\ must be a junction to <DayZ install>\\!Workshop\\.

    Missing and the game is found: AUTOFIX (mklink /J is non-destructive).
    Any other problem (real folder, dangling junction, no game install):
    HARD_STOP with preflight's own explanation and fix command.
    """
    if not p_drive_mounted():
        return None
    problem = preflight.validate_p_mods()
    if problem is None:
        return None
    if not os.path.lexists(P_MODS) and preflight.find_dayz_game() is not None:
        return EnvIssue(
            name="mods_junction",
            severity=Severity.AUTOFIX,
            message="P:\\Mods\\ junction to !Workshop is missing (will create)",
        )
    return EnvIssue(name="mods_junction", severity=Severity.HARD_STOP, message=problem)


CHECKS = [check_python, check_p_drive, check_dayz_tools, check_vanilla_data, check_mods_junction]


def run_all() -> list[EnvIssue]:
    """Run every check; return the issues in check order."""
    return [issue for check in CHECKS if (issue := check()) is not None]


def classify(issues: list[EnvIssue]) -> tuple[list[EnvIssue], list[EnvIssue]]:
    """Split issues into (autofix, hard_stop), preserving order."""
    autofix = [i for i in issues if i.severity == Severity.AUTOFIX]
    hard_stop = [i for i in issues if i.severity == Severity.HARD_STOP]
    return autofix, hard_stop
