"""dayz-setup-objectbuilder: One-time Object Builder configuration.

Imports the default registry settings shipped with DayZ Tools when Object
Builder's registry tree is missing, then sets four preferred Object Builder
flags (PREFERRED_FLAGS_ON) under HKCU, writing only the ones that differ
(--no-prefs skips that step so a flag turned off on purpose stays off).
If the Object Builder key exists without its CConfig subkey (a partial tree),
it is exported to a backup first, the defaults are merged over it, and the
backup is restored if that import fails.

Pass --force to re-import the .reg and reset Object Builder to factory
defaults (asks first; --yes skips the question). A forced reset first exports
the current Object Builder key with `reg export` to a timestamped .reg under
.claude/local-memory/ so it can be restored, then deletes the key with
`reg delete` so the import starts from an empty tree (values and subkeys the
.reg does not mention, such as saved MainFrame-* layouts, are gone too).
If the import fails or leaves the key missing after that delete, the backup is
imported again automatically so the user's settings come back.

The .reg is imported only if every key it touches is under HKEY_CURRENT_USER.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

REG_KEY = r"Software\Bohemia Interactive\DayZ Tools\Object Builder"
REG_SUBKEY_CCONFIG = REG_KEY + r"\CConfig"

# Preferences we force on after .reg import. Each entry is the exact registry
# value name as Bohemia's Object Builder reads it (verified via `reg query`).
# All REG_SZ strings, but the "on" value is inconsistent across settings —
# most flags use "1" but Direct3D uses the literal string "On". Captured by
# toggling each one in OB's Preferences dialog and diffing the registry.
# Format: { name: (value_when_on, human_label) }
PREFERRED_FLAGS_ON: dict[str, tuple[str, str]] = {
    "#View background LOD":                    ("1",  "View > Background LOD"),
    "#View bgrnd LOD in 3D Preview":           ("1",  "Background LOD shown in 3D preview pane"),
    "#Show background LOD in UV (by default)": ("1",  "UV editor shows background LOD by default"),
    "#Use Direct3D renderer by default":       ("On", "Use Direct3D renderer by default"),
}

INFO = "[INFO] "
# The project root as dayz-init resolves it (CLAUDE_PROJECT_DIR, else the nearest
# folder at or above the current one holding the /dayz-init cache), so a run
# from a subfolder still backs up into the project, not the plugin install.
PROJECT_DIR = h.load_module("dayz_setup_ob_state", h.DAYZ_INIT_STATE).find_project_dir()
BACKUP_DIR = PROJECT_DIR / ".claude" / "local-memory"
HKCU_PREFIX = "HKEY_CURRENT_USER\\"


def _hkcu_key_exists(subkey: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey):
            return True
    except OSError:
        return False


def registry_has_objectbuilder_settings() -> bool:
    """True if the Object Builder registry tree exists with at least the CConfig
    subkey populated. Bohemia's default .reg lays this down on first import."""
    return _hkcu_key_exists(REG_SUBKEY_CCONFIG)


def registry_has_objectbuilder_key() -> bool:
    """True if the parent Object Builder key exists at all. It can hold saved
    MainFrame-* layouts or HistoryPaths even when CConfig is missing."""
    return _hkcu_key_exists(REG_KEY)


def apply_preferences() -> Optional[int]:
    """Set each PREFERRED_FLAGS_ON value to its "on" string under CConfig
    ("1" for most flags, "On" for the Direct3D one). Values already on are left
    alone; missing or different values are written. Returns how many were
    written, or None when CConfig cannot be opened for writing or a write fails
    (a [FAIL] line naming the error is printed)."""
    if sys.platform != "win32":
        return 0
    try:
        import winreg
    except ImportError:
        return 0
    changed = 0
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            REG_SUBKEY_CCONFIG,
            0,
            winreg.KEY_READ | winreg.KEY_SET_VALUE,
        ) as key:
            for name, (on_value, label) in PREFERRED_FLAGS_ON.items():
                existing: str
                try:
                    existing, _ = winreg.QueryValueEx(key, name)
                except OSError:
                    existing = ""
                if existing == on_value:
                    print(f"{h.OK} {label}: already on")
                    continue
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, on_value)
                print(f"{INFO} {label}: turned on")
                changed += 1
    except OSError as exc:
        print(f"{h.FAIL} Could not write preferences under HKCU\\{REG_SUBKEY_CCONFIG}: {exc}",
              file=sys.stderr)
        print(f"        {changed} of {len(PREFERRED_FLAGS_ON)} were written before the error. "
              "Re-run with --no-prefs to skip this step.", file=sys.stderr)
        return None
    return changed


def _read_reg_text(reg_path: Path) -> str:
    """Decode a .reg file (regedit writes UTF-16 LE with a BOM; REGEDIT4 files are ANSI)."""
    data = reg_path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig", errors="replace")


