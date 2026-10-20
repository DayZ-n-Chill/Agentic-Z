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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

# PROJECT_DIR = user's project (where workspace/ lives).
PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
WORKSPACE = PROJECT_DIR / "workspace"
NEW_MOD = h.SKILLS_DIR / "dayz-new-mod" / "new_mod.py"

OK, WARN, FAIL = h.OK, h.WARN, h.FAIL
SKIP = "[SKIP] "

PIECES = ("config", "prefix", "workbench", "readme", "skeleton")

# What each piece function returns.
ADDED = "added"      # wrote at least one file or folder
PRESENT = "present"  # everything the piece covers already exists
SKIPPED = "skipped"  # missing, but could not be written (e.g. DayZ Tools not installed)

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

    return ADDED if wrote_anything else SKIPPED


def add_piece(piece: str, target: Path, modname: str, get_author) -> str:
    """Add one piece; returns ADDED, PRESENT or SKIPPED. Used by /dayz-import-mod too."""
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add missing DayZ scaffold pieces into existing workspace/<ModName>/.",
    )
    parser.add_argument("modname", help="Mod name (folder under workspace/).")
    parser.add_argument(
        "--piece",
        choices=(*PIECES, "all"),
        default="all",
        help="Which piece to add. Default 'all' adds every missing piece.",
    )
    parser.add_argument("--author", help="Author handle (cached for future runs).")
    args = parser.parse_args()

    h.gate_on_preflight()
    _nm.validate_name(args.modname)

    target = WORKSPACE / args.modname
    try:
        rel = target.relative_to(PROJECT_DIR)
    except ValueError:
        rel = target
    if not target.exists():
        sys.exit(
            f"{FAIL} {rel} does not exist.\n"
            "       Use /dayz-new-mod to scaffold a fresh mod, or /dayz-import-mod\n"
            "       to import an existing folder."
        )
    if not target.is_dir():
        sys.exit(f"{FAIL} {rel} is not a directory.")

    print()
    print(f"Scaffolding {rel}/\n")

    get_author = lazy_author(args.author)
    pieces = PIECES if args.piece == "all" else (args.piece,)
    results = [add_piece(piece, target, args.modname, get_author) for piece in pieces]
    added, present, skipped = (results.count(s) for s in (ADDED, PRESENT, SKIPPED))

    print()
    if added == 0 and skipped == 0:
        print(f"{OK} Nothing to add - {rel} is already fully scaffolded.")
    else:
        print(f"{OK} {added} piece(s) added, {present} already present, {skipped} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
