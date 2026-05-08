"""Plan building, rendering, and execution for /dayz-init.

A Plan is a list of Steps. Each Step has a `kind` (string identifying which
skill to invoke), a human-readable label for the plan render, and optional
extra args.

Execution wraps each step in a try/except. On failure, returns the index
of the failing step so the caller can show "stopped at step N/M".
"""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from env_check import EnvIssue
from intent import Intent

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass
class Step:
    kind: str
    label: str
    args: list[str] = field(default_factory=list)


def build_steps(intent: Intent, autofix_issues: list[EnvIssue]) -> list[Step]:
    """Compose the full ordered list of steps from intent + env state."""
    steps: list[Step] = []

    # Autofix env issues first.
    for issue in autofix_issues:
        steps.append(
            Step(
                kind=f"autofix:{issue.name}",
                label=issue.message,
            )
        )

    # Required: scaffold OR import.
    if intent.is_new:
        steps.append(
            Step(
                kind="scaffold",
                label=f"Scaffold {intent.mod_name} at {intent.project_path}",
                args=[intent.mod_name, str(intent.project_path)],
            )
        )
    else:
        steps.append(
            Step(
                kind="import_mod",
                label=f"Import existing mod at {intent.project_path}",
                args=[str(intent.project_path), intent.mod_name],
            )
        )

    # Required: junction P:\<Mod>\.
    steps.append(
        Step(
            kind="junction_mod",
            label=f"Junction P:\\{intent.mod_name}\\",
            args=[intent.mod_name, str(intent.project_path)],
        )
    )

    # Required: cache project root.
    steps.append(
        Step(
            kind="cache_project",
            label="Cache project root",
            args=[str(intent.project_path)],
        )
    )

    # Optional: server stage.
    if intent.add_server and intent.server_map:
        steps.append(
            Step(
                kind="stage_server",
                label=f"Stage {intent.server_map} server",
                args=[intent.server_map, intent.server_map],  # instance name = map alias for now
            )
        )

    # Optional: PBO build.
    if intent.build_pbo:
        steps.append(
            Step(
                kind="build_pbo",
                label=f"Build {intent.mod_name}.pbo",
                args=[intent.mod_name],
            )
        )

    # Optional: launch diag.
    if intent.launch_diag and intent.server_map:
        steps.append(
            Step(
                kind="launch_diag",
                label=(
                    f"Launch DayZDiag with {intent.mod_name} loaded "
                    f"on {intent.server_map}"
                ),
                args=[intent.mod_name, intent.server_map],
            )
        )

    return steps


def render_plan(steps: list[Step]) -> str:
    """Pretty-print the plan for the consent gate."""
    lines = ["── Plan ──"]
    for step in steps:
        lines.append(f"  • {step.label}")
    return "\n".join(lines)


def execute(steps: list[Step]) -> int:
    """Run each step in order. Return the 1-indexed failing step, or 0 on success."""
    for i, step in enumerate(steps, start=1):
        print(f"[{i}/{len(steps)}] {step.label}")
        try:
            _dispatch(step)
        except Exception as exc:
            print(f"  failed [{step.kind}]: {exc}")
            return i
        print("  ok")
    return 0


def _dispatch(step: Step) -> None:
    """Map a step kind to the existing skill that performs it."""
    if step.kind.startswith("autofix:"):
        which = step.kind.split(":", 1)[1]
        if which == "p_drive":
            _dispatch_p_drive_autofix()
        elif which == "mods_junction":
            _create_mods_junction()
        else:
            raise RuntimeError(f"Unknown autofix kind: {which}")
        return

    if step.kind == "scaffold":
        mod_name, project_path = step.args
        _run("dayz-new-mod", "new_mod.py", mod_name, "--path", project_path)
    elif step.kind == "import_mod":
        project_path, mod_name = step.args
        _run("dayz-import-mod", "import_mod.py", "--source", project_path, "--name", mod_name)
    elif step.kind == "junction_mod":
        _create_mod_junction(*step.args)
    elif step.kind == "cache_project":
        from state import write_cached_project_root  # local import
        write_cached_project_root(Path(step.args[0]))
    elif step.kind == "stage_server":
        instance, map_name = step.args
        _run("dayz-add-server", "add_server.py", instance, "--map", map_name)
    elif step.kind == "build_pbo":
        _run("dayz-build-pbo", "build.py", *step.args)
    elif step.kind == "launch_diag":
        mod_name, server_map = step.args
        _run("dayz-launch-test", "launch.py", mod_name, "--server", server_map)
    else:
        raise RuntimeError(f"Unknown step kind: {step.kind}")


def _run(skill_name: str, entry_filename: str, *args: str) -> None:
    """Invoke an existing skill via subprocess. Raises on non-zero exit."""
    skill_path = REPO_ROOT / ".claude" / "skills" / skill_name / entry_filename
    cmd = [sys.executable, str(skill_path), *args]
    subprocess.run(cmd, check=True)


def _dispatch_p_drive_autofix() -> None:
    """Mount P:\\ via dayz-workdrive's mount.ps1."""
    skill_dir = REPO_ROOT / ".claude" / "skills" / "dayz-workdrive"
    subprocess.run(
        ["powershell", "-NoProfile", "-File", str(skill_dir / "mount.ps1")],
        check=True,
    )


def _create_mods_junction() -> None:
    """Create P:\\Mods\\ junction to <DayZ install>\\!Workshop\\.

    Reads the DayZ install path from Steam's app manifest if available,
    otherwise falls back to the conventional path. Best-effort.
    """
    workshop_candidates = [
        Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZ\!Workshop"),
        Path(r"C:\Program Files\Steam\steamapps\common\DayZ\!Workshop"),
    ]
    workshop = next((p for p in workshop_candidates if p.is_dir()), None)
    if workshop is None:
        raise RuntimeError(
            "Could not find DayZ !Workshop directory. "
            "Verify DayZ is installed via Steam, then re-run /dayz-init."
        )
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", "P:\\Mods", str(workshop)],
        check=True,
    )


def _create_mod_junction(mod_name: str, project_path: str) -> None:
    """Create P:\\<ModName>\\ junction to <project_path>."""
    target = f"P:\\{mod_name}"
    try:
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", target, project_path],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Failed to create junction {target} -> {project_path}.\n"
            f"  mklink output: {exc.stderr or exc.stdout}\n"
            f"  Try running Claude Code with elevated privileges, or enable Developer Mode."
        ) from exc
