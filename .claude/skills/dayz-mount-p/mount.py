"""Mount P:\\ as the DayZ work drive without opening DayZ Tools.

P:\\ is just a folder mounted as a drive letter via Windows' subst command.
DayZ Tools' "Mount P Drive" menu does the same thing — this skill bypasses
the GUI so you can mount from a script after a fresh Windows boot.

Run:
    python .claude/skills/dayz-mount-p/mount.py
    python .claude/skills/dayz-mount-p/mount.py --path "C:\\Path\\To\\WorkDrive"
    python .claude/skills/dayz-mount-p/mount.py --unmount
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Reuse preflight resolvers
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "dayz-preflight"))
from preflight import find_dayz_tools  # noqa: E402

REPO_ROOT = _HERE.parent.parent.parent  # G:\AI-Templates
CACHE = REPO_ROOT / ".claude" / "local-memory" / "dayz-work-drive.json"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "
INFO = "[INFO] "


def _read_cached_path() -> Optional[Path]:
    if not CACHE.exists():
        return None
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        p = Path(data.get("work_drive_path", ""))
        return p if p.exists() and p.is_dir() else None
    except (json.JSONDecodeError, OSError):
        return None


def _write_cached_path(p: Path) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps({"work_drive_path": str(p)}, indent=2),
        encoding="utf-8",
    )


def _read_registry_string(hive, subkey: str, value_name: str) -> Optional[str]:
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(hive, subkey) as key:
            val, _ = winreg.QueryValueEx(key, value_name)
            return str(val) if val else None
    except OSError:
        return None


def _read_settings_ini(tools_root: Path) -> Optional[Path]:
    """Read DayZ Tools' settings.ini and return [ProjectDrive] path if set.

    This is the canonical source — it's what WorkDrive.exe itself reads. Far more
    reliable than registry probing (Tools doesn't store the path in registry).

    The actual ini layout (verified against DayZ Tools 1.x):
        [ProjectDrive]
        path=G:\\P Drives\\Vanilla
        Letter=P

    Note: WorkDrive.exe's runtime log prints these as friendly names like
    "Project Space" / "WorkDirPath", but the on-disk section/key are
    "[ProjectDrive]" / "path".
    """
    ini = tools_root / "settings.ini"
    if not ini.exists():
        return None
    try:
        import configparser
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        cp.read(ini, encoding="utf-8-sig")
        for section in cp.sections():
            if section.strip().lower() == "projectdrive":
                for key, val in cp.items(section):
                    if key.strip().lower() == "path" and val.strip():
                        return Path(val.strip().strip('"').strip("'"))
    except (OSError, Exception):
        return None
    return None


def find_work_drive() -> Optional[Path]:
    """Locate the folder that should be mounted as P:\\.

    Resolution order, first existing folder wins:
      1. $DAYZ_WORK_DRIVE env var
      2. Cached path from prior successful mount
      3. <DayZ Tools install>\\settings.ini → [Project Space] WorkDirPath  (canonical)
      4. Registry under Bohemia Interactive\\DayZ Tools (legacy fallback)
      5. <DayZ Tools install>\\Bin\\WorkDrive\\ (last-resort default — usually empty)
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_WORK_DRIVE")
    if env_override:
        candidates.append(Path(env_override))

    cached = _read_cached_path()
    if cached:
        candidates.append(cached)

    tools = find_dayz_tools()
    if tools:
        ini_path = _read_settings_ini(tools)
        if ini_path:
            candidates.append(ini_path)

    if sys.platform == "win32":
        try:
            import winreg
        except ImportError:
            winreg = None  # type: ignore[assignment]
        if winreg is not None:
            registry_locations = [
                (winreg.HKEY_CURRENT_USER, r"Software\Bohemia Interactive\DayZ Tools"),
                (winreg.HKEY_CURRENT_USER, r"Software\bohemia interactive\dayz tools"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\bohemia interactive\dayz tools"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\bohemia interactive\dayz tools"),
            ]
            value_names = ("WorkDrive", "WorkDrivePath", "WorkDrive Path", "P:", "P_Drive", "PDrive")
            for hive, subkey in registry_locations:
                for value_name in value_names:
                    val = _read_registry_string(hive, subkey, value_name)
                    if val:
                        candidates.append(Path(val))

    if tools:
        candidates.append(tools / "Bin" / "WorkDrive")

    for cand in candidates:
        try:
            if cand.exists() and cand.is_dir():
                return cand
        except OSError:
            continue
    return None


def is_p_mounted() -> bool:
    p = Path(r"P:\\")
    try:
        return p.exists() and p.is_dir()
    except OSError:
        return False


def _find_workdrive_exe() -> Optional[Path]:
    tools = find_dayz_tools()
    if not tools:
        return None
    exe = tools / "Bin" / "WorkDrive" / "WorkDrive.exe"
    return exe if exe.exists() else None


def mount_via_workdrive(exe: Path, path: Path) -> bool:
    """Mount via DayZ Tools' official WorkDrive.exe /Mount [source].

    Args passed as a list so neither cmd nor MSYS Bash mangles `/Mount` into a path.
    """
    result = subprocess.run(
        [str(exe), "/Mount", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout).strip() or "(no output)"
        print(f"{WARN} WorkDrive.exe returned {result.returncode}: {msg}", file=sys.stderr)
        return False
    return True


def mount_via_subst(path: Path) -> bool:
    """Fallback: mount via Windows' built-in subst command."""
    result = subprocess.run(
        ["cmd", "/c", "subst", "P:", str(path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "(no output)"
        print(f"{FAIL} subst returned {result.returncode}: {msg}", file=sys.stderr)
        return False
    return True


def mount(path: Path) -> bool:
    """Mount path as P:\\. Prefer official WorkDrive.exe; fall back to subst."""
    exe = _find_workdrive_exe()
    if exe:
        print(f"{INFO} Using official WorkDrive.exe")
        if mount_via_workdrive(exe, path):
            return True
        print(f"{WARN} WorkDrive.exe failed; falling back to subst")
    else:
        print(f"{WARN} WorkDrive.exe not found; falling back to subst")
    return mount_via_subst(path)


def unmount() -> int:
    if not is_p_mounted():
        print(f"{INFO} P:\\ is not currently mounted")
        return 0
    exe = _find_workdrive_exe()
    if exe:
        print(f"{INFO} Using official WorkDrive.exe /Dismount")
        result = subprocess.run(
            [str(exe), "/Dismount"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and not is_p_mounted():
            print(f"{OK} P:\\ unmounted")
            return 0
        print(f"{WARN} WorkDrive.exe /Dismount returned {result.returncode}; falling back to subst /D")
    result = subprocess.run(
        ["cmd", "/c", "subst", "P:", "/D"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "(no output)"
        print(f"{FAIL} subst /D returned {result.returncode}: {msg}", file=sys.stderr)
        return 1
    print(f"{OK} P:\\ unmounted")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mount the P:\\ drive without opening DayZ Tools")
    parser.add_argument("--path", help="Explicit work drive path (overrides resolution)")
    parser.add_argument("--unmount", action="store_true", help="Unmount P:\\ instead of mounting")
    args = parser.parse_args()

    print("DayZ P:\\ mount\n")

    if sys.platform != "win32":
        print(f"{FAIL} This skill only runs on Windows (subst is Windows-only).", file=sys.stderr)
        return 1

    if args.unmount:
        return unmount()

    if is_p_mounted():
        print(f"{OK} P:\\ already mounted")
        return 0

    if args.path:
        work = Path(args.path)
        if not work.exists() or not work.is_dir():
            print(f"{FAIL} Path does not exist or is not a directory: {work}", file=sys.stderr)
            return 1
    else:
        work = find_work_drive()
        if not work:
            print(f"{FAIL} Could not resolve a work drive folder.", file=sys.stderr)
            print("        Tried: $DAYZ_WORK_DRIVE, cached path, registry, DayZ Tools\\Bin\\WorkDrive\\.", file=sys.stderr)
            print('        Pass --path "C:\\path\\to\\workdrive" to specify explicitly.', file=sys.stderr)
            print("        On first use, mount once via DayZ Tools to identify the path,", file=sys.stderr)
            print("        then unmount and pass --path here so the cache gets populated.", file=sys.stderr)
            return 1

    print(f"{INFO} Mounting P: -> {work}")
    if not mount(work):
        return 1

    if not is_p_mounted():
        print(f"{FAIL} subst returned 0 but P:\\ still isn't visible", file=sys.stderr)
        return 1

    _write_cached_path(work)
    print(f"{OK} P:\\ mounted -> {work}")
    print(f"{INFO} Cached for future runs at {CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
