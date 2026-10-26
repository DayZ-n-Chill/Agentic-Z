"""dayz-pack-texture: Convert PNG/TGA -> .paa via DayZ Tools' ImageToPAA.exe.

Validates that each input ends in a texture-role suffix used by vanilla DayZ
(_co, _nohq, _smdi and the rest of ALLOWED_SUFFIXES) so ImageToPAA and the
engine treat the texture as the right kind, and that both sides of the image are
powers of two. Every input is checked before anything converts, and every
problem is reported in one run. An existing .paa next to the source is copied to
one rolling backup, <name>.paa.bak (replacing the backup from the previous run,
so repacking never piles up copies), before it is overwritten; if the conversion
then fails, the backup is copied back over it. --dry-run validates and lists what
would be written, writing nothing.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_shared"))
import skill_helpers as h  # noqa: E402

ALLOWED_EXTS = {".png", ".tga"}
# Texture-role suffixes that both appear on vanilla .paa files under P:\DZ and
# have an entry in DayZ Tools' Bin\ImageToPAA\TexConvert.cfg, which picks the
# compression and color space from the suffix.
ALLOWED_SUFFIXES = (
    "_co", "_ca", "_lco", "_lca",          # color, color+alpha, terrain layer color (+alpha)
    "_nohq", "_no", "_non", "_nopx",       # normal maps (HQ, plain, alpha noise, parallax)
    "_smdi", "_sm",                        # specular
    "_as", "_ads", "_adshq",               # ambient shadow
    "_mc", "_mco",                         # macro, multiply color
    "_dt", "_detail", "_cdt", "_dtsmdi",   # detail
    "_mask", "_sky",                       # masks, sky
)
SUFFIX_RE = re.compile(
    "(" + "|".join(re.escape(s) for s in ALLOWED_SUFFIXES) + ")$", re.IGNORECASE
)
# Rename hints for a basename with no role suffix. A trailing word that names the
# role is replaced by the suffix (vest_normal.png -> vest_nohq.png); a role word
# elsewhere in the stem gets the suffix appended; anything else gets _co.
ROLE_WORDS = {
    "_nohq": ("normal", "normals", "nrm", "norm", "nor", "nml"),
    "_smdi": ("specular", "spec", "spc", "gloss"),
    "_ca": ("alpha",),
    "_co": ("diffuse", "diff", "albedo", "basecolor", "color", "colour", "col"),
}
ROLE_LABELS = {
    "_co": "color/diffuse",
    "_ca": "color with alpha",
    "_nohq": "normal map",
    "_smdi": "specular",
}
# Older releases of this skill numbered extra backups (<name>.paa.bak.1, .bak.2
# ...). They are counted, never deleted, so the user can clear them out.
NUMBERED_BACKUP_RE = re.compile(r"\.bak\.\d+$", re.IGNORECASE)
# Texture sides vanilla uses (skills/_shared/textures/suffixes-and-sizes.md).
VANILLA_SIZES = (64, 128, 256, 512, 1024, 2048)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
# TGA header fields (Truevision TGA 2.0 spec): byte 1 color map type, byte 2
# image type (1-3 uncompressed, 9-11 RLE; 0 means no image data), byte 16 bits per pixel.
TGA_COLOR_MAP_TYPES = {0, 1}
TGA_IMAGE_TYPES = {1, 2, 3, 9, 10, 11}
TGA_PIXEL_DEPTHS = {8, 15, 16, 24, 32}


def resolve_image_to_paa() -> Path:
    tools_root = h.preflight.find_dayz_tools()
    if tools_root is None:
        sys.exit(
            f"{h.FAIL} DayZ Tools not found.\n"
            "       Set DAYZ_TOOLS_PATH or install via Steam (Tools section)."
        )
    exe = tools_root / "Bin" / "ImageToPAA" / "ImageToPAA.exe"
    if not exe.exists():
        sys.exit(f"{h.FAIL} ImageToPAA.exe not at {exe}\n       DayZ Tools install may be incomplete.")
    print(f"{h.OK} ImageToPAA: {exe}")
    return exe


def image_size(path: Path) -> tuple[int, int] | None:
    """Width and height from the PNG IHDR chunk or the TGA header, or None if unreadable."""
    with path.open("rb") as f:
        head = f.read(24)
    if path.suffix.lower() == ".png":
        if len(head) < 24 or not head.startswith(PNG_SIGNATURE) or head[12:16] != b"IHDR":
            return None
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    # TGA has no signature, so check the header fields that a real image always
    # has; a corrupt file or a renamed PNG then fails here, before anything converts.
    if (
        len(head) < 18
        or head[1] not in TGA_COLOR_MAP_TYPES
        or head[2] not in TGA_IMAGE_TYPES
        or head[16] not in TGA_PIXEL_DEPTHS
    ):
        return None
    return int.from_bytes(head[12:14], "little"), int.from_bytes(head[14:16], "little")


def is_power_of_two(n: int) -> bool:
    return n > 0 and n & (n - 1) == 0


def nearest_vanilla_size(n: int) -> int:
    return min(VANILLA_SIZES, key=lambda size: (abs(size - n), -size))


def suggest_name(path: Path) -> tuple[str, str]:
    """A renamed filename for an input with no role suffix, and the suffix it uses,
    picked from the stem: 'normal' or 'nrm' gives _nohq, 'spec' gives _smdi,
    'alpha' gives _ca, and anything else gives _co (color, the most common role)."""
    stem = path.stem
    head, sep, last = stem.rpartition("_")
    if sep and head:
        for suffix, words in ROLE_WORDS.items():
            if last.lower() in words:
                return f"{head}{suffix}{path.suffix}", suffix
    lower = stem.lower()
    for suffix, words in ROLE_WORDS.items():
        # Skip the short words here ('nor', 'spc', 'nml'): inside a longer stem
        # they are too often part of a different word (e.g. 'north').
        if suffix != "_co" and any((len(w) >= 4 or w == "nrm") and w in lower for w in words):
            return f"{stem}{suffix}{path.suffix}", suffix
    return f"{stem}_co{path.suffix}", "_co"


def validate_input(path: Path) -> list[str]:
    """Every problem with one input as [FAIL] lines; an empty list means it is fine."""
    if not path.exists():
        return [f"{h.FAIL} Input not found: {path}"]
    if not path.is_file():
        return [f"{h.FAIL} {path}: is a folder, not an image file. Pass the .png or .tga itself."]
    errors = []
    ext_ok = path.suffix.lower() in ALLOWED_EXTS
    if not ext_ok:
        errors.append(
            f"{h.FAIL} {path.name}: only {', '.join(sorted(ALLOWED_EXTS))} accepted "
            f"(got {path.suffix or 'no extension'})."
        )
    if not SUFFIX_RE.search(path.stem):
        hint, role = suggest_name(path)
        errors.append(
            f"{h.FAIL} {path.name}: basename must end with one of "
            f"{', '.join(ALLOWED_SUFFIXES)} before the extension.\n"
            f"       The DayZ engine uses this suffix to assign the texture role.\n"
            f"       Rename to e.g. {hint} ({ROLE_LABELS[role]})."
        )
    if not ext_ok:
        return errors  # the header check needs a known image format
    try:
        size = image_size(path)
    except OSError as e:
        errors.append(
            f"{h.FAIL} {path.name}: cannot read the file ({e.strerror or e}).\n"
            "       Close any program that has it open and check its permissions."
        )
        return errors
    if size is None:
        errors.append(
            f"{h.FAIL} {path.name}: cannot read the image size from its header.\n"
            "       Re-export it from your image editor as a real PNG or TGA."
        )
        return errors
    width, height = size
    if not (is_power_of_two(width) and is_power_of_two(height)):
        errors.append(
            f"{h.FAIL} {path.name}: {width} x {height} is not a power of two on every side.\n"
            f"       Resize to the nearest vanilla size: "
            f"{nearest_vanilla_size(width)} x {nearest_vanilla_size(height)} "
            "(see skills/_shared/textures/suffixes-and-sizes.md)."
        )
    return errors


def check_unique_outputs(inputs: list[Path]) -> list[str]:
    """[FAIL] lines for inputs that would write the same .paa (vest_co.png and
    vest_co.tga), since the second conversion would silently replace the first."""
    seen: dict[str, Path] = {}
    errors = []
    for src in inputs:
        # normcase: Windows paths are case-insensitive, so VEST_CO.png and vest_co.tga collide too.
        key = os.path.normcase(str(src.with_suffix(".paa")))
        if key in seen:
            errors.append(
                f"{h.FAIL} {seen[key].name} and {src.name} would both write "
                f"{src.with_suffix('.paa').name}.\n"
                "       Pass only one of them, or rename one."
            )
        else:
            seen[key] = src
    return errors


def validate_all(inputs: list[Path]) -> list[str]:
    """Every problem across all inputs, so one run reports them all."""
    errors = [line for src in inputs for line in validate_input(src)]
    return errors + check_unique_outputs(inputs)


def backup_path(dst: Path) -> Path:
    """The one rolling backup for dst. Each repack replaces it, so iterating on a
    texture leaves a single copy next to it, which the build's *.bak exclude matches."""
    return dst.with_name(dst.name + ".bak")


