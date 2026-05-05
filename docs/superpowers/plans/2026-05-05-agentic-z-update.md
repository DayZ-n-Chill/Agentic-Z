# Agentic-Z Auto-Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the destructive `git checkout` overwrite in `/agentic-z-update` with a three-way merge that respects user customizations, plus a SessionStart hook that quietly nudges when upstream is ahead, plus a check for newer prebuilt search-index releases.

**Architecture:** Single Python script (`update.py`) keeps the existing CLI surface but routes every file change through a `classify_per_file(baseline, local, upstream)` pure function. Per-file status drives a preview, then either auto-apply (safe cases) or per-file picker (conflicts). A new `.claude/.upstream-baseline` file (gitignored) tracks the last-pulled SHA. A new `.claude/.upstream-update.lock` (gitignored, PID-based) prevents concurrent runs. SessionStart hook calls `update.py --check --quiet`.

**Tech Stack:** Python 3.8+ stdlib (subprocess, json, time, pathlib, urllib.request). `unittest` for tests (stdlib, no pytest dependency). No new third-party deps.

**Spec reference:** `docs/superpowers/specs/2026-05-05-agentic-z-update-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `.claude/skills/agentic-z-update/update.py` | Modified (rewrite of merge path; keep CLI/remote helpers) | Main entry point + all merge logic |
| `.claude/skills/agentic-z-update/test_update.py` | **New** | Unit tests for `classify_per_file` and helpers — runnable as `python test_update.py` (uses stdlib `unittest`) |
| `.claude/skills/agentic-z-update/SKILL.md` | Modified | Document new flags, baseline file, hook behavior |
| `.claude/settings.json` | Modified | Add `SessionStart` hook entry |
| `.gitignore` | Modified | Add `.claude/.upstream-baseline` and `.claude/.upstream-update.lock` |

Everything stays in one Python file. No new modules. The current `update.py` is ~250 lines and the rewrite stays comparable.

---

## Task 1: Add gitignore entries for baseline + lock files

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Read current `.gitignore` to find the right insertion point**

Run: `grep -n "settings.local.json\|local-memory" .gitignore`

Expected: lines like `.claude/settings.local.json` and `.claude/local-memory/` showing where per-clone Claude state goes.

- [ ] **Step 2: Append the new entries near the existing `.claude/` block**

Edit `.gitignore`. Find the existing block:

```
# Per-clone Claude settings (user/machine-specific permissions, hooks, etc.)
.claude/settings.local.json

# Per-clone local memory (user/machine-specific notes; never rules or conventions)
.claude/local-memory/
```

Add immediately after that block:

```
# Per-clone agentic-z-update state (last-pulled upstream SHA + concurrency lock)
.claude/.upstream-baseline
.claude/.upstream-update.lock
```

- [ ] **Step 3: Verify untracked**

Run: `git status --short .claude/`

Expected: only the `.gitignore` itself appears modified. Files like `.claude/.upstream-baseline` (if they happen to exist locally) should NOT appear.

- [ ] **Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore agentic-z-update baseline + lock files"
```

---

## Task 2: Add `classify_per_file` pure function with unit tests (TDD)

**Files:**
- Create: `.claude/skills/agentic-z-update/test_update.py`
- Modify: `.claude/skills/agentic-z-update/update.py` (add classify function near top)

This is a pure function: given three blobs, return a status enum. Easy to test without git.

- [ ] **Step 1: Write the test file with all 9 cases failing first**

Create `.claude/skills/agentic-z-update/test_update.py` with this complete content:

```python
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
```

- [ ] **Step 2: Run the test file. It should fail with ImportError**

Run: `python .claude/skills/agentic-z-update/test_update.py`

Expected: `ImportError: cannot import name 'classify_per_file' from 'update'`

- [ ] **Step 3: Add the FileStatus enum + classify_per_file function to update.py**

Find the location in `update.py` right after the imports block (after `UPSTREAM_BRANCH = "main"` and `TEMPLATE_PATHS = [...]`). Add:

```python
import enum
from typing import Optional


class FileStatus(enum.Enum):
    UNCHANGED = "unchanged"          # no-op
    SAFE_OVERWRITE = "safe-overwrite"  # local == baseline, take upstream
    NEW = "new"                       # baseline + local missing, take upstream
    LOCAL_ONLY_EDIT = "local-only-edit"  # only the user changed it, leave alone
    CONFLICT = "conflict"             # both diverged, ask user
    DELETED_CLEAN = "deleted-clean"   # local == baseline, upstream gone, delete OK
    DELETED_CONFLICT = "deleted-conflict"  # local diverged, upstream gone, ask user


def classify_per_file(
    baseline: Optional[bytes],
    local: Optional[bytes],
    upstream: Optional[bytes],
) -> FileStatus:
    """Three-way classification for a single template file.

    None for any blob means "file does not exist at that revision".
    Returns a FileStatus enum value indicating what action (if any) to take.

    See the spec at docs/superpowers/specs/2026-05-05-agentic-z-update-design.md
    for the full classification table.
    """
    # Defensive: nothing exists anywhere.
    if local is None and upstream is None and baseline is None:
        return FileStatus.UNCHANGED

    # Upstream removed the file.
    if upstream is None:
        if local is None:
            # Already gone locally too; nothing to do.
            return FileStatus.UNCHANGED
        if local == baseline:
            return FileStatus.DELETED_CLEAN
        return FileStatus.DELETED_CONFLICT

    # Upstream has the file.
    if local is None:
        # Local missing. If baseline also missing, user never had it → new.
        # If baseline existed, user deliberately deleted it → still treat as new
        # (re-add upstream version; user can delete again if they want).
        return FileStatus.NEW

    # Local exists.
    if local == upstream:
        # Already identical, regardless of baseline.
        return FileStatus.UNCHANGED

    # Local != upstream. What did baseline look like?
    if local == baseline:
        # User didn't touch it; safe to take upstream.
        return FileStatus.SAFE_OVERWRITE

    # Local != baseline → user changed it locally.
    if upstream == baseline:
        # Upstream is unchanged from baseline; user's edit is the only change.
        return FileStatus.LOCAL_ONLY_EDIT

    # Both local and upstream diverged from baseline → conflict.
    return FileStatus.CONFLICT
```

