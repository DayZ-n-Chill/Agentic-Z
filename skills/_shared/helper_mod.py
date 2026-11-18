"""Pack and remove a session-only helper mod under P:\\Mods\\@<name>\\.

Used by /dayz-gate visual (AZ_VisualHelper) and the dayz-testbridge MCP server
(AZ_TestBridge). A helper mod is packed for one test session and removed
afterwards; it is never part of a user's mod. The folder gets an ownership
marker so remove() and /dayz-clean-workspace may delete it and nothing else.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable


class HelperModError(ValueError):
    """The helper could not be packed or its folder belongs to someone else."""


class ForeignFolderError(HelperModError):
    """P:\\Mods\\@<name>\\ exists without our ownership marker."""


class PackError(HelperModError):
    """AddonBuilder failed or wrote no PBO."""


def root(p_drive: Path, name: str) -> Path:
    return p_drive / "Mods" / f"@{name}"


def owned(folder: Path, name: str, marker: str) -> bool:
    try:
        return (folder / marker).read_text(encoding="utf-8").strip() == name
    except OSError:
        return False


def install(source: Path, name: str, p_drive: Path, addon_builder: Path, marker: str,
            run: Callable[[list[str]], tuple[int, str]], stage_name: str = "") -> Path:
    """Pack `source` into P:\\Mods\\@<name>\\Addons\\<name>.pbo and return the @ folder.

    The source is copied to P:\\temp\\<stage_name>\\ (default _<name>) first,
    because AddonBuilder packs only from the work drive. Raises
    ForeignFolderError when the @ folder exists and is not ours, PackError when
    AddonBuilder fails or writes no PBO.
    """
    target = root(p_drive, name)
    if target.exists() and not owned(target, name, marker):
        raise ForeignFolderError(f"{target} exists but has no Agentic-Z ownership marker")
    stage = p_drive / "temp" / (stage_name or f"_{name}")
    if stage.exists():
        shutil.rmtree(stage)
    shutil.copytree(source, stage / name)
    addons = target / "Addons"
    addons.mkdir(parents=True, exist_ok=True)
    (target / marker).write_text(name + "\n", encoding="utf-8")
    cmd = [str(addon_builder), str(stage / name), str(addons), f"-prefix={name}",
           f"-temp={stage / 'tmp'}", "-packonly"]
    rc, out = run(cmd)
    pbo = addons / f"{name}.pbo"
    if rc != 0 or not pbo.is_file():
        raise PackError(f"AddonBuilder exit {rc}: {out.strip()[-300:]}")
    shutil.rmtree(stage, ignore_errors=True)
    return target


def remove(p_drive: Path, name: str, marker: str) -> bool:
    """Delete P:\\Mods\\@<name>\\ when it holds our marker. True when it was removed."""
    target = root(p_drive, name)
    if target.exists() and owned(target, name, marker):
        shutil.rmtree(target)
        return True
    return False
