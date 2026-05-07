"""Entry point for /dayz-init.

First run: setup wizard. Every run after: mission-control hub.
"""
from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    """Stub. Real orchestration arrives in later tasks."""
    print("dayz-init: not yet implemented")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
