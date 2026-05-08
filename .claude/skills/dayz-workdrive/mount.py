r"""dayz-workdrive: Mount P:\ as the DayZ work drive without DayZ Tools' GUI.

Resolves the work-drive folder (env var, cache, settings.ini, registry, fallback)
and mounts it via DayZ Tools' WorkDrive.exe /Mount, falling back to Windows'
built-in subst command. Idempotent: exits OK if already mounted.

This skill does NOT gate on /dayz-preflight — chicken-and-egg: preflight checks
that P:\ is mounted, this skill mounts it.

Usage:
    python .claude/skills/dayz-workdrive/mount.py
    python .claude/skills/dayz-workdrive/mount.py --path "C:\P Drives\Vanilla"
    python .claude/skills/dayz-workdrive/mount.py --unmount
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
CACHE = PROJECT_DIR / ".claude" / "local-memory" / "dayz-work-drive.json"
P_DRIVE = Path("P:\\")
PREFLIGHT = REPO_ROOT / ".claude" / "skills" / "dayz-preflight" / "preflight.py"

OK = "[OK]   "
INFO = "[INFO] "
WARN = "[WARN] "
FAIL = "[FAIL] "
CMD = "[CMD]  "


def _load_preflight_module():
    spec = importlib.util.spec_from_file_location("dayz_preflight_module", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preflight module at {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reuse preflight's find_dayz_tools (env DAYZ_TOOLS_PATH -> 3 registry keys ->
# common Steam paths, validated by AddonBuilder.exe presence). Importing the
# module here does NOT run preflight's gate — it just exposes the helper.
find_dayz_tools = _load_preflight_module().find_dayz_tools


def is_p_mounted() -> bool:
    return P_DRIVE.is_dir()


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


def find_work_drive() -> Optional[Path]:
    """Resolve the work-drive folder. Returns the first candidate that exists.

    Resolution order:
      1. $DAYZ_WORK_DRIVE env var
      2. Cached path from prior run
      3. <DayZ Tools>/settings.ini [ProjectDrive] path=
      4. Registry values WorkDrive / WorkDrivePath / P_Drive / PDrive under
         3 well-known DayZ Tools keys (HKCU + HKLM 64-bit + HKLM 32-bit)
      5. <DayZ Tools>/Bin/WorkDrive (default location DayZ Tools creates)
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
                    val = _read_registry_string(hive, subkey, value_name)
                    if val:
                        candidates.append(Path(val))

    if tools:
        candidates.append(tools / "Bin" / "WorkDrive")

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
    subprocess.run(["subst", "P:", str(target)], shell=True)
    return is_p_mounted()


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
    rc = subprocess.run(["subst", "P:", "/D"], shell=True).returncode
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
        print(f"{OK}P:\\ already mounted")
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
                "       Tried: $DAYZ_WORK_DRIVE, cached path, settings.ini, registry, "
                "DayZ Tools\\Bin\\WorkDrive\\.",
                file=sys.stderr,
            )
            print('       Pass --path "C:\\path\\to\\workdrive" to specify explicitly.', file=sys.stderr)
            return 1

    print(f"{INFO}Mounting P: -> {work}")
    if not invoke_mount(work):
        return 1

    if not is_p_mounted():
        print(f"{FAIL}Mount returned 0 but P:\\ still isn't visible", file=sys.stderr)
        return 1

    set_cached_path(work)
    print(f"{OK}P:\\ mounted -> {work}")
    print(f"{INFO}Cached for future runs at {CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
