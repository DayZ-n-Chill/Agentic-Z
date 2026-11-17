"""dayz-build-pbo: Pack workspace/<ModName>/ into P:\\Mods\\@<ModName>\\Addons\\<ModName>.pbo.

Path discovery comes from dayz-preflight; the preflight gate, project cache and
ownership-marker rules come from skills/_shared/skill_helpers.py.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
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
pbo_entries = h.load_module("dayz_build_pbo_entries", Path(__file__).resolve().parent / "pbo_entries.py")

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


def clear_stale_temp(temp_dir: Path) -> None:
    """Remove a temp dir left by an earlier build, and exit unless it is gone.

    AddonBuilder syncs the source into its temp dir incrementally, so files left there
    (a failed build keeps the folder for debugging) can be packed in place of the
    current source while the build still reports success. The build therefore starts
    from an empty temp dir, and stops rather than build on one it could not empty.
    """
    if not temp_dir.exists():
        return
    try:
        remove_tree(temp_dir)
    except OSError as e:
        sys.exit(
            f"{FAIL} Could not empty the temp dir of an earlier build: {e.filename or temp_dir} is locked"
            f" ({e.strerror or e}).\n"
            "       Building on it could pack old files in place of the current source. Close the program\n"
            "       that holds it (Explorer, an editor, a stuck AddonBuilder: taskkill /im AddonBuilder.exe /f),\n"
            "       then build again."
        )
    if temp_dir.exists():
        # Windows can report a delete as done while an open handle keeps the folder alive.
        sys.exit(
            f"{FAIL} The temp dir of an earlier build is still there after removing it: {temp_dir}\n"
            "       Close the program that holds it open, then build again."
        )
    print(f"{OK} Removed the temp dir left by an earlier build: {temp_dir}")


# The line AddonBuilder 1.0.240639 writes last for each run in <DayZ Tools>\Bin\Logs\AddonBuilder.rpt:
# 2026-11-17 11:01:33,968 [DEBUG] 1: AddonBuilder.Program.RunComandLineApp - Build finished. [ResultCode]=1
_RESULT_CODE_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ .*Build finished\. \[ResultCode\]=(-?\d+)")


def addon_builder_log(addon_builder: Path) -> Path:
    """<DayZ Tools>\\Bin\\Logs\\AddonBuilder.rpt for <DayZ Tools>\\Bin\\AddonBuilder\\AddonBuilder.exe."""
    return addon_builder.parent.parent / "Logs" / "AddonBuilder.rpt"


def logged_result_code(log: Path, build_started: float) -> Optional[int]:
    """The [ResultCode] AddonBuilder logged for the run that ended after build_started.

    AddonBuilder.exe exits 0 when CfgConvert or binarize fails; only its log says
    [ResultCode]=1. Returns None when the log is missing or its last result is older
    than this build, so the caller falls back to the PBO checks. The log's times are
    local and cut to the second, hence the 1 s slack.
    """
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        m = _RESULT_CODE_RE.match(line)
        if m:
            logged = time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
            return int(m.group(2)) if logged >= build_started - 1 else None
    return None


_LOG_STDERR_RE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ .*?process_ErrorDataReceived - (.*\S.*)$")


def logged_tool_errors(log: Path, build_started: float, limit: int = 10) -> list[str]:
    """What CfgConvert and binarize wrote to stderr during this build, from AddonBuilder's log.

    binarize runs silent, so a failed build names its cause only here, for example
    "File ...\\config.cpp, line 17: /CfgVehicles/MyItem.scope: Member already defined."
    The cache-size banner binarize prints on every run is left out.
    """
    try:
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    found = []
    for line in lines:
        m = _LOG_STDERR_RE.match(line)
        if not m or m.group(2).startswith("FileServer MaxCacheSize"):
            continue
        if time.mktime(time.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")) >= build_started - 1:
            found.append(m.group(2).strip())
    return found[-limit:]


# Staged file types whose absence from the PBO breaks the mod with no error in the log:
# a script that never compiles, a model that is not there.
MUST_SHIP_SUFFIXES = {".c", ".p3d"}
# Entries AddonBuilder adds that have no source file.
GENERATED_ENTRIES = {"texheaders.bin", "$pboprefix$.txt", "$pboprefix$", "$prefix$"}
# FileBank packs with DayZ Tools' own Bin\PboUtils\exclude.lst, whose *\Source\*, *\Temp\* and
# *\Doc\* patterns drop these folders at any depth, even though the sync copied them.
FILEBANK_DROPPED_FOLDERS = {"source", "temp", "doc"}


def include_patterns() -> list[str]:
    """The wildcard patterns in include.lst, lower case."""
    return [p.strip().lower() for p in INCLUDE_LIST.read_text(encoding="utf-8").split(";") if p.strip()]


def check_pbo_contents(pbo_path: Path, stage: Path, modname: str) -> tuple[list[str], list[str], Optional[str]]:
    """Compare the built PBO's entry table with the staged source.

    Returns (errors, warnings, summary). The expected entries are derived from the
    stage, never from a hand-kept list: every staged file that include.lst lets
    through should be an entry. An error is a missing script or model, a missing
    config, or a wrong prefix: each loads as a mod that silently does nothing.
    Everything else is a warning. summary is None when the PBO could not be read.
    """
    try:
        pbo = pbo_entries.read_pbo(pbo_path)
    except (pbo_entries.PboError, OSError) as e:
        return [], [f"Could not read the entry table of {pbo_path} ({e}); its contents were not checked."], None

    errors: list[str] = []
    warnings: list[str] = []
    if pbo.trailer_ok is False:
        warnings.append(
            f"{pbo_path.name} does not end in the checksum AddonBuilder writes (a zero byte and the SHA-1 of the\n"
            "       file before it). The file may be cut short; build again before testing with it."
        )
    if pbo.prefix.lower() != modname.lower():
        errors.append(
            f"{pbo_path.name} has the header prefix {pbo.prefix!r}, expected {modname!r}.\n"
            "       Script and asset paths resolve against the prefix, so nothing in this PBO would be found."
        )

    patterns = include_patterns()
    staged = sorted(
        str(p.relative_to(stage)).replace("/", "\\") for p in stage.rglob("*") if p.is_file()
    ) if stage.is_dir() else []
    packable, unlisted = [], []
    for rel in staged:
        name = rel.rsplit("\\", 1)[-1].lower()
        if any(fnmatch.fnmatchcase(name, pat) for pat in patterns):
            packable.append(rel)
        elif rel != "$PBOPREFIX$":
            unlisted.append(rel)
    names = pbo.names()

    missing = [rel for rel in packable if rel.lower() not in names]
    must = [rel for rel in missing if Path(rel).suffix.lower() in MUST_SHIP_SUFFIXES]
    other = [rel for rel in missing if Path(rel).suffix.lower() not in MUST_SHIP_SUFFIXES]
    if "config.cpp" in (rel.lower() for rel in staged) and not names & {"config.bin", "config.cpp"}:
        errors.append(f"{pbo_path.name} holds neither config.bin nor config.cpp, so the game cannot load it as a mod.")
        other = [rel for rel in other if rel.lower() != "config.cpp"]

    def folder_hint(rels: list[str]) -> str:
        if not any(FILEBANK_DROPPED_FOLDERS & set(rel.lower().split("\\")[:-1]) for rel in rels):
            return ""
        return (
            "\n       The packer leaves out every folder named Source, Temp or Doc, at any depth."
            " Rename the folder."
        )

    if must:
        errors.append(
            f"{len(must)} staged script or model file(s) are not in {pbo_path.name}: "
            + ", ".join(must[:10]) + (" ..." if len(must) > 10 else "")
            + "\n       The mod would load with those scripts never compiled or those models missing."
            + folder_hint(must)
        )
    if other:
        warnings.append(
            f"{len(other)} staged file(s) that include.lst lets through are not in {pbo_path.name}: "
            + ", ".join(other[:10]) + (" ..." if len(other) > 10 else "") + folder_hint(other)
        )

    expected = {rel.lower() for rel in staged} | GENERATED_ENTRIES
    # AddonBuilder packs a config.bin beside config.cpp (measured at the mod root; a nested
    # config.cpp is given the same allowance).
    expected |= {
        rel.lower()[: -len("cpp")] + "bin" for rel in staged if rel.lower().rsplit("\\", 1)[-1] == "config.cpp"
    }
    extras = sorted(e.name for e in pbo.entries if e.key not in expected)
    if extras:
        warnings.append(
            f"{len(extras)} entr{'y' if len(extras) == 1 else 'ies'} in {pbo_path.name} did not come from the staged"
            " source: " + ", ".join(extras[:10]) + (" ..." if len(extras) > 10 else "")
        )

    summary = f"{pbo_path.name} holds {len(pbo.entries)} entries; all {len(packable)} packable staged files are in it"
    if missing:
        summary = f"{pbo_path.name} holds {len(pbo.entries)} entries; {len(packable) - len(missing)} of {len(packable)} packable staged files are in it"
    if unlisted:
        by_suffix: dict[str, int] = {}
        for rel in unlisted:
            suffix = Path(rel).suffix.lower() or "(no extension)"
            by_suffix[suffix] = by_suffix.get(suffix, 0) + 1
        summary += (
            f" ({len(unlisted)} staged file(s) match no include.lst pattern and stay out: "
            + ", ".join(f"{suffix} {count}" for suffix, count in sorted(by_suffix.items())) + ")"
        )
    return errors, warnings, summary


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
    # A temp dir kept by a failed build must never feed this one.
    clear_stale_temp(temp_dir)
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

    # AddonBuilder exits 0 when CfgConvert or binarize fails; its log holds the real result.
    log = addon_builder_log(addon_builder)
    result_code = logged_result_code(log, build_started)
    if result_code not in (None, 0):
        print(f"{FAIL} AddonBuilder exited 0, but its log says the build failed ([ResultCode]={result_code}).")
        for message in logged_tool_errors(log, build_started):
            print(f"       {message}")
        print(f"       Look for [ERROR] lines above, or in {log}")
        print(f"       Kept for debugging: temp dir {temp_dir}, stage dir {stage}")
        return 1

    pbo_path = target_dir / f"{args.modname}.pbo"
    error = check_pbo_output(pbo_path, build_started)
    if error is not None:
        print(f"{FAIL} {error}")
        print(f"       Kept for inspection: temp dir {temp_dir}, stage dir {stage}")
        return 1

    errors, warnings, summary = check_pbo_contents(pbo_path, stage, args.modname)
    for warning in warnings:
        print(f"{WARN} {warning}")
    if errors:
        for error in errors:
            print(f"{FAIL} {error}")
        print(f"       {pbo_path} was written but is not a working build; do not test with it.")
        print(f"       Kept for inspection: temp dir {temp_dir}, stage dir {stage}")
        return 1

    print(f"{OK} Built: {pbo_path} ({pbo_path.stat().st_size:,} bytes)")
    if summary:
        print(f"{OK} {summary}")
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
