"""dayz-build-pbo: Pack workspace/<ModName>/ into P:\\Mods\\@<ModName>\\Addons\\<ModName>.pbo.

Imports find_dayz_tools() from dayz-preflight to keep path discovery consistent.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# .../.claude/skills/dayz-build-pbo/build.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace"
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
INCLUDE_LIST = Path(__file__).resolve().parent / "include.lst"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"
TEMP_ROOT = P_DRIVE / "temp"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def _load_preflight_module():
    """Load preflight.py as a module by file path so static analyzers don't choke
    on a sys.path-based sibling import (preflight lives in dayz-preflight/, a
    sibling skill folder)."""
    spec = importlib.util.spec_from_file_location("dayz_preflight_module", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preflight module at {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reuse path resolution + validation from preflight per L2 conventions (single source of truth).
_preflight = _load_preflight_module()
find_dayz_tools = _preflight.find_dayz_tools
validate_p_mods = _preflight.validate_p_mods


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(
            f"{FAIL} dayz-preflight skill not found at "
            f"{PREFLIGHT.relative_to(REPO_ROOT)}"
        )
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def _link_target(path: Path) -> Optional[Path]:
    try:
        target = os.readlink(path)
    except OSError:
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return Path(target)


def _paths_equal(a: Path, b: Path) -> bool:
    return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))


def verify_workspace(modname: str) -> Path:
    target = WORKSPACE / modname
    if not target.exists():
        sys.exit(
            f"{FAIL} {target.relative_to(REPO_ROOT)} not found.\n"
            f"       Run: python .claude/skills/dayz-new-mod/new_mod.py {modname}"
        )
    if not (target / "config.cpp").exists():
        sys.exit(f"{FAIL} {target.relative_to(REPO_ROOT)}/config.cpp missing.")
    if not (target / "$PBOPREFIX$").exists():
        sys.exit(f"{FAIL} {target.relative_to(REPO_ROOT)}/$PBOPREFIX$ missing.")
    print(f"{OK} {target.relative_to(REPO_ROOT)}\\ found")
    return target


def verify_junction(modname: str, workspace_target: Path) -> Path:
    p_drive_link = P_DRIVE / modname
    if not os.path.lexists(p_drive_link):
        sys.exit(
            f"{FAIL} P:\\{modname} junction is missing.\n"
            f"       Run: python .claude/skills/dayz-new-mod/new_mod.py {modname}\n"
            f"       (or re-create the junction manually)."
        )
    link_target = _link_target(p_drive_link)
    if link_target is None:
        sys.exit(
            f"{FAIL} P:\\{modname} exists as a real folder, not a link.\n"
            "       Build expects the /dayz-new-mod junction. Move it aside and re-scaffold."
        )
    if not _paths_equal(link_target, workspace_target):
        sys.exit(
            f"{FAIL} P:\\{modname} points at {link_target}, expected {workspace_target}\n"
            "       Remove the wrong link and re-run /dayz-new-mod."
        )
    print(f"{OK} P:\\{modname} junction valid")
    return p_drive_link


def resolve_addon_builder() -> Path:
    tools_root = find_dayz_tools()
    if tools_root is None:
        sys.exit(
            f"{FAIL} DayZ Tools not found.\n"
            "       Set DAYZ_TOOLS_PATH or install via Steam (Tools section)."
        )
    addon_builder = tools_root / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
    if not addon_builder.exists():
        sys.exit(
            f"{FAIL} AddonBuilder.exe not under {tools_root}\\Bin\\AddonBuilder\\\n"
            "       DayZ Tools install may be incomplete."
        )
    print(f"{OK} AddonBuilder: {addon_builder}")
    return addon_builder


def run_addon_builder(
    addon_builder: Path,
    source: Path,
    target_dir: Path,
    modname: str,
    temp_dir: Path,
    clean: bool,
) -> int:
    cmd = [
        str(addon_builder),
        str(source),
        str(target_dir),
        f"-prefix={modname}",
        f"-temp={temp_dir}",
        f"-include={INCLUDE_LIST}",
    ]
    if clean:
        cmd.append("-clear")

    print()
    print(f"[AddonBuilder] {' '.join(cmd)}")
    print()
    sys.stdout.flush()  # ensure our prints land before AddonBuilder takes over stdout
    result = subprocess.run(cmd)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a DayZ mod into a .pbo via AddonBuilder.")
    parser.add_argument("modname", help="Mod name (must match workspace/<ModName>/).")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe P:\\Mods\\@<ModName>\\Addons\\ before building (-clear).",
    )
    args = parser.parse_args()

    gate_on_preflight()
    p_mods_err = validate_p_mods()
    if p_mods_err is not None:
        sys.exit(f"{FAIL} {p_mods_err}")
    print(f"{OK} P:\\Mods junction valid")
    workspace_target = verify_workspace(args.modname)
    verify_junction(args.modname, workspace_target)
    addon_builder = resolve_addon_builder()

    target_dir = MODS_ROOT / f"@{args.modname}" / "Addons"
    temp_dir = TEMP_ROOT / args.modname
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    pbo_path = target_dir / f"{args.modname}.pbo"
    build_started = time.time()

    rc = run_addon_builder(
        addon_builder,
        source=P_DRIVE / args.modname,
        target_dir=target_dir,
        modname=args.modname,
        temp_dir=temp_dir,
        clean=args.clean,
    )

    if rc != 0:
        print()
        print(f"{FAIL} AddonBuilder exited {rc}")
        print(f"       Temp dir kept for debugging: {temp_dir}")
        return rc

    if not pbo_path.exists():
        print()
        print(f"{FAIL} AddonBuilder reported success but {pbo_path} is missing.")
        print(f"       Temp dir kept for inspection: {temp_dir}")
        return 1

    if pbo_path.stat().st_mtime < build_started - 1:
        # PBO exists but wasn't refreshed by this build. AddonBuilder can exit 0
        # even when the sync step fails (no files matched, malformed include.lst,
        # etc.), leaving the prior build's PBO in place. Fail loudly.
        print()
        print(f"{FAIL} {pbo_path} was not updated by this build (stale PBO from a prior run).")
        print("       AddonBuilder reported success but produced no new PBO.")
        print("       Scroll up and look for [ERROR] lines in the AddonBuilder output.")
        return 1

    size = pbo_path.stat().st_size
    print()
    print(f"{OK} Built: {pbo_path} ({size:,} bytes)")

    try:
        shutil.rmtree(temp_dir)
        print(f"{OK} Cleaned temp dir")
    except OSError as e:
        print(f"{WARN} Could not remove {temp_dir}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
