r"""dayz-workdrive: Mount P:\ as the DayZ work drive without DayZ Tools' GUI.

Resolves the work-drive folder (env var, cache, settings.ini)
and mounts it via DayZ Tools' WorkDrive.exe /Mount, falling back to Windows'
built-in subst command. Idempotent: exits OK if already mounted.

This skill does not gate on /dayz-preflight: preflight checks
that P:\ is mounted, this skill mounts it.

Usage:
    python skills/dayz-workdrive/mount.py
    python skills/dayz-workdrive/mount.py --path "C:\P Drives\Vanilla"
    python skills/dayz-workdrive/mount.py --unmount [--force]
"""
from __future__ import annotations

import argparse
import csv
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

# WorkDrive.exe normally finishes in seconds; past this it is treated as hung.
WORKDRIVE_TIMEOUT = 60

# Processes that work from P:\ and break when it disappears under them: the DayZ
# Tools apps (names as installed under <DayZ Tools>\Bin\Workbench, \ObjectBuilder,
# \AddonBuilder, \Binarize) and the diag game that /dayz-launch-test runs.
# Lower-case, because Windows image names are case-insensitive.
P_DRIVE_USERS = (
    "workbenchapp.exe",
    "objectbuilder.exe",
    "addonbuilder.exe",
    "binarize.exe",
    "dayzdiag_x64.exe",
)

# Hint for a P: letter this skill did not create and cannot remove.
FREE_LETTER_HINT = "       Free the letter in Disk Management, or with 'net use P: /delete' for a network drive."

# Reuse preflight's resolvers (loading the module does not run its checks).
find_dayz_tools = h.preflight.find_dayz_tools
paths_equal = h.preflight.paths_equal


def is_p_mounted() -> bool:
    """True when P:\\ is visible as a folder (the mapping exists and its target is reachable)."""
    return P_DRIVE.is_dir()


def query_p_device() -> Optional[str]:
    r"""What the P: drive letter is assigned to, or None when the letter is free.

    This reads the drive-letter mapping itself, so it still reports a mapping
    whose folder was renamed, deleted or sits on an unplugged disk, while P:\
    then reads as not a directory. A folder mapping reads "\??\C:\folder", a
    volume "\Device\HarddiskVolume3", a network drive "\Device\LanmanRedirector\...".
    """
    if sys.platform != "win32":
        return None
    import ctypes

    buf = ctypes.create_unicode_buffer(1024)
    if not ctypes.windll.kernel32.QueryDosDeviceW("P:", buf, len(buf)):
        return None
    return buf.value or None


def current_p_target() -> Optional[Path]:
    r"""Folder P: is mapped to, or None if it is not a folder mapping.

    WorkDrive.exe and subst both create a DOS device mapping, which
    QueryDosDeviceW reports as "\??\C:\folder". The folder may be missing.
    """
    device = query_p_device()
    prefix = "\\??\\"
    if not device or not device.startswith(prefix):
        return None  # letter free, or a volume or network device
    return Path(device[len(prefix):])


def p_letter_in_use() -> bool:
    """True while P:\\ is visible or any mapping still holds the letter, even a stale one."""
    return is_p_mounted() or query_p_device() is not None


def get_cached_path() -> Optional[Path]:
    if not CACHE.exists():
        return None
    try:
        data = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    # Valid JSON that is not the {"work_drive_path": "..."} object counts as no cache.
    if not isinstance(data, dict):
        return None
    p = data.get("work_drive_path")
    if isinstance(p, str) and p and Path(p).is_dir():
        return Path(p)
    return None


def set_cached_path(p: Path) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"work_drive_path": str(p)}), encoding="utf-8")


def _read_projectdrive_value(tools_root: Path, name: str) -> Optional[str]:
    """Return a non-empty [ProjectDrive] <name>= value from <tools>/settings.ini."""
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
                if key.strip().lower() == name:
                    v = value.strip().strip('"').strip("'")
                    if v:
                        return v
    except OSError:
        return None
    return None


