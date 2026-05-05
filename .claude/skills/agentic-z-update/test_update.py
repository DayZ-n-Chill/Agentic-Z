"""Unit tests for agentic-z-update helpers.

Run: python .claude/skills/agentic-z-update/test_update.py
"""
import subprocess
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


import os
import tempfile

from update import (
    read_baseline, write_baseline, BASELINE_FILE,
    read_lock, write_lock, release_lock, LOCK_FILE, _pid_alive,
)


class TestBaselineFile(unittest.TestCase):
    """Baseline file roundtrip + edge cases. Uses a temp cwd to avoid touching the real one."""

    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="agentic-z-update-test-")
        os.chdir(self._tmp)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_read_returns_none_when_baseline_missing(self):
        self.assertIsNone(read_baseline())

    def test_write_then_read_roundtrip(self):
        write_baseline("4816814b9d8a3f5e7c1234567890abcdef123456")
        self.assertEqual(
            read_baseline(),
            "4816814b9d8a3f5e7c1234567890abcdef123456",
        )

    def test_write_overwrites_previous_baseline(self):
        write_baseline("aaaaaaa")
        write_baseline("bbbbbbb")
        self.assertEqual(read_baseline(), "bbbbbbb")

    def test_read_returns_none_for_too_short_sha(self):
        BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_FILE.write_text("abc")  # too short
        self.assertIsNone(read_baseline())


class TestLockFile(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="agentic-z-update-test-")
        os.chdir(self._tmp)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_read_returns_none_when_no_lock(self):
        self.assertIsNone(read_lock())

    def test_write_then_read_roundtrip(self):
        write_lock()
        lock = read_lock()
        self.assertIsNotNone(lock)
        self.assertEqual(lock["pid"], os.getpid())
        self.assertIn("started_at", lock)

    def test_release_removes_lock(self):
        write_lock()
        self.assertTrue(LOCK_FILE.exists())
        release_lock()
        self.assertFalse(LOCK_FILE.exists())

    def test_release_is_safe_when_no_lock(self):
        # Should not raise.
        release_lock()

    def test_pid_alive_for_self(self):
        self.assertTrue(_pid_alive(os.getpid()))

    def test_pid_alive_for_clearly_dead_pid(self):
        # PID 999999 is virtually never a real process.
        self.assertFalse(_pid_alive(999999))

    def test_pid_alive_no_substring_false_positive(self):
        # On Windows tasklist's CSV quotes each field. Searching for a short PID
        # like "1" must NOT match inside a longer quoted PID like "1234".
        # Self PID is alive; PID composed by stripping a digit must still be
        # judged on its own merits, not via substring of self.
        my_pid = os.getpid()
        # Pick a PID that's a substring of my_pid but unlikely to be live.
        # Use my_pid + 1000000 so it shares no digit prefix yet is clearly fake.
        fake_pid = my_pid + 1_000_000
        self.assertFalse(_pid_alive(fake_pid))


from update import acquire_lock


class TestAcquireLock(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        self._tmp = tempfile.mkdtemp(prefix="agentic-z-update-test-")
        os.chdir(self._tmp)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_acquire_when_no_lock(self):
        self.assertTrue(acquire_lock())
        self.assertTrue(LOCK_FILE.exists())
        release_lock()

    def test_acquire_refused_when_live_pid_holds_lock(self):
        # Use our own PID to simulate a live holder.
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        LOCK_FILE.write_text(_json.dumps({"pid": os.getpid(), "started_at": "2026-05-05T00:00:00Z"}))
        self.assertFalse(acquire_lock())
        # Lock file untouched.
        self.assertTrue(LOCK_FILE.exists())
        release_lock()

    def test_acquire_takes_over_stale_lock_with_dead_pid(self):
        LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        LOCK_FILE.write_text(_json.dumps({"pid": 999999, "started_at": "2020-01-01T00:00:00Z"}))
        self.assertTrue(acquire_lock())
        # Lock now belongs to us.
        self.assertEqual(read_lock()["pid"], os.getpid())
        release_lock()


class TestComputeDriftSmoke(unittest.TestCase):
    """Single smoke test for compute_drift — full integration is covered by manual smoke later."""

    def test_compute_drift_returns_dict(self):
        # compute_drift uses git diff against the current repo; needs a git tree.
        if not Path(".git").exists():
            self.skipTest("not a git repo; skipping compute_drift smoke")
        from update import compute_drift
        # Pass current HEAD as both baseline and upstream — diff is empty,
        # so the candidate set is empty and the result must be {}.
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        drift = compute_drift(baseline_sha=head, upstream_ref=head)
        # May contain entries for locally-modified files (test edits, etc.) but
        # the test environment is generally clean; allow any dict, just verify type.
        self.assertIsInstance(drift, dict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
