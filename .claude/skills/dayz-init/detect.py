"""Detection helpers for /dayz-init.

cwd, mod name from disk, mod-dir heuristic. Pure functions over Paths;
no I/O side effects beyond reading.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


_CFGPATCHES_CLASS_RE = re.compile(
    r"class\s+CfgPatches\s*\{[^}]*?class\s+(\w+)",
    re.DOTALL,
)


def cwd() -> Path:
    """Current working directory as an absolute Path."""
    return Path(os.getcwd()).resolve()


def mod_name_from_cwd(path: Path | None = None) -> str:
    """Default mod name from a directory's basename."""
    return (path or cwd()).name


def mod_name_from_config_cpp(mod_dir: Path) -> str | None:
    """Extract first CfgPatches class name from <mod_dir>/config.cpp.

    Returns None if config.cpp is missing or has no CfgPatches block.
    """
    cfg = mod_dir / "config.cpp"
    if not cfg.is_file():
        return None
    text = cfg.read_text(encoding="utf-8", errors="replace")
    match = _CFGPATCHES_CLASS_RE.search(text)
    return match.group(1) if match else None


def is_mod_dir(path: Path) -> bool:
    """Heuristic: does this directory look like a DayZ mod?

    Yes if it has either config.cpp or $PBOPREFIX$ at the top.
    """
    return (path / "config.cpp").is_file() or (path / "$PBOPREFIX$").is_file()
