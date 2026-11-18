"""Read each peer's script log and RPT from a saved point: a session's start or a `mark`.

On DayZDiag, `Print` goes to script_*.log, not the RPT (references/diag-flow-traps.md),
and the client cuts its log lines at 255 characters (screenshots-and-cameras.md).
The host saves the byte size of every log file when the session starts and at
each mark; logs_since reads only what was written after that point. A file
that is new since then is read from its start, and a file that is now shorter
than its saved size was rotated and is also read from its start.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
TRIAGE_PY = HERE.parents[2] / "skills" / "dayz-gate" / "triage.py"

KINDS = ("script", "rpt")
MARK_RE = re.compile(r"\[AZ-BRIDGE\] MARK (\S+)")
ERROR_RE = re.compile(r"\[AZ-BRIDGE\] ERROR\b")
CLIENT_LINE_LIMIT = 255


def kind_of(path: Path) -> Optional[str]:
    name = path.name.lower()
    if name.startswith("script") and name.endswith(".log"):
        return "script"
    if name.endswith(".rpt"):
        return "rpt"
    if name.startswith("crash") and name.endswith(".log"):
        return "crash"
    return None


def log_files(folder: Path) -> list[Path]:
    """Script logs, RPTs and crash logs directly in a profile folder."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and kind_of(p))


def snapshot(dirs: dict[str, Path]) -> dict[str, int]:
    """{file path: size in bytes} for every log file of every peer folder."""
    return {str(p): p.stat().st_size for d in dirs.values() for p in log_files(Path(d))}


def new_crash_logs(dirs: dict[str, Path], offsets: dict[str, int]) -> list[str]:
    return [str(p) for d in dirs.values() for p in log_files(Path(d)) if kind_of(p) == "crash" and str(p) not in offsets]


def read_since(path: Path, offset: int) -> tuple[int, list[str]]:
    """(first line number, lines) written to `path` after byte `offset`; a shorter file is read whole."""
    data = path.read_bytes()
    if offset > len(data):
        offset = 0
    first = data.count(b"\n", 0, offset) + 1
    return first, data[offset:].decode("utf-8", errors="replace").splitlines()


def lines_since(dirs: dict[str, Path], offsets: dict[str, int], peers: Optional[list[str]] = None,
                kinds: tuple[str, ...] = KINDS, pattern: Optional[str] = None) -> list[dict]:
    """Every log line written since `offsets`, as {peer, file, line, text}, optionally filtered by a regex."""
    rx = re.compile(pattern) if pattern else None
    out = []
    for peer, folder in dirs.items():
        if peers and peer not in peers:
            continue
        for path in log_files(Path(folder)):
            if kind_of(path) not in kinds:
                continue
            first, lines = read_since(path, offsets.get(str(path), 0))
            for n, text in enumerate(lines, first):
                if rx is None or rx.search(text):
                    out.append({"peer": peer, "file": path.name, "line": n, "text": text})
    return out


def find_mark(lines: list[dict], label: str) -> list[dict]:
    """The MARK lines for `label` among `lines` (a client line may be cut at 255 characters)."""
    return [ln for ln in lines if (m := MARK_RE.search(ln["text"])) and label.startswith(m.group(1))]


def bridge_errors(lines: list[dict]) -> list[dict]:
    return [ln for ln in lines if ERROR_RE.search(ln["text"])]


_triage = None


def triage(lines: list[dict]) -> list[dict]:
    """Each line with its /dayz-gate triage category (skills/dayz-gate/triage.py classify)."""
    global _triage
    if _triage is None:
        sys.path.insert(0, str(TRIAGE_PY.parents[1] / "_shared"))
        import skill_helpers as h
        _triage = h.load_module("dayz_testbridge_triage", TRIAGE_PY)
    return [{**ln, "category": _triage.classify(ln["text"])} for ln in lines]
