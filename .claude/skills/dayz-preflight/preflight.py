"""DayZ preflight checks.

Verify the DayZ modding environment before any DayZ work. Hard-fails if P:\\ is
not mounted; warns on DayZ Tools, DayZ Diag, DayZ Server, vanilla data and the
P:\\Mods junction. The one thing it changes on disk is creating the
P:\\Mods -> <game>\\!Workshop junction when P:\\Mods is absent (see
validate_p_mods).

Path resolution order (first hit wins; each resolver's docstring has the detail):
    DayZ Tools:   $DAYZ_TOOLS_PATH, Windows registry, Steam libraries
    DayZ game:    $DAYZ_GAME_PATH, Steam libraries
    DayZ Diag:    $DAYZ_DIAG_PATH (the exe, or a folder holding it), the DayZ game
                  install, Steam libraries
    DayZ Server:  $DAYZ_SERVER_PATH, Steam libraries
    Vanilla data: $DAYZ_VANILLA_DATA_PATH, P:\\dz (no Steam fallback)
Steam libraries are the Steam root from the registry (or the default install
paths) plus every library in its steamapps\\libraryfolders.vdf.
A *_PATH variable whose value fails its check is skipped and the next source is
tried; the matching check_* function prints "[WARN] <VAR> ignored: <value>".

Run:
    python .claude/skills/dayz-preflight/preflight.py
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "

# Fixed by DayZ engine convention. Module-level so tests can point them at tmp dirs.
P_DRIVE = Path("P:\\")
MODS_LINK = P_DRIVE / "Mods"
# Windows paths are case-insensitive, so P:\dz also matches the P:\DZ that Extract Game Data writes.
VANILLA_DIR_NAMES = ("dz",)
# DZ_Scripts is unpacked beside P:\DZ, not inside it (P:\scripts\config.cpp:3 declares class DZ_Scripts).
VANILLA_SCRIPTS_DIR = "scripts"
DIAG_EXE = "DayZDiag_x64.exe"


def _is_tools_root(root: Path) -> bool:
    return (root / "Bin" / "AddonBuilder" / "AddonBuilder.exe").exists()


def _is_game_root(root: Path) -> bool:
    return (root / "DayZ_x64.exe").exists()


def _is_server_root(root: Path) -> bool:
    return (root / "DayZServer_x64.exe").exists()


def _is_nonempty_dir(path: Path) -> bool:
    try:
        return path.is_dir() and any(path.iterdir())
    except OSError:
        return False


def _diag_exe_in(path: Path) -> Optional[Path]:
    """DayZDiag_x64.exe given its own path or a folder holding it, else None."""
    if path.is_file() and path.name.lower() == DIAG_EXE.lower():
        return path
    if path.is_dir() and (path / DIAG_EXE).is_file():
        return path / DIAG_EXE
    return None


def warn_if_override_ignored(var: str, accepts, must: str) -> None:
    """Warn when env var `var` is set but `accepts(Path(value))` is False.

    The resolvers skip such a value and fall back to the next source, so without
    this warning the user could not tell that their setting had no effect.
    """
    value = os.environ.get(var)
    if value and not accepts(Path(value)):
        print(f"{WARN} {var} ignored: {value}")
        print(f"        It must be {must}.")


def read_registry_string(hive, subkey: str, value_name: str) -> Optional[str]:
    """Read a REG_SZ value from the Windows registry. Returns None if unavailable."""
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


def parse_library_folders(text: str) -> list[Path]:
    """Library roots listed in a Steam steamapps/libraryfolders.vdf file.

    VDF escapes backslashes, so "D:\\\\SteamLibrary" in the file is D:\\SteamLibrary.
    """
    return [
        Path(m.group(1).replace("\\\\", "\\"))
        for m in re.finditer(r'"path"\s+"([^"]+)"', text)
    ]


def _steam_common_dirs() -> list[Path]:
    """Every Steam library's steamapps/common dir on this machine.

    Resolves the Steam root via the registry (falling back to the default
    install paths), then parses steamapps/libraryfolders.vdf so games
    installed on non-default library drives are found too (#49).
    """
    steam_roots: list[Path] = []
    if sys.platform == "win32":
        import winreg

        for hive, subkey, value in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        ):
            val = read_registry_string(hive, subkey, value)
            if val:
                steam_roots.append(Path(val))
    steam_roots.extend(
        [
            Path(r"C:\Program Files (x86)\Steam"),
            Path(r"C:\Program Files\Steam"),
        ]
    )

    commons: list[Path] = []
    seen: set[str] = set()

    def add_library(lib_root: Path) -> None:
        common = lib_root / "steamapps" / "common"
        key = os.path.normcase(str(common))
        if key not in seen and common.is_dir():
            seen.add(key)
            commons.append(common)

    for root in steam_roots:
        add_library(root)
        vdf = root / "steamapps" / "libraryfolders.vdf"
        if vdf.is_file():
            try:
                text = vdf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lib in parse_library_folders(text):
                add_library(lib)
    return commons


def find_dayz_tools() -> Optional[Path]:
    """Locate the DayZ Tools install root.

    Resolution order:
      1. $DAYZ_TOOLS_PATH env var (explicit override)
      2. Windows registry (HKLM/HKCU under Bohemia Interactive\\DayZ Tools); every key
         with a Path value is tried, so a stale first entry cannot hide a valid later one
      3. Steam libraries

    Returns the first candidate root (parent of Bin/) holding AddonBuilder.exe, else None.
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_TOOLS_PATH")
    if env_override:
        candidates.append(Path(env_override))

    if sys.platform == "win32":
        import winreg

        registry_locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\bohemia interactive\dayz tools"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\bohemia interactive\dayz tools"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\bohemia interactive\dayz tools"),
        ]
        for hive, subkey in registry_locations:
            val = read_registry_string(hive, subkey, "Path")
            if val:
                candidates.append(Path(val))

    candidates.extend(common / "DayZ Tools" for common in _steam_common_dirs())

    for root in candidates:
        if _is_tools_root(root):
            return root
    return None


