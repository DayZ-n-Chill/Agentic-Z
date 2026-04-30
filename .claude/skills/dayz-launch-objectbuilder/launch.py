r"""dayz-launch-objectbuilder: Open Object Builder, optionally on a specific .p3d.

Verifies environment + that /dayz-setup-objectbuilder has run, then spawns
ObjectBuilder.exe detached so the shell returns immediately.

Usage:
    python .claude/skills/dayz-launch-objectbuilder/launch.py
    python .claude/skills/dayz-launch-objectbuilder/launch.py --file P:\MyMod\data\model.p3d
    python .claude/skills/dayz-launch-objectbuilder/launch.py --mod MyMod

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
P_DRIVE = Path("P:\\")

REG_KEY = r"Software\Bohemia Interactive\DayZ Tools\Object Builder"
REG_SUBKEY_CCONFIG = REG_KEY + r"\CConfig"

# Windows process creation flag: detach the child so it survives the parent shell
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

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


def resolve_target(file_arg: Optional[str], mod_arg: Optional[str]) -> Optional[Path]:
    """Decide which file/folder to pass to ObjectBuilder.exe.

    --file beats --mod. Without either, no argument — Object Builder opens with
    its last-used file (or empty).
    """
    if file_arg:
        p = Path(file_arg)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        if not p.exists():
            sys.exit(f"{FAIL} --file path does not exist: {p}")
        if p.suffix.lower() != ".p3d":
            print(f"{WARN} --file is not a .p3d ({p.suffix}); Object Builder may refuse to open it.")
        return p

    if mod_arg:
        mod_root = P_DRIVE / mod_arg
        if not mod_root.exists():
            sys.exit(
                f"{FAIL} --mod path does not exist: {mod_root}\n"
                f"        Did you run /dayz-new-mod {mod_arg}?"
            )
        return mod_root

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Object Builder")
    parser.add_argument(
        "--file",
        help="Absolute path to a .p3d to open (e.g. P:\\MyMod\\data\\model.p3d)",
    )
    parser.add_argument(
        "--mod",
        help="Mod name — opens P:\\<ModName>\\ as the working folder so the open-dialog lands inside your mod",
    )
    args = parser.parse_args()

    if args.file and args.mod:
        sys.exit(f"{FAIL} Pass --file OR --mod, not both.")

    print("DayZ Object Builder launcher\n")

    gate_on_preflight()
    print()

    tools_root = find_dayz_tools()
    if not tools_root:
        print(f"{FAIL} DayZ Tools not found. Install via Steam first.", file=sys.stderr)
        return 1

    ob_exe = tools_root / "Bin" / "ObjectBuilder" / "ObjectBuilder.exe"
    if not ob_exe.exists():
        print(f"{FAIL} ObjectBuilder.exe not found at {ob_exe}", file=sys.stderr)
        return 1
    print(f"{OK} ObjectBuilder.exe: {ob_exe}")

    if not registry_has_objectbuilder_settings():
        print(
            f"{FAIL} Object Builder is not configured (registry empty).\n"
            f"        Run: /dayz-setup-objectbuilder\n"
            f"        (one-time per machine; populates HKCU\\{REG_KEY})",
            file=sys.stderr,
        )
        return 1
    print(f"{OK} Registry configured")

    target = resolve_target(args.file, args.mod)

    cmd: list[str] = [str(ob_exe)]
    if target is not None:
        cmd.append(str(target))
        print(f"{INFO} Opening: {target}")
    else:
        print(f"{INFO} No --file/--mod given; Object Builder will open its last-used model (or empty).")

    try:
        proc = subprocess.Popen(
            cmd,
            close_fds=True,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            cwd=str(tools_root / "Bin" / "ObjectBuilder"),
        )
    except OSError as exc:
        print(f"{FAIL} Failed to spawn ObjectBuilder.exe: {exc}", file=sys.stderr)
        return 1

    print(f"\n{OK} Object Builder launched (PID {proc.pid}). The window may take a few seconds to appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
