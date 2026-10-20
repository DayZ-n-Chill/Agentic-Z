"""dayz-pack-texture: Convert PNG/TGA -> .paa via DayZ Tools' ImageToPAA.exe.

Validates the required DayZ suffix (_co, _nohq, _smdi) on each input so the
engine assigns the correct texture role. An existing .paa next to the source is
overwritten.

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
ALLOWED_SUFFIXES = ("_co", "_nohq", "_smdi")
SUFFIX_RE = re.compile(r"_(co|nohq|smdi)$", re.IGNORECASE)


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


def pack_one(image_to_paa: Path, src: Path) -> bool:
    dst = src.with_suffix(".paa")
    print()
    print(f"[Pack] {src.name}  ->  {dst.name}")
    sys.stdout.flush()
    result = subprocess.run([str(image_to_paa), str(src), str(dst)])
    if result.returncode != 0:
        print(f"{h.FAIL} ImageToPAA exited {result.returncode} on {src.name}", file=sys.stderr)
        return False
    if not dst.exists():
        print(f"{h.FAIL} ImageToPAA reported success but {dst} is missing", file=sys.stderr)
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
        help="One or more PNG/TGA files. Basenames must end with _co, _nohq, or _smdi.",
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