def find_dayz_game() -> Optional[Path]:
    """Locate the DayZ game install root containing DayZ_x64.exe.

    Resolution order:
      1. $DAYZ_GAME_PATH env var
      2. Steam libraries
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_GAME_PATH")
    if env_override:
        candidates.append(Path(env_override))

    candidates.extend(common / "DayZ" for common in _steam_common_dirs())

    for root in candidates:
        if _is_game_root(root):
            return root
    return None


def diag_from_env() -> Optional[Path]:
    """DayZDiag_x64.exe named by $DAYZ_DIAG_PATH, or None if unset or unusable.

    The value should be the full exe path. A folder is also accepted when it holds
    DayZDiag_x64.exe, since the other *_PATH overrides are folders. Anything else
    (a missing path, another file, a folder without the exe) is ignored.
    """
    value = os.environ.get("DAYZ_DIAG_PATH")
    if not value:
        return None
    return _diag_exe_in(Path(value))


def find_dayz_diag() -> Optional[Path]:
    """Locate DayZDiag_x64.exe, the diagnostic client required for mod development.

    Required because retail DayZ_x64.exe blocks past the loading screen with
    -filePatching enabled, and -filePatching is needed for live source iteration.
    DayZ Diag lives alongside the retail exe in the DayZ game install dir.

    Resolution order:
      1. $DAYZ_DIAG_PATH env var (see diag_from_env; an unusable value is skipped)
      2. Inside the DayZ game install (DayZDiag_x64.exe next to DayZ_x64.exe)
      3. Steam libraries

    Always returns the exe file itself, never a folder.
    """
    env_exe = diag_from_env()
    if env_exe is not None:
        return env_exe

    candidates: list[Path] = []
    game_root = find_dayz_game()
    if game_root is not None:
        candidates.append(game_root / DIAG_EXE)

    candidates.extend(common / "DayZ" / DIAG_EXE for common in _steam_common_dirs())

    for path in candidates:
        if path.is_file():
            return path
    return None


def find_dayz_server() -> Optional[Path]:
    """Locate the DayZ Server install root containing DayZServer_x64.exe.

    DayZ Server is a separate free Steam download (appid 223350), not bundled
    with the game.

    Resolution order:
      1. $DAYZ_SERVER_PATH env var
      2. Steam libraries
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_SERVER_PATH")
    if env_override:
        candidates.append(Path(env_override))

    candidates.extend(common / "DayZServer" for common in _steam_common_dirs())

    for root in candidates:
        if _is_server_root(root):
            return root
    return None


