"""dayz-deploy-pbo: Mirror pre-compiled PBOs from workspace/<ModName>/ to P:\\Mods\\@<ModName>\\.

Pure copy of Addons/*.pbo (+ *.bisign), Keys/*.bikey, and optional meta.cpp/mod.cpp.
No AddonBuilder, no source required, never deletes anything in the deploy dir.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

# REPO_ROOT = where this skill ships from (plugin or template clone).
# Project dir (where workspace/ lives) is resolved at runtime from the
# /dayz-init project cache; see resolve_project_dir().
REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-preflight"
PREFLIGHT = PREFLIGHT_DIR / "preflight.py"
DAYZ_INIT_DIR = REPO_ROOT / ".claude" / "skills" / "dayz-init"
P_DRIVE = Path("P:\\")
MODS_ROOT = P_DRIVE / "Mods"

# Ownership marker at P:\Mods\@<ModName>\<MARKER> — same file, same content
# convention as dayz-build-pbo (single line: the modname). dayz-clean-workspace
# gates deployed-dir removal on it. Deploy additionally gates on it *before*
# writing: an existing @<ModName> without the marker could be a subscribed mod
# or hand-placed folder and is never touched.
SCAFFOLD_MARKER = ".agentic-z-scaffold"

# Idempotency tolerance for mtime comparison (copy2 preserves mtime; some
# filesystems store it at 2-second granularity).
MTIME_TOLERANCE_SEC = 2

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "


def _load_module_from_path(name: str, path: Path):
    """Load a sibling-skill .py as a module by file path so static analyzers don't
    choke on a sys.path-based sibling import."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Reuse path validation from preflight per L2 conventions (single source of truth).
_preflight = _load_module_from_path("dayz_preflight_module", PREFLIGHT)
validate_p_mods = _preflight.validate_p_mods

# Reuse the project-root cache reader from /dayz-init so deploy follows the same source of truth.
_dayz_init_state = _load_module_from_path("dayz_init_state_module", DAYZ_INIT_DIR / "state.py")
cached_project_root = _dayz_init_state.cached_project_root


def resolve_project_dir() -> Path:
    """Return the cached project root, or bail out pointing the user at /dayz-init."""
    project = cached_project_root()
    if project is None:
        print("error: no project cached.", file=sys.stderr)
        print("  Run /dayz-init to set up your DayZ environment and project.", file=sys.stderr)
        sys.exit(2)
    return project.resolve()


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(
            f"{FAIL} dayz-preflight skill not found at "
            f"{PREFLIGHT.relative_to(REPO_ROOT)}"
        )
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def verify_bundle(modname: str, project_dir: Path) -> Path:
    """A bundle only needs Addons/ with at least one .pbo. No config.cpp,
    no $PBOPREFIX$, no P:\\<ModName> junction — those belong to the build path."""
    target = project_dir / "workspace" / modname
    if not target.exists():
        sys.exit(
            f"{FAIL} {target.relative_to(project_dir)} not found.\n"
            f"       Expected a bundle folder at workspace\\{modname}\\ with Addons\\*.pbo inside."
        )
    addons = target / "Addons"
    if not addons.is_dir():
        sys.exit(
            f"{FAIL} {target.relative_to(project_dir)}\\Addons\\ missing.\n"
            "       Pre-compiled payload PBOs go in workspace\\"
            f"{modname}\\Addons\\*.pbo."
        )
    if not any(addons.glob("*.pbo")):
        sys.exit(
            f"{FAIL} No .pbo files in {target.relative_to(project_dir)}\\Addons\\.\n"
            "       Nothing to deploy."
        )
    print(f"{OK} workspace\\{modname}\\Addons\\ found (with .pbo payload)")
    return target


