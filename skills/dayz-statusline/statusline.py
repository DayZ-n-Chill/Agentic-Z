"""Claude Code status line for DayZ work: one line, always prints something.

    P: mounted | mod MyVest | Diag off | RAG 3d old

Claude Code runs this after each assistant message (debounced, see
https://code.claude.com/docs/en/statusline) and passes session JSON on stdin;
only workspace.project_dir / cwd is used. The machine-wide checks (P:\\ drive,
DayZDiag_x64.exe process, RAG manifest) are cached in a temp file for a few
seconds so a burst of updates costs one check. Any error prints a fallback
line instead of failing.

Installed by install.py (/dayz-statusline); run it by hand with:
    python skills/dayz-statusline/statusline.py < NUL
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
STATE_PY = HERE.parent / "dayz-init" / "state.py"
P_DRIVE = Path("P:\\")
MANIFEST = Path.home() / ".claude" / "dayz-search-index" / "manifest.json"
CACHE_FILE = Path(tempfile.gettempdir()) / "agentic-z-statusline.json"
CACHE_TTL = 5.0  # seconds
DIAG_EXE = "dayzdiag_x64.exe"
FALLBACK = "DayZ status unavailable"


# ------------------------------------------------------------ machine checks

def p_mounted() -> bool:
    return P_DRIVE.is_dir()


def diag_running() -> bool:
    """True if any DayZDiag_x64.exe process exists. Toolhelp snapshot via ctypes:
    a few ms, where spawning tasklist costs 100-300 ms."""
    if os.name != "nt":
        return False
    import ctypes
    from ctypes import wintypes

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    snap = k32.CreateToolhelp32Snapshot(0x00000002, 0)  # TH32CS_SNAPPROCESS
    if snap in (None, wintypes.HANDLE(-1).value):
        return False
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == DIAG_EXE:
                return True
            ok = k32.Process32NextW(snap, ctypes.byref(entry))
        return False
    finally:
        k32.CloseHandle(snap)


def index_time() -> Optional[float]:
    """Unix time of the last /dayz-search-index run, or None if there is no index."""
    if not MANIFEST.is_file():
        return None
    return float(json.loads(MANIFEST.read_text(encoding="utf-8"))["indexed_at"])


def machine_state(now: float) -> dict:
    """The cached checks, refreshed when the cache is older than CACHE_TTL."""
    try:
        cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if 0 <= now - cached["at"] < CACHE_TTL:
            return cached
    except (OSError, ValueError, KeyError, TypeError):
        pass
    state = {"at": now, "p": _safe(p_mounted), "diag": _safe(diag_running), "indexed_at": _safe(index_time)}
    try:
        tmp = CACHE_FILE.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, CACHE_FILE)  # atomic, so a parallel run never reads half a file
    except OSError:
        pass
    return state


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


# ------------------------------------------------------------ project checks

def active_mod(project: Path) -> tuple[Optional[str], bool]:
    """(active mod, project cached). Uses /dayz-init's state.py so the rules match the hub."""
    spec = importlib.util.spec_from_file_location("dayz_init_state_statusline", STATE_PY)
    state = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(state)
    root = state.cached_project_root(state.local_memory(project))
    if root is None:
        return None, False
    return state.active_mod(root), True


# ------------------------------------------------------------------- render

def age(seconds: float) -> str:
    seconds = max(0, seconds)
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // 86400)}d"


def render(machine: dict, mod: Optional[str], cached: Optional[bool], now: float) -> str:
    """cached: True/False for project cache present/absent, None when the lookup itself failed."""
    p = {True: "P: mounted", False: "P: NOT mounted"}.get(machine.get("p"), "P: ?")
    if cached is None:
        m = "mod ?"  # broken state file or state.py: re-running /dayz-init is not the fix
    elif not cached:
        m = "no project (/dayz-init)"
    else:
        m = f"mod {mod}" if mod else "no active mod"
    d = {True: "Diag running", False: "Diag off"}.get(machine.get("diag"), "Diag ?")
    ts = machine.get("indexed_at")
    r = f"RAG {age(now - ts)} old" if isinstance(ts, (int, float)) else "RAG not indexed"
    return " | ".join((p, m, d, r))


def project_dir(stdin_text: str) -> Path:
    try:
        data = json.loads(stdin_text) if stdin_text.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    ws = data.get("workspace") or {}
    return Path(ws.get("project_dir") or data.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def main() -> int:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")  # a mod name the console can't encode stays printable
        now = time.time()
        project = project_dir(sys.stdin.read())
        try:
            mod, cached = active_mod(project)
        except Exception:
            mod, cached = None, None
        print(render(machine_state(now), mod, cached, now))
    except Exception:
        print(FALLBACK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