def find_vanilla_data() -> Optional[Path]:
    """Locate unpacked vanilla DayZ data on P:\\.

    Resolution order:
      1. $DAYZ_VANILLA_DATA_PATH env var
      2. P:\\dz (also matches P:\\DZ: Windows paths are case-insensitive)

    A candidate counts only if it exists and is non-empty.
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_VANILLA_DATA_PATH")
    if env_override:
        candidates.append(Path(env_override))

    candidates.extend(P_DRIVE / name for name in VANILLA_DIR_NAMES)

    for path in candidates:
        if _is_nonempty_dir(path):
            return path
    return None


def find_vanilla_scripts() -> Optional[Path]:
    """P:\\scripts (vanilla DZ_Scripts) if it exists and is non-empty, else None."""
    path = P_DRIVE / VANILLA_SCRIPTS_DIR
    return path if _is_nonempty_dir(path) else None


def check_p_drive() -> bool:
    """P:\\ is mandatory. Hard fail if not mounted."""
    if P_DRIVE.is_dir():
        print(f"{OK} P:\\ is mounted")
        return True
    print(f"{FAIL} P:\\ is NOT mounted", file=sys.stderr)
    print(
        "        Open DayZ Tools and mount the P drive "
        "(Tools menu > Mount P drive), or run /dayz-workdrive.",
        file=sys.stderr,
    )
    return False


def check_dayz_tools() -> None:
    """Look for AddonBuilder.exe via env / registry / Steam libraries. Warn only."""
    warn_if_override_ignored(
        "DAYZ_TOOLS_PATH", _is_tools_root,
        "the DayZ Tools folder, the one that holds Bin\\AddonBuilder\\AddonBuilder.exe",
    )
    root = find_dayz_tools()
    if root:
        print(f"{OK} DayZ Tools found: {root}")
        return
    print(f"{WARN} DayZ Tools not detected")
    print("        Tried: $DAYZ_TOOLS_PATH, Windows registry, Steam libraries.")
    print("        Set DAYZ_TOOLS_PATH if your install is elsewhere.")


def check_dayz_diag() -> None:
    """DayZDiag_x64.exe, which /dayz-launch-test needs. Warn only."""
    warn_if_override_ignored(
        "DAYZ_DIAG_PATH", lambda p: _diag_exe_in(p) is not None,
        f"the full path to {DIAG_EXE}, or a folder that holds it",
    )
    diag = find_dayz_diag()
    if diag:
        print(f"{OK} DayZ Diag found: {diag}")
        return
    print(f"{WARN} DayZ Diag (DayZDiag_x64.exe) not detected")
    print("        Tried: $DAYZ_DIAG_PATH, the DayZ game install, Steam libraries.")
    print("        /dayz-launch-test needs it. Update DayZ in Steam, or set DAYZ_DIAG_PATH.")


def check_dayz_server() -> None:
    """DayZ Server install, which /dayz-add-server copies mission templates from. Warn only."""
    warn_if_override_ignored(
        "DAYZ_SERVER_PATH", _is_server_root,
        "the DayZ Server folder, the one that holds DayZServer_x64.exe",
    )
    root = find_dayz_server()
    if root:
        print(f"{OK} DayZ Server found: {root}")
        return
    print(f"{WARN} DayZ Server (DayZServer_x64.exe) not detected")
    print("        Tried: $DAYZ_SERVER_PATH, Steam libraries.")
    print("        /dayz-add-server needs it. Install 'DayZ Server' from Steam's Tools")
    print("        section (free, appid 223350), or set DAYZ_SERVER_PATH.")


def check_vanilla_data() -> None:
    """Vanilla DayZ data unpacked under P:\\. Warn only."""
    warn_if_override_ignored(
        "DAYZ_VANILLA_DATA_PATH", _is_nonempty_dir,
        "a folder of unpacked vanilla data that exists and is not empty",
    )
    path = find_vanilla_data()
    if path:
        print(f"{OK} Vanilla data found: {path}")
    else:
        print(f"{WARN} Vanilla DayZ data not detected on P:\\")
        print("        Tried: $DAYZ_VANILLA_DATA_PATH, P:\\dz.")
        print("        Unpack vanilla PBOs via DayZ Tools 'Extract Game Data'.")
    scripts = find_vanilla_scripts()
    if scripts:
        print(f"{OK} Vanilla scripts found: {scripts}")
    else:
        print(f"{WARN} Vanilla scripts not detected: {P_DRIVE / VANILLA_SCRIPTS_DIR} is missing or empty")
        print("        Linting and vanilla search need DZ_Scripts there.")
        print("        Re-run DayZ Tools 'Extract Game Data' so it unpacks scripts.pbo too.")


def link_target(path: Path) -> Optional[Path]:
    """Target of a junction or symlink without the \\\\?\\ prefix; None if `path` is not a link."""
    try:
        target = os.readlink(path)
    except (OSError, ValueError):
        return None
    return Path(target[4:] if target.startswith("\\\\?\\") else target)


def _create_junction(link: Path, target: Path) -> None:
    """Create a directory junction (mklink /J needs no admin rights). Raises OSError on failure."""
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise OSError(detail or f"mklink exited {result.returncode}")


def paths_equal(a: Path, b: Path) -> bool:
    """True when two paths name the same location (case and separator insensitive)."""
    return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))


def validate_p_mods() -> Optional[str]:
    """Make sure P:\\Mods\\ is a junction to <DayZ install>\\!Workshop\\.

    Built PBOs deploy under P:\\Mods\\@<Mod>\\Addons\\; the junction makes them land
    in the folder the engine and Launcher actually load mods from.

    - P:\\Mods absent and the game's !Workshop folder found: create the junction
      (mklink /J is non-destructive and the target is canonical), return None.
    - P:\\Mods absent, game found but its !Workshop folder missing: return an
      error naming the folder to create. Nothing is created.
    - P:\\Mods is a real folder, a dangling link, or a link to anywhere other
      than <game>\\!Workshop: return an error. An existing path is never changed.
    - Game install not locatable: a live link whose target folder is named
      !Workshop is accepted, since the exact target can't be checked.

    Returns None when the junction is valid, else a multi-line error with the fix.
    Preflight prints it as a warning; build and deploy skills hard-fail on it.
    """
    mods = MODS_LINK
    game_root = find_dayz_game()
    workshop = game_root / "!Workshop" if game_root else None
    expected = str(workshop) if workshop else "<DayZ install>\\!Workshop"
    fix_cmd = f'cmd /c mklink /J P:\\Mods "{expected}"'

    if not os.path.lexists(mods):
        if workshop is None:
            return (
                "P:\\Mods\\ does not exist and was not created: the DayZ install was\n"
                "       not found (set DAYZ_GAME_PATH if DayZ is installed somewhere unusual).\n"
                f"       Fix: {fix_cmd}"
            )
        if not workshop.is_dir():
            return (
                "P:\\Mods\\ does not exist and was not created: DayZ is installed at\n"
                f"       {game_root}, but its !Workshop folder does not exist yet.\n"
                "       Fix: create the folder, then run preflight again to create the junction:\n"
                f'         mkdir "{workshop}"'
            )
        try:
            _create_junction(mods, workshop)
        except OSError as e:
            return (
                f"P:\\Mods\\ does not exist and creating the junction failed: {e}\n"
                f"       Fix: {fix_cmd}"
            )
        print(f"{OK} Created junction P:\\Mods -> {workshop}")
        return None

    target_path = link_target(mods)
    if target_path is None:
        return (
            "P:\\Mods\\ exists as a regular folder, not a junction.\n"
            "       Built PBOs deployed under P:\\Mods\\@<Mod>\\Addons\\ will be\n"
            "       invisible to the engine.\n"
            "       Fix: move its contents out, remove the folder and create a junction:\n"
            "         cmd /c rmdir P:\\Mods\n"
            f"         {fix_cmd}"
        )

    if not target_path.exists():
        return (
            f"P:\\Mods\\ junction is dangling (target {target_path} is missing).\n"
            "       Fix: remove and recreate the junction with a valid target:\n"
            "         cmd /c rmdir P:\\Mods\n"
            f"         {fix_cmd}"
        )

    if workshop is not None:
        wrong_target = not paths_equal(target_path, workshop)
    else:
        wrong_target = target_path.name.lower() != "!workshop"
    if wrong_target:
        return (
            f"P:\\Mods\\ points to {target_path}, not {expected}.\n"
            "       Built PBOs would not land where the engine loads mods.\n"
            "       Fix: remove and recreate the junction:\n"
            "         cmd /c rmdir P:\\Mods\n"
            f"         {fix_cmd}"
        )

    return None


def check_workshop_deploy() -> None:
    """Check (or create) the P:\\Mods junction. Warn only here.

    Build and deploy skills hard-fail on the same condition by calling
    validate_p_mods() directly.
    """
    warn_if_override_ignored(
        "DAYZ_GAME_PATH", _is_game_root,
        "the DayZ game folder, the one that holds DayZ_x64.exe",
    )
    err = validate_p_mods()
    if err is None:
        print(f"{OK} P:\\Mods -> {link_target(MODS_LINK)}")
        return
    print(f"{WARN} {err}")


def main(argv: Optional[list[str]] = None) -> int:
    argparse.ArgumentParser(
        description="Check the P:\\ drive, DayZ Tools, DayZ Diag, DayZ Server, vanilla data and the P:\\Mods junction "
                    "(creates the junction when P:\\Mods is missing). Takes no options.",
    ).parse_args(argv)
    print("DayZ preflight\n", flush=True)
    if not check_p_drive():
        return 1
    check_dayz_tools()
    check_dayz_diag()
    check_dayz_server()
    check_vanilla_data()
    check_workshop_deploy()
    print("\nPreflight complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
