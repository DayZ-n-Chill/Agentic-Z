r"""dayz-workdrive: Mount P:\ as the DayZ work drive without DayZ Tools' GUI.

Resolves the work-drive folder (env var, cache, settings.ini, registry)
and mounts it via DayZ Tools' WorkDrive.exe /Mount, falling back to Windows'
built-in subst command. Idempotent: exits OK if already mounted.

This skill does not gate on /dayz-preflight: preflight checks
that P:\ is mounted, this skill mounts it.

Usage:
    python .claude/skills/dayz-workdrive/mount.py
    python .claude/skills/dayz-workdrive/mount.py --path "C:\P Drives\Vanilla"
    python .claude/skills/dayz-workdrive/mount.py --unmount
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# The cache is per project, resolved by dayz-init/state.py: $CLAUDE_PROJECT_DIR,
# else the nearest folder at or above the current directory that holds the
# project cache, else the current directory. Not the script's own folder, which
# is the shared plugin cache on a plugin install.
PROJECT_DIR = h.load_module("dayz_workdrive_state", h.DAYZ_INIT_STATE).find_project_dir()
CACHE = PROJECT_DIR / ".claude" / "local-memory" / "dayz-work-drive.json"
P_DRIVE = Path("P:\\")

OK = h.OK
INFO = "[INFO] "
WARN = h.WARN
FAIL = h.FAIL
CMD = "[CMD]  "

# Reuse preflight's resolvers (loading the module does not run its checks).
find_dayz_tools = h.preflight.find_dayz_tools
read_registry_string = h.preflight.read_registry_string
paths_equal = h.preflight.paths_equal


def is_p_mounted() -> bool:
    return P_DRIVE.is_dir()


def current_p_target() -> Optional[Path]:
    r"""Folder P: is mapped to, or None if it is not a folder mapping.

    WorkDrive.exe and subst both create a DOS device mapping, which
    QueryDosDeviceW reports as "\??\C:\folder".
    """
    if sys.platform != "win32":
        return None
    import ctypes

    buf = ctypes.create_unicode_buffer(1024)
    if not ctypes.windll.kernel32.QueryDosDeviceW("P:", buf, len(buf)):
        return None
    prefix = "\\??\\"
    if not buf.value.startswith(prefix):
        return None  # a volume or network device, not a folder mapping
    return Path(buf.value[len(prefix):])


def get_cached_path() -> Optional[Path]:
    if not CACHE.exists():
        return None
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
        p = data.get("work_drive_path")
        if p and Path(p).is_dir():
            return Path(p)
    except (OSError, json.JSONDecodeError):
        pass
    return None


def set_cached_path(p: Path) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"work_drive_path": str(p)}), encoding="utf-8")


def read_settings_ini_path(tools_root: Path) -> Optional[Path]:
    """Parse <tools>/settings.ini for the [ProjectDrive] path= line."""
    ini = tools_root / "settings.ini"
    if not ini.exists():
        return None
    section = ""
    try:
        for raw in ini.read_text(encoding="utf-8", errors="replace").splitlines():
            t = raw.strip()
            if t.startswith("[") and t.endswith("]"):
                section = t[1:-1].strip().lower()
                continue
            if section == "projectdrive" and "=" in t:
                key, _, value = t.partition("=")
                if key.strip().lower() == "path":
                    v = value.strip().strip('"').strip("'")
                    if v:
                        return Path(v)
    except OSError:
        return None
    return None


def find_work_drive() -> Optional[Path]:
    """Resolve the work-drive folder. Returns the first candidate that exists.

    Resolution order:
      1. $DAYZ_WORK_DRIVE env var
      2. Cached path from prior run
      3. <DayZ Tools>/settings.ini [ProjectDrive] path=
      4. Registry values WorkDrive / WorkDrivePath / P_Drive / PDrive under
         3 well-known DayZ Tools keys (HKCU + HKLM 64-bit + HKLM 32-bit)

    There is no default: <DayZ Tools>/Bin/WorkDrive holds WorkDrive.exe itself,
    not a project drive, so mounting it would be wrong. Returns None instead and
    the caller asks for --path.
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_WORK_DRIVE")
    if env_override:
        candidates.append(Path(env_override))

    cached = get_cached_path()
    if cached:
        candidates.append(cached)

    tools = find_dayz_tools()
    if tools:
        ini_path = read_settings_ini_path(tools)
        if ini_path:
            candidates.append(ini_path)

    if sys.platform == "win32":
        try:
            import winreg
        except ImportError:
            winreg = None  # type: ignore[assignment]
        if winreg is not None:
            registry_keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Bohemia Interactive\DayZ Tools"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\bohemia interactive\dayz tools"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\bohemia interactive\dayz tools"),
            ]
            for hive, subkey in registry_keys:
                for value_name in ("WorkDrive", "WorkDrivePath", "P_Drive", "PDrive"):
                    val = read_registry_string(hive, subkey, value_name)
                    if val:
                        candidates.append(Path(val))

    for c in candidates:
        if c and c.is_dir():
            return c
    return None


