"""dayz-setup-objectbuilder: One-time Object Builder configuration.

Imports the default registry settings shipped with DayZ Tools when Object
Builder's registry tree is missing, then on every run sets four preferred
Object Builder flags (PREFERRED_FLAGS_ON) under HKCU, writing only the ones
that differ. Pass --force to re-import the .reg and reset Object Builder to
factory defaults (asks first; --yes skips the question). A forced reset first
exports the current Object Builder key with `reg export` to a timestamped .reg
under .claude/local-memory/ so it can be restored.

The .reg is imported only if every key it touches is under HKEY_CURRENT_USER.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
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
# Same project-root rule as dayz-init/state.py: the clone or user project, not
# the plugin install this script may live in.
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
BACKUP_DIR = PROJECT_DIR / ".claude" / "local-memory"
HKCU_PREFIX = "HKEY_CURRENT_USER\\"


def registry_has_objectbuilder_settings() -> bool:
    """True if the Object Builder registry tree exists with at least the CConfig
    subkey populated. Bohemia's default .reg lays this down on first import."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
    except ImportError:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY_CCONFIG):
            return True
    except OSError:
        return False


def apply_preferences() -> int:
    """Set each PREFERRED_FLAGS_ON value to its "on" string under CConfig
    ("1" for most flags, "On" for the Direct3D one). Values already on are left
    alone; missing or different values are written. Returns how many were written."""
    if sys.platform != "win32":
        return 0
    try:
        import winreg
    except ImportError:
        return 0
    changed = 0
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

    already_configured = registry_has_objectbuilder_settings()

    if already_configured and not args.force:
        print(f"{h.OK} Registry already configured at HKCU\\{REG_KEY}")
        print(f"{INFO} Re-run with --force to reset Object Builder to factory defaults.")
    else:
        if already_configured:
            print(f"{INFO} Registry already populated; --force will overwrite it with defaults.")
            if not confirm_reset(args.yes):
                print(f"{INFO} Reset cancelled. Registry left unchanged.")
                return 1
            backup = backup_registry(BACKUP_DIR)
            if backup is None:
                print(f"{h.FAIL} Could not back up HKCU\\{REG_KEY}; reset not attempted.", file=sys.stderr)
                return 1
            print(f"{h.OK} Current settings backed up to {backup}")
            print(f"{INFO} Restore them with: reg import \"{backup}\"")
        else:
            print(f"{INFO} Registry empty — importing defaults.")
        foreign = foreign_reg_keys(ob_reg)
        if foreign:
            print(f"{h.FAIL} {ob_reg.name} writes outside HKEY_CURRENT_USER; refusing to import:", file=sys.stderr)
            for key in foreign:
                print(f"          {key}", file=sys.stderr)
            return 1
        rc = import_reg_file(ob_reg)
        if rc != 0:
            print(f"{h.FAIL} reg import failed (exit {rc}).", file=sys.stderr)
            print("        Importing into HKCU does not need elevation, but try an", file=sys.stderr)
            print("        Administrator shell if the failure persists.", file=sys.stderr)
            return rc
        if not registry_has_objectbuilder_settings():
            print(f"{h.FAIL} Registry import claimed success but the keys are still missing.", file=sys.stderr)
            return 1
        print(f"{h.OK} Registry imported successfully.")

    print(f"\n{INFO} Applying preferred Object Builder defaults:")
    apply_preferences()

    print(f"\n{h.OK} Object Builder is ready. Launch with: /dayz-launch-objectbuilder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
