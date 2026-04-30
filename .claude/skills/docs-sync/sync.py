"""Drift detector for docs ↔ wiki sync.

Compares canonical source files (.claude/agents/, .claude/skills/, docs/, L1 files)
to their Docusaurus wiki mirrors at wiki/docs/. Reports what's out of sync.

Does NOT apply edits — that's the docs-wiki-sync agent's job. This script is
designed to run in hooks (Stop hook) for fast, LLM-free drift detection.

Usage:
    python .claude/skills/docs-sync/sync.py --check       # report drift, exit 0 if clean
    python .claude/skills/docs-sync/sync.py --check --quiet  # silent unless drift
    python .claude/skills/docs-sync/sync.py --map         # print canonical→mirror map and exit
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def find_canonical_targets() -> list[tuple[Path, Path, str]]:
    """Return list of (canonical, wiki_mirror, kind) tuples."""
    targets: list[tuple[Path, Path, str]] = []

    agents_src = REPO_ROOT / ".claude" / "agents"
    agents_dst = REPO_ROOT / "wiki" / "docs" / "agents"
    if agents_src.is_dir():
        for src in sorted(agents_src.glob("*.md")):
            targets.append((src, agents_dst / src.name, "agent"))

    skills_src = REPO_ROOT / ".claude" / "skills"
    skills_dst = REPO_ROOT / "wiki" / "docs" / "skills"
    if skills_src.is_dir():
        for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir() and p.name != "_shared"):
            src = skill_dir / "SKILL.md"
            if src.is_file():
                targets.append((src, skills_dst / f"{skill_dir.name}.md", "skill"))

    flat_pairs = [
        (REPO_ROOT / ".claude" / "skills" / "_shared" / "dayz-conventions.md",
         REPO_ROOT / "wiki" / "docs" / "dayz-conventions.md", "doc"),
        (REPO_ROOT / "docs" / "dayz-modding.md",
         REPO_ROOT / "wiki" / "docs" / "dayz-modding.md", "doc"),
        (REPO_ROOT / "docs" / "model-routing.md",
         REPO_ROOT / "wiki" / "docs" / "model-routing.md", "doc"),
    ]
    for src, dst, kind in flat_pairs:
        if src.is_file():
            targets.append((src, dst, kind))

    return targets


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm_block, body = parts[1], parts[2]
    fm: dict[str, str] = {}
    for line in fm_block.strip().splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm, body.lstrip("\n")


def signature_for_kind(kind: str, src_text: str) -> str:
    """Compute a content signature for drift detection.

    Strips fields the wiki version reasonably differs on (description moves
    out of frontmatter, etc.) and normalizes whitespace. Mirror's signature
    is computed the same way.
    """
    fm, body = split_frontmatter(src_text)
    if kind == "agent":
        normalized_fm = {k: fm.get(k, "") for k in ("name", "model", "color", "memory")}
    elif kind == "skill":
        normalized_fm = {k: fm.get(k, "") for k in ("name",)}
    else:
        normalized_fm = {k: fm.get(k, "") for k in ("name", "title")}

    body_norm = re.sub(r"\s+", " ", body).strip()
    fm_norm = "|".join(f"{k}={v}" for k, v in sorted(normalized_fm.items()))
    return f"{fm_norm}::{body_norm}"


def mirror_signature(kind: str, mirror_text: str) -> str:
    """Mirror files have already been transformed (description in body, etc.).
    For drift detection we hash the body only — frontmatter is reduced and we
    don't try to round-trip the description back out for comparison."""
    fm, body = split_frontmatter(mirror_text)
    if kind == "agent":
        normalized_fm = {k: fm.get(k, "") for k in ("name", "model", "color", "memory")}
    elif kind == "skill":
        normalized_fm = {k: fm.get(k, "") for k in ("name",)}
    else:
        normalized_fm = {k: fm.get(k, "") for k in ("name", "title")}
    body_norm = re.sub(r"\s+", " ", body).strip()
    fm_norm = "|".join(f"{k}={v}" for k, v in sorted(normalized_fm.items()))
    return f"{fm_norm}::{body_norm}"


def detect_drift() -> dict[str, list[Path]]:
    targets = find_canonical_targets()
    out: dict[str, list[Path]] = {"missing_mirror": [], "src_newer": [], "orphan": []}

    seen_mirrors: set[Path] = set()

    for src, mirror, kind in targets:
        seen_mirrors.add(mirror)
        if not mirror.is_file():
            out["missing_mirror"].append(src)
            continue
        try:
            src_mtime = src.stat().st_mtime
            mirror_mtime = mirror.stat().st_mtime
        except OSError:
            continue
        if src_mtime > mirror_mtime + 1.0:
            out["src_newer"].append(src)

    for wiki_dir, kind in [
        (REPO_ROOT / "wiki" / "docs" / "agents", "agent"),
        (REPO_ROOT / "wiki" / "docs" / "skills", "skill"),
    ]:
        if not wiki_dir.is_dir():
            continue
        for mirror in wiki_dir.glob("*.md"):
            if mirror.name.startswith("_"):
                continue
            if mirror in seen_mirrors:
                continue
            out["orphan"].append(mirror)

    return out


def report(drift: dict[str, list[Path]], quiet: bool) -> int:
    n_missing = len(drift["missing_mirror"])
    n_newer = len(drift["src_newer"])
    n_orphan = len(drift["orphan"])
    total = n_missing + n_newer + n_orphan

    if total == 0:
        if not quiet:
            print("docs-sync: wiki is in sync with canonical sources.")
        return 0

    if quiet:
        print(f"docs-sync: {total} file(s) need wiki sync. Run /docs-sync.")
        return 0

    print(f"docs-sync: {total} file(s) need wiki sync.")
    if n_missing:
        print(f"  Missing wiki mirror ({n_missing}):")
        for p in drift["missing_mirror"]:
            print(f"    - {p.relative_to(REPO_ROOT)}")
    if n_newer:
        print(f"  Source newer than mirror ({n_newer}):")
        for p in drift["src_newer"]:
            print(f"    - {p.relative_to(REPO_ROOT)}")
    if n_orphan:
        print(f"  Orphan wiki page (canonical source missing) ({n_orphan}):")
        for p in drift["orphan"]:
            print(f"    - {p.relative_to(REPO_ROOT)}")
    print()
    print("Run /docs-sync (or invoke the docs-wiki-sync agent) to apply updates.")
    return 0


def print_map() -> int:
    targets = find_canonical_targets()
    print(f"{'CANONICAL':60} {'WIKI MIRROR':60} KIND")
    print("-" * 130)
    for src, mirror, kind in targets:
        s = str(src.relative_to(REPO_ROOT))
        m = str(mirror.relative_to(REPO_ROOT))
        print(f"{s:60} {m:60} {kind}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="Report drift (default)")
    p.add_argument("--quiet", action="store_true", help="Silent on success, single-line on drift (for hooks)")
    p.add_argument("--map", action="store_true", help="Print canonical→mirror map and exit")
    args = p.parse_args()

    if args.map:
        return print_map()

    drift = detect_drift()
    return report(drift, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
