"""DayZ preflight checks.

Verify the DayZ modding environment before any DayZ work. Hard-fails if P:\\ is
not mounted; warns on Tools / vanilla data / workshop folder.

Path resolution order (DayZ Tools, vanilla data):
    1. Environment variable override
    2. Windows registry (DayZ Tools only)
    3. Hard-coded common-default fallbacks

Run:
    python .claude/skills/dayz-preflight/preflight.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def _read_registry_string(hive, subkey: str, value_name: str) -> Optional[str]:
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


def find_dayz_tools() -> Optional[Path]:
    """Locate the DayZ Tools install root.

    Resolution order:
      1. $DAYZ_TOOLS_PATH env var (explicit override)
      2. Windows registry (HKLM/HKCU under Bohemia Interactive\\DayZ Tools)
      3. Common Steam install paths

    Returns the install root (parent of Bin/) if AddonBuilder.exe is found, else None.
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_TOOLS_PATH")
    if env_override:
        candidates.append(Path(env_override))

    if sys.platform == "win32":
        try:
            import winreg
        except ImportError:
            winreg = None  # type: ignore[assignment]
        if winreg is not None:
            registry_locations = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\bohemia interactive\dayz tools"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\bohemia interactive\dayz tools"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\bohemia interactive\dayz tools"),
            ]
            for hive, subkey in registry_locations:
                val = _read_registry_string(hive, subkey, "Path")
                if val:
                    candidates.append(Path(val))
                    break

    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZ Tools"),
            Path(r"C:\Program Files\Steam\steamapps\common\DayZ Tools"),
        ]
    )

    for root in candidates:
        if (root / "Bin" / "AddonBuilder" / "AddonBuilder.exe").exists():
            return root
    return None


def find_dayz_game() -> Optional[Path]:
    """Locate the DayZ game install root containing DayZ_x64.exe.

    Resolution order:
      1. $DAYZ_GAME_PATH env var
      2. Common Steam install paths
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_GAME_PATH")
    if env_override:
        candidates.append(Path(env_override))

    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZ"),
            Path(r"C:\Program Files\Steam\steamapps\common\DayZ"),
        ]
    )

    for root in candidates:
        if (root / "DayZ_x64.exe").exists():
            return root
    return None


def find_dayz_diag() -> Optional[Path]:
    """Locate DayZDiag_x64.exe — the diagnostic client required for mod development.

    Required because retail DayZ_x64.exe blocks past the loading screen with
    -filePatching enabled, and -filePatching is needed for live source iteration.
    DayZ Diag lives alongside the retail exe in the DayZ game install dir.

    Resolution order:
      1. $DAYZ_DIAG_PATH env var
      2. Inside the DayZ game install (DayZDiag_x64.exe next to DayZ_x64.exe)
      3. Common Steam install paths
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_DIAG_PATH")
    if env_override:
        candidates.append(Path(env_override))

    game_root = find_dayz_game()
    if game_root is not None:
        candidates.append(game_root / "DayZDiag_x64.exe")

    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZ\DayZDiag_x64.exe"),
            Path(r"C:\Program Files\Steam\steamapps\common\DayZ\DayZDiag_x64.exe"),
        ]
    )

    for path in candidates:
        if path.exists():
            return path
    return None


