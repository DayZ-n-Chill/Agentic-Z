"""dayz-build-pbo: Pack workspace/<ModName>/ into P:\\Mods\\@<ModName>\\Addons\\<ModName>.pbo.

Path discovery comes from dayz-preflight; the preflight gate, project cache and
ownership-marker rules come from .claude/skills/_shared/skill_helpers.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

lint = h.load_module("dayz_build_pbo_lint", Path(__file__).resolve().parents[1] / "dayz-lint" / "lint.py")
_nm = h.load_module("dayz_new_mod_module", h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py")

INCLUDE_LIST = Path(__file__).resolve().parent / "include.lst"
# Patterns left out of the PBO, including .gui-sources/ (imageset sprite sources).
# build.py applies them itself while staging the mod (see stage_source): AddonBuilder
# 1.0.240639 crashes on any -exclude= (ArgumentNullException in TextureHeaderBinazrizeTask,
# because BuilderConfiguration leaves ExcludeListFilename null when -exclude is given).
EXCLUDE_LIST = Path(__file__).resolve().parent / "exclude.lst"
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
    addons = target / "Addons"
    if not (target / "config.cpp").exists() and addons.is_dir() and any(addons.glob("*.pbo")):
        # A payload-only bundle (prebuilt Addons\*.pbo, no source) has nothing to build.
        sys.exit(
            f"{FAIL} {rel}\\ is a payload-only bundle (prebuilt Addons\\*.pbo, no config.cpp).\n"
            f"       There is nothing to build. Deploy it with /dayz-deploy-pbo {modname}."
        )
    for required in ("config.cpp", "$PBOPREFIX$"):
        if not (target / required).exists():
            sys.exit(
                f"{FAIL} {rel}\\{required} missing.\n"
                f"       Add it with /dayz-add-scaffold {modname}."
            )
    print(f"{OK} {rel}\\ found")
    gate_on_prefix(target / "$PBOPREFIX$", modname, rel)
    return target


def gate_on_prefix(prefix_file: Path, modname: str, rel: Path) -> None:
    """Exit unless $PBOPREFIX$ holds exactly <ModName>.

    The build passes -prefix=<ModName> and packs through the P:\\<ModName>\\
    junction, so the PBO's internal paths are <ModName>\\... A different
    $PBOPREFIX$ means the mod's own config paths expect another root; packing
    under <ModName> anyway would build a PBO whose paths do not resolve.
    """
    prefix = prefix_file.read_text(encoding="utf-8-sig").strip()
    if prefix != modname:
        sys.exit(
            f"{FAIL} {rel}\\$PBOPREFIX$ is {prefix!r}, expected {modname!r}.\n"
            "       This build packs the mod under the prefix <ModName> (the P:\\<ModName>\\ junction),\n"
            "       so the PBO prefix must match. Set the file's content to the single line\n"
            f"       {modname}, and check that config.cpp paths use {modname}\\ as their root."
        )
    print(f"{OK} $PBOPREFIX$ matches {modname}")


def verify_junction(modname: str, workspace_target: Path) -> Path:
    p_drive_link = P_DRIVE / modname
    if not os.path.lexists(p_drive_link):
        sys.exit(
            f"{FAIL} {p_drive_link} junction is missing.\n"
            f"       Create it with /dayz-add-scaffold {modname} --piece junction."
        )
    target = h.link_target(p_drive_link)
    if target is None:
        sys.exit(
            f"{FAIL} {p_drive_link} exists as a real folder, not a link.\n"
            "       Build expects a link to the workspace folder. Move the real folder aside,\n"
            f"       then run /dayz-add-scaffold {modname} --piece junction."
        )
    if not h.paths_equal(target, workspace_target):
        sys.exit(
            f"{FAIL} {p_drive_link} points at {target}, expected {workspace_target}\n"
            f"       Remove the wrong link (cmd /c rmdir \"{p_drive_link}\"), then run\n"
            f"       /dayz-add-scaffold {modname} --piece junction."
        )
    print(f"{OK} {p_drive_link} junction valid")
    return p_drive_link


def gate_on_lint(modname: str, project_dir: Path) -> None:
    """Exit unless /dayz-lint finds no errors: a mod that would not load is not packed.

    The P:\\<ModName>\\ link is left to verify_junction, which gives the repair hint.
    """
    target = project_dir / "workspace" / modname
    if not target.is_dir():
        return  # verify_workspace reports the missing folder
    report = lint.lint_mod(modname, target, project_dir, check_link=False, project_dir=project_dir)
    errors = []
    for f in report["findings"]:
        where = f"{f['file']}:{f['line']}" if f["line"] else f["file"]
        if f["severity"] == lint.ERROR:
            errors.append(f"       {where}: {f['message']}")
        else:
            print(f"{WARN} lint {where}: {f['message']}")
    if errors:
        sys.exit("\n".join([
            f"{FAIL} /dayz-lint found {len(errors)} error(s); the mod would not load, so it is not packed.",
            *errors,
            f"       Run /dayz-lint {modname} for the fix and owner of each one.",
        ]))
    print(f"{OK} /dayz-lint passed")


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


def exclude_patterns() -> list[str]:
    """The patterns in exclude.lst, without blank and ';' comment lines."""
    lines = EXCLUDE_LIST.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith(";")]


def is_excluded(rel_path: str, patterns: list[str]) -> bool:
    """True when a mod-relative path (backslash separators) matches an exclude pattern.

    The whole relative path is matched, case-insensitive, and '*' crosses folder
    separators, so "workbench\\*" drops every file in the root workbench folder
    (extensionless ones too) and
    "*.bak" drops .bak files at any depth.
    """
    rel = rel_path.lower()
    return any(fnmatch.fnmatchcase(rel, pat.lower()) for pat in patterns)


def remove_tree(folder: Path) -> None:
    """shutil.rmtree that also deletes read-only files.

    shutil.copy2 keeps a source file's read-only flag, so a stage built from a
    read-only file would otherwise make the next build's rmtree fail.
    """
    def _force(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    if sys.version_info >= (3, 12):
        shutil.rmtree(folder, onexc=_force)
    else:
        shutil.rmtree(folder, onerror=_force)


def stage_source(source: Path, stage: Path, patterns: list[str]) -> tuple[int, int]:
    """Copy source to a fresh stage folder, leaving out excluded files.

    Returns (files copied, files left out). AddonBuilder then packs the stage, so the
    exclude list holds without passing -exclude=. Exits with [FAIL] when a file in the
    old stage or the source cannot be removed or copied (usually a lock held by a
    crashed AddonBuilder or by Workbench).
    """
    copied = skipped = 0
    try:
        if stage.exists():
            remove_tree(stage)
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(source)).replace("/", "\\")
            if is_excluded(rel, patterns):
                skipped += 1
                continue
            dest = stage / path.relative_to(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            copied += 1
    except OSError as e:
        sys.exit(
            f"{FAIL} Could not stage the mod in {stage}: {e.filename or stage} is locked or unreadable"
            f" ({e.strerror or e}).\n"
            "       Close Workbench or any program that has the file open, or stop a stuck AddonBuilder\n"
            "       with: taskkill /im AddonBuilder.exe /f   Then build again."
        )
    return copied, skipped


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


def signatures(addons_dir: Path) -> list[str]:
    """Names of .bisign files in addons_dir (sorted).

    AddonBuilder never writes them: they are copied in by /dayz-deploy-pbo or
    made by hand with DSSignFile, so -clear would delete them for good.
    """
    if not addons_dir.is_dir():
        return []
    return sorted(f.name for f in addons_dir.iterdir() if f.is_file() and f.suffix.lower() == ".bisign")


def own_signatures(addons_dir: Path, modname: str) -> list[str]:
    """The <modname>.pbo.<key>.bisign names in addons_dir (case-insensitive)."""
    prefix = f"{modname}.pbo.".lower()
    return [name for name in signatures(addons_dir) if name.lower().startswith(prefix)]


def gate_clean(addons_dir: Path, modname: str) -> None:
    """Exit if --clean would wipe PBOs other than <modname>.pbo, or any .bisign."""
    others = other_pbos(addons_dir, modname)
    sigs = signatures(addons_dir)
    if others or sigs:
        sys.exit(
            f"{FAIL} --clean would wipe files in {addons_dir}\\ that AddonBuilder does not make: "
            f"{', '.join(others + sigs)}\n"
            "       Other PBOs and .bisign signatures are deployed payload (/dayz-deploy-pbo) or\n"
            "       hand-made signatures. Build without --clean, or move them aside first and\n"
            "       re-deploy or re-sign afterwards."
        )


def warn_stale_signatures(addons_dir: Path, modname: str) -> None:
    """Warn about <modname>.pbo.*.bisign files left from before this build.

    AddonBuilder does not sign, so any such signature was made for an earlier
    <modname>.pbo and does not cover the one just built.
    """
    for name in own_signatures(addons_dir, modname):
        print(
            f"{WARN} {addons_dir / name} was made for an earlier {modname}.pbo, not this build.\n"
            f"       Re-sign {modname}.pbo with DayZ Tools\\Bin\\DsUtils\\DSSignFile.exe, or delete the old signature."
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
        "Refused while Addons\\ holds PBOs other than <ModName>.pbo, or any .bisign.",
    )
    args = parser.parse_args()

    _nm.validate_name(args.modname)
    project_dir = h.resolve_project_dir()
    # Preflight first (L2 rule): a dismounted P:\ must be the first error shown.
    h.gate_on_preflight()
    # The workspace check runs before lint, so a missing file or a payload-only
    # bundle gets its own repair hint instead of a lint error.
    workspace_target = verify_workspace(args.modname, project_dir)
    gate_on_lint(args.modname, project_dir)
    p_mods_err = validate_p_mods()
    if p_mods_err is not None:
        sys.exit(f"{FAIL} {p_mods_err}")
    print(f"{OK} P:\\Mods junction valid")
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
    created_root = not deploy_root.exists()
    target_dir.mkdir(parents=True, exist_ok=True)
    # Mark a folder this run created before building, so a failed first build
    # does not leave an unmarked @<ModName> that gate_on_marker then refuses.
    if created_root and not h.write_marker(deploy_root, args.modname):
        return 1
    temp_dir.mkdir(parents=True, exist_ok=True)
    # The stage keeps the <ModName> folder name, which AddonBuilder uses for the PBO name.
    stage = TEMP_ROOT / "_stage" / args.modname
    copied, skipped = stage_source(workspace_target, stage, exclude_patterns())
    print(f"{OK} Staged {copied} files in {stage} ({skipped} left out by exclude.lst)")

    cmd = build_addon_builder_cmd(addon_builder, stage, target_dir, args.modname, temp_dir, args.clean)
    print()
    # list2cmdline quotes arguments with spaces (the default path holds "DayZ Tools"),
    # so the echoed line can be pasted into a terminal and run as is.
    print(f"[AddonBuilder] {subprocess.list2cmdline(cmd)}")
    print()
    sys.stdout.flush()  # our lines land before AddonBuilder takes over stdout
    build_started = time.time()
    rc = subprocess.run(cmd).returncode

    print()
    if rc != 0:
        print(f"{FAIL} AddonBuilder exited {rc}")
        print(f"       Kept for debugging: temp dir {temp_dir}, stage dir {stage}")
        return rc

    pbo_path = target_dir / f"{args.modname}.pbo"
    error = check_pbo_output(pbo_path, build_started)
    if error is not None:
        print(f"{FAIL} {error}")
        print(f"       Kept for inspection: temp dir {temp_dir}, stage dir {stage}")
        return 1

    print(f"{OK} Built: {pbo_path} ({pbo_path.stat().st_size:,} bytes)")
    warn_stale_signatures(target_dir, args.modname)

    cleaned = True
    for folder in (temp_dir, stage):
        try:
            remove_tree(folder)
        except OSError as e:
            cleaned = False
            print(f"{WARN} Could not remove {folder}: {e}")
    if cleaned:
        print(f"{OK} Cleaned temp and stage dirs")

    return 0


if __name__ == "__main__":
    sys.exit(main())
