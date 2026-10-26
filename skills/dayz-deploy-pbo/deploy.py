"""dayz-deploy-pbo: Mirror pre-compiled PBOs from workspace/<ModName>/ to P:\\Mods\\@<ModName>\\.

Pure copy of Addons/*.pbo (+ *.bisign), Keys/*.bikey, and optional meta.cpp/mod.cpp.
No AddonBuilder, no source required, never deletes anything in the deploy dir.
Refuses to overwrite a deployed file that is newer than the bundle copy unless
--force is passed. --dry-run prints the copy plan and warnings without writing
anything. The preflight gate, project cache and ownership-marker rules come from
skills/_shared/skill_helpers.py.

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

# Same mod-name rule as /dayz-new-mod and /dayz-import-mod. The name becomes
# workspace/<ModName> and P:\Mods\@<ModName>, so it must not carry a path.
_nm = h.load_module("dayz_new_mod_module", h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py")


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


def needs_copy(src: Path, dst_dir: Path) -> bool:
    """False when dst_dir already holds a file with src's name, size and mtime."""
    dst = dst_dir / src.name
    if dst.exists():
        s, d = src.stat(), dst.stat()
        if s.st_size == d.st_size and abs(s.st_mtime - d.st_mtime) <= MTIME_TOLERANCE_SEC:
            return False
    return True


def deployed_is_newer(src: Path, dst_dir: Path) -> bool:
    """True when dst_dir holds a file with src's name whose mtime is later than
    src's (beyond the copy2 tolerance): copying would replace a newer deployed
    build with an older bundle copy."""
    dst = dst_dir / src.name
    return dst.exists() and dst.stat().st_mtime - src.stat().st_mtime > MTIME_TOLERANCE_SEC


def copy_if_changed(src: Path, dst_dir: Path) -> bool:
    """Copy src into dst_dir unless a file with the same size and mtime is
    already there. Returns True if copied, False if skipped."""
    if not needs_copy(src, dst_dir):
        return False
    dst = dst_dir / src.name
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def unsigned_pbos(pbos: list[Path], bisigns: list[Path]) -> list[Path]:
    """PBOs with no <name>.pbo.<key>.bisign next to them. Case-insensitive,
    like Windows file names and stale_files()."""
    signed = [s.name.lower() for s in bisigns]
    return [p for p in pbos if not any(n.startswith(p.name.lower() + ".") for n in signed)]


def linker_collision(modname: str, bundle: Path, pbos: list[Path],
                     bisigns: list[Path]) -> Path | None:
    """The bundle's Addons/<ModName>.pbo or Addons/<ModName>.pbo.<key>.bisign
    (any case) when the bundle also carries a linker config.cpp.
    /dayz-build-pbo writes the linker and its signature to those same deploy
    paths, so copying the payload file would silently replace them."""
    if not (bundle / "config.cpp").is_file():
        return None
    own = f"{modname}.pbo".lower()
    return next(
        (f for f in pbos + bisigns if f.name.lower() == own or f.name.lower().startswith(own + ".")),
        None,
    )


STALE_REASON = {
    ".pbo": "it still loads in game.",
    ".bisign": "a leftover signature for a PBO the bundle no longer ships signed this way.",
    ".bikey": "servers that take keys from this mod keep trusting it.",
}


def stale_files(modname: str, bundle: Path, pbos: list[Path], bisigns: list[Path],
                bikeys: list[Path], deploy_root: Path) -> list[Path]:
    """Deployed Addons\\*.pbo, Addons\\*.bisign and Keys\\*.bikey files the bundle
    no longer ships (dropped or renamed). The built linker <ModName>.pbo and
    any <ModName>.pbo.*.bisign are excluded when the bundle has a linker
    config.cpp, since /dayz-build-pbo owns them. Deploy never deletes, so
    these stay in the deploy dir until removed by hand."""
    linker = f"{modname}.pbo".lower() if (bundle / "config.cpp").is_file() else None
    checks = [
        (deploy_root / "Addons", (".pbo", ".bisign"), pbos + bisigns),
        (deploy_root / "Keys", (".bikey",), bikeys),
    ]
    stale = []
    for folder, suffixes, shipped in checks:
        if not folder.is_dir():
            continue
        keep = {p.name.lower() for p in shipped}
        for f in folder.iterdir():
            n = f.name.lower()
            if not f.is_file() or f.suffix.lower() not in suffixes or n in keep:
                continue
            if linker and (n == linker or n.startswith(linker + ".")):
                continue
            stale.append(f)
    return sorted(stale)


