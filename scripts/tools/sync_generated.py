"""Generated copies: one edited source, sealed copies, and the check that catches drift.

    python scripts/tools/sync_generated.py sync  --root .    regenerate every declared copy
    python scripts/tools/sync_generated.py check --root .    exit 1 on drift

The sha256 is over the raw bytes of the source, with no normalization, no BOM and no CRLF
variant. This file owns both halves, writing a copy and checking one, so the rule that
decides "in sync" cannot drift between the writer and the checker.

Why a sealed copy rather than one file everyone reads: `dayz_3d_viewer` is an installed
package. It installs non-editable (a real copy under site-packages), so nothing above it
resolves to the repository root and `skills/_shared/` does not exist from there. So the
copy stays, and the check makes hand-editing it a failure.

Copies are discovered by their header, never read from a registry alone: a registry can
forget a file, and a copy that loses its header is reported instead of silently exempted.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

MARK = "# GENERATED FILE - DO NOT EDIT."
SOURCE_PREFIX = "# Source: "
SHA_PREFIX = "# source-sha256: "
REGEN_LINE = "# Regenerate: python scripts/tools/sync_generated.py sync --root ."

SKIP_PARTS = {".git", ".worktrees", "__pycache__", "build", "dist", ".venv", "node_modules"}

# (edited source, generated copy) -- repo-relative, POSIX separators.
PAIRS: list[tuple[str, str]] = [
    ("skills/_shared/viewer_core.py", "scripts/tools/dayz-3d-viewer/dayz_3d_viewer/viewer_core.py"),
]


def sha_upper(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def header_for(source_rel: str, sha: str) -> bytes:
    return (
        f"{MARK}\n{SOURCE_PREFIX}{source_rel}\n{SHA_PREFIX}{sha}\n{REGEN_LINE}\n"
    ).encode("utf-8")


def expected_bytes(root: Path, source_rel: str) -> bytes:
    data = (root / source_rel).read_bytes()
    return header_for(source_rel, sha_upper(data)) + data


def sync(root: Path) -> list[str]:
    """Regenerate every copy in PAIRS. Returns the repo-relative paths written."""
    written: list[str] = []
    for source_rel, target_rel in PAIRS:
        target = root / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(expected_bytes(root, source_rel))
        written.append(target_rel)
    return written


def scan(root: Path) -> list[dict[str, str]]:
    """Check every file that declares itself generated. Returns raw problem dicts."""
    problems: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        # Repo-relative parts only: --root is resolved, and a checkout under `.worktrees/`
        # would otherwise skip every one of its own files.
        if any(part in SKIP_PARTS for part in relative.parts):
            continue
        raw = path.read_bytes()
        head = raw[:512].decode("utf-8", "replace").splitlines()
        if not head or head[0].strip() != MARK:
            continue
        rel = relative.as_posix()
        seen.add(rel)
        source_rel = next((l[len(SOURCE_PREFIX):].strip() for l in head if l.startswith(SOURCE_PREFIX)), "")
        pinned = next((l[len(SHA_PREFIX):].strip().upper() for l in head if l.startswith(SHA_PREFIX)), "")
        if not source_rel or not pinned:
            problems.append({"code": "GENERATED-COPY-HEADER-INCOMPLETE", "path": rel,
                             "message": "A generated file does not name its source or does not pin its sha256.",
                             "evidence": f"source={source_rel or '(none)'} pinned={pinned or '(none)'}"})
            continue
        if not (root / source_rel).is_file():
            problems.append({"code": "GENERATED-COPY-SOURCE-MISSING", "path": rel,
                             "message": "A generated file names a source that does not exist.",
                             "evidence": f"source={source_rel}"})
            continue
        actual = sha_upper((root / source_rel).read_bytes())
        if actual != pinned:
            problems.append({"code": "GENERATED-COPY-STALE-PIN", "path": rel,
                             "message": "The source changed since this copy was generated; regenerate it.",
                             "evidence": f"source={source_rel} pinned={pinned[:12]} actual={actual[:12]}"})
        if raw != expected_bytes(root, source_rel):
            problems.append({"code": "GENERATED-COPY-DRIFT", "path": rel,
                             "message": "A generated copy was edited by hand: its body differs from its source.",
                             "evidence": f"source={source_rel}"})
    for source_rel, target_rel in PAIRS:
        if target_rel in seen:
            continue
        if not (root / source_rel).is_file():
            # PAIRS describes this repository, and `scan` runs against any root. With no
            # edited source in the tree there is nothing to be a copy of, so a missing copy
            # is not drift. Dropping the source alone stays covered: the copy keeps its
            # header, so the loop above reports GENERATED-COPY-SOURCE-MISSING.
            continue
        problems.append({"code": "GENERATED-COPY-UNMARKED", "path": target_rel,
                         "message": "A declared generated copy is missing or lost its generated header.",
                         "evidence": "expected the header marker on line 1"})
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sync or check generated file copies.")
    ap.add_argument("action", choices=["sync", "check"])
    ap.add_argument("--root", default=".", help="repository root (default: cwd)")
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()

    if args.action == "sync":
        for rel in sync(root):
            print(f"generated {rel}")
        return 0

    problems = scan(root)
    for item in problems:
        print(f"{item['code']} {item['path']}: {item['message']} ({item['evidence']})")
    print(f"{len(problems)} finding(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
