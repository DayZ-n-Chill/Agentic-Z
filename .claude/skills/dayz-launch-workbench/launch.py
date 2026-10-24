r"""dayz-launch-workbench: Open Enfusion Workbench, optionally on a mod's gproj.

Verifies the environment, then spawns workbenchApp.exe -gproj=<path> detached with
cwd=<DayZ Tools>\Bin\Workbench so Workbench's support files (dta, platforms,
ToolAddons) and its bundled dayz.gproj resolve. Launching from anywhere else
(including P:\) errors with "cannot find file dayz.gproj".

Usage:
    python .claude/skills/dayz-launch-workbench/launch.py
    python .claude/skills/dayz-launch-workbench/launch.py --mod MyMod
    python .claude/skills/dayz-launch-workbench/launch.py --gproj P:\path\to\my.gproj

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# PROJECT_DIR = user's project, used to resolve a relative --gproj path.
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
P_DRIVE = Path("P:\\")

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL
INFO = "[INFO] "

WB_EXE_NAME = "workbenchApp.exe"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch Enfusion Workbench")
    project = parser.add_mutually_exclusive_group()
    project.add_argument(
        "--mod",
        help=r"Mod name; opens P:\<ModName>\workbench\dayz.gproj (scaffolded by /dayz-new-mod or /dayz-add-scaffold)",
    )
    project.add_argument(
        "--gproj",
        help="Path to a custom .gproj (escape hatch for other layouts); a relative path resolves against the project",
    )
    return parser


def resolve_gproj(mod_arg: Optional[str], gproj_arg: Optional[str]) -> Optional[Path]:
    """Decide which .gproj to pass. None means no project argument: Workbench
    falls back to the dayz.gproj shipped next to workbenchApp.exe.
    """
    if mod_arg:
        mod_root = P_DRIVE / mod_arg
        gproj = mod_root / "workbench" / "dayz.gproj"
        if gproj.exists():
            return gproj
        if not mod_root.exists():
            sys.exit(
                f"{FAIL} --mod path does not exist: {mod_root}\n"
                f"       Run /dayz-new-mod {mod_arg} (or /dayz-import-mod for an existing folder)."
            )
        sys.exit(
            f"{FAIL} {gproj} not found.\n"
            f"       Add it with: /dayz-add-scaffold {mod_arg} --piece workbench"
        )

    if gproj_arg:
        p = Path(gproj_arg)
        if not p.is_absolute():
            p = (PROJECT_DIR / p).resolve()
        if not p.exists():
            sys.exit(f"{FAIL} --gproj path does not exist: {p}")
        if p.suffix.lower() != ".gproj":
            print(f"{WARN} --gproj is not a .gproj ({p.suffix}); Workbench may refuse it.")
        return p

    return None


def running_workbench_pids() -> list[int]:
    """PIDs of running workbenchApp.exe processes (tasklist matches names case-insensitively)."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {WB_EXE_NAME}", "/FO", "CSV", "/NH"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [
        int(row[1])
        for row in csv.reader(out.splitlines())
        if len(row) >= 2 and row[0].lower() == WB_EXE_NAME.lower() and row[1].isdigit()
    ]


def main() -> int:
    args = build_parser().parse_args()

    print("DayZ Workbench launcher\n")

    h.gate_on_preflight()
    print()

    tools_root = h.preflight.find_dayz_tools()
    if not tools_root:
        print(f"{FAIL} DayZ Tools not found. Install it via Steam first.", file=sys.stderr)
        return 1

    wb_exe = tools_root / "Bin" / "Workbench" / "workbenchApp.exe"
    if not wb_exe.exists():
        print(f"{FAIL} workbenchApp.exe not found at {wb_exe}", file=sys.stderr)
        return 1
    print(f"{OK} workbenchApp.exe: {wb_exe}")

    gproj = resolve_gproj(args.mod, args.gproj)

    cmd: list[str] = [str(wb_exe)]
    if gproj is not None:
        # The project goes through the -gproj switch (a string in
        # workbenchApp.exe); its default is $CurrentDir:dayz.gproj, so a bare
        # path argument would leave Workbench on the vanilla project.
        cmd.append(f"-gproj={gproj}")
        print(f"{INFO} Project: {gproj}")
    else:
        print(f"{INFO} No --mod/--gproj; Workbench loads its bundled dayz.gproj.")

    # cwd must be Bin\Workbench: Workbench loads its support files (dta,
    # platforms, ToolAddons) and its bundled dayz.gproj relative to cwd, not
    # relative to workbenchApp.exe, and fails with "cannot find file
    # dayz.gproj" from anywhere else even when a valid project is passed.
    workbench_dir = wb_exe.parent
    print(f"{OK} Working directory: {workbench_dir}")

    # tasklist does not show a process's command line, so a running Workbench's
    # project is unknown; refuse any second instance rather than risk two on
    # the same gproj.
    running = running_workbench_pids()
    if running:
        pids = ", ".join(str(pid) for pid in running)
        print(
            f"{FAIL} Workbench is already running (PID {pids}).\n"
            f"       Use that window, or close it and run this again.",
            file=sys.stderr,
        )
        return 1

    try:
        proc = subprocess.Popen(
            cmd,
            close_fds=True,
            creationflags=h.DETACH_FLAGS,
            cwd=str(workbench_dir),
        )
    except OSError as exc:
        print(f"{FAIL} Failed to spawn workbenchApp.exe: {exc}", file=sys.stderr)
        return 1

    print(f"\n{OK} Workbench launched (PID {proc.pid}). The window may take a few seconds to appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
