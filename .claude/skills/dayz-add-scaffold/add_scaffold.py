"""dayz-add-scaffold: Fill missing scaffold pieces into existing workspace/<ModName>/.

Idempotent companion to dayz-new-mod. Where new-mod creates a fresh folder
from nothing, this skill writes missing pieces into a folder that already
exists, without overwriting anything present.

Imports templates and helpers from dayz-new-mod's new_mod.py so both skills
produce byte-identical output for the same inputs.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

NEW_MOD = h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py"
P_DRIVE = Path("P:\\")

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL
SKIP = "[SKIP] "

# Pieces written into the mod folder; `all` runs these in order. The P:\ link
# is not part of `all`: it changes P:\ itself, so it runs only when asked for.
PIECES = ("config", "prefix", "workbench", "readme", "skeleton")
JUNCTION = "junction"

# Pieces whose template needs the author handle, and the file each writes.
AUTHOR_PIECES = {"config": "config.cpp", "readme": "README.md"}

# What each piece function returns.
ADDED = "added"      # wrote at least one file or folder
PRESENT = "present"  # everything the piece covers already exists
SKIPPED = "skipped"  # missing, but could not be written (e.g. DayZ Tools not installed)
WRONG = "wrong"      # present, left unchanged, but holds content a later skill refuses

_nm = h.load_module("dayz_new_mod_module", NEW_MOD)


def add_config(target: Path, modname: str, get_author) -> str:
    f = target / "config.cpp"
    if f.exists():
        print(f"{SKIP} config.cpp present")
        return PRESENT
    author = get_author()
    f.write_text(
        _nm.CONFIG_CPP_TEMPLATE.substitute(modname=modname, author=author),
        encoding="utf-8",
    )
    print(f"{OK} config.cpp written (author: {author})")
    return ADDED


def add_prefix(target: Path, modname: str) -> str:
    f = target / "$PBOPREFIX$"
    if f.exists():
        # Read it the way /dayz-build-pbo's gate_on_prefix does (BOM and
        # surrounding whitespace ignored), so the warning matches its refusal.
        prefix = f.read_text(encoding="utf-8-sig").strip()
        if prefix != modname:
            print(f"{WARN} $PBOPREFIX$ present but holds {prefix!r}, not {modname!r} (left unchanged)")
            print("       /dayz-build-pbo will refuse to build until the file holds the single")
            print(f"       line {modname} and config.cpp paths use {modname}\\ as their root.")
            return WRONG
        print(f"{SKIP} $PBOPREFIX$ present")
        return PRESENT
    f.write_text(modname, encoding="utf-8")
    print(f"{OK} $PBOPREFIX$ written")
    return ADDED


def add_readme(target: Path, modname: str, get_author) -> str:
    f = target / "README.md"
    if f.exists():
        print(f"{SKIP} README.md present")
        return PRESENT
    author = get_author()
    f.write_text(
        _nm.README_TEMPLATE.substitute(modname=modname, author=author),
        encoding="utf-8",
    )
    print(f"{OK} README.md written")
    return ADDED


def add_skeleton(target: Path) -> str:
    folders = ("scripts/3_Game", "scripts/4_World", "scripts/5_Mission", "data", "gui")
    added = 0
    present = 0
    for sub in folders:
        folder = target / sub
        if folder.exists():
            present += 1
            continue
        folder.mkdir(parents=True)
        (folder / ".gitkeep").write_text("", encoding="utf-8")
        added += 1
    if added == 0:
        print(f"{SKIP} Skeleton folders all present")
        return PRESENT
    print(f"{OK} Skeleton folders created ({added} added, {present} already present)")
    return ADDED


def add_workbench(target: Path, modname: str) -> str:
    """Write workbench/dayz.gproj and DayZSetting.xml if missing.

    Uses the same vanilla-copy + injection logic as dayz-new-mod's
    scaffold_workbench(), but skips files already present instead of
    failing on a non-empty workbench/ folder. Creates workbench/ only when
    it has a file to write into it.
    """
    workbench_dir = target / "workbench"
    gproj = workbench_dir / "dayz.gproj"
    setting = workbench_dir / "DayZSetting.xml"

    if gproj.exists() and setting.exists():
        print(f"{SKIP} workbench/ present (dayz.gproj + DayZSetting.xml)")
        return PRESENT

    tools_root = _nm.find_dayz_tools()
    if tools_root is None:
        print(f"{WARN} workbench/ skipped - DayZ Tools not detected")
        print("       Re-run after installing DayZ Tools, or copy")
        print("       <DayZ Tools>\\Bin\\Workbench\\dayz.gproj manually.")
        return SKIPPED

    src_workbench = tools_root / "Bin" / "Workbench"
    src_gproj = src_workbench / "dayz.gproj"
    src_setting = src_workbench / "DayZSetting.xml"

    wrote_anything = False

    if gproj.exists():
        print(f"{SKIP} workbench/dayz.gproj present")
    elif not src_gproj.exists():
        print(f"{WARN} {src_gproj} missing - workbench/dayz.gproj not written")
    else:
        text = src_gproj.read_text(encoding="utf-8")
        text = _nm.inject_mod_paths_into_gproj(text, modname)
        text = _nm.rewrite_filesystem_block(text, modname)
        workbench_dir.mkdir(exist_ok=True)
        gproj.write_text(text, encoding="utf-8")
        print(f"{OK} workbench/dayz.gproj written (mod paths + filesystem mounts injected)")
        wrote_anything = True

    if setting.exists():
        print(f"{SKIP} workbench/DayZSetting.xml present")
    elif not src_setting.exists():
        print(f"{WARN} {src_setting} missing - DayZSetting.xml not copied")
    else:
        workbench_dir.mkdir(exist_ok=True)
        shutil.copyfile(src_setting, setting)
        print(f"{OK} workbench/DayZSetting.xml copied")
        wrote_anything = True

    # The gproj is the piece's purpose: copying only DayZSetting.xml (vanilla
    # dayz.gproj missing from DayZ Tools) still leaves Workbench unopenable,
    # so it counts as skipped and `--piece workbench` exits 1.
    return ADDED if wrote_anything and gproj.exists() else SKIPPED


def add_junction(target: Path, modname: str) -> str:
    """Create the P:\\<ModName>\\ link to workspace/<ModName>/, as /dayz-new-mod does.

    A link that already points at this workspace folder counts as present. A
    real folder, or a link pointing anywhere else, is refused: it may belong to
    another project, so the user removes it by hand.
    """
    p_link = P_DRIVE / modname
    shown = _display(target)
    if os.path.lexists(p_link):
        current = h.link_target(p_link)
        if current is None:
            sys.exit(
                f"{FAIL} {p_link} exists as a real folder, not a link.\n"
                "       Refusing to clobber. Move or remove it manually and re-run."
            )
        if not h.paths_equal(current, target):
            sys.exit(
                f"{FAIL} {p_link} is a link pointing at {current}\n"
                f"       Remove it (cmd /c rmdir \"{p_link}\") and re-run."
            )
        print(f"{SKIP} {p_link} present (links to {shown})")
        return PRESENT
    try:
        kind = _nm.make_dir_link(target, p_link)
    except (OSError, subprocess.CalledProcessError) as e:
        detail = (getattr(e, "stderr", "") or str(e)).strip()
        sys.exit(f"{FAIL} Could not create {p_link}: {detail}")
    print(f"{OK} {p_link} {kind} -> {shown}")
    return ADDED


def add_piece(piece: str, target: Path, modname: str, get_author) -> str:
    """Add one piece; returns ADDED, PRESENT, SKIPPED or WRONG. Used by /dayz-import-mod too."""
    if piece == "config":
        return add_config(target, modname, get_author)
    if piece == "prefix":
        return add_prefix(target, modname)
    if piece == "workbench":
        return add_workbench(target, modname)
    if piece == "readme":
        return add_readme(target, modname, get_author)
    if piece == "skeleton":
        return add_skeleton(target)
    if piece == JUNCTION:
        return add_junction(target, modname)
    raise ValueError(f"unknown scaffold piece: {piece}")


def lazy_author(cli_value: str | None):
    """Return a get_author() that resolves the handle on first call only.

    Avoids the author prompt when config.cpp / README.md already exist.
    """
    cache: list[str] = []

    def get_author() -> str:
        if not cache:
            cache.append(_nm.resolve_author(cli_value))
        return cache[0]

    return get_author


def _display(target: Path) -> Path:
    """workspace/<ModName> as printed in output (the mod folder relative to the project)."""
    return Path(target.parent.name) / target.name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add missing DayZ scaffold pieces into existing workspace/<ModName>/.",
    )
    parser.add_argument("modname", help="Mod name (folder under workspace/).")
    parser.add_argument(
        "--piece",
        choices=(*PIECES, JUNCTION, "all"),
        default="all",
        help="Which piece to add. Default 'all' adds every missing file piece; "
             "'junction' creates the P:\\<ModName> link (never part of 'all').",
    )
    parser.add_argument("--author", help="Author handle (cached for future runs).")
    args = parser.parse_args()

    h.gate_on_preflight()
    _nm.validate_name(args.modname)

    target = h.resolve_project_dir() / "workspace" / args.modname
    rel = _display(target)
    if not target.exists():
        sys.exit(
            f"{FAIL} {rel} does not exist.\n"
            "       Use /dayz-new-mod to scaffold a fresh mod, or /dayz-import-mod\n"
            "       to import an existing folder."
        )
    if not target.is_dir():
        sys.exit(f"{FAIL} {rel} is not a directory.")

    get_author = lazy_author(args.author)
    pieces = PIECES if args.piece == "all" else (args.piece,)
    # Resolve the author before writing anything, so a missing handle (no
    # flag, no cache, no TTY) exits with the folder untouched rather than
    # after some pieces were already written.
    if any(p in AUTHOR_PIECES and not (target / AUTHOR_PIECES[p]).exists() for p in pieces):
        get_author()

    print()
    print(f"Scaffolding {rel}{os.sep}")
    print()

    results = [add_piece(piece, target, args.modname, get_author) for piece in pieces]
    added, present, skipped, wrong = (results.count(s) for s in (ADDED, PRESENT, SKIPPED, WRONG))

    print()
    if args.piece == JUNCTION:
        # Only the link was checked, so say nothing about the other pieces.
        link = P_DRIVE / args.modname
        print(f"{OK} {link} link {'created' if added else 'already in place'}.")
    elif added == 0 and skipped == 0 and wrong == 0:
        print(f"{OK} Nothing to add - {rel} is already fully scaffolded.")
    else:
        # [OK] only when every piece is now in place; a skipped or wrong piece is a warning.
        tag = WARN if skipped or wrong else OK
        line = f"{tag} {added} piece(s) added, {present} already present, {skipped} skipped"
        print(f"{line}, {wrong} need fixing by hand." if wrong else f"{line}.")
    if args.piece != "all" and skipped:
        # The one piece asked for was not written; callers need a failing exit.
        print(f"{FAIL} {args.piece} was not written - see the warning above.")
        return 1
    if args.piece != "all" and wrong:
        # The one piece asked for is present but will be refused downstream.
        print(f"{FAIL} {args.piece} is present but wrong - see the warning above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
