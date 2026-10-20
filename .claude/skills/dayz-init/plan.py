"""dayz-init Steps 4-5: build the setup plan, print it, and optionally run it.

Usage:
    python plan.py --mod NAME [--import-from PATH [--scaffold | --no-scaffold]]
                   [--author HANDLE] [--server MAP] [--build] [--launch] [--execute]

Without --execute: prints the plan and exits 0.
With --execute: runs each step in order and stops at the first failure,
exiting with that step's exit code. Refuses (exit 2) while the environment
check reports a hard stop or P:\\ is not mounted.

Steps, in order (each skipped when not needed):
  1. new-mod / import-mod   skipped when workspace/<mod> already exists
  2. record          write the per-clone project cache and the active mod
  3. add-server      --server
  4. build           --build, or implied by --launch
  5. launch          --launch (needs --server)
The P:\\Mods junction is not a step: /dayz-preflight, which every child skill
runs first, creates it when it is missing.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dispatch import KNOWN_MAPS, DispatchError, command_for, run
from env_check import classify, run_all
from state import PROJECT_DIR, mod_exists, write_cached_project_root, write_state


@dataclass
class Intent:
    mod_name: str
    source: str | None = None        # set for an import, None for a new mod
    scaffold: bool | None = None     # import only: write missing pieces into the source?
    author: str | None = None        # new mod only: passed to /dayz-new-mod --author
    server_map: str | None = None
    build: bool = False
    launch: bool = False


@dataclass
class Step:
    action: str
    label: str
    params: dict = field(default_factory=dict)


def build_steps(intent: Intent, already_exists: bool) -> list[Step]:
    """Ordered steps for this intent."""
    steps: list[Step] = []
    mod = intent.mod_name
    if already_exists:
        pass
    elif intent.source:
        steps.append(Step(
            "import-mod", f"Import {intent.source} as {mod}",
            {"mod": mod, "source": intent.source, "scaffold": intent.scaffold},
        ))
    else:
        steps.append(Step("new-mod", f"Scaffold workspace\\{mod}", {"mod": mod, "author": intent.author}))

    steps.append(Step("record", f"Record {mod} as the active mod"))

    if intent.server_map:
        steps.append(Step("add-server", f"Set up the {intent.server_map} test server", {"server": intent.server_map}))
    if intent.build or intent.launch:
        steps.append(Step("build", f"Build {mod}.pbo", {"mod": mod}))
    if intent.launch:
        steps.append(Step(
            "launch", f"Launch DayZ Diag with {mod} on {intent.server_map}",
            {"mod": mod, "server": intent.server_map},
        ))
    return steps


def render_plan(steps: list[Step]) -> str:
    return "\n".join(["Plan:"] + [f"  {i}. {s.label}" for i, s in enumerate(steps, start=1)])


def record_project(project: Path, intent: Intent) -> None:
    write_cached_project_root(project, project / ".claude" / "local-memory")
    write_state(project, {
        "last_intent": {
            "mod_name": intent.mod_name,
            "is_new": intent.source is None,
            "server_map": intent.server_map or "",
        },
    })


def execute(steps: list[Step], intent: Intent, project: Path) -> int:
    """Run steps in order. Return 0, or the exit code of the first failing step."""
    for i, step in enumerate(steps, start=1):
        print(f"\n[{i}/{len(steps)}] {step.label}", flush=True)
        if step.action == "record":
            record_project(project, intent)
            continue
        rc = run(command_for(step.action, **step.params))
        if rc != 0:
            print(f"[FAIL] Step {i}/{len(steps)} ({step.label}) exited with {rc}.", file=sys.stderr)
            return rc
    print("\n[OK]   Setup complete.")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan and run /dayz-init setup.")
    parser.add_argument("--mod", required=True, help="Mod name (folder under workspace/)")
    parser.add_argument("--import-from", dest="source", help="Existing mod folder to import")
    scaffold = parser.add_mutually_exclusive_group()
    scaffold.add_argument("--scaffold", dest="scaffold", action="store_true", default=None,
                          help="Import: write missing pieces into the source folder")
    scaffold.add_argument("--no-scaffold", dest="scaffold", action="store_false",
                          help="Import: link only, never write into the source folder")
    parser.add_argument("--author", help="New mod: author handle (cached by /dayz-new-mod)")
    parser.add_argument("--server", choices=KNOWN_MAPS, help="Set up a test server on this map")
    parser.add_argument("--build", action="store_true", help="Build the PBO")
    parser.add_argument("--launch", action="store_true", help="Launch DayZ Diag (implies --build)")
    parser.add_argument("--execute", action="store_true", help="Run the plan instead of printing it")
    args = parser.parse_args(argv)
    if args.launch and not args.server:
        parser.error("--launch needs --server")
    if args.scaffold is not None and not args.source:
        parser.error("--scaffold/--no-scaffold only apply with --import-from")
    return args


def main(argv: list[str] | None = None, project: Path | None = None) -> int:
    args = parse_args(argv)
    project = project or PROJECT_DIR
    intent = Intent(
        mod_name=args.mod, source=args.source, scaffold=args.scaffold, author=args.author,
        server_map=args.server, build=args.build, launch=args.launch,
    )

    autofix, hard = classify(run_all())
    if hard or any(i.name == "p_drive" for i in autofix):
        print("[FAIL] Environment not ready; run check_env.py and resolve it first:", file=sys.stderr)
        for issue in hard + autofix:
            print(f"       {issue.message}", file=sys.stderr)
        return 2

    steps = build_steps(intent, mod_exists(project, args.mod))
    print(render_plan(steps))
    if not args.execute:
        return 0
    try:
        return execute(steps, intent, project)
    except DispatchError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