def numbered_backups(dst: Path) -> list[Path]:
    """Leftover <name>.paa.bak.N files from older releases of this skill."""
    return sorted(
        p for p in dst.parent.glob(dst.name + ".bak.*")
        if NUMBERED_BACKUP_RE.search(p.name) and p.is_file()
    )


def report_backups(dst: Path) -> None:
    """Say how many backups of dst sit next to it, naming leftover numbered ones."""
    old = numbered_backups(dst)
    if old:
        print(
            f"{h.WARN} {1 + len(old)} backups of {dst.name} exist: {backup_path(dst).name} plus "
            f"{len(old)} older numbered one(s) ({', '.join(p.name for p in old)}).\n"
            "       This skill no longer writes or reads those; delete them when you no longer need them."
        )


def make_backup(dst: Path, bak: Path) -> None:
    """Copy dst to bak through a temporary file, so a failed copy never leaves a
    half-written backup in place of the previous good one."""
    tmp = bak.with_name(bak.name + ".tmp")
    try:
        shutil.copy2(dst, tmp)
        os.replace(tmp, bak)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def plan_one(src: Path) -> None:
    """Dry run: say what pack_one would write, touching nothing."""
    dst = src.with_suffix(".paa")
    print(f"[Dry run] {src.name}  ->  {dst.name}")
    if dst.exists():
        bak = backup_path(dst)
        note = f", replacing the current {bak.name}" if bak.exists() else ""
        print(f"          would back up the existing {dst.name} to {bak.name}{note}")
        report_backups(dst)


