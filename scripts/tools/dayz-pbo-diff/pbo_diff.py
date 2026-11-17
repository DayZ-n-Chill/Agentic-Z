"""Entry-level diff of two uncompressed PBOs.

Every entry is compared by the SHA-256 of its payload, and the header
properties as a whole. Both archives are read with the fail-closed PBO
reader, scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy/pbo.py: a
compressed entry, an unsafe, duplicate or non-ASCII entry name, a malformed
header, entry data past the end of the file and bytes after the last entry
other than a 21-byte trailer are refused, never skipped.
Read-only: the one file written is the new --out report.

Exit 0: both PBOs read and the report written, whatever they contain.
Exit 1: an input refused or unreadable, or --out already exists; nothing written.
Exit 2: usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


_READER_ROOT = (
    Path(__file__).resolve().parent.parent / "dayz-vehicle-proxy-contract" / "scripts"
)
if str(_READER_ROOT) not in sys.path:
    sys.path.insert(0, str(_READER_ROOT))

from vehicle_proxy.pbo import PboFormatError, digest_pbo  # noqa: E402


# Lists this long or longer print as a count on stdout; the report keeps them whole.
_SUMMARY_LIST_LIMIT = 12


class DiffError(Exception):
    """An input or output the diff refuses; nothing is written."""


def entry_key(name: str) -> str:
    """Entry names with forward slashes, as the report prints them."""
    return name.replace("\\", "/")


def _read(path: Path) -> tuple[dict[str, str], list[tuple[str, str]]]:
    digest = digest_pbo(path)
    hashes = {entry_key(entry.name): sha256 for entry, sha256 in digest.entries}
    return hashes, list(digest.properties)


def _ignored(name: str, prefixes: tuple[str, ...]) -> bool:
    return name.casefold().startswith(prefixes) if prefixes else False


def diff_pbos(old: Path, new: Path, ignore_prefixes: list[str] | tuple[str, ...] = ()) -> dict:
    """The report for two PBOs; raises PboFormatError on an input the reader refuses."""
    old_hashes, old_props = _read(Path(old))
    new_hashes, new_props = _read(Path(new))
    names = set(old_hashes) | set(new_hashes)
    differing = sorted(name for name in names if old_hashes.get(name) != new_hashes.get(name))
    prefixes = tuple(entry_key(prefix).casefold() for prefix in ignore_prefixes)
    return {
        "old": str(old),
        "new": str(new),
        "entries": [len(old_hashes), len(new_hashes)],
        "props_equal": old_props == new_props,
        "props_old": [list(item) for item in old_props],
        "props_new": [list(item) for item in new_props],
        "only_old": sorted(set(old_hashes) - set(new_hashes)),
        "only_new": sorted(set(new_hashes) - set(old_hashes)),
        "differing": differing,
        "differing_count": len(differing),
        "ignored_prefixes": list(ignore_prefixes),
        "differing_not_ignored": [name for name in differing if not _ignored(name, prefixes)],
    }


def _summary(report: dict) -> dict:
    return {
        key: (
            f"{len(value)} items"
            if isinstance(value, list) and len(value) >= _SUMMARY_LIST_LIMIT
            else value
        )
        for key, value in report.items()
    }


def _refuse_existing(out: Path) -> None:
    if out.exists() or out.is_symlink():
        raise DiffError(f"--out already exists, refusing to overwrite it: {out}")


def _write_new(out: Path, text: str) -> None:
    try:
        with out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    except FileExistsError as error:
        raise DiffError(f"--out already exists, refusing to overwrite it: {out}") from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pbo_diff.py",
        description="Compare the entries of two uncompressed PBOs by SHA-256, and their header properties.",
    )
    parser.add_argument("--old", type=Path, required=True, help="the PBO before the change")
    parser.add_argument("--new", type=Path, required=True, help="the PBO after the change")
    parser.add_argument("--out", type=Path, required=True, help="the JSON report to create; must not exist")
    parser.add_argument(
        "--ignore-prefix",
        action="append",
        default=[],
        metavar="PREFIX",
        help=(
            "leave entries under this name prefix out of differing_not_ignored (repeatable; "
            "/ or \\, any case); differing still lists them"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _refuse_existing(args.out)
        report = diff_pbos(args.old, args.new, args.ignore_prefix)
        _write_new(args.out, json.dumps(report, indent=1) + "\n")
    except (DiffError, PboFormatError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"error: cannot write --out {args.out}: {error}", file=sys.stderr)
        return 1
    print(json.dumps(_summary(report), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
