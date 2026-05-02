"""Regenerate wiki/docs/skills/<name>.md from canonical .claude/skills/<name>/SKILL.md.

The wiki mirrors had `<` and `>` HTML-escaped (`&lt;` / `&gt;`) even inside
backticks where escaping is unnecessary. Result: pages display raw `&lt;domain&gt;`
text instead of rendering as code spans. This script does a clean copy so the
wiki version matches the canonical SKILL.md byte-for-byte (frontmatter stays,
body stays — markdown handles `<` inside backticks correctly).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CANONICAL_DIR = REPO / ".claude" / "skills"
WIKI_DIR = REPO / "wiki" / "docs" / "skills"


def main() -> int:
    if not CANONICAL_DIR.exists() or not WIKI_DIR.exists():
        print(f"[ERR]\tmissing dirs: canonical={CANONICAL_DIR}, wiki={WIKI_DIR}")
        return 1

    changed = 0
    for skill_dir in sorted(CANONICAL_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name.startswith("_"):
            continue
        canonical = skill_dir / "SKILL.md"
        if not canonical.exists():
            continue
        wiki = WIKI_DIR / f"{skill_dir.name}.md"
        if not wiki.exists():
            print(f"[SKIP]\t{skill_dir.name} (no wiki mirror)")
            continue

        new = canonical.read_text(encoding="utf-8")
        old = wiki.read_text(encoding="utf-8")
        if new != old:
            wiki.write_text(new, encoding="utf-8")
            print(f"[REGEN]\t{skill_dir.name}")
            changed += 1
        else:
            print(f"[OK]\t{skill_dir.name} (already clean)")

    print(f"\nDone. {changed} files updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
