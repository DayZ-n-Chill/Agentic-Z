"""Unit tests for agentic-z-update helpers.

Run: python .claude/skills/agentic-z-update/test_update.py
"""
import sys
import unittest
from pathlib import Path

# Make update.py importable when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from update import classify_per_file, FileStatus  # noqa: E402


class TestClassifyPerFile(unittest.TestCase):
    """All 9 status branches in the classification table."""

    def test_unchanged_when_all_three_match(self):
        # local == baseline == upstream → no-op
        result = classify_per_file(baseline=b"hello", local=b"hello", upstream=b"hello")
        self.assertEqual(result, FileStatus.UNCHANGED)

    def test_safe_overwrite_when_local_matches_baseline_and_upstream_differs(self):
        # local == baseline, upstream != → apply upstream cleanly
        result = classify_per_file(baseline=b"v1", local=b"v1", upstream=b"v2")
        self.assertEqual(result, FileStatus.SAFE_OVERWRITE)

    def test_new_when_baseline_and_local_missing_but_upstream_exists(self):
        # baseline missing, local missing, upstream exists → create
        result = classify_per_file(baseline=None, local=None, upstream=b"new content")
        self.assertEqual(result, FileStatus.NEW)

    def test_local_only_edit_when_local_diverged_but_upstream_matches_baseline(self):
        # local != baseline, upstream == baseline → user edited only, leave alone
        result = classify_per_file(baseline=b"v1", local=b"v1-mine", upstream=b"v1")
        self.assertEqual(result, FileStatus.LOCAL_ONLY_EDIT)

    def test_conflict_when_both_local_and_upstream_diverged_from_baseline(self):
        # local != baseline AND upstream != baseline AND local != upstream
        result = classify_per_file(baseline=b"v1", local=b"v1-mine", upstream=b"v2")
        self.assertEqual(result, FileStatus.CONFLICT)

    def test_deleted_clean_when_local_matches_baseline_and_upstream_missing(self):
        # local == baseline, upstream gone → user didn't customize, delete OK
        result = classify_per_file(baseline=b"v1", local=b"v1", upstream=None)
        self.assertEqual(result, FileStatus.DELETED_CLEAN)

    def test_deleted_conflict_when_local_diverged_but_upstream_missing(self):
        # local != baseline, upstream gone → user customized but upstream removed it
        result = classify_per_file(baseline=b"v1", local=b"v1-mine", upstream=None)
        self.assertEqual(result, FileStatus.DELETED_CONFLICT)

    def test_local_only_new_when_baseline_and_upstream_missing_but_local_exists(self):
        # baseline missing, upstream missing, local exists → user-created, leave alone
        result = classify_per_file(baseline=None, local=b"my new agent", upstream=None)
        self.assertEqual(result, FileStatus.LOCAL_ONLY_EDIT)

    def test_skip_when_all_three_missing(self):
        # All missing → nothing to do (defensive case; shouldn't normally arise)
        result = classify_per_file(baseline=None, local=None, upstream=None)
        self.assertEqual(result, FileStatus.UNCHANGED)


if __name__ == "__main__":
    unittest.main(verbosity=2)