def read_settings_ini_path(tools_root: Path) -> Optional[Path]:
    """Parse <tools>/settings.ini for the [ProjectDrive] path= line."""
    v = _read_projectdrive_value(tools_root, "path")
    return Path(v) if v else None


def read_settings_ini_letter(tools_root: Path) -> Optional[str]:
    """Parse <tools>/settings.ini for the [ProjectDrive] Letter= line, upper-cased without a colon."""
    v = _read_projectdrive_value(tools_root, "letter")
    return v.rstrip(":").upper() if v else None


def workdrive_letter_is_not_p() -> Optional[str]:
    """The letter DayZ Tools is set to mount when it is not P, else None.

    WorkDrive.exe mounts the letter in settings.ini, so with another letter it
    never creates P:\\ and running it would only add a second mount.
    """
    tools = find_dayz_tools()
    letter = read_settings_ini_letter(tools) if tools else None
    return letter if letter and letter != "P" else None


def find_work_drive() -> tuple[Optional[Path], Optional[str]]:
    """Resolve the work-drive folder: (first candidate that exists, its source), or (None, None).

    Resolution order:
      1. $DAYZ_WORK_DRIVE env var, made absolute against the current folder
      2. Cached path from prior run
      3. <DayZ Tools>/settings.ini [ProjectDrive] path=

    An env var or settings.ini value that is set but is not a folder (a typo, a
    renamed folder) gets a [WARN] naming it before the next source is tried, so
    a different folder is never mounted silently.

    The DayZ Tools registry keys hold no work-drive folder (HKCU only has
    path, exe, version and patch), so they are not a source. There is no
    default: <DayZ Tools>/Bin/WorkDrive holds WorkDrive.exe itself, not a
    project drive, so mounting it would be wrong. Returns (None, None) instead
    and the caller asks for --path.
    """
    env_override = os.environ.get("DAYZ_WORK_DRIVE")
    if env_override:
        # Absolute for the same reason as --path: the folder is cached, and a
        # relative one would point elsewhere when a later run starts in another folder.
        env_path = Path(env_override).resolve()
        if env_path.is_dir():
            return env_path, "$DAYZ_WORK_DRIVE"
        print(f"{WARN}$DAYZ_WORK_DRIVE is set to {env_override}, which is not a folder; ignoring it.")

    cached = get_cached_path()
    if cached:
        return cached, f"cache {CACHE}"

    tools = find_dayz_tools()
    if tools:
        ini_path = read_settings_ini_path(tools)
        if ini_path:
            if ini_path.is_dir():
                return ini_path, f"{tools / 'settings.ini'}"
            print(f"{WARN}{tools / 'settings.ini'} sets [ProjectDrive] path={ini_path}, "
                  "which is not a folder; ignoring it.")
    return None, None


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
    If it is still running after WORKDRIVE_TIMEOUT seconds (stuck at the prompt
    instead of crashing) it is killed and rc is -1, so callers check P:\\ and
    fall through to subst instead of hanging.
    """
    try:
        result = subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=WORKDRIVE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return -1, "", f"WorkDrive.exe did not exit within {WORKDRIVE_TIMEOUT}s and was stopped"
    return result.returncode, result.stdout, result.stderr


def invoke_mount(target: Path) -> bool:
    other = workdrive_letter_is_not_p()
    exe = None if other else find_workdrive_exe()
    if other:
        print(f"{WARN}DayZ Tools' settings.ini sets [ProjectDrive] Letter={other}, so WorkDrive.exe "
              f"would mount {other}: instead of P:\\. Using subst P: instead.")
    elif exe:
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


def parse_tasklist_images(output: str) -> list[str]:
    """Image names (first column) from `tasklist /FO CSV /NH` output."""
    return [row[0] for row in csv.reader(output.splitlines()) if row]


def running_p_drive_users() -> Optional[list[str]]:
    """Sorted, de-duplicated names of running processes listed in P_DRIVE_USERS.

    Returns None when the process list is unknown: tasklist could not start,
    exited non-zero, or printed nothing (a working tasklist always lists at
    least the System Idle Process). The caller must not read None as "none
    running".
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace"
        )
    except OSError:
        return None
    if result.returncode != 0 or not (result.stdout or "").strip():
        return None
    found = {n for n in parse_tasklist_images(result.stdout) if n.lower() in P_DRIVE_USERS}
    return sorted(found, key=str.lower)