- [ ] **Step 4: Run the test file. All 9 tests should pass**

Run: `python .claude/skills/agentic-z-update/test_update.py`

Expected: `Ran 9 tests in 0.00Xs` followed by `OK`.

If any test fails, fix the classify_per_file logic before continuing. The tests are the spec; the implementation conforms to them.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/agentic-z-update/test_update.py .claude/skills/agentic-z-update/update.py
git commit -m "feat(agentic-z-update): add classify_per_file with unit tests"
```

---

## Task 3: Add baseline + lock file helpers (read/write)

**Files:**
- Modify: `.claude/skills/agentic-z-update/update.py`
- Modify: `.claude/skills/agentic-z-update/test_update.py` (add tests for these helpers)

- [ ] **Step 1: Add baseline read/write helpers to update.py**

Find the spot in update.py just before `def main()`. Add:

```python
import os
import tempfile

BASELINE_FILE = Path(".claude/.upstream-baseline")
LOCK_FILE = Path(".claude/.upstream-update.lock")


def read_baseline() -> Optional[str]:
    """Return the SHA of the last upstream merge, or None if not initialized."""
    if not BASELINE_FILE.exists():
        return None
    try:
        sha = BASELINE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not sha or len(sha) < 7:
        return None
    return sha


def write_baseline(sha: str) -> None:
    """Atomically write the baseline SHA. Temp file + rename to avoid partial writes."""
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Use NamedTemporaryFile in same dir so rename is on the same filesystem.
    tmp = BASELINE_FILE.with_suffix(".tmp")
    tmp.write_text(sha.strip() + "\n", encoding="utf-8")
    tmp.replace(BASELINE_FILE)


def _pid_alive(pid: int) -> bool:
    """Return True if a process with this PID is still running. Cross-platform best-effort."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # Windows: use tasklist as a portable check.
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
            capture_output=True, text=True,
        )
        return str(pid) in (r.stdout or "")
    # POSIX: signal 0 = liveness probe.
    try:
        os.kill(pid, 0)
        return True
    except (OSError, PermissionError):
        return False


def read_lock() -> Optional[dict]:
    """Return parsed lock dict (with 'pid' and 'started_at') or None if no lock."""
    if not LOCK_FILE.exists():
        return None
    try:
        return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_lock() -> None:
    """Write a lock file with this process's PID and an ISO timestamp."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "started_at": __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z",
    }
    LOCK_FILE.write_text(json.dumps(payload), encoding="utf-8")


def release_lock() -> None:
    """Best-effort lock removal; ignores missing file."""
    try:
        LOCK_FILE.unlink()
    except (FileNotFoundError, OSError):
        pass
```

Also add `import json` near the top of update.py if not already present.

- [ ] **Step 2: Add tests for read/write_baseline to test_update.py**

Append to `test_update.py` (after the `TestClassifyPerFile` class, before the `if __name__` block):

```python
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
```

- [ ] **Step 3: Run all tests. All should pass**

Run: `python .claude/skills/agentic-z-update/test_update.py`

Expected: `Ran 16+ tests in 0.0Xs` followed by `OK`.

If any baseline/lock test fails, fix the helper before continuing.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/agentic-z-update/update.py .claude/skills/agentic-z-update/test_update.py
git commit -m "feat(agentic-z-update): add baseline + lock file helpers"
```

---

## Task 4: Add per-file blob fetch + walk template paths

**Files:**
- Modify: `.claude/skills/agentic-z-update/update.py`

This task adds the glue between git and `classify_per_file`: read each template file at baseline / local / upstream and call classify.

- [ ] **Step 1: Add a helper that returns the file content at a git ref**

Find a spot in update.py near other git helpers (around `def remote_url()`). Add:

```python
def git_show_blob(ref: str, path: str) -> Optional[bytes]:
    """Return the bytes of `path` at git ref `ref`, or None if it doesn't exist there.

    `ref` is either a commit SHA, a branch name, or 'WORKING_TREE' (sentinel for the
    current on-disk file content rather than any committed version).
    """
    if ref == "WORKING_TREE":
        p = Path(path)
        if not p.exists():
            return None
        try:
            return p.read_bytes()
        except OSError:
            return None
    r = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        check=False,
        capture_output=True,
    )
    if r.returncode != 0:
        return None
    return r.stdout
```

- [ ] **Step 2: Add a helper that lists every file under TEMPLATE_PATHS at a given git ref**

Add right after `git_show_blob`:

