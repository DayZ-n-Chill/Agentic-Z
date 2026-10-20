"""dayz-build-pbo: Pack workspace/<ModName>/ into P:\\Mods\\@<ModName>\\Addons\\<ModName>.pbo.

Path discovery comes from dayz-preflight; the preflight gate, project cache and
ownership-marker rules come from .claude/skills/_shared/skill_helpers.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

INCLUDE_LIST = Path(__file__).resolve().parent / "include.lst"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"
TEMP_ROOT = P_DRIVE / "temp"

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL

find_dayz_tools = h.preflight.find_dayz_tools
validate_p_mods = h.preflight.validate_p_mods


def verify_workspace(modname: str, project_dir: Path) -> Path:
    target = project_dir / "workspace" / modname
    rel = target.relative_to(project_dir)
    if not target.exists():
        sys.exit(
            f"{FAIL} {rel} not found.\n"
            f"       Run /dayz-new-mod {modname} (or /dayz-import-mod) first."
        )
    for required in ("config.cpp", "$PBOPREFIX$"):
        if not (target / required).exists():
            sys.exit(
                f"{FAIL} {rel}\\{required} missing.\n"
                f"       Add it with /dayz-add-scaffold {modname}."
            )
    print(f"{OK} {rel}\\ found")
    return target


def verify_junction(modname: str, workspace_target: Path) -> Path:
    p_drive_link = P_DRIVE / modname
    if not os.path.lexists(p_drive_link):
        sys.exit(
            f"{FAIL} {p_drive_link} junction is missing.\n"
            f"       Run /dayz-new-mod {modname} (or /dayz-import-mod) to create it."
        )
    target = h.link_target(p_drive_link)
    if target is None:
        sys.exit(
            f"{FAIL} {p_drive_link} exists as a real folder, not a link.\n"
            "       Build expects the /dayz-new-mod junction. Move the folder aside and re-scaffold."
        )
    if not h.paths_equal(target, workspace_target):
        sys.exit(
            f"{FAIL} {p_drive_link} points at {target}, expected {workspace_target}\n"
            "       Remove the wrong link and re-run /dayz-new-mod."
        )
    print(f"{OK} {p_drive_link} junction valid")
    return p_drive_link


def resolve_addon_builder() -> Path:
    # find_dayz_tools only returns a root that contains Bin\AddonBuilder\AddonBuilder.exe.
    tools_root = find_dayz_tools()
    if tools_root is None:
        sys.exit(
            f"{FAIL} DayZ Tools not found.\n"
            "       Set DAYZ_TOOLS_PATH or install DayZ Tools via Steam."
        )
    addon_builder = tools_root / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
    print(f"{OK} AddonBuilder: {addon_builder}")
    return addon_builder


def build_addon_builder_cmd(
    addon_builder: Path, source: Path, target_dir: Path, modname: str, temp_dir: Path, clean: bool
) -> list[str]:
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
    return cmd


def other_pbos(addons_dir: Path, modname: str) -> list[str]:
    """Names of .pbo files in addons_dir other than <modname>.pbo (sorted).

    These are the payload PBOs /dayz-deploy-pbo copies in. AddonBuilder -clear
    would wipe them, so --clean refuses while any exist.
    """
    if not addons_dir.is_dir():
        return []
    own = f"{modname}.pbo".lower()
    return sorted(
        f.name for f in addons_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".pbo" and f.name.lower() != own
    )


def gate_clean(addons_dir: Path, modname: str) -> None:
    """Exit if --clean would wipe PBOs other than <modname>.pbo."""
    others = other_pbos(addons_dir, modname)
    if others:
        sys.exit(
            f"{FAIL} --clean would wipe other PBOs in {addons_dir}\\: {', '.join(others)}\n"
            "       They are deployed payload (/dayz-deploy-pbo). Build without --clean,\n"
            "       or remove them yourself first and re-deploy afterwards."
        )


def check_pbo_output(pbo_path: Path, build_started: float) -> Optional[str]:
    """Return a failure message if the build did not produce a fresh PBO, else None.

    AddonBuilder can exit 0 when its sync step fails (no files matched,
    malformed include.lst), leaving the previous build's PBO in place. A PBO
    older than the build start is that stale file. The 1 s slack covers
    filesystems that round mtimes.
    """
    if not pbo_path.exists():
        return f"AddonBuilder reported success but {pbo_path} is missing."
    if pbo_path.stat().st_mtime < build_started - 1:
        return (
            f"{pbo_path} was not updated by this build (stale PBO from a prior run).\n"
            "       Scroll up and look for [ERROR] lines in the AddonBuilder output."
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a DayZ mod into a .pbo via AddonBuilder.")
    parser.add_argument("modname", help="Mod name (must match workspace/<ModName>/).")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe P:\\Mods\\@<ModName>\\Addons\\ before building (AddonBuilder -clear). "
        "Refused while Addons\\ holds PBOs other than <ModName>.pbo.",
    )
    args = parser.parse_args()

    project_dir = h.resolve_project_dir()
    h.gate_on_preflight()
    p_mods_err = validate_p_mods()
    if p_mods_err is not None:
        sys.exit(f"{FAIL} {p_mods_err}")
    print(f"{OK} P:\\Mods junction valid")
    workspace_target = verify_workspace(args.modname, project_dir)
    verify_junction(args.modname, workspace_target)
    addon_builder = resolve_addon_builder()

    deploy_root = MODS_ROOT / f"@{args.modname}"
    # Same rule as /dayz-deploy-pbo: never build into (or -clear) an @<ModName>
    # that we did not create.
    h.gate_on_marker(args.modname, deploy_root)

    target_dir = deploy_root / "Addons"
    if args.clean:
        gate_clean(target_dir, args.modname)
    temp_dir = TEMP_ROOT / args.modname
    target_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_addon_builder_cmd(
        addon_builder, P_DRIVE / args.modname, target_dir, args.modname, temp_dir, args.clean
    )
    print()
    print(f"[AddonBuilder] {' '.join(cmd)}")
    print()
    sys.stdout.flush()  # our lines land before AddonBuilder takes over stdout
    build_started = time.time()
    rc = subprocess.run(cmd).returncode

    print()
    if rc != 0:
        print(f"{FAIL} AddonBuilder exited {rc}")
        print(f"       Temp dir kept for debugging: {temp_dir}")
        return rc

    pbo_path = target_dir / f"{args.modname}.pbo"
    error = check_pbo_output(pbo_path, build_started)
    if error is not None:
        print(f"{FAIL} {error}")
        print(f"       Temp dir kept for inspection: {temp_dir}")
        return 1

    print(f"{OK} Built: {pbo_path} ({pbo_path.stat().st_size:,} bytes)")
    h.write_marker(deploy_root, args.modname)

    try:
        shutil.rmtree(temp_dir)
        print(f"{OK} Cleaned temp dir")
    except OSError as e:
        print(f"{WARN} Could not remove {temp_dir}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
