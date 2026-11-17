"""CLI for the generated-copy seals. The rule itself lives in `packctl.generated`.

    python scripts/tools/sync_generated.py sync  --root .    regenerate every declared copy
    python scripts/tools/sync_generated.py check --root .    exit 1 on drift

`packctl validate` runs the same check through `validate_generated`; this script exists so
you can regenerate a copy without invoking the whole validator.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Running a script puts ITS directory on sys.path, not the cwd, so `packctl` (which lives
# in scripts/dev/knowledge-pack/) is not importable from scripts/tools/. Derived from
# __file__, never a machine path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dev" / "knowledge-pack"))

from packctl.generated import scan, sync  # noqa: E402


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