```python
def list_template_files_at_ref(ref: str) -> set[str]:
    """List every file under TEMPLATE_PATHS at the given ref. Returns relative paths."""
    files: set[str] = set()
    for tp in TEMPLATE_PATHS:
        # `git ls-tree -r --name-only` for directories; for single files, just check existence.
        r = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ref, "--", tp],
            check=False,
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                line = line.strip()
                if line:
                    files.add(line)
    return files


def list_template_files_in_working_tree() -> set[str]:
    """List every file under TEMPLATE_PATHS in the current working tree. Returns relative paths."""
    files: set[str] = set()
    for tp in TEMPLATE_PATHS:
        p = Path(tp)
        if p.is_file():
            files.add(tp)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    files.add(f.as_posix())
    return files
```

- [ ] **Step 3: Add the `compute_drift` function that produces a per-file status map**

Add right after the listing helpers:

```python
def compute_drift(baseline_sha: Optional[str], upstream_ref: str) -> dict[str, FileStatus]:
    """Return a {path: FileStatus} dict for every file that exists in any of the
    three trees (baseline, working tree, upstream).

    If baseline_sha is None (first run), every file is treated as already-up-to-date
    relative to upstream (no warnings shown). Concretely we set baseline = upstream
    so SAFE_OVERWRITE never fires until the user has a real baseline recorded.
    """
    if baseline_sha is None:
        # Bootstrap: pretend baseline IS upstream. No drift surfaces this run.
        baseline_sha = upstream_ref

    upstream_files = list_template_files_at_ref(upstream_ref)
    baseline_files = list_template_files_at_ref(baseline_sha)
    local_files = list_template_files_in_working_tree()

    all_paths = upstream_files | baseline_files | local_files
    result: dict[str, FileStatus] = {}
    for path in sorted(all_paths):
        baseline_blob = git_show_blob(baseline_sha, path)
        upstream_blob = git_show_blob(upstream_ref, path)
        local_blob = git_show_blob("WORKING_TREE", path)
        status = classify_per_file(baseline=baseline_blob, local=local_blob, upstream=upstream_blob)
        if status != FileStatus.UNCHANGED:
            result[path] = status
    return result
```

- [ ] **Step 4: Add a smoke test for compute_drift**

Append to test_update.py before the `if __name__` block:

```python
class TestComputeDriftSmoke(unittest.TestCase):
    """Single smoke test for compute_drift — full integration is covered by manual smoke later."""

    def test_compute_drift_returns_dict(self):
        # Without a real baseline, this calls list_template_files_at_ref which
        # needs to be inside a git repo. Skip if we're in a temp dir.
        if not Path(".git").exists():
            self.skipTest("not a git repo; skipping compute_drift smoke")
        from update import compute_drift
        # Pass current HEAD as both baseline and upstream — drift should be empty.
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        drift = compute_drift(baseline_sha=head, upstream_ref=head)
        self.assertEqual(drift, {})
```

Add `import subprocess` at the top of test_update.py if not already there.

- [ ] **Step 5: Run all tests**

Run: `python .claude/skills/agentic-z-update/test_update.py`

Expected: all tests pass (the smoke test skips if not in a git repo).

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/agentic-z-update/update.py .claude/skills/agentic-z-update/test_update.py
git commit -m "feat(agentic-z-update): add git blob fetch + drift computation"
```

---

## Task 5: Add `--check` flag (preview only, no apply)

**Files:**
- Modify: `.claude/skills/agentic-z-update/update.py`

- [ ] **Step 1: Add the `--check` and `--quiet` flags to the argparser in `main()`**

Find the existing `argparse.ArgumentParser` block in `main()`. Add these two arguments:

```python
    parser.add_argument(
        "--check",
        action="store_true",
        help="Preview drift only; do not apply. Exits 1 if changes pending, 0 if up to date.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="With --check: silent on no-change, single line on drift. Used by SessionStart hook.",
    )
```

- [ ] **Step 2: Add a `format_preview` helper that turns a drift dict into human output**

Find a spot near other top-level helpers in update.py. Add:

```python
def format_preview(drift: dict[str, FileStatus], baseline_sha: Optional[str], upstream_sha: str, quiet: bool = False) -> str:
    """Format a drift dict into preview output. `quiet=True` returns a one-liner suitable for hooks."""
    if not drift:
        return ""

    if quiet:
        n = len(drift)
        n_conflict = sum(1 for s in drift.values() if s in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT))
        if n_conflict:
            return f"agentic-z: {n} template change(s) available, {n_conflict} conflict(s). Run /agentic-z-update."
        return f"agentic-z: {n} template change(s) available. Run /agentic-z-update."

    by_status: dict[FileStatus, list[str]] = {}
    for path, status in drift.items():
        by_status.setdefault(status, []).append(path)

    lines = []
    lines.append(f"Agentic-Z update preview (upstream: {upstream_sha[:7]}, baseline: {(baseline_sha or 'first-run')[:7] if baseline_sha else 'first-run'})")
    lines.append("")

    # Order matters: safe stuff first, conflicts last.
    order = [
        (FileStatus.SAFE_OVERWRITE, "safe to apply"),
        (FileStatus.NEW, "new files added"),
        (FileStatus.DELETED_CLEAN, "deletions (clean)"),
        (FileStatus.LOCAL_ONLY_EDIT, "your local-only edits (left alone)"),
        (FileStatus.CONFLICT, "CONFLICTS — both you and upstream edited these"),
        (FileStatus.DELETED_CONFLICT, "CONFLICTS — upstream deleted these but you edited them"),
    ]
    for status, label in order:
        paths = by_status.get(status, [])
        if not paths:
            continue
        lines.append(f"  {label}: {len(paths)} file(s)")
        for p in paths:
            lines.append(f"    - {p}")
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 3: Wire `--check` into `main()` to short-circuit before any apply path**

