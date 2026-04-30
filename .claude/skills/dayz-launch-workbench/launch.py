r"""dayz-launch-workbench: Open Enfusion Workbench, optionally on a mod's gproj.

Verifies environment, then spawns workbenchApp.exe detached with cwd=P:\ so
the gproj's `Directory "./"` resolves to the work drive root (where vanilla
DayZ data is unpacked).

Usage:
    python .claude/skills/dayz-launch-workbench/launch.py
    python .claude/skills/dayz-launch-workbench/launch.py --mod MyMod
    python .claude/skills/dayz-launch-workbench/launch.py --gproj P:\path\to\my.gproj

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
PREFLIGHT = REPO_ROOT / ".claude" / "skills" / "dayz-preflight" / "preflight.py"
P_DRIVE = Path("P:\\")

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


def resolve_gproj(mod_arg: Optional[str], gproj_arg: Optional[str]) -> Optional[Path]:
    """Decide which .gproj to pass. Returns None to mean 'no project arg' (Workbench
    falls back to the default dayz.gproj shipped next to workbenchApp.exe).
    """
    if mod_arg:
        gproj = P_DRIVE / mod_arg / "workbench" / "dayz.gproj"
        if not gproj.exists():
            mod_root = P_DRIVE / mod_arg
            if not mod_root.exists():
                sys.exit(
                    f"{FAIL} --mod path does not exist: {mod_root}\n"
                    f"        Run: /dayz-new-mod {mod_arg}"
                )
            sys.exit(
                f"{FAIL} {gproj} not found.\n"
                "        The workbench/ folder is scaffolded by /dayz-new-mod. If this\n"
                "        mod predates that, copy dayz.gproj + DayZSetting.xml from\n"
                "        <DayZ Tools>\\Bin\\Workbench\\ into the mod's workbench/ folder."
            )
        return gproj

    if gproj_arg:
        p = Path(gproj_arg)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        if not p.exists():
            sys.exit(f"{FAIL} --gproj path does not exist: {p}")
        if p.suffix.lower() != ".gproj":
            print(f"{WARN} --gproj is not a .gproj ({p.suffix}); Workbench may refuse it.")
        return p

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch Enfusion Workbench")
    parser.add_argument(
        "--mod",
        help="Mod name — opens P:\\<ModName>\\workbench\\dayz.gproj (scaffolded by /dayz-new-mod)",
    )
    parser.add_argument(
        "--gproj",
        help="Absolute path to a custom .gproj (escape hatch for non-scaffolded projects)",
    )
    args = parser.parse_args()

    if args.mod and args.gproj:
        sys.exit(f"{FAIL} Pass --mod OR --gproj, not both.")

    print("DayZ Workbench launcher\n")

    gate_on_preflight()
    print()

    tools_root = find_dayz_tools()
    if not tools_root:
        print(f"{FAIL} DayZ Tools not found. Install via Steam first.", file=sys.stderr)
        return 1

    wb_exe = tools_root / "Bin" / "Workbench" / "workbenchApp.exe"
    if not wb_exe.exists():
        print(f"{FAIL} workbenchApp.exe not found at {wb_exe}", file=sys.stderr)
        return 1
    print(f"{OK} workbenchApp.exe: {wb_exe}")

    gproj = resolve_gproj(args.mod, args.gproj)

    cmd: list[str] = [str(wb_exe)]
    if gproj is not None:
        cmd.append(str(gproj))
        print(f"{INFO} Project: {gproj}")
    else:
        print(f"{INFO} No --mod/--gproj; Workbench loads its bundled dayz.gproj.")

    # cwd MUST be the Bin\Workbench folder. Workbench loads its support files
    # (dta, platforms, ToolAddons) and its bundled dayz.gproj relative to cwd,
    # not relative to workbenchApp.exe. Launching from elsewhere triggers a
    # "cannot find file dayz.gproj" error even when a valid project is passed
    # as an argument.
    workbench_dir = wb_exe.parent
    print(f"{OK} Working directory: {workbench_dir}")

    try:
        proc = subprocess.Popen(
            cmd,
            close_fds=True,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            cwd=str(workbench_dir),
        )
    except OSError as exc:
        print(f"{FAIL} Failed to spawn workbenchApp.exe: {exc}", file=sys.stderr)
        return 1

    print(f"\n{OK} Workbench launched (PID {proc.pid}). The window may take a few seconds to appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
