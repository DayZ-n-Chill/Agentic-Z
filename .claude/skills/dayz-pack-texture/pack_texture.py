"""dayz-pack-texture: Convert PNG/TGA -> .paa via DayZ Tools' ImageToPAA.exe.

Validates that each input ends in a texture-role suffix used by vanilla DayZ
(_co, _nohq, _smdi and the rest of ALLOWED_SUFFIXES) so ImageToPAA and the
engine treat the texture as the right kind, and that both sides of the image are
powers of two. An existing .paa next to the source is overwritten.

See SKILL.md for full usage.
"""
from __future__ import annotations

import argparse
import re
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
# Texture sides vanilla uses (.claude/skills/_shared/textures/suffixes-and-sizes.md).
VANILLA_SIZES = (64, 128, 256, 512, 1024, 2048)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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
    if len(head) < 18:
        return None
    return int.from_bytes(head[12:14], "little"), int.from_bytes(head[14:16], "little")


def is_power_of_two(n: int) -> bool:
    return n > 0 and n & (n - 1) == 0


def nearest_vanilla_size(n: int) -> int:
    return min(VANILLA_SIZES, key=lambda size: (abs(size - n), -size))


def validate_input(path: Path) -> None:
    if not path.exists():
        sys.exit(f"{h.FAIL} Input not found: {path}")
    if path.suffix.lower() not in ALLOWED_EXTS:
        sys.exit(
            f"{h.FAIL} {path.name}: only {', '.join(sorted(ALLOWED_EXTS))} accepted "
            f"(got {path.suffix})."
        )
    if not SUFFIX_RE.search(path.stem):
        sys.exit(
            f"{h.FAIL} {path.name}: basename must end with one of "
            f"{', '.join(ALLOWED_SUFFIXES)} before the extension.\n"
            f"       The DayZ engine uses this suffix to assign the texture role.\n"
            f"       Rename to e.g. {path.stem}_co{path.suffix} (color/diffuse)."
        )
    size = image_size(path)
    if size is None:
        sys.exit(f"{h.FAIL} {path.name}: cannot read the image size from its header.")
    width, height = size
    if not (is_power_of_two(width) and is_power_of_two(height)):
        sys.exit(
            f"{h.FAIL} {path.name}: {width} x {height} is not a power of two on every side.\n"
            f"       Resize to the nearest vanilla size: "
            f"{nearest_vanilla_size(width)} x {nearest_vanilla_size(height)} "
            "(see .claude/skills/_shared/textures/suffixes-and-sizes.md)."
        )


def pack_one(image_to_paa: Path, src: Path) -> bool:
    dst = src.with_suffix(".paa")
    print()
    print(f"[Pack] {src.name}  ->  {dst.name}")
    sys.stdout.flush()
    # Remember an existing .paa's mtime so a run that exits 0 without writing
    # is not mistaken for success because the old file is still there.
    before = dst.stat().st_mtime_ns if dst.exists() else None
    result = subprocess.run([str(image_to_paa), str(src), str(dst)])
    if result.returncode != 0:
        print(f"{h.FAIL} ImageToPAA exited {result.returncode} on {src.name}", file=sys.stderr)
        return False
    if not dst.exists():
        print(f"{h.FAIL} ImageToPAA reported success but {dst} is missing", file=sys.stderr)
        return False
    if before is not None and dst.stat().st_mtime_ns == before:
        print(
            f"{h.FAIL} ImageToPAA reported success but did not rewrite {dst}; "
            "the existing file is from an earlier run",
            file=sys.stderr,
        )
        return False
    size = dst.stat().st_size
    print(f"{h.OK} Wrote {dst.name} ({size:,} bytes)")
    return True


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
    args = parser.parse_args()

    h.gate_on_preflight()
    print()

    inputs = [Path(p).resolve() for p in args.inputs]
    for src in inputs:
        validate_input(src)

    image_to_paa = resolve_image_to_paa()

    success = 0
    for src in inputs:
        if pack_one(image_to_paa, src):
            success += 1

    print()
    print(f"{h.OK if success == len(inputs) else h.FAIL}{success} of {len(inputs)} textures packed.")
    return 0 if success == len(inputs) else 1


if __name__ == "__main__":
    sys.exit(main())
