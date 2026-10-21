"""dayz-deploy-pbo: Mirror pre-compiled PBOs from workspace/<ModName>/ to P:\\Mods\\@<ModName>\\.

Pure copy of Addons/*.pbo (+ *.bisign), Keys/*.bikey, and optional meta.cpp/mod.cpp.
No AddonBuilder, no source required, never deletes anything in the deploy dir.
The preflight gate, project cache and ownership-marker rules come from
.claude/skills/_shared/skill_helpers.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"

# copy2 preserves mtime; some filesystems store it at 2-second granularity.
MTIME_TOLERANCE_SEC = 2

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL

validate_p_mods = h.preflight.validate_p_mods


def verify_bundle(modname: str, project_dir: Path) -> Path:
    """A bundle only needs Addons/ with at least one .pbo. No config.cpp,
    no $PBOPREFIX$, no P:\\<ModName> junction: those belong to the build path."""
    target = project_dir / "workspace" / modname
    rel = target.relative_to(project_dir)
    if not target.exists():
        sys.exit(
            f"{FAIL} {rel} not found.\n"
            f"       Expected a bundle folder at {rel}\\ with Addons\\*.pbo inside."
        )
    addons = target / "Addons"
    if not addons.is_dir():
        sys.exit(
            f"{FAIL} {rel}\\Addons\\ missing.\n"
            f"       Pre-compiled payload PBOs go in {rel}\\Addons\\*.pbo."
        )
    if not any(addons.glob("*.pbo")):
        sys.exit(f"{FAIL} No .pbo files in {rel}\\Addons\\. Nothing to deploy.")
    print(f"{OK} {rel}\\Addons\\ found (with .pbo payload)")
    return target


def copy_if_changed(src: Path, dst_dir: Path) -> bool:
    """Copy src into dst_dir unless a file with the same size and mtime is
    already there. Returns True if copied, False if skipped."""
    dst = dst_dir / src.name
    if dst.exists():
        s, d = src.stat(), dst.stat()
        if s.st_size == d.st_size and abs(s.st_mtime - d.st_mtime) <= MTIME_TOLERANCE_SEC:
            return False
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def unsigned_pbos(pbos: list[Path], bisigns: list[Path]) -> list[Path]:
    """PBOs with no <name>.pbo.<key>.bisign next to them."""
    return [p for p in pbos if not any(s.name.startswith(p.name + ".") for s in bisigns)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy pre-compiled PBOs from a workspace bundle to P:\\Mods\\@<ModName>\\."
    )
    parser.add_argument("modname", help="Mod name (must match workspace/<ModName>/ with Addons/*.pbo inside).")
    args = parser.parse_args()

    project_dir = h.resolve_project_dir()
    h.gate_on_preflight()
    p_mods_err = validate_p_mods()
    if p_mods_err is not None:
        sys.exit(f"{FAIL} {p_mods_err}")
    print(f"{OK} P:\\Mods junction valid")
    bundle = verify_bundle(args.modname, project_dir)

    deploy_root = MODS_ROOT / f"@{args.modname}"
    h.gate_on_marker(args.modname, deploy_root)

    # Purely additive: nothing is deleted, so a linker PBO built by
    # /dayz-build-pbo into the same Addons\ stays untouched.
    addons_src = bundle / "Addons"
    pbos = sorted(addons_src.glob("*.pbo"))
    bisigns = sorted(addons_src.glob("*.bisign"))
    keys_src = bundle / "Keys"
    bikeys = sorted(keys_src.glob("*.bikey")) if keys_src.is_dir() else []
    metas = [bundle / n for n in ("meta.cpp", "mod.cpp") if (bundle / n).is_file()]

    plan = (
        [(f, deploy_root / "Addons") for f in pbos + bisigns]
        + [(f, deploy_root / "Keys") for f in bikeys]
        + [(f, deploy_root) for f in metas]
    )
    copied = 0
    for src, dst_dir in plan:
        try:
            copied += copy_if_changed(src, dst_dir)
        except OSError as e:
            # Typically a PBO held open by a running DayZ client or server.
            print(f"{FAIL} could not copy {src.name}: {e}")
            print("       Close DayZ or run /dayz-stop-test, then rerun /dayz-deploy-pbo.")
            # The gate above passed, so this dir is ours (or new): mark it so
            # the rerun is not refused as an unowned folder.
            if deploy_root.exists():
                h.write_marker(deploy_root, args.modname)
            return 1
    skipped = len(plan) - copied

    for p in unsigned_pbos(pbos, bisigns):
        print(f"{WARN} {p.name} has no matching .bisign - clients with signature "
              "verification enabled will reject it.")

    print()
    print(f"{OK} Deployed to {deploy_root}\\ - "
          f"{copied} copied, {skipped} unchanged "
          f"({len(pbos)} .pbo, {len(bisigns)} .bisign, {len(bikeys)} .bikey"
          f"{', ' + str(len(metas)) + ' meta' if metas else ''})")

    return 0 if h.write_marker(deploy_root, args.modname) else 1


if __name__ == "__main__":
    sys.exit(main())