def foreign_reg_keys(reg_path: Path) -> list[str]:
    """Key headers in the .reg that are not under HKEY_CURRENT_USER.

    Covers both `[KEY]` and the deleting `[-KEY]` form. A file with no key
    headers at all is reported too, since there is nothing safe to import.
    """
    keys = [
        line.strip()[1:-1].lstrip("-")
        for line in _read_reg_text(reg_path).splitlines()
        if line.strip().startswith("[") and line.strip().endswith("]")
    ]
    if not keys:
        return ["<no registry keys found>"]
    return [k for k in keys if not k.upper().startswith(HKCU_PREFIX)]


def import_reg_file(reg_path: Path) -> int:
    """Run `reg import` on the .reg file. Returns the process exit code."""
    cmd = ["reg", "import", str(reg_path)]
    print(f"{INFO} Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0 and result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def backup_registry(backup_dir: Path) -> Optional[Path]:
    """`reg export` the HKCU Object Builder key to a timestamped .reg in backup_dir.

    Returns the backup path, or None if the export failed (its error is printed).
    """
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"objectbuilder-backup-{datetime.now():%Y%m%d-%H%M%S}.reg"
    cmd = ["reg", "export", f"HKCU\\{REG_KEY}", str(dest), "/y"]
    print(f"{INFO} Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not dest.is_file():
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return None
    return dest


def delete_objectbuilder_key() -> int:
    """`reg delete` the HKCU Object Builder key and everything under it.

    Returns the process exit code (its error is printed on failure).
    """
    cmd = ["reg", "delete", f"HKCU\\{REG_KEY}", "/f"]
    print(f"{INFO} Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return result.returncode


def restore_backup(backup: Path, had_cconfig: bool = True) -> bool:
    """Put the user's settings back after an import failed part way.

    Clears whatever the failed import left, then imports the backup taken
    before it. The clearing delete may fail because the key is already gone;
    only the backup import and the key check decide the result. had_cconfig is
    False for a partial tree, whose backup never held CConfig, so only the
    parent key is checked then.
    """
    print(f"{INFO} Restoring your previous settings from {backup}")
    delete_objectbuilder_key()
    rc = import_reg_file(backup)
    restored = registry_has_objectbuilder_settings() if had_cconfig else registry_has_objectbuilder_key()
    if rc != 0 or not restored:
        print(f"{h.FAIL} Restore failed (exit {rc}). Restore by hand with: reg import \"{backup}\"",
              file=sys.stderr)
        return False
    print(f"{h.OK} Previous settings restored; Object Builder is as it was before this run.")
    return True


def objectbuilder_state() -> tuple[Optional[bool], int]:
    """(running, tasklist exit code). running is True or False, or None when
    tasklist failed and the answer is unknown."""
    if sys.platform != "win32":
        return False, 0
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ObjectBuilder.exe", "/NH"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.returncode
    return "objectbuilder.exe" in result.stdout.lower(), 0


def objectbuilder_running() -> bool:
    """Lenient check shared with /dayz-launch-objectbuilder: a failed tasklist warns
    and counts as not running. This script's own main() uses objectbuilder_state()
    instead, because Object Builder writes its settings back to HKCU when it closes
    and would undo a reset or preference written while it is open."""
    running, rc = objectbuilder_state()
    if running is None:
        print(f"{h.WARN} tasklist failed (exit code {rc}); "
              "could not check whether Object Builder is running, so treating it as not running.",
              file=sys.stderr)
        return False
    return running


def confirm_reset(assume_yes: bool) -> bool:
    """Ask before --force wipes an existing Object Builder configuration."""
    if assume_yes:
        return True
    if not sys.stdin.isatty():
        print(
            f"{h.FAIL} --force resets Object Builder to factory defaults (custom layouts are lost).\n"
            "        No terminal to ask in: re-run with --force --yes to confirm.",
            file=sys.stderr,
        )
        return False
    answer = input("Reset Object Builder to factory defaults? Custom layouts are lost. [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="One-time Object Builder setup")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-import the .reg file even if Object Builder is already configured (resets to defaults)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm --force without asking (needed when there is no terminal)",
    )
    parser.add_argument(
        "--no-prefs",
        action="store_true",
        help="Leave the four preferred flags as they are (keeps e.g. Direct3D turned off on purpose)",
    )
    args = parser.parse_args(argv)

    print("DayZ Object Builder setup\n")

    h.gate_on_preflight()
    print()

    tools_root = h.preflight.find_dayz_tools()
    if not tools_root:
        print(f"{h.FAIL} DayZ Tools not found. Install via Steam first.", file=sys.stderr)
        return 1
    print(f"{h.OK} DayZ Tools: {tools_root}")

    ob_dir = tools_root / "Bin" / "ObjectBuilder"
    ob_exe = ob_dir / "ObjectBuilder.exe"
    ob_reg = ob_dir / "ObjectBuilder_defaultSettings.reg"

    if not ob_exe.exists():
        print(f"{h.FAIL} ObjectBuilder.exe not found at {ob_exe}", file=sys.stderr)
        return 1
    print(f"{h.OK} ObjectBuilder.exe: {ob_exe}")

    if not ob_reg.exists():
        print(f"{h.FAIL} Default settings .reg missing at {ob_reg}", file=sys.stderr)
        print("        Reinstall DayZ Tools to restore it.", file=sys.stderr)
        return 1
    print(f"{h.OK} Default settings file: {ob_reg.name}")

    running, tasklist_rc = objectbuilder_state()
    if running is None:
        print(f"{h.FAIL} tasklist failed (exit code {tasklist_rc}), so it is unknown whether "
              "Object Builder is running.\n"
              "        Close Object Builder if it is open and re-run; it rewrites these settings on exit.",
              file=sys.stderr)
        return 1
    if running:
        print(f"{h.FAIL} Close Object Builder first; it rewrites these settings on exit.", file=sys.stderr)
        return 1

    already_configured = registry_has_objectbuilder_settings()
    # A key without CConfig still holds user data (MainFrame-* layouts,
    # HistoryPaths), so it is backed up before the defaults are merged over it.
    partial_tree = not already_configured and registry_has_objectbuilder_key()
    backup: Optional[Path] = None  # set once a backup exists and the registry is about to change

    if already_configured and not args.force:
        print(f"{h.OK} Registry already configured at HKCU\\{REG_KEY}")
        print(f"{INFO} Re-run with --force to reset Object Builder to factory defaults.")
    else:
        foreign = foreign_reg_keys(ob_reg)
        if foreign:
            print(f"{h.FAIL} {ob_reg.name} writes outside HKEY_CURRENT_USER; refusing to import:", file=sys.stderr)
            for key in foreign:
                print(f"          {key}", file=sys.stderr)
            return 1
        if already_configured:
            print(f"{INFO} Registry already populated; --force will delete it and import the defaults.")
            if not confirm_reset(args.yes):
                print(f"{INFO} Reset cancelled. Registry left unchanged.")
                return 1
            saved = backup_registry(BACKUP_DIR)
            if saved is None:
                print(f"{h.FAIL} Could not back up HKCU\\{REG_KEY}; reset not attempted.", file=sys.stderr)
                return 1
            print(f"{h.OK} Current settings backed up to {saved}")
            print(f"{INFO} Restore them with: reg import \"{saved}\"")
            rc = delete_objectbuilder_key()
            if rc != 0:
                print(f"{h.FAIL} Could not delete HKCU\\{REG_KEY} (exit {rc}); defaults not imported.", file=sys.stderr)
                return 1
            backup = saved
            print(f"{h.OK} Deleted HKCU\\{REG_KEY}.")
        elif partial_tree:
            print(f"{INFO} HKCU\\{REG_KEY} exists without CConfig; backing it up before merging the defaults.")
            saved = backup_registry(BACKUP_DIR)
            if saved is None:
                print(f"{h.FAIL} Could not back up HKCU\\{REG_KEY}; defaults not imported.", file=sys.stderr)
                return 1
            print(f"{h.OK} Current settings backed up to {saved}")
            print(f"{INFO} Restore them with: reg import \"{saved}\"")
            backup = saved
        else:
            print(f"{INFO} Registry empty — importing defaults.")
        rc = import_reg_file(ob_reg)
        if rc != 0:
            print(f"{h.FAIL} reg import failed (exit {rc}).", file=sys.stderr)
            print("        Importing into HKCU does not need elevation, but try an", file=sys.stderr)
            print("        Administrator shell if the failure persists.", file=sys.stderr)
            if backup is not None:
                restore_backup(backup, had_cconfig=not partial_tree)
            return rc
        if not registry_has_objectbuilder_settings():
            print(f"{h.FAIL} Registry import claimed success but the keys are still missing.", file=sys.stderr)
            if backup is not None:
                restore_backup(backup, had_cconfig=not partial_tree)
            return 1
        print(f"{h.OK} Registry imported successfully.")

    if args.no_prefs:
        print(f"\n{INFO} --no-prefs: preferred flags left as they are.")
    else:
        print(f"\n{INFO} Applying preferred Object Builder defaults (skip with --no-prefs):")
        changed = apply_preferences()
        if changed is None:
            return 1
        print(f"{INFO} {changed} of {len(PREFERRED_FLAGS_ON)} preferences changed.")

    print(f"\n{h.OK} Object Builder is ready. Launch with: /dayz-launch-objectbuilder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
