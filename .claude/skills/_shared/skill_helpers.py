"""Shared helpers for the DayZ pipeline skills (build, deploy, clean, scaffold, launch).

One copy of the logic every pipeline script needs:
  - load a sibling skill's .py by file path (load_module)
  - the /dayz-preflight resolvers, loaded on first use (h.preflight.find_dayz_tools, ...)
  - the /dayz-preflight gate (gate_on_preflight)
  - the cached project root written by /dayz-init (resolve_project_dir)
  - link inspection that never follows a junction (is_link, link_target, paths_equal)
  - the P:\\Mods\\@<ModName>\\ ownership marker (owns_deploy_dir, gate_on_marker, write_marker)
  - creation flags that detach a launched GUI tool from the console (DETACH_FLAGS)

Import from a skill script with:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
    import skill_helpers as h
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional

SKILLS_DIR = Path(__file__).resolve().parents[1]
PREFLIGHT = SKILLS_DIR / "dayz-preflight" / "preflight.py"
DAYZ_INIT_STATE = SKILLS_DIR / "dayz-init" / "state.py"

# Ownership marker at P:\Mods\@<ModName>\<SCAFFOLD_MARKER>, content = the modname.
# Written by /dayz-build-pbo and /dayz-deploy-pbo after a successful run. Build
# and deploy refuse to write into an existing @<ModName> without it, and
# /dayz-clean-workspace only removes a deployed dir that has it, so a subscribed
# or hand-placed mod with a colliding name is never touched. It sits one level
# above Addons\ so AddonBuilder's -clear (which wipes Addons\) keeps it.
SCAFFOLD_MARKER = ".agentic-z-scaffold"

# Popen creationflags for a GUI tool that must outlive this script and the
# console it ran in: DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP.
DETACH_FLAGS = 0x00000008 | 0x00000200

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def load_module(name: str, path: Path) -> ModuleType:
    """Load a .py file as a module by path (sibling skills are not packages)."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def __getattr__(name: str):
    """Load dayz-preflight/preflight.py on first access of h.preflight.

    Lazy so importing skill_helpers never executes preflight.py (and a missing
    preflight.py only fails the callers that need it).
    """
    if name == "preflight":
        module = load_module("dayz_preflight_module", PREFLIGHT)
        globals()["preflight"] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def gate_on_preflight() -> None:
    """Run /dayz-preflight and exit with its code if it fails."""
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight skill not found at {PREFLIGHT}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def resolve_project_dir() -> Path:
    """Return the project root cached by /dayz-init.

    Exits 2 pointing at /dayz-init when nothing is cached or the cached
    directory no longer exists (moved or deleted clone).
    """
    state = load_module("dayz_init_state_module", DAYZ_INIT_STATE)
    project = state.cached_project_root()
    if project is None:
        print(f"{FAIL} No project cached.", file=sys.stderr)
        print("       Run /dayz-init to set up your DayZ environment and project.", file=sys.stderr)
        sys.exit(2)
    if not project.is_dir():
        print(f"{FAIL} Cached project directory no longer exists: {project}", file=sys.stderr)
        print("       Run /dayz-init again to re-cache the project root.", file=sys.stderr)
        sys.exit(2)
    return project.resolve()


def is_link(path: Path) -> bool:
    """True for a symlink or a Windows junction.

    os.path.islink is False for junctions, so on Windows also check the
    reparse-point attribute. Callers rely on this to avoid shutil.rmtree on a
    junction, which would recurse into (and delete) the link's target.
    """
    if os.path.islink(path):
        return True
    if os.name == "nt":
        try:
            st = os.lstat(path)
        except OSError:
            return False
        return bool(getattr(st, "st_file_attributes", 0) & 0x400)  # FILE_ATTRIBUTE_REPARSE_POINT
    return False


def _preflight() -> ModuleType:
    return globals().get("preflight") or __getattr__("preflight")


def link_target(path: Path) -> Optional[Path]:
    """The target of a symlink or junction, or None if not a link (preflight's resolver)."""
    return _preflight().link_target(path)


def paths_equal(a: Path, b: Path) -> bool:
    """True when two paths name the same location (preflight's resolver)."""
    return _preflight().paths_equal(a, b)


def owns_deploy_dir(deploy_root: Path, modname: str) -> bool:
    """True when deploy_root holds the ownership marker with content == modname."""
    marker = deploy_root / SCAFFOLD_MARKER
    if not marker.is_file():
        return False
    try:
        return marker.read_text(encoding="utf-8").strip() == modname
    except OSError:
        return False


def gate_on_marker(modname: str, deploy_root: Path) -> None:
    """Exit if deploy_root exists but is not ours. A missing deploy_root passes."""
    if not deploy_root.exists():
        return
    if not owns_deploy_dir(deploy_root, modname):
        sys.exit(
            f"{FAIL} {deploy_root}\\ exists but has no Agentic-Z ownership marker\n"
            f"       ({SCAFFOLD_MARKER} missing or content mismatch).\n"
            "       Refusing to write into it: it could be a subscribed mod or a hand-placed folder.\n"
            f"       If it is yours, remove it first: cmd /c rmdir /s /q \"{deploy_root}\""
        )
    print(f"{OK} {deploy_root}\\ ownership marker valid")


def write_marker(deploy_root: Path, modname: str) -> None:
    """Write the ownership marker. A failure only warns: the deploy itself succeeded."""
    marker = deploy_root / SCAFFOLD_MARKER
    try:
        marker.write_text(modname + "\n", encoding="utf-8")
    except OSError as e:
        print(f"{WARN} Could not write ownership marker {marker}: {e}")
        print("       /dayz-clean-workspace will refuse to remove this deployed dir.")
