"""Pytest setup for the packctl tests.

Puts the knowledge-pack folder on sys.path so `import packctl` works when the
suite is started from the repository root, and exposes the shared fixture.
Helpers live in packctl_testlib.py, not here, so a second conftest.py elsewhere
in the repository cannot shadow them.
"""
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[2]
if str(PACK_ROOT) not in sys.path:
    sys.path.insert(0, str(PACK_ROOT))

from packctl_testlib import repo_factory  # noqa: E402,F401