def find_dayz_server() -> Optional[Path]:
    """Locate the DayZ Server install root containing DayZServer_x64.exe.

    DayZ Server is a separate free Steam download (appid 223350) — not bundled
    with the game.

    Resolution order:
      1. $DAYZ_SERVER_PATH env var
      2. Common Steam install paths
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_SERVER_PATH")
    if env_override:
        candidates.append(Path(env_override))

    candidates.extend(
        [
            Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZServer"),
            Path(r"C:\Program Files\Steam\steamapps\common\DayZServer"),
        ]
    )

    for root in candidates:
        if (root / "DayZServer_x64.exe").exists():
            return root
    return None


def find_vanilla_data() -> Optional[Path]:
    """Locate unpacked vanilla DayZ data on P:\\.

    Resolution order:
      1. $DAYZ_VANILLA_DATA_PATH env var
      2. Canonical names: P:\\dz, P:\\DZ, P:\\dta
    """
    candidates: list[Path] = []

    env_override = os.environ.get("DAYZ_VANILLA_DATA_PATH")
    if env_override:
        candidates.append(Path(env_override))

    candidates.extend([Path(r"P:\dz"), Path(r"P:\DZ"), Path(r"P:\dta")])

    for path in candidates:
        try:
            if path.exists() and any(path.iterdir()):
                return path
        except OSError:
            continue
    return None


def check_p_drive() -> bool:
    """P:\\ is mandatory. Hard fail if not mounted."""
    p = Path("P:\\")
    if p.exists() and p.is_dir():
        print(f"{OK} P:\\ is mounted")
        return True
    print(f"{FAIL} P:\\ is NOT mounted", file=sys.stderr)
    print(
        "        Open DayZ Tools and mount the P drive "
        "(Tools menu > Mount P drive).",
        file=sys.stderr,
    )
    return False


def check_dayz_tools() -> None:
    """Look for AddonBuilder.exe via env / registry / Steam paths. Warn only."""
    root = find_dayz_tools()
    if root:
        print(f"{OK} DayZ Tools found: {root}")
        return
    print(f"{WARN} DayZ Tools not detected")
    print("        Tried: $DAYZ_TOOLS_PATH, Windows registry, common Steam paths.")
    print("        Set DAYZ_TOOLS_PATH if your install is elsewhere.")


def check_vanilla_data() -> None:
    """Vanilla DayZ data unpacked under P:\\. Warn only."""
    path = find_vanilla_data()
    if path:
        print(f"{OK} Vanilla data found: {path}")
        return
    print(f"{WARN} Vanilla DayZ data not detected on P:\\")
    print("        Tried: $DAYZ_VANILLA_DATA_PATH, P:\\dz, P:\\DZ, P:\\dta.")
    print("        Unpack vanilla PBOs via DayZ Tools 'Extract Game Data'.")


def validate_p_mods() -> Optional[str]:
    """Verify P:\\Mods\\ is a directory junction (or symlink) to the DayZ
    `!Workshop` folder, so built PBOs deployed under P:\\Mods\\@<Mod>\\Addons\\
    actually land where the engine can load them.

    Returns None on success, or a multi-line error message describing the issue
    and the exact fix command. Used by preflight (warn) and build-pbo (hard fail).
    """
    import os
    mods = Path(r"P:\Mods")
    game_root = find_dayz_game()
    workshop = game_root / "!Workshop" if game_root else None
    if workshop:
        fix_cmd = f'cmd /c mklink /J P:\\Mods "{workshop}"'
    else:
        fix_cmd = 'cmd /c mklink /J P:\\Mods "<DayZ install>\\!Workshop"'

    if not os.path.lexists(mods):
        # Auto-create the junction when we have a valid target. Creating a
        # junction is non-destructive and doesn't need admin; the target is
        # canonical (<DayZ>\!Workshop). Only fall through to a hard error if
        # we can't resolve the DayZ install or the target folder is missing.
        if workshop and workshop.exists():
            try:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(mods), str(workshop)],
                    check=True, capture_output=True, text=True,
                )
                print(f"{OK} Created junction P:\\Mods -> {workshop}")
                return None
            except subprocess.CalledProcessError as e:
                return (
                    "P:\\Mods\\ does not exist and auto-create failed.\n"
                    f"       Tried: mklink /J P:\\Mods \"{workshop}\"\n"
                    f"       Error: {(e.stderr or '').strip()}\n"
                    f"       Fix manually: {fix_cmd}"
                )
        return (
            "P:\\Mods\\ does not exist and DayZ game install couldn't be located\n"
            "       to auto-create the junction. It MUST be a junction to\n"
            "       <DayZ install>\\!Workshop\\ so built PBOs deploy where the\n"
            "       engine actually loads them.\n"
            f"       Fix: {fix_cmd}"
        )

    try:
        target_str = os.readlink(mods)
    except OSError:
        return (
            "P:\\Mods\\ exists as a regular folder, not a junction.\n"
            "       Built PBOs deployed under P:\\Mods\\@<Mod>\\Addons\\ will be\n"
            "       invisible to the engine.\n"
            "       Fix: remove the folder and create a junction:\n"
            "         cmd /c rmdir P:\\Mods\n"
            f"         {fix_cmd}"
        )

    if target_str.startswith("\\\\?\\"):
        target_str = target_str[4:]
    target_path = Path(target_str)
    if not target_path.exists():
        return (
            f"P:\\Mods\\ junction is dangling (target {target_path} is missing).\n"
            "       Fix: remove and recreate the junction with a valid target:\n"
            "         cmd /c rmdir P:\\Mods\n"
            f"         {fix_cmd}"
        )

    return None  # all good


def check_workshop_deploy() -> None:
    """P:\\Mods\\ must be a junction to the DayZ `!Workshop` folder. Warn only.

    Build skills should hard-fail on the same condition by calling validate_p_mods()
    directly.
    """
    err = validate_p_mods()
    if err is None:
        import os
        target = os.readlink(Path(r"P:\Mods"))
        if target.startswith("\\\\?\\"):
            target = target[4:]
        print(f"{OK} P:\\Mods -> {target}")
        return
    print(f"{WARN} {err}")


def main() -> int:
    print("DayZ preflight\n", flush=True)
    if not check_p_drive():
        return 1
    check_dayz_tools()
    check_vanilla_data()
    check_workshop_deploy()
    print("\nPreflight complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
