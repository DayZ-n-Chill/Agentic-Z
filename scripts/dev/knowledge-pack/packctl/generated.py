"""Generated copies: one edited source, sealed copies, and the gate that catches drift.

Same idea as the MOVED-EXACT seals, applied to whole files instead of Markdown blocks:
the sha256 is over the RAW BYTES of the source, with no normalization, no BOM and no CRLF
variant. This module owns both halves -- writing a copy and checking one -- so the rule
that decides "in sync" cannot drift between the writer and the checker. `packctl validate`
and `tools/sync_generated.py` both call in here.

Why a sealed copy rather than one file everyone reads: `dayz_3d_viewer` ships as an
installed package. Measured 2026-09-02, it installs NON-editable (a real copy under
site-packages, `direct_url.json` with an empty `dir_info`), so nothing above it resolves to
the pack root and `skills/_shared/` does not exist from there. A package that walked up to
`_shared` would break `python -m dayz_3d_viewer`, a command the README and AGENTS.md
document. So the copy stays, and the gate makes hand-editing it a build failure.

Copies are DISCOVERED by their header, never read from a registry alone: a registry can
forget a file, and a copy that loses its header is reported instead of silently exempted.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

MARK = "# GENERATED FILE - DO NOT EDIT."
SOURCE_PREFIX = "# Source: "
SHA_PREFIX = "# source-sha256: "
REGEN_LINE = "# Regenerate: python tools/sync_generated.py sync --root ."

SKIP_PARTS = {".git", ".worktrees", "__pycache__", "build", "dist", ".venv", "node_modules"}

# (edited source, generated copy) -- repo-relative, POSIX separators.
PAIRS: list[tuple[str, str]] = [
    ("skills/_shared/viewer_core.py", "tools/dayz-3d-viewer/dayz_3d_viewer/viewer_core.py"),
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
    """Check every file that declares itself generated. Returns raw problem dicts.

    Kept free of packctl's `finding()` so the standalone CLI can call it too; the
    validator wraps these into findings.
    """
    problems: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        # Repo-relative parts only. packctl resolves --root, and this repo keeps its
        # checkouts under `.worktrees/`, so absolute parts skipped every file of such a
        # checkout and the PAIRS backstop then failed it with GENERATED-COPY-UNMARKED.
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
            # PAIRS describes THIS pack, and `scan` runs against any root: the builder
            # and gate fixtures are whole repositories as far as packctl is concerned.
            # With no edited source in the tree there is nothing to be a copy of, so a
            # missing copy is not drift and must not fail those roots. The two ways to
            # actually lose a pair stay covered: drop the source alone and the copy keeps
            # its header, so the loop above reports GENERATED-COPY-SOURCE-MISSING; drop
            # both and the source map reports SOURCE-OUTPUT-MISSING, since it tracks each
            # half as an artifact.
            continue
        problems.append({"code": "GENERATED-COPY-UNMARKED", "path": target_rel,
                         "message": "A declared generated copy is missing or lost its generated header.",
                         "evidence": "expected the header marker on line 1"})
    return problems