Find the existing flow in `main()` after `fetch_upstream()` returns. Insert (BEFORE the existing dirty-check + merge logic):

```python
    upstream_sha = upstream_head_sha()
    baseline_sha = read_baseline()

    if args.check:
        drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
        output = format_preview(drift, baseline_sha, upstream_sha, quiet=args.quiet)
        if output:
            print(output)
            return 1  # drift exists
        if not args.quiet:
            print("Up to date.")
        return 0
```

- [ ] **Step 4: Smoke-test `--check` and `--check --quiet` manually**

Run: `python .claude/skills/agentic-z-update/update.py --check`

Expected: Either a preview block or "Up to date." Exit code visible via `echo $?` (Bash) or `$LASTEXITCODE` (PowerShell).

Run: `python .claude/skills/agentic-z-update/update.py --check --quiet`

Expected: Either a single line `agentic-z: ...` or no output. Same exit codes.

If the script errors (e.g. `upstream` remote not yet added), check that `ensure_upstream()` is being called before `fetch_upstream()` — the existing code should handle it.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/agentic-z-update/update.py
git commit -m "feat(agentic-z-update): add --check and --quiet flags for preview-only mode"
```

---

## Task 6: Add interactive prompt + smart apply (replaces the `git checkout` overwrite)

**Files:**
- Modify: `.claude/skills/agentic-z-update/update.py`

- [ ] **Step 1: Add the `apply_drift` helper that walks the drift dict and applies changes**

Find a spot near `format_preview`. Add:

```python
def apply_drift(drift: dict[str, FileStatus], upstream_ref: str, conflict_choices: Optional[dict[str, str]] = None) -> tuple[list[str], list[str]]:
    """Apply changes from a drift dict.

    `conflict_choices` is an optional {path: 'keep'|'take'} dict for resolving
    conflicts. Paths missing from conflict_choices are LEFT ALONE (default
    bulk-apply behavior).

    Returns (applied, skipped) — lists of paths.
    """
    conflict_choices = conflict_choices or {}
    applied: list[str] = []
    skipped: list[str] = []

    for path, status in drift.items():
        if status == FileStatus.SAFE_OVERWRITE or status == FileStatus.NEW:
            r = subprocess.run(
                ["git", "checkout", upstream_ref, "--", path],
                check=False, capture_output=True, text=True,
            )
            if r.returncode == 0:
                applied.append(path)
            else:
                log("WARN", f"failed to checkout {path}: {r.stderr.strip()}")
                skipped.append(path)
        elif status == FileStatus.DELETED_CLEAN:
            try:
                Path(path).unlink()
                applied.append(path)
            except FileNotFoundError:
                applied.append(path)  # already gone, that's fine
            except OSError as e:
                log("WARN", f"failed to delete {path}: {e}")
                skipped.append(path)
        elif status == FileStatus.LOCAL_ONLY_EDIT:
            # Nothing to do — user's edit is the only change.
            skipped.append(path)
        elif status in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT):
            choice = conflict_choices.get(path)
            if choice == "take":
                if status == FileStatus.DELETED_CONFLICT:
                    try:
                        Path(path).unlink()
                        applied.append(path)
                    except OSError:
                        skipped.append(path)
                else:
                    r = subprocess.run(
                        ["git", "checkout", upstream_ref, "--", path],
                        check=False, capture_output=True, text=True,
                    )
                    if r.returncode == 0:
                        applied.append(path)
                    else:
                        skipped.append(path)
            else:
                # 'keep' or no choice → leave alone
                skipped.append(path)
    return applied, skipped
```

- [ ] **Step 2: Replace the existing `merge_template_paths` body to use `apply_drift`**

Find the existing `merge_template_paths` function. Replace its entire body with:

```python
def merge_template_paths() -> tuple[list[str], list[str]]:
    """Compute drift and apply with the default rules (no conflict resolution).

    Conflicts are SKIPPED — user must resolve via --per-file or by editing first.
    Returns (applied, conflicted) lists for the existing main() flow to log.
    """
    upstream_sha = upstream_head_sha()
    baseline_sha = read_baseline()
    drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
    applied, skipped = apply_drift(drift, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
    # Conflicted = the skipped files that were actually conflicts (not LOCAL_ONLY_EDIT).
    conflicted = [
        p for p in skipped
        if drift.get(p) in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT)
    ]
    return applied, conflicted
```

- [ ] **Step 3: Wire the preview + prompt into `main()` (only when not `--check`)**

Find the existing flow in `main()` AFTER the `--check` short-circuit (added in Task 5) and BEFORE the existing dirty-check/merge sequence. Add:

```python
    # Default flow: preview, prompt, apply.
    drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
    if not drift:
        log("INFO", "Up to date.")
        return 0

    print(format_preview(drift, baseline_sha, upstream_sha, quiet=False))

    if not args.dry_run:
        try:
            answer = input("Apply these changes? [y/N]: ").strip().lower()
        except EOFError:
            log("FAIL", "Non-interactive shell. Pass --yes to apply without prompting.")
            return 1
        if answer not in ("y", "yes"):
            log("INFO", "Cancelled by user.")
            return 0
