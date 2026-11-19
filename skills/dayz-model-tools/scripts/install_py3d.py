#!/usr/bin/env python3
"""Install the DayZ py3d fork from a wheel, with the interpreter that ran this script.

The wheel is looked for in this skill's wheels/ folder first, then in the dist/
folder of the fork that ships in this repository (scripts/tools/py3d/dist). The
script stops, changing nothing, when no wheel or more than one is found, when a
legacy py3d-*.whl sits beside it, or when a py3d that is already installed is
not the DayZ fork (the PyPI package named py3d is an unrelated library).

Without a wheel, install the fork from source instead:
    python -m pip install -e scripts/tools/py3d
"""

from __future__ import annotations

import argparse
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


WHEEL_GLOB = "py3d_dayz-*-py3-none-any.whl"
# <skill>/wheels: a wheel placed next to this skill wins over the fallback.
PRIMARY_WHEELS = Path(__file__).resolve().parent.parent / "wheels"
# <repo>/scripts/tools/py3d/dist: where the fork's wheel build leaves its wheel.
FALLBACK_DIST = Path(__file__).resolve().parents[3] / "scripts" / "tools" / "py3d" / "dist"


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
            "no py3d_dayz-*-py3-none-any.whl matched the primary or fallback location"
            f"{detail}"
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
    new_wheels = sorted(PRIMARY_WHEELS.glob(WHEEL_GLOB))
    legacy_wheels = _legacy_wheels(PRIMARY_WHEELS)

    if not new_wheels:
        new_wheels = sorted(FALLBACK_DIST.glob(WHEEL_GLOB))
        legacy_wheels.extend(_legacy_wheels(FALLBACK_DIST))
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the wheel and the pip commands that would run, without running pip",
    )
    args = parser.parse_args(argv)
    wheel = _select_wheel()
    action = _preexisting_action()
    if args.dry_run:
        if action == "replace-dayz-legacy":
            print("would run: " + " ".join(pip_command("uninstall", "-y", "py3d")))
        print("would run: " + " ".join(pip_command("install", "--break-system-packages", str(wheel))))
        return 0
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
