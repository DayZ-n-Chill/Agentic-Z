"""Drift detector + applier for docs <-> wiki sync.

Compares canonical source files (.claude/agents/, .claude/skills/, docs/,
.claude/skills/_shared/dayz-conventions.md) to their Docusaurus wiki mirrors
under wiki/docs/.

Modes:
  --check (default)    Detect drift (missing mirror, mirror content differs
                       from the transformed source, orphan mirror) and print a
                       report. Exits 0, also when PyYAML is missing under
                       --quiet, so the Stop hook never fails. With --quiet
                       (how the Stop hook runs it) it prints nothing when in
                       sync, else one {"systemMessage": ...} JSON line, the
                       hook output Claude Code shows the user.
  --apply              Run the canonical->wiki transforms in apply.py, write
                       every changed mirror, and prune orphan wiki pages.
  --apply --dry-run    Print what --apply would write or prune; changes nothing
                       on disk. --dry-run without --apply is a usage error.
  --map                Print the canonical->mirror map and exit.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
YAML_HINT = "PyYAML is required. Install it with: python -m pip install pyyaml"


def hook_notice(message: str) -> None:
    """Print a message for the Stop hook (--quiet) as hook JSON output.

    Claude Code sends a command hook's plain stdout on exit 0 to the debug log,
    not the transcript; a `systemMessage` field is what it shows the user.
    """
    print(json.dumps({"systemMessage": message}))


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


def find_orphans(seen_mirrors: set[Path]) -> list[Path]:
    """Return agent/skill wiki pages that no canonical source maps to.

    `_*.md` files and the hand-written about.md are not auto-mirrors and are
    never reported or pruned.
    """
    orphans: list[Path] = []
    for wiki_dir in (REPO_ROOT / "wiki" / "docs" / "agents", REPO_ROOT / "wiki" / "docs" / "skills"):
        if not wiki_dir.is_dir():
            continue
        for mirror in sorted(wiki_dir.glob("*.md")):
            if mirror.name.startswith("_") or mirror.name == "about.md":
                continue
            if mirror not in seen_mirrors:
                orphans.append(mirror)
    return orphans


def _transformers() -> dict:
    apply_mod = _load_apply_module()
    return {
        "skill": apply_mod.transform_skill,
        "agent": apply_mod.transform_agent,
        "doc": apply_mod.transform_doc,
    }


def detect_drift() -> dict[str, list[Path]]:
    """Compare each mirror's content with its freshly transformed source.

    Content comparison (not modification times) so a checkout, copy or touch
    never reports false drift, and an edited mirror is always caught. A source
    whose frontmatter fails to parse is reported as stale; --apply shows the error.
    """
    transform_for = _transformers()
    out: dict[str, list[Path]] = {"missing_mirror": [], "stale": [], "orphan": []}
    seen_mirrors: set[Path] = set()

    for src, mirror, kind in find_canonical_targets():
        seen_mirrors.add(mirror)
        if not mirror.is_file():
            out["missing_mirror"].append(src)
            continue
        try:
            expected = transform_for[kind](src.read_text(encoding="utf-8"))
            current = mirror.read_text(encoding="utf-8")
        except (OSError, ValueError):
            out["stale"].append(src)
            continue
        if expected != current:
            out["stale"].append(src)

    out["orphan"] = find_orphans(seen_mirrors)
    return out


def report(drift: dict[str, list[Path]], quiet: bool) -> int:
    """Print the drift. Returns 1 when drift is found, so CI can gate on it.

    --quiet (the Stop hook) always returns 0 so it never fails a session.
    """
    n_missing = len(drift["missing_mirror"])
    n_stale = len(drift["stale"])
    n_orphan = len(drift["orphan"])
    total = n_missing + n_stale + n_orphan

    if total == 0:
        if not quiet:
            print("docs-sync: wiki is in sync with canonical sources.")
        return 0

    if quiet:
        hook_notice(f"docs-sync: {total} file(s) need wiki sync. Run /docs-sync.")
        return 0

    print(f"docs-sync: {total} file(s) need wiki sync.")
    if n_missing:
        print(f"  Missing wiki mirror ({n_missing}):")
        for p in drift["missing_mirror"]:
            print(f"    - {p.relative_to(REPO_ROOT)}")
    if n_stale:
        print(f"  Mirror out of date ({n_stale}):")
        for p in drift["stale"]:
            print(f"    - {p.relative_to(REPO_ROOT)}")
    if n_orphan:
        print(f"  Orphan wiki page (canonical source missing) ({n_orphan}):")
        for p in drift["orphan"]:
            print(f"    - {p.relative_to(REPO_ROOT)}")
    print()
    print("Run `python .claude/skills/docs-sync/sync.py --apply` to update the wiki.")
    return 1


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

    Returns 0 on success, 1 on any read, parse or write error.
    """
    transform_for = _transformers()
    targets = find_canonical_targets()

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

        try:
            new_text = transform_for[kind](canonical_text)
        except ValueError as e:
            print(f"[FAIL] {src}: {e}", file=sys.stderr)
            errors += 1
            continue

        existing_text: str | None = None
        if mirror.exists():
            try:
                existing_text = mirror.read_text(encoding="utf-8")
            except OSError as e:
                print(f"[FAIL] read existing mirror {mirror}: {e}", file=sys.stderr)
                errors += 1
                continue

        if existing_text == new_text:
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
    for mirror in find_orphans(seen_mirrors):
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
    wrote_word, pruned_word = ("would write", "would prune") if dry_run else ("wrote", "pruned")
    print(f"docs-sync apply: {wrote_word} {written}, {pruned_word} {pruned}, unchanged {unchanged}, errors {errors}")
    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="Report drift (default)")
    p.add_argument("--quiet", action="store_true", help="Stop hook mode: silent when in sync, otherwise one JSON systemMessage line")
    p.add_argument("--map", action="store_true", help="Print canonical->mirror map and exit")
    p.add_argument("--apply", action="store_true", help="Apply Docusaurus transform and write all mirrors")
    p.add_argument("--dry-run", action="store_true", help="With --apply: preview what would change without writing (requires --apply)")
    args = p.parse_args(argv)
    if args.dry_run and not args.apply:
        p.error("--dry-run only works with --apply")

    if args.map:
        return print_map()

    if importlib.util.find_spec("yaml") is None:
        if args.quiet:
            # The Stop hook runs --check --quiet; it must never fail a session.
            hook_notice(f"docs-sync: drift check skipped. {YAML_HINT}")
            return 0
        print(f"docs-sync: {YAML_HINT}", file=sys.stderr)
        return 1

    if args.apply:
        return apply_all(dry_run=args.dry_run)

    drift = detect_drift()
    return report(drift, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