def report_warnings(modname: str, bundle: Path, pbos: list[Path], bisigns: list[Path],
                    bikeys: list[Path], deploy_root: Path) -> None:
    for p in unsigned_pbos(pbos, bisigns):
        print(f"{WARN} {p.name} has no matching .bisign - clients with signature "
              "verification enabled will reject it.")

    for p in stale_files(modname, bundle, pbos, bisigns, bikeys, deploy_root):
        print(f"{WARN} {p.name} is deployed but not in the bundle - {STALE_REASON[p.suffix.lower()]}")
        print("       Deploy never deletes. If the bundle dropped or renamed it, remove it by hand:")
        print(f'       del "{p}"')


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy pre-compiled PBOs from a workspace bundle to P:\\Mods\\@<ModName>\\."
    )
    parser.add_argument("modname", help="Mod name (must match workspace/<ModName>/ with Addons/*.pbo inside).")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the copy plan and warnings without copying anything or writing the marker.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite deployed files even when they are newer than the bundle copy.",
    )
    args = parser.parse_args()

    _nm.validate_name(args.modname)
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

    clash = linker_collision(args.modname, bundle, pbos, bisigns)
    if clash is not None:
        rel = bundle.relative_to(project_dir)
        what = "linker PBO" if clash.suffix.lower() == ".pbo" else "linker PBO's signature"
        sys.exit(
            f"{FAIL} {rel}\\Addons\\{clash.name} has the same name as the {what} that\n"
            f"       /dayz-build-pbo builds from {rel}\\config.cpp, so deploying it would overwrite\n"
            f"       the linker in {deploy_root}\\Addons\\. Rename the payload file, or remove\n"
            "       the linker config.cpp + $PBOPREFIX$ if the bundle has no linker."
        )

    plan = (
        [(f, deploy_root / "Addons") for f in pbos + bisigns]
        + [(f, deploy_root / "Keys") for f in bikeys]
        + [(f, deploy_root) for f in metas]
    )
    # Deployed files newer than the bundle copy: overwriting them would roll a
    # newer build back with no backup, so a real run refuses unless --force.
    newer = set() if args.force else {
        dst_dir / src.name for src, dst_dir in plan
        if needs_copy(src, dst_dir) and deployed_is_newer(src, dst_dir)
    }

    if args.dry_run:
        print()
        print(f"Dry run - nothing will be written to {deploy_root}\\")
        copied = 0
        for src, dst_dir in plan:
            dst = dst_dir / src.name
            if not needs_copy(src, dst_dir):
                action = "unchanged"
            elif dst in newer:
                action = "newer"
            else:
                copied += 1
                action = "overwrite" if dst.exists() else "copy"
            print(f"  {action:<9}  {dst}")
        report_warnings(args.modname, bundle, pbos, bisigns, bikeys, deploy_root)
        print()
        if newer:
            print(f"{WARN} {len(newer)} deployed file(s) marked 'newer' are newer than the bundle "
                  "copy. A real run refuses unless --force is passed.")
        print(f"{OK} Dry run: {copied} would be copied, {len(plan) - copied - len(newer)} unchanged. "
              "Rerun without --dry-run to deploy.")
        return 0

    if newer:
        listing = "\n".join(f"         {p}" for p in sorted(newer))
        sys.exit(
            f"{FAIL} Deployed file(s) are newer than the bundle copy, so deploying would replace a\n"
            f"       newer build with an older one. Nothing was copied:\n{listing}\n"
            "       Update the bundle, or rerun with --force to overwrite them anyway."
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

    report_warnings(args.modname, bundle, pbos, bisigns, bikeys, deploy_root)

    print()
    print(f"{OK} Deployed to {deploy_root}\\ - "
          f"{copied} copied, {skipped} unchanged "
          f"({len(pbos)} .pbo, {len(bisigns)} .bisign, {len(bikeys)} .bikey"
          f"{', ' + str(len(metas)) + ' meta' if metas else ''})")

    return 0 if h.write_marker(deploy_root, args.modname) else 1


if __name__ == "__main__":
    sys.exit(main())
