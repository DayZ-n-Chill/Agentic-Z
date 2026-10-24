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
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# PROJECT_DIR = user's project, used to resolve a relative --file path. Found the
# way the other DayZ skills find it (dayz-init's find_project_dir: CLAUDE_PROJECT_DIR,
# else the nearest folder at or above the current one holding the /dayz-init cache,
# else the current folder), so a run from workspace\<mod>\ resolves the same way.
PROJECT_DIR = h.load_module("dayz_launch_ob_state", h.DAYZ_INIT_STATE).find_project_dir()
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
objectbuilder_running = _setup.objectbuilder_running

# The mod name rule belongs to /dayz-new-mod, which creates P:\<ModName>\; reuse it
# so --mod is checked against the same pattern before it is joined onto P:\.
_new_mod = h.load_module("dayz_new_mod_module", h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py")
MOD_NAME_PATTERN = _new_mod.NAME_PATTERN

# Top-level P:\ folders that are not mods (vanilla data such as P:\DZ, and the
# P:\Mods junction). /dayz-launch-workbench owns the list; reuse it so --mod DZ
# is refused instead of scanning the whole vanilla tree for .p3d files.
_workbench = h.load_module(
    "dayz_launch_workbench_module", h.SKILLS_DIR / "dayz-launch-workbench" / "launch.py"
)
RESERVED_P_FOLDERS = _workbench.RESERVED_P_FOLDERS

# With several .p3d files under a mod, list at most this many, then a count.
MAX_LISTED_MODELS = 20

# How long to watch the new process before reporting it launched. A bad install
# or a missing DLL makes ObjectBuilder.exe exit at once; a real start keeps running.
STARTUP_CHECK_SECONDS = 1.0
STARTUP_POLL_INTERVAL = 0.1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Launch Object Builder")
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--file",
        help=r"Path to a .p3d to open (e.g. P:\MyMod\data\model.p3d); a relative path is looked up under the project root, then the current folder",
    )
    target.add_argument(
        "--mod",
        help=r"Mod name; opens the one .p3d anywhere under P:\<ModName>\ (opens the editor empty when there is none; lists them and asks for --file when there are several)",
    )
    return parser


def resolve_target(file_arg: Optional[str], mod_arg: Optional[str]) -> Optional[Path]:
    """Decide which .p3d to pass to ObjectBuilder.exe.

    The parser makes --file and --mod mutually exclusive. With neither there is
    no argument, and Object Builder opens its last-used file (or nothing).
    --mod resolves to a file, never a folder: Object Builder opens model files,
    and nothing shows that it accepts a directory argument. A mod with no .p3d
    yet (a fresh scaffold) also gives no argument, so the editor opens empty.
    """
    if file_arg:
        p = Path(file_arg)
        if p.is_absolute():
            if not p.exists():
                sys.exit(f"{FAIL} --file path does not exist: {p}")
        else:
            # The project root first (as the sibling DayZ skills do), then the
            # current folder, so `--file data\model.p3d` run from
            # workspace\<ModName>\ still finds the model there.
            bases = list(dict.fromkeys([PROJECT_DIR.resolve(), Path.cwd().resolve()]))
            candidates = [(base / p).resolve() for base in bases]
            found = next((c for c in candidates if c.exists()), None)
            if found is None:
                tried = "\n".join(f"         {c}" for c in candidates)
                sys.exit(
                    f"{FAIL} --file path does not exist: {file_arg}\n"
                    "       A relative path is looked up under the project root, then the current folder. Tried:\n"
                    f"{tried}"
                )
            p = found
        if not p.is_file():
            # Object Builder opens model files, not folders (see --mod below).
            sys.exit(f"{FAIL} --file is a folder, not a file: {p}\n       Pass a .p3d file, or use --mod <ModName>.")
        if p.suffix.lower() != ".p3d":
            print(f"{WARN} --file is not a .p3d ({p.suffix}); Object Builder may refuse to open it.")
        return p

    if mod_arg:
        if not MOD_NAME_PATTERN.fullmatch(mod_arg):
            sys.exit(
                f"{FAIL} Invalid mod name: {mod_arg!r}\n"
                "       Must start with a letter; letters, digits, underscores only; max 64 chars."
            )
        reason = RESERVED_P_FOLDERS.get(mod_arg.lower())
        if reason:
            sys.exit(
                f"{FAIL} --mod {mod_arg}: P:\\{mod_arg} is {reason}, not a mod.\n"
                f"       To open a vanilla model, pass its path with --file (e.g. --file P:\\{mod_arg}\\...\\model.p3d)."
            )
        mod_root = P_DRIVE / mod_arg
        if not mod_root.exists():
            sys.exit(
                f"{FAIL} --mod path does not exist: {mod_root}\n"
                f"       Did you run /dayz-new-mod {mod_arg}?"
            )
        # The whole mod tree, not only data\: mods keep models in models\, or elsewhere.
        models = sorted(mod_root.rglob("*.p3d"))
        if not models:
            # A fresh /dayz-new-mod scaffold has no model yet; open the editor
            # with no model argument so the user can create or import one.
            print(
                f"{INFO} No .p3d under {mod_root} yet (searched every subfolder); "
                "opening Object Builder with no model."
            )
            return None
        if len(models) > 1:
            listing = "\n".join(f"         {m}" for m in models[:MAX_LISTED_MODELS])
            if len(models) > MAX_LISTED_MODELS:
                listing += f"\n         ... and {len(models) - MAX_LISTED_MODELS} more"
            sys.exit(
                f"{FAIL} {len(models)} .p3d files under {mod_root}; pick one with --file:\n{listing}"
            )
        return models[0]

    return None


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

    if objectbuilder_running():
        print(
            f"{FAIL} Object Builder is already running; not starting a second instance.\n"
            f"       Switch to its window and open the model there, or close it and re-run.",
            file=sys.stderr,
        )
        return 1

    cmd: list[str] = [str(ob_exe)]
    if target is not None:
        cmd.append(str(target))
        print(f"{INFO} Opening: {target}")
    elif not args.mod:
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

    exit_code = wait_for_early_exit(proc)
    if exit_code is not None:
        print(
            f"{FAIL} ObjectBuilder.exe exited right after starting (exit code {exit_code}).\n"
            f"       Check the DayZ Tools install, or run /dayz-setup-objectbuilder --force to reset its settings.",
            file=sys.stderr,
        )
        return 1

    print(f"\n{OK} Object Builder launched (PID {proc.pid}). The window may take a few seconds to appear.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