```

Then locate the existing `merge_template_paths()` call further down in main() and ensure it's still being called after the prompt. The flow becomes: classify → preview → prompt → apply via `merge_template_paths` (which now uses the new logic).

- [ ] **Step 4: Update the post-merge logic to write the new baseline**

Find where `stage_and_commit` is called in `main()`. Right after a successful commit, add:

```python
    # Record the upstream SHA as the new baseline so the next run starts fresh.
    write_baseline(upstream_head_sha())
    log("OK", "Baseline updated.")
```

- [ ] **Step 5: Smoke-test the full flow against an artificial drift scenario**

Run: `python .claude/skills/agentic-z-update/update.py --check`

If it shows "Up to date," skip this step. If it shows drift, run:

`python .claude/skills/agentic-z-update/update.py --dry-run`

Expected: same preview output as `--check`, but exits 0 without changes (the existing `--dry-run` early-exits before merge).

- [ ] **Step 6: Run unit tests one more time**

Run: `python .claude/skills/agentic-z-update/test_update.py`

Expected: all tests still pass.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/agentic-z-update/update.py
git commit -m "feat(agentic-z-update): preview + interactive prompt + smart apply"
```

---

## Task 7: Add `--yes` and `--per-file` flags

**Files:**
- Modify: `.claude/skills/agentic-z-update/update.py`

- [ ] **Step 1: Add the two new flags to the argparser in `main()`**

In the existing argparser block, add:

```python
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the apply confirmation prompt (CI / scripted use).",
    )
    parser.add_argument(
        "--per-file",
        action="store_true",
        help="Walk each conflict interactively: keep / take / diff / skip.",
    )
```

- [ ] **Step 2: Modify the prompt block to honor `--yes`**

In `main()`, find the prompt block added in Task 6:

```python
        try:
            answer = input("Apply these changes? [y/N]: ").strip().lower()
```

Wrap it with the `--yes` short-circuit:

```python
    if not args.dry_run:
        if args.yes:
            log("INFO", "--yes: skipping confirmation.")
        else:
            try:
                answer = input("Apply these changes? [y/N]: ").strip().lower()
            except EOFError:
                log("FAIL", "Non-interactive shell. Pass --yes to apply without prompting.")
                return 1
            if answer not in ("y", "yes"):
                log("INFO", "Cancelled by user.")
                return 0
```

- [ ] **Step 3: Add a `resolve_conflicts_per_file` helper for `--per-file` mode**

Add near `apply_drift`:

```python
def resolve_conflicts_per_file(drift: dict[str, FileStatus], upstream_ref: str) -> dict[str, str]:
    """Walk each conflict interactively. Returns a {path: 'keep'|'take'} dict."""
    choices: dict[str, str] = {}
    conflicts = [p for p, s in drift.items() if s in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT)]
    if not conflicts:
        return choices

    print()
    print(f"Walking {len(conflicts)} conflict(s). For each: k=keep mine, t=take upstream, d=diff, s=skip (= keep).")
    for path in conflicts:
        while True:
            try:
                ans = input(f"  {path} [k/t/d/s]: ").strip().lower()
            except EOFError:
                log("WARN", f"non-interactive; defaulting {path} to 'keep'")
                choices[path] = "keep"
                break
            if ans in ("k", "keep", "s", "skip", ""):
                choices[path] = "keep"
                break
            if ans in ("t", "take"):
                choices[path] = "take"
                break
            if ans in ("d", "diff"):
                # Show a unified diff for the user.
                local = Path(path).read_bytes() if Path(path).exists() else b""
                upstream = git_show_blob(upstream_ref, path) or b""
                _print_diff(path, local, upstream)
                # Re-prompt after diff
                continue
            print("    invalid choice; try k/t/d/s")
    return choices


def _print_diff(path: str, local: bytes, upstream: bytes) -> None:
    """Print a unified diff between two byte blobs."""
    import difflib
    try:
        local_text = local.decode("utf-8").splitlines(keepends=True)
        upstream_text = upstream.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        print(f"    (binary file, no diff)")
        return
    diff = difflib.unified_diff(
        local_text, upstream_text,
        fromfile=f"a/{path} (yours)",
        tofile=f"b/{path} (upstream)",
        n=3,
    )
    sys.stdout.writelines(diff)
    print()
```

- [ ] **Step 4: Wire `--per-file` into the apply path**

In `main()`, modify the `merge_template_paths()` call site. Replace it with a more flexible block that respects `--per-file`:

```python
    # Replace the old merge_template_paths() call with this:
    upstream_ref = f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"
    if args.per_file:
        choices = resolve_conflicts_per_file(drift, upstream_ref)
    else:
        choices = {}
    applied, skipped = apply_drift(drift, upstream_ref, conflict_choices=choices)
    conflicted = [
        p for p in skipped
        if drift.get(p) in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT)
    ]
```

