r"""dayz-launch-objectbuilder: Open Object Builder, optionally on a specific .p3d.

Verifies the environment and that /dayz-setup-objectbuilder has run, then
spawns ObjectBuilder.exe detached so the shell returns immediately.

Usage:
    python .claude/skills/dayz-launch-objectbuilder/launch.py
    python .claude/skills/dayz-launch-objectbuilder/launch.py --file P:\MyMod\data\model.p3d
    python .claude/skills/dayz-launch-objectbuilder/launch.py --mod MyMod

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# PROJECT_DIR = user's project, used to resolve a relative --file path.
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
P_DRIVE = Path("P:\\")

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL
INFO = "[INFO] "

# The registry key and its "is Object Builder configured" check belong to
# /dayz-setup-objectbuilder, which writes that key; read them from there.
_setup = h.load_module(
    "dayz_setup_objectbuilder_module", h.SKILLS_DIR / "dayz-setup-objectbuilder" / "setup.py"
)
REG_KEY = _setup.REG_KEY
registry_has_objectbuilder_settings = _setup.registry_has_objectbuilder_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch Object Builder")
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--file",
        help=r"Path to a .p3d to open (e.g. P:\MyMod\data\model.p3d); a relative path resolves against the project",
    )
    target.add_argument(
        "--mod",
        help=r"Mod name; opens the one .p3d under P:\<ModName>\data\ (lists them and asks for --file when there are several)",
    )
    return parser


def resolve_target(file_arg: Optional[str], mod_arg: Optional[str]) -> Optional[Path]:
    """Decide which .p3d to pass to ObjectBuilder.exe.

    The parser makes --file and --mod mutually exclusive. With neither there is
    no argument, and Object Builder opens its last-used file (or nothing).
    --mod resolves to a file, never a folder: Object Builder opens model files,
    and nothing shows that it accepts a directory argument.
    """
    if file_arg:
        p = Path(file_arg)
        if not p.is_absolute():
            p = (PROJECT_DIR / p).resolve()
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
                f"       Did you run /dayz-new-mod {mod_arg}?"
            )
        data_dir = mod_root / "data"
        models = sorted(data_dir.rglob("*.p3d")) if data_dir.is_dir() else []
        if not models:
            sys.exit(
                f"{FAIL} No .p3d under {data_dir}\n"
                f"       Run without flags to open Object Builder empty, or pass --file <p3d>."
            )
        if len(models) > 1:
            listing = "\n".join(f"         {m}" for m in models)
            sys.exit(
                f"{FAIL} {len(models)} .p3d files under {data_dir}; pick one with --file:\n{listing}"
            )
        return models[0]

    return None


def main() -> int:
    args = build_parser().parse_args()

    print("DayZ Object Builder launcher\n")

    # Preflight first (as /dayz-launch-workbench does): --mod resolves under
    # P:\, so an unmounted P: must fail with preflight's fix, not "folder missing".
    h.gate_on_preflight()
    print()

    target = resolve_target(args.file, args.mod)

    tools_root = h.preflight.find_dayz_tools()
    if not tools_root:
        print(f"{FAIL} DayZ Tools not found. Install it via Steam first.", file=sys.stderr)
        return 1

    ob_exe = tools_root / "Bin" / "ObjectBuilder" / "ObjectBuilder.exe"
    if not ob_exe.exists():
        print(f"{FAIL} ObjectBuilder.exe not found at {ob_exe}", file=sys.stderr)
        return 1
    print(f"{OK} ObjectBuilder.exe: {ob_exe}")

    if not registry_has_objectbuilder_settings():
        print(
            f"{FAIL} Object Builder is not configured (registry empty).\n"
            f"       Run: /dayz-setup-objectbuilder\n"
            f"       (one-time per machine; populates HKCU\\{REG_KEY})",
            file=sys.stderr,
        )
        return 1
    print(f"{OK} Registry configured")

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
            creationflags=h.DETACH_FLAGS,
            cwd=str(ob_exe.parent),
        )
    except OSError as exc:
        print(f"{FAIL} Failed to spawn ObjectBuilder.exe: {exc}", file=sys.stderr)
        return 1

    print(f"\n{OK} Object Builder launched (PID {proc.pid}). The window may take a few seconds to appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
