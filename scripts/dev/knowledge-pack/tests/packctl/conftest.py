"""Pytest setup for the packctl tests.

Puts the folder that holds packctl on sys.path so `import packctl` works when the
suite is started from the repository root, and exposes the shared fixture.
Helpers live in packctl_testlib.py, not here, so a second conftest.py elsewhere
in the repository cannot shadow them.
"""
import sys
from pathlib import Path

TOOLING_ROOT = Path(__file__).resolve().parents[2]
if str(TOOLING_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLING_ROOT))

from packctl_testlib import repo_factory  # noqa: E402,F401
