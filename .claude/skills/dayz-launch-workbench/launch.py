r"""dayz-launch-workbench: Open Enfusion Workbench, optionally on a mod's gproj.

Verifies the environment, then spawns workbenchApp.exe -gproj=<path> detached with
cwd=<DayZ Tools>\Bin\Workbench so Workbench's support files (dta, platforms,
ToolAddons) and its bundled dayz.gproj resolve. Launching from anywhere else
(including P:\) errors with "cannot find file dayz.gproj". Watches the new
process for a second and fails if it exits at once.

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
import time
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

# The mod name rule belongs to /dayz-new-mod, which creates P:\<ModName>\; reuse it
# so --mod is checked against the same pattern before it is joined onto P:\.
_new_mod = h.load_module("dayz_new_mod_module", h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py")
MOD_NAME_PATTERN = _new_mod.NAME_PATTERN

# Top-level P:\ folders that are not mods, keyed by lowercase name (Windows
# paths ignore case). The vanilla ones are the PBO prefixes of the game's own
# data: DayZ\Addons\*.pbo all carry a "DZ\..." prefix, and DayZ\dta\ holds
# bin, core, graphics, gui, languagecore, scripts and system.pbo, each with its
# own name as prefix. P:\Mods is the Workshop junction /dayz-preflight makes.
RESERVED_P_FOLDERS = {
    name: "a vanilla DayZ data folder"
    for name in ("dz", "bin", "core", "graphics", "gui", "languagecore", "scripts", "system")
}
RESERVED_P_FOLDERS["mods"] = "the Workshop junction made by /dayz-preflight"

# How long to watch the new process before reporting it launched. A broken
# install or a missing DLL makes workbenchApp.exe exit at once; a real start
# keeps running.
STARTUP_CHECK_SECONDS = 1.0
STARTUP_POLL_INTERVAL = 0.1


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


def check_mod_name(mod_arg: str) -> None:
    """Refuse a --mod value that is not a mod name, without touching the disk,
    so a typo fails before the preflight output."""
    if not MOD_NAME_PATTERN.fullmatch(mod_arg):
        sys.exit(
            f"{FAIL} Invalid mod name: {mod_arg!r}\n"
            "       Must start with a letter; letters, digits, underscores only; max 64 chars."
        )
    reason = RESERVED_P_FOLDERS.get(mod_arg.lower())
    if reason:
        sys.exit(
            f"{FAIL} --mod {mod_arg}: P:\\{mod_arg} is {reason}, not a mod.\n"
            "       Run without --mod to open vanilla DayZ in Workbench."
        )


def resolve_gproj(mod_arg: Optional[str], gproj_arg: Optional[str]) -> Optional[Path]:
    """Decide which .gproj to pass. None means no project argument: Workbench
    falls back to the dayz.gproj shipped next to workbenchApp.exe.
    """
    if mod_arg:
        check_mod_name(mod_arg)
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
        if not p.is_file():
            sys.exit(
                f"{FAIL} --gproj is a folder, not a project file: {p}\n"
                "       Pass the .gproj file inside it, e.g. <folder>\\dayz.gproj."
            )
        if " " in str(p):
            # Workbench has not been confirmed to open a quoted "-gproj=<path>"
            # with spaces, so refuse it instead of handing over a path that may
            # silently open the vanilla project.
            sys.exit(
                f"{FAIL} --gproj path contains a space: {p}\n"
                "       Workbench is not known to open such a path. Move or link the project\n"
                "       to a path without spaces, such as one under P:\\, and pass that."
            )
        if p.suffix.lower() != ".gproj":
            print(f"{WARN} --gproj is not a .gproj ({p.suffix}); Workbench may refuse it.")
        return p

    return None


def running_workbench_pids() -> list[int]:
    """PIDs of running workbenchApp.exe processes (tasklist matches names case-insensitively).
    Warns and returns [] when tasklist cannot run, so the launch goes on
    without the single-instance check instead of losing it silently."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {WB_EXE_NAME}", "/FO", "CSV", "/NH"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, OSError) as exc:
        print(
            f"{WARN} tasklist failed ({exc}); cannot check for a running Workbench.\n"
            "       Launching anyway; close any other Workbench window on the same project.",
            file=sys.stderr,
        )
        return []
    return [
        int(row[1])
        for row in csv.reader(out.splitlines())
        if len(row) >= 2 and row[0].lower() == WB_EXE_NAME.lower() and row[1].isdigit()
    ]


def wait_for_early_exit(proc: subprocess.Popen) -> Optional[int]:
    """Poll the new process for STARTUP_CHECK_SECONDS. Return its exit code if it
    already exited, or None if it is still running."""
    deadline = time.monotonic() + STARTUP_CHECK_SECONDS
    while True:
        code = proc.poll()
        if code is not None or time.monotonic() >= deadline:
            return code
        time.sleep(STARTUP_POLL_INTERVAL)


def main() -> int:
    args = build_parser().parse_args()
    # Preflight is a child process writing straight to the console; line
    # buffering keeps this script's lines in order with it when piped.
    sys.stdout.reconfigure(line_buffering=True)

    print("DayZ Workbench launcher\n")

    if args.mod:
        check_mod_name(args.mod)

    h.gate_on_preflight()
    print()

    # The project is checked before DayZ Tools, so a missing mod or gproj is
    # the first failure reported; P:\ is known to be mounted by now.
    gproj = resolve_gproj(args.mod, args.gproj)

    tools_root = h.preflight.find_dayz_tools()
    if not tools_root:
        print(f"{FAIL} DayZ Tools not found. Install it via Steam first.", file=sys.stderr)
        return 1

    wb_exe = tools_root / "Bin" / "Workbench" / "workbenchApp.exe"
    if not wb_exe.exists():
        print(f"{FAIL} workbenchApp.exe not found at {wb_exe}", file=sys.stderr)
        return 1
    print(f"{OK} workbenchApp.exe: {wb_exe}")

    cmd: list[str] = [str(wb_exe)]
    if gproj is not None:
        # The project goes through the -gproj switch (a string in
        # workbenchApp.exe); its default is $CurrentDir:dayz.gproj, so a bare
        # path argument would leave Workbench on the vanilla project.
        cmd.append(f"-gproj={gproj}")
        print(f"{INFO} Project: {gproj}")
    else:
        # With no -gproj switch Workbench opens $CurrentDir:dayz.gproj; on a
        # partial install that file is missing and Workbench reports "cannot
        # find file dayz.gproj", possibly in a dialog that outlives the
        # startup check, so check for it here.
        bundled = wb_exe.parent / "dayz.gproj"
        if not bundled.is_file():
            print(
                f"{FAIL} Bundled dayz.gproj not found at {bundled}\n"
                "       Verify the DayZ Tools install in Steam (Properties > Installed Files >\n"
                "       Verify integrity of tool files).",
                file=sys.stderr,
            )
            return 1
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

    exit_code = wait_for_early_exit(proc)
    if exit_code is not None:
        print(
            f"{FAIL} workbenchApp.exe exited right after starting (exit code {exit_code}).\n"
            f"       Check that the project file is a valid .gproj, and verify the DayZ Tools\n"
            f"       install in Steam (a missing DLL in {workbench_dir} stops it at once).",
            file=sys.stderr,
        )
        return 1

    print(f"\n{OK} Workbench launched (PID {proc.pid}). The window may take a few seconds to appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
