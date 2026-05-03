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
import importlib.util
import shutil
import sys
from pathlib import Path

# .../.claude/skills/dayz-add-scaffold/add_scaffold.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace"
NEW_MOD = REPO_ROOT / ".claude" / "skills" / "dayz-new-mod" / "new_mod.py"

OK = "[OK]   "
SKIP = "[SKIP] "
WARN = "[WARN] "
FAIL = "[FAIL] "

PIECES = ("config", "prefix", "workbench", "readme", "skeleton")


def _load_new_mod_module():
    spec = importlib.util.spec_from_file_location("dayz_new_mod_module", NEW_MOD)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load dayz-new-mod module at {NEW_MOD}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_nm = _load_new_mod_module()


def add_config(target: Path, modname: str, get_author) -> bool:
    f = target / "config.cpp"
    if f.exists():
        print(f"{SKIP} config.cpp present")
        return False
    author = get_author()
    f.write_text(
        _nm.CONFIG_CPP_TEMPLATE.substitute(modname=modname, author=author),
        encoding="utf-8",
    )
    print(f"{OK} config.cpp written (author: {author})")
    return True


def add_prefix(target: Path, modname: str) -> bool:
    f = target / "$PBOPREFIX$"
    if f.exists():
        print(f"{SKIP} $PBOPREFIX$ present")
        return False
    f.write_text(modname, encoding="utf-8")
    print(f"{OK} $PBOPREFIX$ written")
    return True


def add_readme(target: Path, modname: str, get_author) -> bool:
    f = target / "README.md"
    if f.exists():
        print(f"{SKIP} README.md present")
        return False
    author = get_author()
    f.write_text(
        _nm.README_TEMPLATE.substitute(modname=modname, author=author),
        encoding="utf-8",
    )
    print(f"{OK} README.md written")
    return True


def add_skeleton(target: Path) -> bool:
    folders = ("scripts/3_Game", "scripts/4_World", "scripts/5_Mission", "data", "gui")
    added = 0
    present = 0
    for sub in folders:
        folder = target / sub
        if folder.exists():
            present += 1
            continue
        folder.mkdir(parents=True)
        gitkeep = folder / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")
        added += 1
    if added == 0:
        print(f"{SKIP} Skeleton folders all present")
        return False
    print(f"{OK} Skeleton folders created ({added} added, {present} already present)")
    return True


def add_workbench(target: Path, modname: str) -> bool:
    """Write workbench/dayz.gproj and DayZSetting.xml if missing.

    Uses the same vanilla-copy + injection logic as dayz-new-mod's
    scaffold_workbench(), but skips files already present instead of
    failing on a non-empty workbench/ folder.
    """
    workbench_dir = target / "workbench"
    workbench_dir.mkdir(exist_ok=True)

    gproj = workbench_dir / "dayz.gproj"
    setting = workbench_dir / "DayZSetting.xml"

    if gproj.exists() and setting.exists():
        print(f"{SKIP} workbench/ present (dayz.gproj + DayZSetting.xml)")
        return False

    tools_root = _nm.find_dayz_tools()
    if tools_root is None:
        print(f"{WARN} workbench/ skipped - DayZ Tools not detected")
        print("       Re-run after installing DayZ Tools, or copy")
        print("       <DayZ Tools>\\Bin\\Workbench\\dayz.gproj manually.")
        return False

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
        gproj.write_text(text, encoding="utf-8")
        print(f"{OK} workbench/dayz.gproj written (mod paths + filesystem mounts injected)")
        wrote_anything = True

    if setting.exists():
        print(f"{SKIP} workbench/DayZSetting.xml present")
    elif not src_setting.exists():
        print(f"{WARN} {src_setting} missing - DayZSetting.xml not copied")
    else:
        shutil.copyfile(src_setting, setting)
        print(f"{OK} workbench/DayZSetting.xml copied")
        wrote_anything = True

    return wrote_anything


PIECE_FUNCS = {
    "config": lambda target, modname, get_author: add_config(target, modname, get_author),
    "prefix": lambda target, modname, get_author: add_prefix(target, modname),
    "readme": lambda target, modname, get_author: add_readme(target, modname, get_author),
    "skeleton": lambda target, modname, get_author: add_skeleton(target),
    "workbench": lambda target, modname, get_author: add_workbench(target, modname),
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add missing DayZ scaffold pieces into existing workspace/<ModName>/.",
    )
    parser.add_argument("modname", help="Mod name (folder under workspace/).")
    parser.add_argument(
        "--piece",
        choices=("config", "prefix", "workbench", "readme", "skeleton", "all"),
        default="all",
        help="Which piece to add. Default 'all' adds every missing piece.",
    )
    parser.add_argument("--author", help="Author handle (cached for future runs).")
    args = parser.parse_args()

    _nm.gate_on_preflight()
    _nm.validate_name(args.modname)

    target = WORKSPACE / args.modname
    if not target.exists():
        try:
            rel = target.relative_to(REPO_ROOT)
        except ValueError:
            rel = target
        sys.exit(
            f"{FAIL} {rel} does not exist.\n"
            "       Use /dayz-new-mod to scaffold a fresh mod, or /dayz-import-mod\n"
            "       to import an existing folder."
        )
    if not target.is_dir():
        sys.exit(f"{FAIL} {target.relative_to(REPO_ROOT)} is not a directory.")

    print()
    try:
        rel = target.relative_to(REPO_ROOT)
    except ValueError:
        rel = target
    print(f"Scaffolding {rel}/\n")

    # Lazy author resolution: only prompt if a piece needing author actually has to write.
    # Avoids the prompt when config.cpp / README.md already exist.
    _cache: list[str] = []

    def get_author() -> str:
        if _cache:
            return _cache[0]
        author = _nm.resolve_author(args.author)
        _cache.append(author)
        return author

    pieces = PIECES if args.piece == "all" else (args.piece,)
    added = 0
    skipped = 0
    for piece in pieces:
        wrote = PIECE_FUNCS[piece](target, args.modname, get_author)
        if wrote:
            added += 1
        else:
            skipped += 1

    print()
    if added == 0:
        print(f"{OK} Nothing to add - {rel} is already fully scaffolded.")
    else:
        print(f"{OK} {added} piece(s) added, {skipped} piece(s) already present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
