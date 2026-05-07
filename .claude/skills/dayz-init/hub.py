"""Mission-control hub for /dayz-init.

Runs every time /dayz-init is invoked after setup is complete. Renders
project status, a flat menu of actions, and dispatches the user's pick
to existing skills via subprocess.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from prompts import ask_select, ask_yes_no
from state import read_state


REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Status:
    project: Path
    pbo_path: Path | None
    pbo_age_minutes: int | None
    server_instance: str | None
    diag_running: bool
    rag_on: bool
    audit_recent: bool


def gather_status(project: Path) -> Status:
    state = read_state(project)
    mod_name = project.name
    pbo = Path(f"P:\\Mods\\@{mod_name}\\Addons\\{mod_name}.pbo")
    pbo_path = pbo if pbo.is_file() else None
    pbo_age = (
        int((datetime.now(timezone.utc).timestamp() - pbo.stat().st_mtime) / 60)
        if pbo_path
        else None
    )
    server_dir = project / ".server"
    server_instance: str | None = None
    if server_dir.is_dir():
        instances = [p.name for p in server_dir.iterdir() if p.is_dir()]
        server_instance = instances[0] if instances else None

    return Status(
        project=project,
        pbo_path=pbo_path,
        pbo_age_minutes=pbo_age,
        server_instance=server_instance,
        diag_running=_diag_running(),
        rag_on=bool(os.environ.get("VOYAGE_API_KEY"))
        and state.get("rag_choice") in ("paste", "pull"),
        audit_recent=False,
    )


def render_status(status: Status) -> str:
    mod_name = status.project.name
    lines = [f"-- /dayz-init  -  {mod_name} --"]
    lines.append(f"Path:    {status.project}")
    if status.pbo_path:
        lines.append(f"PBO:     built {status.pbo_age_minutes}m ago")
    else:
        lines.append("PBO:     not built yet")
    if status.server_instance:
        running_tag = "running" if status.diag_running else "staged (not running)"
        lines.append(f"Server:  {status.server_instance}, {running_tag}")
    else:
        lines.append("Server:  not configured")
    lines.append(f"Diag:    {'running' if status.diag_running else 'not running'}")
    lines.append(f"RAG:     {'on' if status.rag_on else 'skipped'}")
    return "\n".join(lines)


def _diag_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq DayZDiag_x64.exe"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return "DayZDiag_x64.exe" in out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _run_skill(skill_name: str, entry_filename: str, *args: str) -> int:
    path = REPO_ROOT / ".claude" / "skills" / skill_name / entry_filename
    return subprocess.run([sys.executable, str(path), *args]).returncode


def _action_build_and_launch(status: Status) -> None:
    if status.server_instance is None:
        if ask_yes_no("No server configured. Set one up first?", default=True):
            chosen = ask_select(
                "Map?",
                ["chernarus", "livonia", "sakhal", "namalsk"],
                default="chernarus",
            )
            _run_skill("dayz-add-server", "add_server.py", chosen, "--map", chosen)
            status.server_instance = chosen
        else:
            return
    mod_name = status.project.name
    if _run_skill("dayz-build-pbo", "build.py", mod_name) != 0:
        print("(build failed; see output above)")
        return
    _run_skill(
        "dayz-launch-test",
        "launch.py",
        mod_name,
        "--server",
        status.server_instance,
    )


def _action_stop_diag(_: Status) -> None:
    if not ask_yes_no("Stop the diag client?", default=True):
        return
    _run_skill("dayz-stop-test", "stop_test.py")


def _action_tail_log(status: Status) -> None:
    if not status.server_instance:
        print("(no server to tail)")
        return
    log = (
        status.project
        / ".server"
        / status.server_instance
        / "server-profiles"
        / "script.log"
    )
    if not log.is_file():
        print(f"(log not found: {log})")
        return
    print(f"Tailing {log}. Ctrl-C to return to the hub.")
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "Get-Content", "-Wait", str(log)]
        )
    except KeyboardInterrupt:
        pass


def _action_workbench(status: Status) -> None:
    _run_skill(
        "dayz-launch-workbench", "launch.py", "--mod", status.project.name
    )


def _action_objbuilder(status: Status) -> None:
    _run_skill(
        "dayz-launch-objectbuilder",
        "launch.py",
        "--mod",
        status.project.name,
    )


def _action_quit(_: Status) -> None:
    raise SystemExit(0)


ACTIONS: list[tuple[str, Callable[[Status], None]]] = [
    ("build & launch", _action_build_and_launch),
    ("stop diag", _action_stop_diag),
    ("tail server log", _action_tail_log),
    ("open in workbench", _action_workbench),
    ("open in objectbuilder", _action_objbuilder),
    ("quit", _action_quit),
]


def run_hub(project: Path) -> int:
    while True:
        status = gather_status(project)
        print()
        print(render_status(status))
        print()
        labels = [label for label, _ in ACTIONS]
        choice = ask_select("? what now", labels, default=labels[0])
        for label, action in ACTIONS:
            if label == choice:
                try:
                    action(status)
                except SystemExit:
                    return 0
                break