def undo_failed_pack(dst: Path, bak: Path | None) -> None:
    """Put dst back the way it was before ImageToPAA ran, so config.cpp and .rvmat
    never point at a half-written .paa. With a backup, copy it back; without one
    there was no .paa before, so remove whatever the failed run left."""
    try:
        if bak is not None:
            shutil.copy2(bak, dst)
            print(f"{h.OK} Restored the previous {dst.name} from {bak.name}", file=sys.stderr)
        elif dst.exists():
            dst.unlink()
            print(f"{h.OK} Removed the partial {dst.name} the failed run wrote", file=sys.stderr)
    except OSError as e:
        todo = f"copy {bak.name} over {dst.name}" if bak is not None else f"delete {dst.name}"
        print(f"{h.FAIL} Could not undo the failed run ({e.strerror or e}); {todo} by hand", file=sys.stderr)


def pack_one(image_to_paa: Path, src: Path) -> bool:
    dst = src.with_suffix(".paa")
    print()
    print(f"[Pack] {src.name}  ->  {dst.name}")
    bak = None
    before = None
    if dst.exists():
        # Keep the existing .paa (possibly hand-tuned) before ImageToPAA replaces it.
        bak = backup_path(dst)
        replacing = bak.exists()
        try:
            make_backup(dst, bak)
        except OSError as e:
            print(
                f"{h.FAIL} Could not back up {dst.name} to {bak.name} ({e.strerror or e}); "
                "skipped, so the existing file is untouched",
                file=sys.stderr,
            )
            return False
        note = " (replaced the previous backup)" if replacing else ""
        print(f"{h.OK} Backed up existing {dst.name} to {bak.name}{note}")
        report_backups(dst)
        # Remember the mtime so a run that exits 0 without writing is not
        # mistaken for success because the old file is still there.
        before = dst.stat().st_mtime_ns
    sys.stdout.flush()
    result = subprocess.run([str(image_to_paa), str(src), str(dst)])
    if result.returncode != 0:
        print(f"{h.FAIL} ImageToPAA exited {result.returncode} on {src.name}", file=sys.stderr)
    elif not dst.exists():
        print(f"{h.FAIL} ImageToPAA reported success but {dst} is missing", file=sys.stderr)
    elif before is not None and dst.stat().st_mtime_ns == before:
        print(
            f"{h.FAIL} ImageToPAA reported success but did not rewrite {dst}; "
            "the existing file is from an earlier run",
            file=sys.stderr,
        )
    else:
        print(f"{h.OK} Wrote {dst.name} ({dst.stat().st_size:,} bytes)")
        return True
    undo_failed_pack(dst, bak)
    return False


def gate(dry_run: bool) -> None:
    """Preflight first. A dry run uses only the read-only P:\\ check, because the
    full /dayz-preflight creates the P:\\Mods junction when it is missing."""
    if not dry_run:
        h.gate_on_preflight()
        return
    print("DayZ preflight (dry run: read-only P:\\ check)\n", flush=True)
    if not h.preflight.check_p_drive():
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert PNG/TGA -> .paa via DayZ Tools ImageToPAA.exe."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more PNG/TGA files. Basenames must end with a DayZ texture-role "
        "suffix such as _co, _ca, _nohq or _smdi (full list in SKILL.md).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the inputs and list the .paa files and backups that would be "
        "written, without converting or writing anything.",
    )
    args = parser.parse_args()

    gate(args.dry_run)
    print()

    inputs = [Path(p).resolve() for p in args.inputs]
    errors = validate_all(inputs)
    if errors:
        sys.stdout.flush()  # keep the preflight lines above the [FAIL] list
        for line in errors:
            print(line, file=sys.stderr)
        print(f"\n{h.FAIL}{len(errors)} input problem(s) found; nothing converted.", file=sys.stderr)
        return 1

    image_to_paa = resolve_image_to_paa()

    if args.dry_run:
        print()
        for src in inputs:
            plan_one(src)
        print()
        print(f"{h.OK} Dry run: {len(inputs)} textures would be packed; nothing written.")
        return 0

    success = 0
    for src in inputs:
        if pack_one(image_to_paa, src):
            success += 1

    print()
    print(f"{h.OK if success == len(inputs) else h.FAIL}{success} of {len(inputs)} textures packed.")
    return 0 if success == len(inputs) else 1


if __name__ == "__main__":
    sys.exit(main())