def gate_on_marker(modname: str, deploy_root: Path) -> None:
    """Refuse to touch an existing @<ModName> that we don't own. Same ownership
    rule as dayz-clean-workspace's deployed_owned_by_us(): marker file present
    with content == modname."""
    if not deploy_root.exists():
        return
    marker = deploy_root / SCAFFOLD_MARKER
    owned = False
    if marker.is_file():
        try:
            owned = marker.read_text(encoding="utf-8").strip() == modname
        except OSError:
            owned = False
    if not owned:
        sys.exit(
            f"{FAIL} P:\\Mods\\@{modname}\\ exists but has no Agentic-Z ownership marker\n"
            f"       ({SCAFFOLD_MARKER} missing or content mismatch).\n"
            "       Refusing to deploy into it - could be a subscribed mod or hand-placed folder.\n"
            f"       If it's actually yours, remove it manually first: cmd /c rmdir /s /q P:\\Mods\\@{modname}"
        )
    print(f"{OK} P:\\Mods\\@{modname}\\ ownership marker valid")


def copy_if_changed(src: Path, dst_dir: Path) -> bool:
    """Copy src into dst_dir unless an identical file (size + mtime) is already
    there. Returns True if copied, False if skipped. copy2 preserves mtime so
    the check holds across runs."""
    dst = dst_dir / src.name
    if dst.exists():
        s, d = src.stat(), dst.stat()
        if s.st_size == d.st_size and abs(s.st_mtime - d.st_mtime) <= MTIME_TOLERANCE_SEC:
            return False
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy pre-compiled PBOs from a workspace bundle to P:\\Mods\\@<ModName>\\."
    )
    parser.add_argument("modname", help="Mod name (must match workspace/<ModName>/ with Addons/*.pbo inside).")
    args = parser.parse_args()

    project_dir = resolve_project_dir()
    gate_on_preflight()
    p_mods_err = validate_p_mods()
    if p_mods_err is not None:
        sys.exit(f"{FAIL} {p_mods_err}")
    print(f"{OK} P:\\Mods junction valid")
    bundle = verify_bundle(args.modname, project_dir)

    deploy_root = MODS_ROOT / f"@{args.modname}"
    gate_on_marker(args.modname, deploy_root)

    copied = 0
    skipped = 0

    # Addons: *.pbo + *.bisign. Purely additive — never deletes, so a linker
    # PBO built by /dayz-build-pbo into the same Addons\ stays untouched.
    addons_src = bundle / "Addons"
    pbos = sorted(addons_src.glob("*.pbo"))
    bisigns = sorted(addons_src.glob("*.bisign"))
    for f in pbos + bisigns:
        if copy_if_changed(f, deploy_root / "Addons"):
            copied += 1
        else:
            skipped += 1

    # Keys: *.bikey (optional).
    keys_src = bundle / "Keys"
    bikeys = sorted(keys_src.glob("*.bikey")) if keys_src.is_dir() else []
    for f in bikeys:
        if copy_if_changed(f, deploy_root / "Keys"):
            copied += 1
        else:
            skipped += 1

    # Optional mod metadata at bundle root.
    metas = [bundle / n for n in ("meta.cpp", "mod.cpp") if (bundle / n).is_file()]
    for f in metas:
        if copy_if_changed(f, deploy_root):
            copied += 1
        else:
            skipped += 1

    # Verify signatures: each payload .pbo should have a <name>.pbo.<key>.bisign.
    unsigned = [p for p in pbos if not any(s.name.startswith(p.name + ".") for s in bisigns)]
    for p in unsigned:
        print(f"{WARN} {p.name} has no matching .bisign - clients with signature "
              "verification enabled will reject it.")

    print()
    print(f"{OK} Deployed to P:\\Mods\\@{args.modname}\\ - "
          f"{copied} copied, {skipped} unchanged "
          f"({len(pbos)} .pbo, {len(bisigns)} .bisign, {len(bikeys)} .bikey"
          f"{', ' + str(len(metas)) + ' meta' if metas else ''})")

    marker_path = deploy_root / SCAFFOLD_MARKER
    try:
        marker_path.write_text(args.modname + "\n", encoding="utf-8")
    except OSError as e:
        print(f"{WARN} Could not write ownership marker {marker_path}: {e}")
        print("       dayz-clean-workspace will refuse to remove this deployed dir.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
