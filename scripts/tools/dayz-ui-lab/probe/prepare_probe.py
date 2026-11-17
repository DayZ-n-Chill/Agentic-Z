from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SOURCE_ROOT = Path(__file__).with_name("LF_UIProbe")
TEMPLATE_RELATIVE_PATH = Path("gui/layouts/continuation.layout.template")


def build_probe(destination: Path) -> tuple[Path, Path]:
    """Stage the source-only probe with exact LF and CRLF layout variants."""
    if destination.exists():
        raise FileExistsError(f"destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_ROOT, destination)

    staged_template = destination / TEMPLATE_RELATIVE_PATH
    template = staged_template.read_bytes()
    if b"\r" in template:
        raise ValueError("probe template must be canonical LF")
    if template.count(b"\\\n") != 1:
        raise ValueError("probe template must contain one physical continuation")

    lf_path = staged_template.with_name("continuation-lf.layout")
    crlf_path = staged_template.with_name("continuation-crlf.layout")
    lf_path.write_bytes(template)
    crlf_path.write_bytes(template.replace(b"\n", b"\r\n"))
    staged_template.unlink()
    return lf_path, crlf_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Stage LF_UIProbe with byte-controlled LF/CRLF fixtures."
    )
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="new destination directory for the staged LF_UIProbe source",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    lf_path, crlf_path = build_probe(args.out)
    print(f"staged={args.out}")
    print(f"lf={lf_path}")
    print(f"crlf={crlf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
