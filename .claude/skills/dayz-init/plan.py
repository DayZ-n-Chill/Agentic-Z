"""dayz-init Steps 4-5: build the setup plan, print it, and optionally run it.

Usage:
    python plan.py --mod NAME [--import-from PATH [--scaffold | --no-scaffold]]
                   [--author HANDLE] [--goal TEXT [--item TEXT]... [--behavior TEXT]...
                   [--done-check TEXT]...] [--server MAP] [--build] [--launch [--deps MOD ...]]
                   [--execute]

Without --execute: prints the plan and exits 0.
With --execute: runs each step in order and stops at the first failure,
exiting with that step's exit code. Refuses (exit 2) while the environment
check reports a hard stop or P:\\ is not mounted.

Steps, in order (each skipped when not needed):
  1. new-mod / import-mod   skipped when workspace/<mod> already exists
  2. spec            --goal; writes workspace/<mod>/spec.md for the
                     dayz-mod-architect, skipped when spec.md already exists
  3. record          write the per-clone project cache and the active mod
  4. add-server      --server
  5. build           --build, or implied by --launch
  6. launch          --launch (needs --server); --deps mods load before the mod
The P:\\Mods junction is not a step: /dayz-preflight, which every child skill
runs first, creates it when it is missing.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dispatch import KNOWN_MAPS, DispatchError, command_for, run
from env_check import classify, run_all
from state import PROJECT_DIR, mod_exists, write_cached_project_root, write_state
from skill_helpers import is_link  # on sys.path via env_check

SPEC_FILENAME = "spec.md"


@dataclass
class Spec:
    """What the mod should do, in the user's words. dayz-mod-architect reads it first."""
    goal: str
    items: list[str] = field(default_factory=list)
    behaviors: list[str] = field(default_factory=list)
    done_checks: list[str] = field(default_factory=list)


@dataclass
class Intent:
    mod_name: str
    source: str | None = None        # set for an import, None for a new mod
    scaffold: bool | None = None     # import only: write missing pieces into the source?
    author: str | None = None        # new mod or --scaffold import: passed as --author
    server_map: str | None = None
    build: bool = False
    launch: bool = False
    deps: list[str] = field(default_factory=list)  # launch: @mods the mod's requiredAddons need
    spec: Spec | None = None


@dataclass
class Step:
    action: str
    label: str
    params: dict = field(default_factory=dict)


def spec_path(project: Path, mod_name: str) -> Path:
    return project / "workspace" / mod_name / SPEC_FILENAME


def build_steps(
    intent: Intent, already_exists: bool, spec_exists: bool = False, linked: bool = False,
) -> list[Step]:
    """Ordered steps for this intent.

    linked: workspace/<mod> is a link to the user's source folder. Only a
    --scaffold import may write into it, so a re-run never adds spec.md there.
    """
    steps: list[Step] = []
    mod = intent.mod_name
    if already_exists:
        pass
    elif intent.source:
        params = {"mod": mod, "source": intent.source, "scaffold": intent.scaffold}
        if intent.scaffold:
            # A scaffolded config.cpp needs the author handle.
            params["author"] = intent.author
        steps.append(Step("import-mod", f"Import {intent.source} as {mod}", params))
    else:
        steps.append(Step("new-mod", f"Scaffold workspace\\{mod}", {"mod": mod, "author": intent.author}))

    if intent.spec and not spec_exists and not (linked and intent.scaffold is not True):
        steps.append(Step("spec", f"Write workspace\\{mod}\\{SPEC_FILENAME}"))

    steps.append(Step("record", f"Record {mod} as the active mod"))

    if intent.server_map:
        steps.append(Step("add-server", f"Set up the {intent.server_map} test server", {"server": intent.server_map}))
    if intent.build or intent.launch:
        steps.append(Step("build", f"Build {mod}.pbo", {"mod": mod}))
    if intent.launch:
        params = {"mod": mod, "server": intent.server_map}
        with_deps = ""
        if intent.deps:
            params["deps"] = list(intent.deps)
            with_deps = f" (after {', '.join(intent.deps)})"
        steps.append(Step("launch", f"Launch DayZ Diag with {mod}{with_deps} on {intent.server_map}", params))
    return steps


def render_plan(steps: list[Step]) -> str:
    return "\n".join(["Plan:"] + [f"  {i}. {s.label}" for i, s in enumerate(steps, start=1)])


def _one_line(text: str) -> str:
    return " ".join(text.split())


def render_spec(mod_name: str, spec: Spec) -> str:
    def section(title: str, entries: list[str]) -> list[str]:
        lines = [f"- {_one_line(e)}" for e in entries if e.strip()] or ["- None yet."]
        return ["", f"## {title}", ""] + lines

    lines = [f"# {mod_name} spec", "", "## Goal", "", _one_line(spec.goal)]
    lines += section("Items", spec.items)
    lines += section("Behaviors", spec.behaviors)
    lines += section("Done checks", spec.done_checks)
    return "\n".join(lines) + "\n"


