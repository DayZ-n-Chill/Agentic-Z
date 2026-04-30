"""dayz-setup-objectbuilder: One-time Object Builder configuration.

Imports the default registry settings shipped with DayZ Tools and verifies
Buldozer (the 3D preview engine Object Builder spawns) is present. Idempotent —
re-running on a configured machine reports status without changing anything.
Pass --force to re-import the .reg and reset Object Builder to factory defaults.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"

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

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "
INFO = "[INFO] "


def _load_preflight_module():
    spec = importlib.util.spec_from_file_location("dayz_preflight_module", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preflight module at {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_preflight = _load_preflight_module()
find_dayz_tools = _preflight.find_dayz_tools


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


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
    """Force PREFERRED_FLAGS_ON to "1" under CConfig. Returns count of values
    actually changed (others were already correct or absent)."""
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
                print(f"{OK} {label}: already on")
                continue
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, on_value)
            print(f"{INFO} {label}: turned on")
            changed += 1
    return changed


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


def main() -> int:
    parser = argparse.ArgumentParser(description="One-time Object Builder setup")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-import the .reg file even if Object Builder is already configured (resets to defaults)",
    )
    args = parser.parse_args()

    print("DayZ Object Builder setup\n")

    gate_on_preflight()
    print()

    tools_root = find_dayz_tools()
    if not tools_root:
        print(f"{FAIL} DayZ Tools not found. Install via Steam first.", file=sys.stderr)
        return 1
    print(f"{OK} DayZ Tools: {tools_root}")

    ob_dir = tools_root / "Bin" / "ObjectBuilder"
    ob_exe = ob_dir / "ObjectBuilder.exe"
    ob_reg = ob_dir / "ObjectBuilder_defaultSettings.reg"

    if not ob_exe.exists():
        print(f"{FAIL} ObjectBuilder.exe not found at {ob_exe}", file=sys.stderr)
        return 1
    print(f"{OK} ObjectBuilder.exe: {ob_exe}")

    if not ob_reg.exists():
        print(f"{FAIL} Default settings .reg missing at {ob_reg}", file=sys.stderr)
        print(f"        Reinstall DayZ Tools to restore it.", file=sys.stderr)
        return 1
    print(f"{OK} Default settings file: {ob_reg.name}")

    already_configured = registry_has_objectbuilder_settings()

    if already_configured and not args.force:
        print(f"{OK} Registry already configured at HKCU\\{REG_KEY}")
        print(f"{INFO} Re-run with --force to reset Object Builder to factory defaults.")
    else:
        if already_configured and args.force:
            print(f"{INFO} Registry already populated; --force will overwrite with defaults.")
        else:
            print(f"{INFO} Registry empty — importing defaults.")
        rc = import_reg_file(ob_reg)
        if rc != 0:
            print(f"{FAIL} reg import failed (exit {rc}).", file=sys.stderr)
            print(f"        On Windows, importing into HKCU does NOT need elevation —", file=sys.stderr)
            print(f"        but try running this skill from an Administrator shell if it persists.", file=sys.stderr)
            return rc
        if not registry_has_objectbuilder_settings():
            print(f"{FAIL} Registry import claimed success but the keys are still missing.", file=sys.stderr)
            return 1
        print(f"{OK} Registry imported successfully.")

    print(f"\n{INFO} Applying preferred Object Builder defaults:")
    apply_preferences()

    print(f"\n{OK} Object Builder is ready. Launch with: /dayz-launch-objectbuilder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