def find_workdrive_exe() -> Optional[Path]:
    tools = find_dayz_tools()
    if not tools:
        return None
    exe = tools / "Bin" / "WorkDrive" / "WorkDrive.exe"
    return exe if exe.exists() else None


def _run_workdrive(args: list[str]) -> tuple[int, str, str]:
    """Run WorkDrive.exe and capture both streams.

    WorkDrive.exe ends with "press any key" then crashes (Unhandled Exception)
    when stdin is redirected. The work itself completes BEFORE the prompt, so
    callers should check actual P:\\ state rather than trusting the rc/stderr.
    Captured stderr is returned so callers can surface it ONLY on real failure.
    """
    result = subprocess.run(
        args,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def invoke_mount(target: Path) -> bool:
    exe = find_workdrive_exe()
    if exe:
        print(f'{CMD}"{exe}" /Mount "{target}"')
        rc, _stdout, stderr = _run_workdrive([str(exe), "/Mount", str(target)])
        if is_p_mounted():
            return True
        print(f"{WARN}WorkDrive.exe completed but P:\\ not visible (rc={rc}); falling back to subst")
        if stderr.strip():
            print(stderr.rstrip(), file=sys.stderr)
    else:
        print(f"{WARN}WorkDrive.exe not found; falling back to subst")

    print(f'{CMD}subst P: "{target}"')
    rc = subprocess.run(["subst", "P:", str(target)]).returncode
    if is_p_mounted():
        return True
    print(f"{FAIL}subst P: exited with code {rc}; P:\\ is not mounted", file=sys.stderr)
    return False


def invoke_unmount() -> int:
    if not is_p_mounted():
        print(f"{INFO}P:\\ is not currently mounted")
        return 0

    exe = find_workdrive_exe()
    if exe:
        print(f'{CMD}"{exe}" /Dismount')
        rc, _stdout, stderr = _run_workdrive([str(exe), "/Dismount"])
        if not is_p_mounted():
            print(f"{OK}P:\\ unmounted")
            return 0
        print(f"{WARN}WorkDrive.exe /Dismount completed but P:\\ still visible (rc={rc}); falling back to subst /D")
        if stderr.strip():
            print(stderr.rstrip(), file=sys.stderr)

    print(f"{CMD}subst P: /D")
    rc = subprocess.run(["subst", "P:", "/D"]).returncode
    if rc != 0 or is_p_mounted():
        print(f"{FAIL}subst /D returned {rc}; P:\\ still mounted={is_p_mounted()}", file=sys.stderr)
        return 1
    print(f"{OK}P:\\ unmounted")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mount P:\\ as the DayZ work drive (Windows-only).",
    )
    parser.add_argument(
        "--path",
        help='Explicit work-drive folder (e.g. "C:\\P Drives\\Vanilla")',
    )
    parser.add_argument(
        "--unmount",
        action="store_true",
        help="Unmount P:\\ instead of mounting",
    )
    args = parser.parse_args()

    print("DayZ P:\\ mount\n")

    if args.unmount:
        return invoke_unmount()

    if is_p_mounted():
        current = current_p_target()
        print(f"{OK}P:\\ already mounted" + (f" -> {current}" if current else ""))
        if args.path and current and not paths_equal(current, Path(args.path)):
            print(f"{WARN}--path was not used: P:\\ already points to {current}, not {args.path}.")
            print("       Run with --unmount first, then mount again with --path.")
        elif args.path and current is None:
            print(f"{WARN}--path was not used: P:\\ is mounted to something that is not a folder mapping "
                  f"(a volume or network drive), not {args.path}.")
            print("       Run with --unmount first, then mount again with --path.")
        return 0

    if args.path:
        work = Path(args.path)
        if not work.is_dir():
            print(f"{FAIL}Path does not exist or is not a directory: {work}", file=sys.stderr)
            return 1
    else:
        work = find_work_drive()
        if not work:
            print(f"{FAIL}Could not resolve a work drive folder.", file=sys.stderr)
            print(
                "       Tried: $DAYZ_WORK_DRIVE, cached path, settings.ini, registry.",
                file=sys.stderr,
            )
            print(
                '       Pass --path "C:\\path\\to\\workdrive" with the folder P:\\ should show '
                "(it is cached for later runs).",
                file=sys.stderr,
            )
            return 1

    print(f"{INFO}Mounting P: -> {work}")
    if not invoke_mount(work):
        return 1

    set_cached_path(work)
    print(f"{OK}P:\\ mounted -> {work}")
    print(f"{INFO}Cached for future runs at {CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
