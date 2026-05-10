"""dayz-build-imageset: Pack PNG sprites into a DayZ .imageset + .paa atlas.

Reads `<mod>/.gui-sources/<setname>/*.png`, shelf-packs into a square POT atlas
with a 10px gutter, converts to .paa via ImageToPAA.exe, and writes a matching
.imageset definition file under `<mod>/gui/imagesets/`.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
PREFLIGHT = REPO_ROOT / ".claude" / "skills" / "dayz-preflight" / "preflight.py"

OK = "[OK]   "
WARN = "[WARN] "
FAIL = "[FAIL] "
INFO = "[INFO] "

GAP = 10
POT_DIMS = [256, 512, 1024, 2048, 4096]
ATLAS_SIZES = sorted(
    {(w, h) for w in POT_DIMS for h in POT_DIMS},
    key=lambda s: (s[0] * s[1], abs(s[0] - s[1])),
)


def _load_preflight_module():
    spec = importlib.util.spec_from_file_location("dayz_preflight_module", PREFLIGHT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load preflight module at {PREFLIGHT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


find_dayz_tools = _load_preflight_module().find_dayz_tools


def gate_on_preflight() -> None:
    if not PREFLIGHT.exists():
        sys.exit(f"{FAIL} dayz-preflight not found at {PREFLIGHT.relative_to(REPO_ROOT)}")
    result = subprocess.run([sys.executable, str(PREFLIGHT)])
    if result.returncode != 0:
        sys.exit(result.returncode)


def resolve_image_to_paa() -> Path:
    tools_root = find_dayz_tools()
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

    Greedy first-fit-decreasing: sort sprites by height desc, then for each sprite
    try to add it to the current atlas; if it overflows, start a new atlas.
    Returns list of (dims, placed) tuples, or None if a single sprite is too big
    for the largest allowed atlas.
    """
    sorted_metas = sorted(metas, key=lambda m: (-m[2], -m[1]))
    atlases = []
    current: list = []
    for sprite in sorted_metas:
        trial = current + [sprite]
        dims, placed = shelf_pack(trial, gap)
        if dims is not None:
            current = trial
            continue
        if not current:
            return None  # single sprite doesn't fit even in the largest atlas
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
                    mod_name: str, out_dir: Path, image_to_paa: Path) -> bool:
    """Compose, convert, and emit a single atlas + .imageset for `placed` sprites."""
    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))
    for sprite_path, _, _, x, y in placed:
        with Image.open(sprite_path) as sprite:
            atlas.paste(sprite.convert("RGBA"), (x, y))

    paa_path = out_dir / f"{stem}.paa"
    imageset_path = out_dir / f"{stem}.imageset"

    with tempfile.TemporaryDirectory() as td:
        temp_png = Path(td) / f"{stem}.png"
        atlas.save(temp_png, "PNG")
        result = subprocess.run([str(image_to_paa), str(temp_png), str(paa_path)])
        if result.returncode != 0:
            print(f"{FAIL} ImageToPAA exited {result.returncode} on {stem}", file=sys.stderr)
            return False
        if not paa_path.exists():
            print(f"{FAIL} ImageToPAA reported success but {paa_path} is missing", file=sys.stderr)
            return False

    print(f"{OK} Wrote {paa_path.name} ({paa_path.stat().st_size:,} bytes)")

    paa_path_in_mod = f"{mod_name}\\gui\\imagesets\\{stem}.paa"
    write_imageset_file(imageset_path, stem, atlas_w, atlas_h, paa_path_in_mod, placed)
    print(f"{OK} Wrote {imageset_path.name}")
    return True


def build_one(set_dir: Path, mod_name: str, out_dir: Path, image_to_paa: Path) -> bool:
    set_name = set_dir.name
    pngs = sorted(p for p in set_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png")

    print()
    print(f"[Pack] {set_name}")

    if not pngs:
        print(f"{WARN} {set_name}: no .png files in {set_dir}, skipping")
        return True

    metas = []
    for p in pngs:
        with Image.open(p) as im:
            metas.append((p, im.width, im.height))

    atlases = pack_split(metas)
    if atlases is None:
        max_dim = POT_DIMS[-1]
        print(
            f"{FAIL} {set_name}: at least one sprite is larger than {max_dim}x{max_dim} "
            f"(minus gutter). Shrink it or use a different delivery format.",
            file=sys.stderr,
        )
        return False

    out_dir.mkdir(parents=True, exist_ok=True)

    if len(atlases) == 1:
        (atlas_w, atlas_h), placed = atlases[0]
        print(f"{INFO} {len(pngs)} sprite(s) -> {atlas_w}x{atlas_h} atlas")
        return write_one_atlas(set_name, atlas_w, atlas_h, placed, mod_name, out_dir, image_to_paa)

    print(
        f"{INFO} {len(pngs)} sprite(s) won't fit in one atlas, splitting into "
        f"{len(atlases)} parts: {set_name}_1 ... {set_name}_{len(atlases)}"
    )
    all_ok = True
    for idx, ((atlas_w, atlas_h), placed) in enumerate(atlases, start=1):
        stem = f"{set_name}_{idx}"
        print(f"{INFO}   {stem}: {len(placed)} sprite(s) -> {atlas_w}x{atlas_h} atlas")
        if not write_one_atlas(stem, atlas_w, atlas_h, placed, mod_name, out_dir, image_to_paa):
            all_ok = False
    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pack .gui-sources/<setname>/*.png into DayZ imagesets in <mod>/gui/imagesets/."
    )
    parser.add_argument(
        "mod_root",
        nargs="?",
        default=".",
        help="Mod root containing .gui-sources/ (default: current directory).",
    )
    parser.add_argument(
        "--mod-name",
        default=None,
        help="Mod name used in the path field of the .imageset (default: basename of mod_root).",
    )
    args = parser.parse_args()

    mod_root = Path(args.mod_root).resolve()
    if not mod_root.is_dir():
        sys.exit(f"{FAIL} mod_root not a directory: {mod_root}")

    sources_dir = mod_root / ".gui-sources"
    if not sources_dir.is_dir():
        sys.exit(
            f"{FAIL} .gui-sources/ not found at {sources_dir}\n"
            f"       Create {sources_dir}\\<setname>\\*.png and re-run."
        )

    set_dirs = sorted(d for d in sources_dir.iterdir() if d.is_dir())
    if not set_dirs:
        sys.exit(
            f"{FAIL} no imageset subfolders under {sources_dir}\n"
            f"       Each subfolder of .gui-sources/ becomes one imageset."
        )

    mod_name = args.mod_name or mod_root.name
    out_dir = mod_root / "gui" / "imagesets"

    gate_on_preflight()
    print()
    image_to_paa = resolve_image_to_paa()
    print(f"{OK} ImageToPAA: {image_to_paa}")
    print(f"{INFO} mod root:   {mod_root}")
    print(f"{INFO} mod name:   {mod_name}")
    print(f"{INFO} sources:    {sources_dir}")
    print(f"{INFO} output dir: {out_dir}")
    print(f"{INFO} {len(set_dirs)} imageset(s): {', '.join(d.name for d in set_dirs)}")

    success = 0
    for set_dir in set_dirs:
        if build_one(set_dir, mod_name, out_dir, image_to_paa):
            success += 1

    total = len(set_dirs)
    print()
    print(f"{OK if success == total else FAIL}{success} of {total} imagesets built.")
    return 0 if success == total else 1


if __name__ == "__main__":
    sys.exit(main())
