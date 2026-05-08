"""Drift detector + applier for docs ↔ wiki sync.

Compares canonical source files (.claude/agents/, .claude/skills/, docs/, L1 files)
to their Docusaurus wiki mirrors at wiki/docs/. Detects drift (--check) and
applies the Docusaurus transform (--apply).

Two modes:
  --check (default)    Detect drift, print report, exit 0 even with drift.
                       Used by the SessionStop hook for fast, LLM-free polling.
  --apply              Run the canonical->wiki transforms in apply.py and
                       write every mirror. Prunes orphan wiki pages whose
                       canonical source no longer exists.

Pre-apply.py history: the apply step used to live in a `docs-wiki-sync`
agent that Claude had to dispatch manually, so wiki updates rotted between
manual invocations. The transforms are deterministic, so they live here
in pure Python now.

Usage:
    python .claude/skills/docs-sync/sync.py --check       # report drift, exit 0 if clean
    python .claude/skills/docs-sync/sync.py --check --quiet  # silent unless drift
    python .claude/skills/docs-sync/sync.py --apply       # apply transforms, prune orphans
    python .claude/skills/docs-sync/sync.py --apply --dry-run  # preview what --apply would do
    python .claude/skills/docs-sync/sync.py --map         # print canonical->mirror map and exit
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def _load_apply_module():
    """Load apply.py as a sibling module without polluting sys.path."""
    spec = importlib.util.spec_from_file_location(
        "docs_sync_apply", Path(__file__).parent / "apply.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load apply.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            if mirror.name.startswith("_") or mirror.name == "about.md":
                # `_*.md` files and the hand-written about.md aren't auto-mirrors
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
    print("Run `python .claude/skills/docs-sync/sync.py --apply` to update the wiki.")
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


def apply_all(dry_run: bool = False) -> int:
    """Run every transform and write mirror files. Prune orphan wiki pages.

    Returns 0 on success, non-zero on any IO error.
    """
    apply_mod = _load_apply_module()
    targets = find_canonical_targets()

    # Build (canonical, mirror, kind, transform_fn) tuples
    transform_for = {
        "skill": apply_mod.transform_skill,
        "agent": apply_mod.transform_agent,
        "doc": apply_mod.transform_doc,
    }

    written = 0
    unchanged = 0
    pruned = 0
    errors = 0
    seen_mirrors: set[Path] = set()

    for src, mirror, kind in targets:
        seen_mirrors.add(mirror)
        try:
            canonical_text = src.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[FAIL] read {src}: {e}", file=sys.stderr)
            errors += 1
            continue

        new_text = transform_for[kind](canonical_text)

        existing_text: str | None = None
        if mirror.exists():
            try:
                existing_text = mirror.read_text(encoding="utf-8")
            except OSError as e:
                print(f"[FAIL] read existing mirror {mirror}: {e}", file=sys.stderr)
                errors += 1
                continue

        if existing_text == new_text:
            # Content already matches, but the canonical's mtime is newer
            # than the mirror's. Touch the mirror so the drift detector
            # (mtime-based) doesn't keep flagging false drift.
            try:
                src_mtime = src.stat().st_mtime
                mirror.touch()
                import os
                os.utime(mirror, (src_mtime, src_mtime))
            except OSError:
                pass
            unchanged += 1
            continue

        if dry_run:
            print(f"[DRY] would write {mirror.relative_to(REPO_ROOT)}")
            written += 1
            continue

        try:
            mirror.parent.mkdir(parents=True, exist_ok=True)
            mirror.write_text(new_text, encoding="utf-8")
            print(f"[OK]   wrote {mirror.relative_to(REPO_ROOT)}")
            written += 1
        except OSError as e:
            print(f"[FAIL] write {mirror}: {e}", file=sys.stderr)
            errors += 1

    # Prune orphan wiki pages (mirror exists but no canonical source).
    for wiki_dir, _kind in [
        (REPO_ROOT / "wiki" / "docs" / "agents", "agent"),
        (REPO_ROOT / "wiki" / "docs" / "skills", "skill"),
    ]:
        if not wiki_dir.is_dir():
            continue
        for mirror in wiki_dir.glob("*.md"):
            if mirror.name.startswith("_") or mirror.name == "about.md":
                # `_` files and the hand-written about.md aren't auto-mirrors
                continue
            if mirror in seen_mirrors:
                continue
            if dry_run:
                print(f"[DRY] would prune orphan {mirror.relative_to(REPO_ROOT)}")
            else:
                try:
                    mirror.unlink()
                    print(f"[OK]   pruned orphan {mirror.relative_to(REPO_ROOT)}")
                except OSError as e:
                    print(f"[FAIL] prune {mirror}: {e}", file=sys.stderr)
                    errors += 1
                    continue
            pruned += 1

    print()
    verb = "would " if dry_run else ""
    print(f"docs-sync apply: {verb}wrote {written}, {verb}pruned {pruned}, unchanged {unchanged}, errors {errors}")
    return 1 if errors else 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="Report drift (default)")
    p.add_argument("--quiet", action="store_true", help="Silent on success, single-line on drift (for hooks)")
    p.add_argument("--map", action="store_true", help="Print canonical->mirror map and exit")
    p.add_argument("--apply", action="store_true", help="Apply Docusaurus transform and write all mirrors")
    p.add_argument("--dry-run", action="store_true", help="With --apply: preview what would change without writing")
    args = p.parse_args()

    if args.map:
        return print_map()

    if args.apply:
        return apply_all(dry_run=args.dry_run)

    drift = detect_drift()
    return report(drift, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