(Now `merge_template_paths` is only called if you keep it for backward-compat. You can remove its definition entirely if it's no longer called.)

- [ ] **Step 5: Smoke-test `--yes` and `--per-file`**

If there's no current drift, fake one for testing:

```bash
echo "test edit" >> README.md
python .claude/skills/agentic-z-update/update.py --check
git restore README.md
```

(This tests classification on a locally-edited file; expected: README.md flagged as `local-only-edit` if upstream README didn't change.)

- [ ] **Step 6: Run all unit tests**

Run: `python .claude/skills/agentic-z-update/test_update.py`

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/agentic-z-update/update.py
git commit -m "feat(agentic-z-update): add --yes and --per-file flags"
```

---

## Task 8: Wrap apply path with lock acquisition

**Files:**
- Modify: `.claude/skills/agentic-z-update/update.py`

- [ ] **Step 1: Add an `acquire_lock` helper that enforces the rules from the spec**

Add near `read_lock` / `write_lock`:

```python
def acquire_lock() -> bool:
    """Acquire the update lock. Returns True if acquired, False if another live process holds it.

    Stale locks (PID dead) are taken over automatically.
    """
    existing = read_lock()
    if existing is not None:
        pid = int(existing.get("pid", 0))
        if pid > 0 and _pid_alive(pid):
            log("FAIL", f"Another update is running (PID {pid}, started {existing.get('started_at', '?')}).")
            log("FAIL", "If you're sure it's stuck, delete .claude/.upstream-update.lock")
            return False
        # Stale lock — overwrite it.
        log("WARN", f"Found stale lock from dead PID {pid}; taking over.")
    write_lock()
    return True
```

- [ ] **Step 2: Wrap the apply phase with acquire_lock + try/finally release**

In `main()`, find the prompt block + apply_drift block. Wrap them:

```python
    if not args.dry_run:
        if args.yes:
            log("INFO", "--yes: skipping confirmation.")
        else:
            # ... existing prompt logic ...

        if not acquire_lock():
            return 1
        try:
            upstream_ref = f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"
            if args.per_file:
                choices = resolve_conflicts_per_file(drift, upstream_ref)
            else:
                choices = {}
            applied, skipped = apply_drift(drift, upstream_ref, conflict_choices=choices)
            # ... existing post-apply logic (stage_and_commit, write_baseline, sync-skills) ...
        finally:
            release_lock()
```

- [ ] **Step 3: Manually test the lock by spawning a stuck update**

Open two terminals.

Terminal 1: simulate a stuck update by writing a fake lock with your own PID:

```cmd
python -c "import json,os; open('.claude/.upstream-update.lock','w').write(json.dumps({'pid': os.getpid(), 'started_at': '2026-05-05T00:00:00Z'}))"
```

(If you can't run `python -c` due to deny rules, manually write `{"pid": <your-pid>, "started_at": "2026-05-05T00:00:00Z"}` to `.claude/.upstream-update.lock`.)

Terminal 2: try to run the update:

```cmd
python .claude/skills/agentic-z-update/update.py --yes
```

Expected: refuses with `Another update is running (PID ...)`. Exit code 1.

Cleanup:
```cmd
del .claude\.upstream-update.lock
```

- [ ] **Step 4: Test stale lock takeover**

Write a fake lock with a clearly-dead PID:

```cmd
echo {"pid": 999999, "started_at": "2020-01-01T00:00:00Z"} > .claude\.upstream-update.lock
python .claude/skills/agentic-z-update/update.py --check
```

Expected: warning about stale lock, then proceeds normally.

Cleanup:
```cmd
del .claude\.upstream-update.lock 2> nul
```

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/agentic-z-update/update.py
git commit -m "feat(agentic-z-update): wrap apply phase with PID-based lock"
```

---

## Task 9: Add search-index update check

**Files:**
- Modify: `.claude/skills/agentic-z-update/update.py`

- [ ] **Step 1: Add helpers for reading the local release tag + querying GitHub Releases**

Add near other helpers in update.py:

```python
import urllib.request
import urllib.error

SEARCH_INDEX_TAG_FILE = Path.home() / ".claude" / "dayz-search-index" / "release-tag.txt"
GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/DayZ-n-Chill/Agentic-Z/releases/latest"
SEARCH_INDEX_ASSET_PREFIX = "dayz-search-index-"


def installed_search_index_tag() -> Optional[str]:
    """Return the installed search-index release tag, or None if not present."""
    if not SEARCH_INDEX_TAG_FILE.exists():
        return None
    try:
        return SEARCH_INDEX_TAG_FILE.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def latest_search_index_tag() -> Optional[str]:
    """Query GitHub for the latest release that has a dayz-search-index-* asset.
    Returns None on any failure (offline, rate-limited, no matching asset)."""
    req = urllib.request.Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "agentic-z-update"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    assets = data.get("assets", [])
    for a in assets:
        name = a.get("name", "")
        if name.startswith(SEARCH_INDEX_ASSET_PREFIX):
            return data.get("tag_name")
    return None


def search_index_update_available() -> Optional[tuple[str, str]]:
    """Return (installed_tag, latest_tag) if a newer search index is available, else None."""
    installed = installed_search_index_tag()
    if not installed:
        return None  # User built locally or hasn't installed; nothing to suggest.
    latest = latest_search_index_tag()
    if not latest:
        return None  # API failed; silent skip.
    if latest == installed:
        return None
    # Best-effort SemVer-ish comparison: only suggest if latest sorts newer.
    if _is_newer(latest, installed):
        return (installed, latest)
    return None


def _is_newer(latest: str, installed: str) -> bool:
    """Naive tag comparison. Strips leading 'v' and compares dotted ints; falls back to string."""
    def parse(t: str) -> tuple:
        t = t.lstrip("v")
        parts = []
        for p in t.split("."):
            try:
                parts.append((0, int(p)))
            except ValueError:
                parts.append((1, p))
        return tuple(parts)
    try:
        return parse(latest) > parse(installed)
    except Exception:
        return latest != installed
```

- [ ] **Step 2: Inject the search-index check into `format_preview` output**

Modify the `format_preview` function. After the loop that lists drift entries, add (before the final `return`):

```python
    # Search-index update check — append if applicable.
    sidx = search_index_update_available()
    if sidx:
        installed, latest = sidx
        lines.append(f"  Search index: newer prebuilt available (you have {installed}, latest {latest})")
        lines.append("                Run /dayz-search-download to fetch separately.")
        lines.append("")
```

And modify the `quiet` branch at the top of `format_preview` to also surface index news:

```python
    if quiet:
        n = len(drift)
        n_conflict = sum(1 for s in drift.values() if s in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT))
        sidx = search_index_update_available()
        parts = []
        if n:
            if n_conflict:
                parts.append(f"{n} template change(s), {n_conflict} conflict(s)")
            else:
                parts.append(f"{n} template change(s)")
        if sidx:
            parts.append(f"new search index {sidx[1]}")
        if not parts:
            return ""
        return f"agentic-z: {' + '.join(parts)} available. Run /agentic-z-update or /dayz-search-download."
```

- [ ] **Step 3: Update `--check` exit code to also reflect search-index news**

In `main()`, find the `--check` block. Modify to consider both drift AND search-index:

```python
    if args.check:
        drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
        output = format_preview(drift, baseline_sha, upstream_sha, quiet=args.quiet)
        if output:
            print(output)
            return 1
        if not args.quiet:
            print("Up to date.")
        return 0
```

(format_preview now returns empty string when nothing's pending including search-index, so the existing logic still works.)

- [ ] **Step 4: Smoke-test the search-index check**

Run: `python .claude/skills/agentic-z-update/update.py --check`

Expected: if you have `~/.claude/dayz-search-index/release-tag.txt` with a tag that's older than what's on GitHub, the preview shows the search-index line. Otherwise it's silent.

To force-test: temporarily edit `release-tag.txt` to `v0.0.1`:

```cmd
echo v0.0.1 > %USERPROFILE%\.claude\dayz-search-index\release-tag.txt
python .claude/skills/agentic-z-update/update.py --check
```

Then restore:

```cmd
:: replace v0.X.Y with whatever was actually there
echo v0.X.Y > %USERPROFILE%\.claude\dayz-search-index\release-tag.txt
```

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/agentic-z-update/update.py
git commit -m "feat(agentic-z-update): check for newer search-index releases"
```

---

## Task 10: Add SessionStart hook to settings.json

**Files:**
- Modify: `.claude/settings.json`

- [ ] **Step 1: Read the current settings.json to find the existing `hooks` block**

Run: `cat .claude/settings.json`

Look for the existing `"hooks"` key (added when the `docs-sync` Stop hook was wired up).

- [ ] **Step 2: Add the SessionStart hook**

Edit `.claude/settings.json`. Find the `"hooks"` block:

```json
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/skills/docs-sync/sync.py\" --check --quiet",
            "timeout": 15
          }
        ]
      }
    ]
  }