def write_spec(project: Path, intent: Intent) -> None:
    path = spec_path(project, intent.mod_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_spec(intent.mod_name, intent.spec), encoding="utf-8")


def record_project(project: Path, intent: Intent) -> None:
    write_cached_project_root(project, project / ".claude" / "local-memory")
    write_state(project, {
        "last_intent": {"mod_name": intent.mod_name},
    })


def execute(steps: list[Step], intent: Intent, project: Path) -> int:
    """Run steps in order. Return 0, or the exit code of the first failing step."""
    for i, step in enumerate(steps, start=1):
        print(f"\n[{i}/{len(steps)}] {step.label}", flush=True)
        if step.action == "record":
            record_project(project, intent)
            continue
        if step.action == "spec":
            write_spec(project, intent)
            continue
        rc = run(command_for(step.action, **step.params))
        if rc != 0:
            print(f"[FAIL] Step {i}/{len(steps)} ({step.label}) exited with {rc}.", file=sys.stderr)
            return rc
    print("\n[OK]   Setup complete.")
    return 0


# The mod name rule SKILL.md states: it becomes a folder, a PBO name and a CfgPatches class.
MOD_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan and run /dayz-init setup.")
    parser.add_argument("--mod", required=True, help="Mod name (folder under workspace/)")
    parser.add_argument("--import-from", dest="source", help="Existing mod folder to import")
    scaffold = parser.add_mutually_exclusive_group()
    scaffold.add_argument("--scaffold", dest="scaffold", action="store_true", default=None,
                          help="Import: write missing pieces into the source folder")
    scaffold.add_argument("--no-scaffold", dest="scaffold", action="store_false",
                          help="Import: link only, never write into the source folder")
    parser.add_argument("--author", help="New mod or --scaffold import: author handle (cached for future runs)")
    parser.add_argument("--goal", help="Spec: what the mod should do (writes workspace/<mod>/spec.md)")
    parser.add_argument("--item", dest="items", action="append", default=[],
                        help="Spec: an item the mod adds (repeatable)")
    parser.add_argument("--behavior", dest="behaviors", action="append", default=[],
                        help="Spec: something a player can do or see in game (repeatable)")
    parser.add_argument("--done-check", dest="done_checks", action="append", default=[],
                        help="Spec: a check that proves the mod is done (repeatable)")
    parser.add_argument("--server", choices=KNOWN_MAPS, help="Set up a test server on this map")
    parser.add_argument("--build", action="store_true", help="Build the PBO")
    parser.add_argument("--launch", action="store_true", help="Launch DayZ Diag (implies --build)")
    parser.add_argument("--deps", action="extend", nargs="+", default=[], metavar="MOD",
                        help="Launch: dependency @mods in load order, for requiredAddons that vanilla "
                             "does not provide (repeatable)")
    parser.add_argument("--execute", action="store_true", help="Run the plan instead of printing it")
    args = parser.parse_args(argv)
    if not MOD_NAME_RE.fullmatch(args.mod):
        parser.error(f"--mod {args.mod!r}: use letters, digits and underscores, starting with a letter")
    if args.launch and not args.server:
        parser.error("--launch needs --server")
    if args.deps and not args.launch:
        parser.error("--deps only applies with --launch")
    if args.scaffold is not None and not args.source:
        parser.error("--scaffold/--no-scaffold only apply with --import-from")
    if args.source and args.scaffold is None:
        # import_mod.py would otherwise prompt per piece, and the wizard's
        # scripts never prompt.
        parser.error("--import-from needs --scaffold or --no-scaffold")
    if args.goal is not None and not args.goal.strip():
        parser.error("--goal is empty")
    if (args.items or args.behaviors or args.done_checks) and not args.goal:
        parser.error("--item, --behavior and --done-check need --goal")
    if args.goal and args.scaffold is False:
        # A link-only import never writes into the user's source folder.
        parser.error("--goal does not apply with --no-scaffold")
    return args


def main(argv: list[str] | None = None, project: Path | None = None) -> int:
    args = parse_args(argv)
    project = project or PROJECT_DIR
    intent = Intent(
        mod_name=args.mod, source=args.source, scaffold=args.scaffold, author=args.author,
        server_map=args.server, build=args.build, launch=args.launch, deps=args.deps,
        spec=Spec(args.goal, args.items, args.behaviors, args.done_checks) if args.goal else None,
    )

    autofix, hard = classify(run_all())
    if hard or any(i.name == "p_drive" for i in autofix):
        print("[FAIL] Environment not ready; run check_env.py and resolve it first:", file=sys.stderr)
        for issue in hard + autofix:
            print(f"       {issue.message}", file=sys.stderr)
        return 2

    steps = build_steps(
        intent, mod_exists(project, args.mod), spec_path(project, args.mod).is_file(),
        linked=is_link(project / "workspace" / args.mod),
    )
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
