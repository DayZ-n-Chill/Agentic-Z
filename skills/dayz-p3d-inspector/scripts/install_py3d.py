#!/usr/bin/env python3
"""Install the DayZ fork of py3d from a built wheel, into the interpreter that runs this script.

Optional: the inspector scripts use the fork straight from scripts/tools/py3d in this
repo, with nothing installed. Run this only when you want the fork importable as
`py3d` everywhere (a notebook, another tool) and a wheel has been built.

The wheel is py3d_dayz-<version>-py3-none-any.whl. It is looked for in this skill's
wheels/ folder, then in scripts/tools/py3d/dist/ (where the fork's build script puts
it). Neither folder ships a wheel, so the script stops when none was built.

It refuses to guess: no wheel, more than one wheel, or an old py3d-*.whl beside the
new one all stop it. An installed py3d is replaced only when its own files say it is
the DayZ fork; any other py3d (the upstream library, or
the unrelated PyPI package of the same name) is left alone and the script stops.
Every pip call runs under the interpreter that runs this script.

Offline tool: it does not touch P:\\ or DayZ Tools, so it does not gate on /dayz-preflight.
"""

from __future__ import annotations

import ast
from importlib import import_module
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
from typing import Iterable, Sequence

try:
    from importlib import metadata
except ImportError:  # Python 3.7 compatibility.
    import importlib_metadata as metadata


SKILL_ROOT = Path(__file__).resolve().parent.parent
# Where the fork's own build script writes its wheel, in this repo.
REPO_DIST = SKILL_ROOT.parents[1] / "scripts" / "tools" / "py3d" / "dist"


class InstallerError(RuntimeError):
    """A fail-closed installer refusal."""


def _format_paths(paths: Iterable[Path]) -> str:
    return ", ".join(str(path) for path in paths)


def _legacy_wheels(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.glob("*.whl")
        if path.name.startswith("py3d-")
    )


def resolve_wheel(new_wheels: Sequence[Path], legacy_wheels: Sequence[Path]) -> Path:
    """Return the sole DayZ wheel, reporting absence before legacy collision."""
    new_wheels = list(new_wheels)
    legacy_wheels = list(legacy_wheels)

    if not new_wheels:
        detail = ""
        if legacy_wheels:
            detail = f"; legacy candidates present: {_format_paths(legacy_wheels)}"
        raise InstallerError(
            "no py3d_dayz-*-py3-none-any.whl in this skill's wheels folder or in "
            f"scripts/tools/py3d/dist{detail}"
        )
    if len(new_wheels) != 1:
        raise InstallerError(
            "expected exactly one py3d_dayz-*-py3-none-any.whl; found: "
            + _format_paths(new_wheels)
        )
    if legacy_wheels:
        raise InstallerError(
            "a valid DayZ wheel was found, but legacy py3d wheels are also present; "
            "refusing to install: "
            + _format_paths(legacy_wheels)
        )
    return new_wheels[0]


def _owned_init_files(dist: metadata.Distribution, imported_init: Path) -> list[Path]:
    files = dist.files
    if files is None:
        raise InstallerError(
            "the installed py3d distribution has no RECORD file; ownership is ambiguous"
        )

    distribution_root = Path(dist.locate_file("")).resolve()
    try:
        imported_init.relative_to(distribution_root)
    except ValueError as exc:
        raise InstallerError(
            "the imported py3d module is outside the installed distribution location "
            "and therefore cannot be owned by its RECORD"
        ) from exc

    owned: list[Path] = []
    for entry in files:
        portable = PurePosixPath(str(entry).replace("\\", "/"))
        if portable.is_absolute() or ".." in portable.parts:
            raise InstallerError("the py3d RECORD contains an unsafe path")
        candidate = Path(dist.locate_file(entry)).resolve()
        if candidate == imported_init:
            if portable.as_posix() != "py3d/__init__.py":
                raise InstallerError(
                    "the imported py3d module is not owned as py3d/__init__.py in RECORD"
                )
            owned.append(candidate)
    return owned


