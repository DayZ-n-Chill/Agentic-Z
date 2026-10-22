"""dayz-init dispatch: one command table for every step and hub action.

/dayz-init never re-implements a sibling skill; each action maps to that
skill's own entry point. The plan executor (plan.py) and the hub both go
through command_for(), so SKILL.md, the plan and the hub cannot drift apart.

Usage (hub actions):
    python dispatch.py <action> [--mod NAME] [--server MAP] [--deps CF ...]
    python dispatch.py --list
--mod defaults to the active mod recorded by /dayz-init. Exits with the
child skill's exit code, or 2 if the action is missing a required value.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

from hub_status import launch_needs, needs_message
from state import PROJECT_DIR, active_mod

SKILLS_DIR = Path(__file__).resolve().parents[1]
ADD_SERVER = SKILLS_DIR / "dayz-add-server" / "add_server.py"


def _load_known_maps() -> tuple[str, ...]:
    """The map aliases /dayz-add-server accepts, read from its own table."""
    spec = importlib.util.spec_from_file_location("dayz_add_server_module", ADD_SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.KNOWN_MAPS)


KNOWN_MAPS = _load_known_maps()


class DispatchError(ValueError):
    """An action was asked for without a value it needs."""


def _py(skill: str, script: str, *args: str) -> list[str]:
    return [sys.executable, str(SKILLS_DIR / skill / script), *args]


def _need(value: str | None, flag: str, action: str) -> str:
    if not value:
        raise DispatchError(f"'{action}' needs {flag}")
    return value


def command_for(
    action: str,
    mod: str | None = None,
    server: str | None = None,
    source: str | None = None,
    author: str | None = None,
    scaffold: bool | None = None,
    deps: list[str] | None = None,
) -> list[str]:
    """Return the argv that performs `action`. Raises DispatchError on missing values."""
    if action == "mount-p":
        return _py("dayz-workdrive", "mount.py")
    if action == "new-mod":
        argv = _py("dayz-new-mod", "new_mod.py", _need(mod, "--mod", action))
        return argv + ["--author", author] if author else argv
    if action == "import-mod":
        argv = _py(
            "dayz-import-mod", "import_mod.py",
            "--source", _need(source, "--source", action),
            "--name", _need(mod, "--mod", action),
        )
        if scaffold is not None:
            argv.append("--scaffold" if scaffold else "--no-scaffold")
        if author:
            argv += ["--author", author]
        return argv
    if action == "add-server":
        server = _need(server, "--server", action)
        return _py("dayz-add-server", "add_server.py", server, "--map", server)
    if action == "build":
        return _py("dayz-build-pbo", "build.py", _need(mod, "--mod", action))
    if action == "launch":
        # /dayz-launch-test loads its mod names in order, so dependencies go first.
        names = [d.lstrip("@") for d in deps or []]
        return _py(
            "dayz-launch-test", "launch.py",
            *names, _need(mod, "--mod", action), "--server", _need(server, "--server", action),
        )
    if action == "gate-build":
        return _py("dayz-gate", "gate.py", "build", _need(mod, "--mod", action))
    if action == "gate-ingame":
        argv = _py("dayz-gate", "gate.py", "ingame", _need(mod, "--mod", action),
                   "--server", _need(server, "--server", action))
        return argv + ["--deps", *deps] if deps else argv
    if action == "lint":
        return _py("dayz-lint", "lint.py", _need(mod, "--mod", action))
    if action == "health":
        return _py("dayz-health", "health.py", _need(mod, "--mod", action))
    if action == "stop":
        return ["cmd", "/c", str(SKILLS_DIR / "dayz-stop-test" / "stop_test.bat")]
    if action == "workbench":
        return _py("dayz-launch-workbench", "launch.py", "--mod", _need(mod, "--mod", action))
    if action == "objectbuilder":
        return _py("dayz-launch-objectbuilder", "launch.py", "--mod", _need(mod, "--mod", action))
    if action == "search-download":
        return _py("dayz-search-download", "download.py")
    raise DispatchError(f"unknown action '{action}'")


HUB_ACTIONS = (
    "add-server", "build", "launch", "stop", "workbench", "objectbuilder", "search-download", "mount-p",
    "lint", "gate-build", "gate-ingame", "health",
)


def run(argv: list[str]) -> int:
    print("[CMD]  " + subprocess.list2cmdline(argv), flush=True)
    return subprocess.run(argv).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one /dayz-init hub action.")
    parser.add_argument("action", nargs="?", choices=HUB_ACTIONS)
    parser.add_argument("--mod", help="Mod name (default: the active mod)")
    parser.add_argument("--server", help=f"Server instance / map alias ({', '.join(KNOWN_MAPS)})")
    parser.add_argument("--deps", nargs="+", default=[], metavar="MOD",
                        help="launch and gate-ingame: dependency mods in load order (CF or @CF)")
    parser.add_argument("--list", action="store_true", help="Print the hub actions and exit")
    args = parser.parse_args(argv)

    if args.list or not args.action:
        print("\n".join(HUB_ACTIONS))
        return 0
    mod = args.mod or active_mod(PROJECT_DIR)
    try:
        cmd = command_for(args.action, mod=mod, server=args.server, deps=args.deps)
    except DispatchError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    # gate-ingame refuses this itself; launch.py does not, so check here.
    needs = launch_needs(PROJECT_DIR / "workspace" / mod) if args.action == "launch" and not args.deps else []
    if needs:
        print(f"[FAIL] {needs_message(mod, needs)}", file=sys.stderr)
        return 2
    return run(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
