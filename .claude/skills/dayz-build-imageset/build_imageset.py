"""dayz-build-imageset: Pack PNG sprites into a DayZ .imageset + .paa atlas.

Reads `<mod>/.gui-sources/<setname>/*.png`, shelf-packs into the smallest
power-of-two atlas (rectangular allowed) with a 10px gutter, splitting across
several atlases (next-fit) when one 4096x4096 atlas is not enough, converts to
.paa via ImageToPAA.exe, and writes a matching .imageset definition file under
`<mod>/gui/imagesets/`. Every part is converted into a staging folder first and
only moved over the real outputs once all parts of the set converted, so a
failed run leaves the previous outputs untouched. Outputs left over from a
previous run with a different split count are removed. Generated outputs whose
.gui-sources/<set>/ folder no longer exists are reported, and deleted with
--prune. --dry-run prints the plan without writing or deleting anything.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:  # reported with an install hint in main(); packing logic doesn't need it
    Image = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

OK = h.OK
WARN = h.WARN
FAIL = h.FAIL
INFO = "[INFO] "

GAP = 10
POT_DIMS = [256, 512, 1024, 2048, 4096]
ATLAS_SIZES = sorted(
    {(w, h) for w in POT_DIMS for h in POT_DIMS},
    key=lambda s: (s[0] * s[1], abs(s[0] - s[1])),
)


REQUIREMENTS = Path(__file__).resolve().parent / "requirements.txt"

# A sprite's file stem becomes its ImageSetDefClass name, an unquoted
# identifier in the .imageset file, so it must be a plain identifier.
# A set folder's name becomes the imageset Name, which .layout files reference
# as one space-separated token ("set:dayz_gui image:Close" at
# P:\gui\layouts\day_z_book.layout:141), so it is held to the same rule.
SPRITE_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
OUTPUT_SUFFIXES = (".paa", ".imageset")
# <set>_N, the stem of one part of a split set.
PART_STEM_RE = re.compile(r"(.+)_\d+")


def bad_sprite_names(pngs) -> list[str]:
    """File names whose stem cannot be an ImageSetDefClass name."""
    return [p.name for p in pngs if not SPRITE_NAME_RE.fullmatch(p.stem)]


def is_valid_set_name(name: str) -> bool:
    """True when a .gui-sources/ subfolder name can be an imageset Name."""
    return SPRITE_NAME_RE.fullmatch(name) is not None


def colliding_part_stems(set_name: str, part_count: int, other_sets) -> list[str]:
    """Split stems <set>_N that are also another source set's name.

    Compared case-insensitively because Windows file names are, so icons_1.paa
    from a split of "icons" and from a set named "Icons_1" are the same file.
    """
    if part_count < 2:
        return []
    others = {o.casefold() for o in other_sets}
    return [f"{set_name}_{i}" for i in range(1, part_count + 1)
            if f"{set_name}_{i}".casefold() in others]


def resolve_image_to_paa() -> Path:
    tools_root = h.preflight.find_dayz_tools()
    if tools_root is None:
        sys.exit(
            f"{FAIL} DayZ Tools not found.\n"
            "       Set DAYZ_TOOLS_PATH or install DayZ Tools via Steam."
        )
    exe = tools_root / "Bin" / "ImageToPAA" / "ImageToPAA.exe"
    if not exe.exists():
        sys.exit(f"{FAIL} ImageToPAA.exe not at {exe}\n       DayZ Tools install may be incomplete.")
    return exe


def shelf_pack(metas, gap=GAP):
    """Shelf-pack sprites with `gap` px on all sides.

    metas: list of (path, w, h)
    Returns ((atlas_w, atlas_h), [(path, w, h, x, y), ...]) or (None, None) if nothing fits.
    Tries POT widths/heights ordered by area (favoring square), picks first fit.
    """
    sorted_metas = sorted(metas, key=lambda m: (-m[2], -m[1]))
    for atlas_w, atlas_h in ATLAS_SIZES:
        if any(w + 2 * gap > atlas_w or h + 2 * gap > atlas_h for _, w, h in sorted_metas):
            continue
        cursor_x = gap
        cursor_y = gap
        shelf_h = 0
        placed = []
        ok = True
        for path, w, h in sorted_metas:
            if cursor_x + w + gap > atlas_w:
                cursor_x = gap
                cursor_y += shelf_h + gap
                shelf_h = 0
            if cursor_y + h + gap > atlas_h:
                ok = False
                break
            placed.append((path, w, h, cursor_x, cursor_y))
            cursor_x += w + gap
            if h > shelf_h:
                shelf_h = h
        if ok:
            return (atlas_w, atlas_h), placed
    return None, None


def pack_split(metas, gap=GAP):
    """Pack sprites across one or more atlases when a single atlas can't hold them all.

    Greedy next-fit-decreasing: sort sprites by height desc, then for each sprite
    try to add it to the current atlas; if it overflows, close that atlas and
    start a new one (earlier atlases are never revisited).
    Returns list of (dims, placed) tuples, or None if a single sprite is too big
    for the largest allowed atlas.
    """
    max_dim = POT_DIMS[-1]
    if any(w + 2 * gap > max_dim or h + 2 * gap > max_dim for _, w, h in metas):
        return None  # a sprite doesn't fit even in the largest atlas
    sorted_metas = sorted(metas, key=lambda m: (-m[2], -m[1]))
    atlases = []
    current: list = []
    for sprite in sorted_metas:
        trial = current + [sprite]
        dims, placed = shelf_pack(trial, gap)
        if dims is not None:
            current = trial
            continue
        dims_final, placed_final = shelf_pack(current, gap)
        atlases.append((dims_final, placed_final))
        current = [sprite]
    if current:
        dims_final, placed_final = shelf_pack(current, gap)
        atlases.append((dims_final, placed_final))
    return atlases


def write_imageset_file(path: Path, set_name: str, atlas_w: int, atlas_h: int,
                       paa_path_in_mod: str, placed) -> None:
    lines = [
        "ImageSetClass {",
        f' Name "{set_name}"',
        f" RefSize {atlas_w} {atlas_h}",
        " Textures {",
        "  ImageSetTextureClass {",
        "   mpix 0",
        f'   path "{paa_path_in_mod}"',
        "  }",
        " }",
        " Images {",
    ]
    for sprite_path, w, h, x, y in placed:
        name = sprite_path.stem
        lines.extend([
            f"  ImageSetDefClass {name} {{",
            f'   Name "{name}"',
            f"   Pos {x} {y}",
            f"   Size {w} {h}",
            "   Flags 0",
            "  }",
        ])
    lines.extend([
        " }",
        " Groups {",
        " }",
        "}",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_one_atlas(stem: str, atlas_w: int, atlas_h: int, placed,
                    mod_name: str, stage_dir: Path, image_to_paa: Path) -> bool:
    """Compose and convert one atlas, writing <stem>.paa and <stem>.imageset into `stage_dir`.

    `stage_dir` is a fresh staging folder, never the real output folder, so a
    conversion that fails partway (or truncates its output) cannot damage the
    outputs of an earlier run. build_one() moves the staged files into place.
    """
    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    for sprite_path, _, _, x, y in placed:
        with Image.open(sprite_path) as sprite:
            atlas.paste(sprite.convert("RGBA"), (x, y))

    paa_path = stage_dir / f"{stem}.paa"
    temp_png = stage_dir / f"{stem}.png"
    atlas.save(temp_png, "PNG")
    result = subprocess.run([str(image_to_paa), str(temp_png), str(paa_path)])
    temp_png.unlink()
    if result.returncode != 0:
        print(f"{FAIL} ImageToPAA exited {result.returncode} on {stem}", file=sys.stderr)
        return False
    if not paa_path.is_file():
        print(f"{FAIL} ImageToPAA reported success but wrote no {stem}.paa", file=sys.stderr)
        return False
    print(f"{OK} Converted {stem}.paa ({paa_path.stat().st_size:,} bytes)")

    paa_path_in_mod = f"{mod_name}\\gui\\imagesets\\{stem}.paa"
    write_imageset_file(stage_dir / f"{stem}.imageset", stem, atlas_w, atlas_h,
                        paa_path_in_mod, placed)
    return True


def promote_staged(stage_dir: Path, out_dir: Path) -> None:
    """Move every staged .paa / .imageset over its final file in `out_dir`."""
    for f in sorted(stage_dir.iterdir()):
        if f.suffix.lower() in OUTPUT_SUFFIXES:
            os.replace(f, out_dir / f.name)
            print(f"{OK} Wrote {f.name}")


def remove_stale_outputs(out_dir: Path, set_name: str, part_count: int,
                         other_sets: frozenset = frozenset(), dry_run: bool = False) -> list:
    """Delete <set>.{paa,imageset} / <set>_N.{paa,imageset} this run won't rewrite.

    part_count == 1 keeps <set>.*; part_count > 1 keeps <set>_1 .. <set>_<part_count>;
    part_count == 0 (the set's folder is empty) keeps nothing.
    Stems that are the name of another source set are never touched.
    With dry_run, only reports what it would delete.
    Returns the removed (or, with dry_run, the would-be removed) paths.
    """
    if not out_dir.is_dir():
        return []
    if part_count == 1:
        keep = {set_name}
    else:
        keep = {f"{set_name}_{i}" for i in range(1, part_count + 1)}
    # Compared ignoring case, like colliding_part_stems(), because Windows file
    # names are: after renaming the folder Icons to icons, Icons_2.paa is stale.
    spared = {s.casefold() for s in keep} | {o.casefold() for o in other_sets}
    part_re = re.compile(re.escape(set_name) + r"_\d+", re.IGNORECASE)
    removed = []
    for f in sorted(out_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() not in OUTPUT_SUFFIXES:
            continue
        stem = f.stem
        if stem.casefold() in spared:
            continue
        if stem.casefold() == set_name.casefold() or part_re.fullmatch(stem):
            if dry_run:
                print(f"{INFO} Would remove stale {f.name}")
            else:
                f.unlink()
                print(f"{INFO} Removed stale {f.name}")
            removed.append(f)
    return removed


def looks_generated(imageset: Path) -> bool:
    """True when an .imageset file has the shape write_imageset_file() writes.

    It must start with "ImageSetClass {", name itself after its own stem and
    point at <something>\\gui\\imagesets\\<stem>.paa. Hand-made or vanilla-style
    imagesets (P:\\gui\\imagesets\\playstation_buttons2.imageset:7 uses
    "Gui/imagesets/....edds") do not match.
    """
    try:
        text = imageset.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    stem = re.escape(imageset.stem)
    return (
        text.startswith("ImageSetClass {")
        and re.search(rf'^ Name "{stem}"$', text, re.MULTILINE) is not None
        and re.search(rf'^   path "[^"\n]*\\gui\\imagesets\\{stem}\.paa"$', text,
                      re.MULTILINE | re.IGNORECASE) is not None
    )


def find_orphan_outputs(out_dir: Path, set_names) -> list:
    """Generated outputs in `out_dir` whose .gui-sources/<set>/ folder is gone.

    A stem belongs to a current set when it is the set name or <set>_N
    (ignoring case, as Windows file names do). For every other stem whose
    .imageset looks generated, that .imageset and its <stem>.paa are returned.
    Files this skill did not write are never returned.
    """
    if not out_dir.is_dir():
        return []
    current = {s.casefold() for s in set_names}
    orphans = []
    for f in sorted(out_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".imageset":
            continue
        stem = f.stem
        part = PART_STEM_RE.fullmatch(stem)
        if stem.casefold() in current or (part and part.group(1).casefold() in current):
            continue
        if not looks_generated(f):
            continue
        orphans.append(f)
        paa = out_dir / f"{stem}.paa"
        if paa.is_file():
            orphans.append(paa)
    return sorted(orphans)


def handle_orphans(out_dir: Path, set_names, prune: bool, dry_run: bool) -> list:
    """Report orphan outputs, or delete them when `prune` is set (dry run: report only).

    Returns the orphan paths found.
    """
    orphans = find_orphan_outputs(out_dir, set_names)
    if not orphans:
        return orphans
    print()
    print("[Orphans]")
    for f in orphans:
        if prune and dry_run:
            print(f"{INFO} Would remove orphan {f.name}")
        elif prune:
            f.unlink()
            print(f"{INFO} Removed orphan {f.name}")
        else:
            print(f"{WARN} orphan {f.name}: no .gui-sources/ folder matches it, "
                  "so /dayz-build-pbo still packs it")
    if not prune:
        print(f"{WARN} Re-run with --prune to delete them (add --dry-run to preview).")
    return orphans


def build_one(set_dir: Path, mod_name: str, out_dir: Path, image_to_paa: Path,
              other_sets: frozenset = frozenset(), dry_run: bool = False) -> bool:
    set_name = set_dir.name

    print()
    print(f"[Pack] {set_name}")

    if not is_valid_set_name(set_name):
        print(
            f"{FAIL} {set_name!r}: set folder names must be identifiers (letters, digits,\n"
            "       underscores; not starting with a digit), because the folder name becomes\n"
            "       the imageset Name that .layout files reference as set:<name>.\n"
            f"       Rename the folder {set_dir}",
            file=sys.stderr,
        )
        return False

    pngs = sorted(p for p in set_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png")

    if not pngs:
        print(f"{WARN} {set_name}: no .png files in {set_dir}, skipping")
        # Outputs from when the folder still had sprites would otherwise ship
        # sprites the user has deleted.
        remove_stale_outputs(out_dir, set_name, 0, other_sets, dry_run)
        return True

    bad = bad_sprite_names(pngs)
    if bad:
        print(
            f"{FAIL} {set_name}: sprite file names must be identifiers (letters, digits,\n"
            "       underscores; not starting with a digit), because each name becomes an\n"
            f"       ImageSetDefClass name. Rename: {', '.join(bad)}",
            file=sys.stderr,
        )
        return False

    # A corrupt, truncated or 0-byte .png fails this set only, so the other
    # sets still build. Pillow's UnidentifiedImageError is an OSError; load()
    # catches files whose header reads but whose pixel data is cut short.
    metas = []
    unreadable = []
    for p in pngs:
        try:
            with Image.open(p) as im:
                im.load()
                metas.append((p, im.width, im.height))
        except OSError as e:
            unreadable.append(f"{p.name} ({e})")
    if unreadable:
        print(
            f"{FAIL} {set_name}: cannot read as PNG images. Re-export or remove:\n"
            + "\n".join(f"       {u}" for u in unreadable),
            file=sys.stderr,
        )
        return False

    atlases = pack_split(metas)
    if atlases is None:
        max_dim = POT_DIMS[-1]
        print(
            f"{FAIL} {set_name}: at least one sprite is larger than {max_dim}x{max_dim} "
            f"(minus gutter). Shrink it or use a different delivery format.",
            file=sys.stderr,
        )
        return False

    clashes = colliding_part_stems(set_name, len(atlases), other_sets)
    if clashes:
        print(
            f"{FAIL} {set_name}: splits into {len(atlases)} atlases, but {', '.join(clashes)} "
            "is also a source set name,\n"
            "       so the two would overwrite each other's .paa and .imageset. "
            "Rename one of the set folders.",
            file=sys.stderr,
        )
        return False

    if len(atlases) == 1:
        stems = [set_name]
        (atlas_w, atlas_h), _ = atlases[0]
        print(f"{INFO} {len(pngs)} sprite(s) -> {atlas_w}x{atlas_h} atlas")
    else:
        stems = [f"{set_name}_{i}" for i in range(1, len(atlases) + 1)]
        print(
            f"{INFO} {len(pngs)} sprite(s) won't fit in one atlas, splitting into "
            f"{len(atlases)} parts: {stems[0]} ... {stems[-1]}"
        )
        for stem, ((atlas_w, atlas_h), placed) in zip(stems, atlases):
            print(f"{INFO}   {stem}: {len(placed)} sprite(s) -> {atlas_w}x{atlas_h} atlas")

    if dry_run:
        planned = ", ".join(f"{stem}.paa + {stem}.imageset" for stem in stems)
        print(f"{INFO} Dry run: would write {planned}")
        remove_stale_outputs(out_dir, set_name, len(atlases), other_sets, dry_run=True)
        return True

    out_dir.mkdir(parents=True, exist_ok=True)
    # Stage inside out_dir so os.replace() is a same-volume rename; the folder
    # is removed on exit whether or not the set converted.
    with tempfile.TemporaryDirectory(dir=out_dir, prefix=".staging-") as td:
        stage_dir = Path(td)
        all_ok = True
        for stem, ((atlas_w, atlas_h), placed) in zip(stems, atlases):
            if not write_one_atlas(stem, atlas_w, atlas_h, placed, mod_name, stage_dir, image_to_paa):
                all_ok = False
        if not all_ok:
            print(f"{FAIL} {set_name}: not every atlas converted; previous outputs left unchanged",
                  file=sys.stderr)
            return False
        promote_staged(stage_dir, out_dir)

    # Only after every atlas converted and moved into place.
    remove_stale_outputs(out_dir, set_name, len(atlases), other_sets)
    return True


def is_path_form(arg: str) -> bool:
    """True when the argument is a path to a mod root rather than a <ModName>."""
    return arg in (".", "..") or any(c in arg for c in "/\\:")


def resolve_mod_root(arg: str) -> Path:
    """The mod root for a <ModName> or a path argument.

    A <ModName> resolves to workspace/<ModName>/ under the project cached by
    /dayz-init, like the sibling /dayz-* skills, so the skill works from the
    repo root. A path (the older form) is used as given.
    """
    if is_path_form(arg):
        mod_root = Path(arg).resolve()
        if not mod_root.is_dir():
            sys.exit(f"{FAIL} mod root not a directory: {mod_root}")
        return mod_root
    project_dir = h.resolve_project_dir()
    mod_root = project_dir / "workspace" / arg
    if not mod_root.is_dir():
        sys.exit(
            f"{FAIL} workspace\\{arg} not found under {project_dir}.\n"
            f"       Run /dayz-new-mod {arg} (or /dayz-import-mod) first, or pass a path to the mod root."
        )
    return mod_root


def default_mod_name(mod_root: Path) -> str:
    """The root for the .imageset path field: the mod's $PBOPREFIX$.

    In-PBO paths are rooted at the PBO prefix, not the folder name: vanilla
    P:\\DZ\\gui.txt:1 has prefix=gui\\ and P:\\gui\\imagesets\\playstation_buttons2.imageset:7
    references "Gui/imagesets/playstation_buttons2.edds". Falls back to the
    folder name, with a warning, when the mod has no $PBOPREFIX$ yet.
    """
    prefix_file = mod_root / "$PBOPREFIX$"
    if prefix_file.is_file():
        prefix = prefix_file.read_text(encoding="utf-8-sig").strip().strip("\\/")
        if prefix:
            return prefix
    print(f"{WARN} no $PBOPREFIX$ in {mod_root}; using the folder name {mod_root.name!r} as the mod name")
    return mod_root.name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pack .gui-sources/<setname>/*.png into DayZ imagesets in <mod>/gui/imagesets/."
    )
    parser.add_argument(
        "mod",
        help="<ModName> (resolved to workspace/<ModName>/ in the project cached by /dayz-init) "
             "or a path to a mod root containing .gui-sources/ (any argument with a slash, "
             "backslash or drive, or . / ..).",
    )
    parser.add_argument(
        "--mod-name",
        default=None,
        help="Root used in the path field of the .imageset (default: the mod's $PBOPREFIX$, "
             "else the mod folder name).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned atlases and the stale outputs that would be deleted; "
             "write and delete nothing.",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="Delete generated .paa/.imageset files in gui/imagesets/ whose .gui-sources/<set>/ "
             "folder no longer exists (default: only report them).",
    )
    args = parser.parse_args()

    h.gate_on_preflight()

    if Image is None:
        sys.exit(
            f"{FAIL} Pillow is not installed (needed to compose the atlas).\n"
            f'       Install it: py -m pip install -r "{REQUIREMENTS}"'
        )

    mod_root = resolve_mod_root(args.mod)

    sources_dir = mod_root / ".gui-sources"
    if not sources_dir.is_dir():
        sys.exit(
            f"{FAIL} .gui-sources/ not found at {sources_dir}\n"
            f"       Create {sources_dir}\\<setname>\\*.png and re-run."
        )

    out_dir = mod_root / "gui" / "imagesets"
    # Dot folders (.git, .vscode) are tooling, not imagesets.
    set_dirs = sorted(d for d in sources_dir.iterdir()
                      if d.is_dir() and not d.name.startswith("."))
    if not set_dirs:
        # Every set folder was removed, so every generated output is an orphan.
        handle_orphans(out_dir, (), args.prune, args.dry_run)
        sys.exit(
            f"{FAIL} no imageset subfolders under {sources_dir}\n"
            f"       Each subfolder of .gui-sources/ becomes one imageset."
        )

    mod_name = args.mod_name or default_mod_name(mod_root)

    print()
    image_to_paa = resolve_image_to_paa()
    print(f"{OK} ImageToPAA: {image_to_paa}")
    print(f"{INFO} mod root:   {mod_root}")
    print(f"{INFO} mod name:   {mod_name}")
    print(f"{INFO} sources:    {sources_dir}")
    print(f"{INFO} output dir: {out_dir}")
    print(f"{INFO} {len(set_dirs)} imageset(s): {', '.join(d.name for d in set_dirs)}")
    if args.dry_run:
        print(f"{INFO} dry run: nothing will be written or deleted")

    set_names = frozenset(d.name for d in set_dirs)
    success = 0
    for set_dir in set_dirs:
        if build_one(set_dir, mod_name, out_dir, image_to_paa, set_names - {set_dir.name},
                     args.dry_run):
            success += 1

    handle_orphans(out_dir, set_names, args.prune, args.dry_run)

    total = len(set_dirs)
    print()
    verb = "planned (dry run)" if args.dry_run else "built"
    print(f"{OK if success == total else FAIL}{success} of {total} imagesets {verb}.")
    return 0 if success == total else 1


if __name__ == "__main__":
    sys.exit(main())