def authorize_legacy_uninstall(dist: metadata.Distribution, module: object) -> None:
    """Authorize removal only when this distribution owns the imported DayZ fork."""
    module_file = getattr(module, "__file__", None)
    if not module_file:
        raise InstallerError(
            "the imported py3d module has no concrete __init__.py; ownership is ambiguous"
        )
    imported_init = Path(module_file).resolve()
    if imported_init.name != "__init__.py" or not imported_init.is_file():
        raise InstallerError(
            "the imported py3d module does not resolve to an existing __init__.py"
        )

    owned = _owned_init_files(dist, imported_init)
    if len(owned) != 1:
        raise InstallerError(
            "the installed py3d distribution RECORD does not own the imported "
            "py3d/__init__.py exactly once"
        )

    owned_init = owned[0]
    try:
        source = owned_init.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InstallerError(
            "the RECORD-owned py3d/__init__.py cannot be read; identity is ambiguous"
        ) from exc
    try:
        tree = ast.parse(source, filename=str(owned_init))
    except (SyntaxError, ValueError) as exc:
        raise InstallerError(
            "the RECORD-owned py3d/__init__.py cannot be parsed; identity is ambiguous"
        ) from exc

    flag_values = []
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            matching_targets = [
                target
                for target in statement.targets
                if isinstance(target, ast.Name) and target.id == "IS_DAYZ_FORK"
            ]
            if matching_targets:
                if len(statement.targets) != 1:
                    raise InstallerError(
                        "the RECORD-owned py3d/__init__.py has an ambiguous "
                        "IS_DAYZ_FORK assignment"
                    )
                flag_values.append(statement.value)
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == "IS_DAYZ_FORK"
        ):
            flag_values.append(statement.value)

    if len(flag_values) != 1 or flag_values[0] is None:
        raise InstallerError(
            "the RECORD-owned py3d/__init__.py must contain exactly one "
            "IS_DAYZ_FORK assignment; identity is ambiguous"
        )
    try:
        disk_flag = ast.literal_eval(flag_values[0])
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as exc:
        raise InstallerError(
            "the RECORD-owned py3d/__init__.py IS_DAYZ_FORK value is not a "
            "recognizable literal; identity is ambiguous"
        ) from exc
    if type(disk_flag) is not bool:
        raise InstallerError(
            "the RECORD-owned py3d/__init__.py IS_DAYZ_FORK value is not a "
            "boolean literal; identity is ambiguous"
        )
    if disk_flag is not True:
        raise InstallerError(
            "an existing py3d distribution is not the DayZ fork; refusing to uninstall it"
        )


def pip_command(*arguments: str) -> list[str]:
    """Bind every pip mutation to the interpreter that ran the gate."""
    return [sys.executable, "-m", "pip", *arguments]


def _preexisting_action() -> str:
    distributions = list(metadata.distributions(name="py3d"))
    if not distributions:
        return "install"
    if len(distributions) != 1:
        raise InstallerError(
            "multiple installed distributions claim the py3d name; refusing to mutate"
        )

    try:
        module = import_module("py3d")
    except Exception as exc:
        raise InstallerError(
            f"an installed py3d distribution exists but cannot be imported: {exc}"
        ) from exc

    authorize_legacy_uninstall(distributions[0], module)
    return "replace-dayz-legacy"


def _select_wheel() -> Path:
    primary = SKILL_ROOT / "wheels"
    new_wheels = sorted(primary.glob("py3d_dayz-*-py3-none-any.whl"))
    legacy_wheels = _legacy_wheels(primary)

    if not new_wheels:
        new_wheels = sorted(REPO_DIST.glob("py3d_dayz-*-py3-none-any.whl"))
        legacy_wheels.extend(_legacy_wheels(REPO_DIST))
    return resolve_wheel(new_wheels, legacy_wheels)


def _run_pip(*arguments: str) -> None:
    command = pip_command(*arguments)
    printable = " ".join(shlex.quote(part) for part in command)
    print("+ " + printable)
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise InstallerError(
            f"pip exited with status {completed.returncode}: {printable}"
        )


def main() -> int:
    wheel = _select_wheel()
    action = _preexisting_action()
    if action == "replace-dayz-legacy":
        _run_pip("uninstall", "-y", "py3d")
    _run_pip("install", "--break-system-packages", str(wheel))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except InstallerError as exc:
        print(f"ABORT: {exc}", file=sys.stderr)
        raise SystemExit(1)