```

Add a sibling key `SessionStart` so the block becomes:

```json
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/skills/agentic-z-update/update.py\" --check --quiet",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR/.claude/skills/docs-sync/sync.py\" --check --quiet",
            "timeout": 15
          }
        ]
      }
    ]
  }
```

- [ ] **Step 3: Validate JSON**

Run: `python -c "import json; print(json.load(open('.claude/settings.json'))['hooks'].keys())"`

Wait — `python -c` is denied in this repo. Instead:

Run: `python .claude/skills/sync-skills/sync.py --dry-run`

Expected: runs without complaint. The skill loads settings.json indirectly, so a JSON parse error would surface.

Or simpler: open the file in your editor and confirm the braces / brackets balance.

- [ ] **Step 4: Commit (don't restart Claude Code yet — verify first)**

```bash
git add .claude/settings.json
git commit -m "feat(agentic-z-update): add SessionStart hook for upstream-ahead nudge"
```

- [ ] **Step 5: Restart Claude Code (manual step) and verify**

The SessionStart hook only fires on a fresh session. Restart Claude Code in this repo, then on next session start you should see either silence (up to date) or a single line if upstream is ahead.

If the hook hangs or errors, check the hook output via `claude --debug` or remove the hook block temporarily.

---

## Task 11: Update SKILL.md

**Files:**
- Modify: `.claude/skills/agentic-z-update/SKILL.md`

- [ ] **Step 1: Read the current SKILL.md to understand the existing structure**

Run: `cat .claude/skills/agentic-z-update/SKILL.md`

- [ ] **Step 2: Add a "What's new" section near the top, right after the title**

Add this block after the `name:` / `description:` frontmatter and before the existing main content:

```markdown
## How updates work

This skill pulls template improvements (agents, skills, conventions, docs) from upstream `DayZ-n-Chill/Agentic-Z`'s `main` branch into your clone. Three guarantees:

1. **Your `workspace/` mod work is never touched.** Path scoping limits all changes to template-managed paths only.
2. **Your customizations to template files are not overwritten silently.** A three-way merge per file detects when both you and upstream edited the same file, and asks before doing anything destructive.
3. **No two updates can run at once.** A PID-based lock prevents concurrent invocations.

The first time you run this in a clone, it bootstraps the baseline (the SHA of upstream `main` at install time). From then on, every run compares (your local file) ↔ (the file at baseline) ↔ (upstream's current file) to decide what to do per file.

## Flags

| Flag | Behavior |
|---|---|
| (default) | Preview drift, prompt y/N, apply safe changes (conflicts left alone) |
| `--check` | Preview only; exits 1 if changes pending, 0 if up to date |
| `--quiet` | With `--check`: single-line output for hooks |
| `--yes` | Skip the confirmation prompt (CI / scripted use) |
| `--per-file` | Walk each conflict interactively: keep / take / diff / skip |
| `--force` | Override the dirty-tree check (existing) |
| `--dry-run` | Show preview, do not apply (existing) |
| `--no-sync` | Skip the post-merge `sync-skills` run (existing) |

## Per-file status meanings

| Status | What it means | Default action |
|---|---|---|
| `unchanged` | Your file matches upstream | nothing |
| `safe-overwrite` | You didn't edit, upstream did | apply upstream |
| `new` | New file from upstream | apply upstream |
| `local-only-edit` | Only you edited it (upstream unchanged) | leave alone |
| `conflict` | Both you and upstream edited it | leave alone (use `--per-file` to resolve) |
| `deleted-clean` | Upstream removed it, you didn't customize | delete |
| `deleted-conflict` | Upstream removed it, you customized it | leave alone |

## Files this skill creates

- `.claude/.upstream-baseline` — SHA of last upstream merge. Gitignored.
- `.claude/.upstream-update.lock` — concurrency lock during apply phase. Gitignored.

## SessionStart hook

A `SessionStart` hook runs `update.py --check --quiet` at the start of every Claude Code session in this repo. It prints a one-line nudge if upstream is ahead OR if a newer prebuilt search index is available. Silent on no-change. Configured in `.claude/settings.json`.

To disable temporarily: comment out the `SessionStart` block in `.claude/settings.json`.

## Search index notification

If you previously ran `/dayz-search-download`, this skill ALSO checks whether the GitHub release you installed has been superseded. The check is read-only — it never auto-downloads (the index is ~200MB). Just nudges you to run `/dayz-search-download` when a newer release ships.

To skip the check: ensure `~/.claude/dayz-search-index/release-tag.txt` doesn't exist (the check is silent when no installed tag is recorded).
```

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/agentic-z-update/SKILL.md
git commit -m "docs(agentic-z-update): document new flags + hook + search-index check"
```

---

## Task 12: Final integration smoke test + push

**Files:** none modified — verification only.

- [ ] **Step 1: Run all unit tests one final time**

Run: `python .claude/skills/agentic-z-update/test_update.py`

Expected: all 16+ tests pass. If any fail, fix before push.

- [ ] **Step 2: Run `--check` against the real repo**

Run: `python .claude/skills/agentic-z-update/update.py --check`

Expected: either "Up to date." or a structured preview block. No tracebacks.

- [ ] **Step 3: Run `--check --quiet` and verify it matches hook expectations**

Run: `python .claude/skills/agentic-z-update/update.py --check --quiet`

Expected: silent OR a single line beginning with `agentic-z:`.

- [ ] **Step 4: Verify the SessionStart hook behaves on a fresh shell**

Open a fresh PowerShell or cmd. From the repo root, run the exact command the hook would run:

```cmd
python .claude\skills\agentic-z-update\update.py --check --quiet
```

Expected: completes in < 2 seconds. No tracebacks. Output matches step 3.

- [ ] **Step 5: Push the branch**

```bash
git push origin feat/auto-update
```

- [ ] **Step 6: (Optional) Dispatch superpowers:code-reviewer for an independent audit**

If you want a fresh-context review of the implementation before opening a PR to develop, dispatch `superpowers:code-reviewer` with a prompt summarizing the spec and pointing at the files in this branch. Apply any flagged issues before opening the PR.

- [ ] **Step 7: Open a PR targeting develop (not main)**

Either via the GitHub web URL `https://github.com/DayZ-n-Chill-Z/Agentic-Z/compare/develop...feat/auto-update?quick_pull=1` (paste the spec doc URL in the body), or via `gh pr create --base develop` if `gh` is set up.

---

## Self-review checklist (run by the planning author)

After writing this plan, the writing-plans skill instructs the author to verify the plan against the spec with fresh eyes:

- **Spec coverage:** every Section 1-5 piece of the spec maps to a task: classify (Task 2), baseline+lock helpers (Task 3), drift compute (Task 4), `--check` (Task 5), prompt+apply (Task 6), `--yes`/`--per-file` (Task 7), lock acquire (Task 8), search-index check (Task 9), hook (Task 10), docs (Task 11). ✓
- **Placeholder scan:** no TBD/TODO/"add error handling" entries. Code blocks contain real code. ✓
- **Type consistency:** `FileStatus` enum used the same way in update.py and test_update.py. `compute_drift`, `apply_drift`, `format_preview`, `acquire_lock`, `release_lock` signatures match across tasks. ✓
- **Ambiguity:** lock rule is single-sourced (PID liveness only, no age threshold). Per-file status meanings table is in both spec and SKILL.md docs.