def remove_stale_mapping(target: Path) -> int:
    """Remove a P: folder mapping whose folder is missing.

    No process can be working from P:\\ while it is not visible, so the
    running-process guard does not apply here.
    """
    print(f"{INFO}P: is mapped to {target}, which is missing; removing the stale mapping")
    print(f"{CMD}subst P: /D")
    rc = subprocess.run(["subst", "P:", "/D"]).returncode
    if p_letter_in_use():
        print(f"{FAIL}subst P: /D exited with code {rc}; the stale P: mapping to {target} is still there.",
              file=sys.stderr)
        print("       It may belong to another Windows session; signing out or restarting Windows clears it.",
              file=sys.stderr)
        return 1
    print(f"{OK}Stale P: mapping removed")
    return 0


def invoke_unmount(force: bool = False) -> int:
    if not is_p_mounted():
        stale = current_p_target()
        if stale is not None:
            return remove_stale_mapping(stale)
        device = query_p_device()
        if device is not None:
            print(f"{FAIL}Not unmounting: P: is assigned to {device}, which is not reachable and is not "
                  "a folder mapping made by WorkDrive.exe or subst, so this skill cannot remove it.",
                  file=sys.stderr)
            print(FREE_LETTER_HINT, file=sys.stderr)
            return 1
        print(f"{INFO}P:\\ is not currently mounted")
        return 0

    # subst /D and WorkDrive.exe /Dismount only remove folder mappings; on a real
    # volume or network drive they would fail with nothing but an exit code.
    if current_p_target() is None:
        device = query_p_device() or "an unknown device"
        print(f"{FAIL}Not unmounting: P:\\ is {device} (a volume or network drive), not a folder "
              "mapping made by WorkDrive.exe or subst.", file=sys.stderr)
        print(FREE_LETTER_HINT, file=sys.stderr)
        return 1

    # Pulling P:\ out from under Workbench, Object Builder, a build or DayZDiag breaks
    # those sessions, so refuse unless the user asked for it with --force. A process
    # list that could not be read counts as "maybe running", never as "none running".
    users = running_p_drive_users()
    if users is None:
        if not force:
            print(f"{FAIL}Not unmounting: tasklist failed, so it is unknown whether DayZ Tools "
                  "or DayZDiag is running from P:\\.", file=sys.stderr)
            print("       Close them first (/dayz-stop-test stops DayZDiag), "
                  "then re-run with --unmount --force.", file=sys.stderr)
            return 1
        print(f"{WARN}--force: could not list running processes; unmounting without checking "
              "for DayZ Tools or DayZDiag")
    elif users:
        names = ", ".join(users)
        if not force:
            print(f"{FAIL}Not unmounting: {names} is running and works from P:\\. "
                  "Unmounting now breaks those open sessions.", file=sys.stderr)
            print("       Close them first (/dayz-stop-test stops DayZDiag), "
                  "or re-run with --unmount --force.", file=sys.stderr)
            return 1
        print(f"{WARN}--force: unmounting while {names} is running; those sessions lose P:\\")

    # With another letter in settings.ini, WorkDrive.exe /Dismount would target that letter, not P:.
    exe = None if workdrive_letter_is_not_p() else find_workdrive_exe()
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
    parser.add_argument(
        "--force",
        action="store_true",
        help="With --unmount: unmount even while DayZ Tools or DayZDiag is running from P:\\",
    )
    args = parser.parse_args()
    if args.force and not args.unmount:
        parser.error("--force only applies to --unmount")
    if args.path and args.unmount:
        parser.error("--path cannot be combined with --unmount")
    if sys.platform != "win32":
        print(f"{FAIL}Windows-only: P:\\ is a Windows drive letter mounted with WorkDrive.exe or subst, "
              f"and this is {sys.platform}.", file=sys.stderr)
        return 1
    # Absolute before comparing, mounting or caching: a relative --path cached as-is
    # would point somewhere else (or nowhere) when the next run starts in another folder.
    explicit = Path(args.path).resolve() if args.path else None

    print("DayZ P:\\ mount\n")

    if args.unmount:
        return invoke_unmount(force=args.force)

    if is_p_mounted():
        current = current_p_target()
        print(f"{OK}P:\\ already mounted" + (f" -> {current}" if current else ""))
        if explicit and current and not paths_equal(current, explicit):
            print(f"{WARN}--path was not used: P:\\ already points to {current}, not {explicit}.")
            print("       Run with --unmount first, then mount again with --path.")
        elif explicit and current is None:
            print(f"{WARN}--path was not used: P:\\ is mounted to something that is not a folder mapping "
                  f"(a volume or network drive), not {explicit}.")
            print("       Run with --unmount first, then mount again with --path.")
        return 0

    # P:\ is not visible, but a mapping can still hold the letter: one whose folder
    # is gone, or an unreachable volume or network drive. subst P: would then fail
    # with nothing but an exit code, so name the cause and the fix.
    stale = current_p_target()
    if stale is not None:
        print(f"{FAIL}P: is mapped to a missing folder {stale}; run --unmount to remove the stale "
              "mapping, then mount again.", file=sys.stderr)
        return 1
    device = query_p_device()
    if device is not None:
        print(f"{FAIL}P: is assigned to {device}, which is not reachable, so P:\\ cannot be mounted.",
              file=sys.stderr)
        print(FREE_LETTER_HINT, file=sys.stderr)
        return 1

    if explicit:
        work, source = explicit, "--path"
        if not work.is_dir():
            print(f"{FAIL}Path does not exist or is not a directory: {work}", file=sys.stderr)
            return 1
    else:
        work, source = find_work_drive()
        if not work:
            print(f"{FAIL}Could not resolve a work drive folder.", file=sys.stderr)
            print(
                "       Tried: $DAYZ_WORK_DRIVE, cached path, settings.ini.",
                file=sys.stderr,
            )
            print(
                '       Pass --path "C:\\path\\to\\workdrive" with the folder P:\\ should show '
                "(it is cached for later runs).",
                file=sys.stderr,
            )
            return 1

    print(f"{INFO}Mounting P: -> {work} (from {source})")
    if not invoke_mount(work):
        return 1

    # P:\\ being visible is not enough: confirm it shows the requested folder
    # before caching it, so a wrong mount is never reported as OK or reused.
    mounted = current_p_target()
    if mounted is None or not paths_equal(mounted, work):
        shown = mounted if mounted is not None else (query_p_device() or "an unknown device")
        print(f"{FAIL}P:\\ is mounted but points to {shown}, not {work}; nothing was cached.",
              file=sys.stderr)
        print("       Run with --unmount, then mount again (pass --path to choose the folder).",
              file=sys.stderr)
        return 1

    print(f"{OK}P:\\ mounted -> {work}")
    try:
        set_cached_path(work)
    except OSError as e:
        print(f"{WARN}P:\\ is mounted, but the folder was not cached at {CACHE}: {e}")
        print("       The next run resolves the folder again; pass --path or set $DAYZ_WORK_DRIVE if it cannot.")
        return 0
    print(f"{INFO}Cached for future runs at {CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
