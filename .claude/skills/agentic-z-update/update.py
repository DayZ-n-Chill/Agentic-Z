"""Pull Agentic-Z template updates from upstream into the current clone.

What it touches (TEMPLATE_PATHS):
    agents/, skills/, .claude/agents/, .claude/skills/, .claude/mcp/, .claude/settings.json
    .claude-plugin/, .mcp.json, hooks/, mods/, evals/
    docs/, scripts/
    .claude/CLAUDE.md, AGENTS.md, GEMINI.md, README.md, CONTRIBUTING.md, LICENSE
    .gitignore, pytest.ini, .env.example, package.json, package-lock.json, .github/
    .markdownlint.json, .markdownlint-cli2.jsonc, .markdownlintignore

What it leaves alone:
    workspace/, output/, .claude/local-memory/, .claude/settings.local.json, .env

Applied changes are committed automatically as
"chore: pull Agentic-Z upstream (<sha8>)".

Usage:
    python update.py [--check [--quiet]] [--yes] [--per-file] [--force] [--dry-run] [--no-sync]
"""
from __future__ import annotations

import argparse
import datetime
import enum
import http.client
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Iterable, Optional

UPSTREAM_URL = "https://github.com/DayZ-n-Chill/Agentic-Z.git"
UPSTREAM_REMOTE = "upstream"
UPSTREAM_BRANCH = "main"

# Paths (relative to repo root) that get pulled from upstream. Anything outside
# this list is left alone.
TEMPLATE_PATHS = [
    "agents",
    "skills",
    ".claude/agents",
    ".claude/skills",
    ".claude/mcp",
    ".claude/settings.json",
    ".claude-plugin",
    ".mcp.json",
    "hooks",
    "mods",
    "evals",
    "docs",
    "scripts",
    ".claude/CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    "README.md",
    ".gitignore",
    "pytest.ini",
    ".env.example",
    "package.json",
    "package-lock.json",
    ".github",
    "CONTRIBUTING.md",
    "LICENSE",
    ".markdownlint.json",
    ".markdownlint-cli2.jsonc",
    ".markdownlintignore",
]


class FileStatus(enum.Enum):
    UNCHANGED = "unchanged"          # no-op
    SAFE_OVERWRITE = "safe-overwrite"  # local == baseline, take upstream
    NEW = "new"                       # baseline + local missing, take upstream
    LOCALLY_DELETED = "locally-deleted"  # in baseline, missing locally, leave alone
    LOCAL_ONLY_EDIT = "local-only-edit"  # only the user changed it, leave alone
    CONFLICT = "conflict"             # both diverged, ask user
    DELETED_CLEAN = "deleted-clean"   # local == baseline, upstream gone, delete OK
    DELETED_CONFLICT = "deleted-conflict"  # local diverged, upstream gone, ask user


def classify_per_file(
    baseline: Optional[bytes | str],
    local: Optional[bytes | str],
    upstream: Optional[bytes | str],
) -> FileStatus:
    """Three-way classification for a single template file.

    Each argument is the file's content or git blob id at that revision; None
    means "file does not exist at that revision".
    Returns a FileStatus enum value indicating what action (if any) to take.
    """
    # Defensive: nothing exists anywhere.
    if local is None and upstream is None and baseline is None:
        return FileStatus.UNCHANGED

    # Upstream removed the file (or never had it).
    if upstream is None:
        if local is None:
            # Already gone locally too; nothing to do.
            return FileStatus.UNCHANGED
        if baseline is None:
            # Upstream never had it and neither does baseline → user-created file, leave alone.
            return FileStatus.LOCAL_ONLY_EDIT
        if local == baseline:
            return FileStatus.DELETED_CLEAN
        return FileStatus.DELETED_CONFLICT

    # Upstream has the file.
    if local is None:
        # Baseline also missing: the clone never had it, so it is new upstream.
        # Baseline had it: the user deleted it, which is left alone by default.
        return FileStatus.NEW if baseline is None else FileStatus.LOCALLY_DELETED

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


_QUIET = False


def log(level: str, msg: str) -> None:
    if _QUIET:
        return
    print(f"[{level}]\t{msg}", flush=True)


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )


def repo_root() -> Optional[Path]:
    """Top level of the enclosing git work tree, or None outside a repo (or without git)."""
    try:
        r = run(["git", "rev-parse", "--show-toplevel"], check=False, capture=True)
    except FileNotFoundError:
        return None
    top = r.stdout.strip()
    return Path(top) if r.returncode == 0 and top else None


def working_tree_clean_for(paths: list[str]) -> tuple[bool, list[str]]:
    """Check if any tracked file under the given paths has uncommitted changes.

    Untracked files are ignored (--untracked-files=no): a skill the user just
    added is classified local-only-edit and left alone, and an untracked file at
    a path upstream adds is a conflict, so neither needs the gate. -z keeps
    non-ASCII paths verbatim instead of octal-escaped; git writes them as UTF-8.
    """
    r = subprocess.run(
        ["git", "status", "--porcelain", "-z", "--untracked-files=no", "--", *paths],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    # Each -z entry is `XY path`; a rename or copy is followed by its original path.
    entries = r.stdout.split("\0")
    dirty: list[str] = []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) <= 3:
            continue
        dirty.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            i += 1
    return not dirty, dirty


def remote_url(name: str) -> str | None:
    r = run(["git", "remote", "get-url", name], check=False, capture=True)
    return r.stdout.strip() if r.returncode == 0 else None


def normalize_remote_url(url: str) -> str:
    """Compare-ready form of a GitHub https URL: case-folded, no trailing '/' or '.git'."""
    return url.strip().rstrip("/").casefold().removesuffix(".git")


def ensure_upstream() -> bool:
    existing = remote_url(UPSTREAM_REMOTE)
    if existing is None:
        log("INFO", f"Adding {UPSTREAM_REMOTE} remote = {UPSTREAM_URL}")
        try:
            run(["git", "remote", "add", UPSTREAM_REMOTE, UPSTREAM_URL], capture=True)
        except subprocess.CalledProcessError as e:
            # Return False instead of raising so --check --quiet (the SessionStart
            # hook) still prints its one line and exits 0.
            detail = (e.stderr or "").strip().splitlines()
            log("ERR", f"git remote add {UPSTREAM_REMOTE} failed: {detail[-1] if detail else e}")
            log("ERR", f"Fix: git remote add {UPSTREAM_REMOTE} {UPSTREAM_URL}")
            return False
        return True
    if normalize_remote_url(existing) != normalize_remote_url(UPSTREAM_URL):
        log("ERR", f"upstream remote points to {existing}, expected {UPSTREAM_URL}")
        log("ERR", f"Fix: git remote set-url {UPSTREAM_REMOTE} {UPSTREAM_URL}")
        return False
    log("OK", f"upstream remote already set: {existing}")
    return True


def fetch_upstream() -> bool:
    log("INFO", f"Fetching {UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}...")
    # In quiet mode (SessionStart hook), suppress git's "From <url> ... -> FETCH_HEAD"
    # progress line that goes to stderr. Capture both streams; surface only on failure.
    if _QUIET:
        r = subprocess.run(
            ["git", "fetch", UPSTREAM_REMOTE, UPSTREAM_BRANCH],
            check=False, capture_output=True, text=True,
        )
    else:
        r = run(["git", "fetch", UPSTREAM_REMOTE, UPSTREAM_BRANCH], check=False)
    return r.returncode == 0


def git_show_blob(ref: str, path: str) -> Optional[bytes]:
    """Return the bytes of `path` at git ref `ref`, or None if it doesn't exist there."""
    r = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        check=False,
        capture_output=True,
    )
    if r.returncode != 0:
        return None
    return r.stdout


def tree_object_ids(ref: str) -> dict[str, str]:
    """{path: object id} for every template file at `ref`, from one `git ls-tree`.

    One git process per revision instead of one per file: at about 50 ms per git
    call on Windows, a per-file lookup of a few hundred drifted files runs past
    the SessionStart hook's timeout. An unknown ref gives {} (every file missing).
    """
    r = subprocess.run(
        ["git", "ls-tree", "-r", "-z", ref, "--", *TEMPLATE_PATHS],
        check=False, capture_output=True, text=True, encoding="utf-8",
    )
    if r.returncode != 0:
        return {}
    ids: dict[str, str] = {}
    for entry in r.stdout.split("\0"):
        meta, sep, path = entry.partition("\t")  # "<mode> <type> <id>\t<path>"
        if sep:
            ids[path] = meta.split()[2]
    return ids


def _c_quote(path: str) -> str:
    """Quote a path the way `git hash-object --stdin-paths` unquotes it, so a
    name holding a newline, a quote or a backslash still reads as one path."""
    escaped = (path.replace("\\", "\\\\").replace('"', '\\"')
               .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))
    return f'"{escaped}"'


def working_tree_object_ids(paths: Iterable[str]) -> dict[str, str]:
    """{path: blob id} for each path that is a file on disk; missing files are left out.

    Hashes every file in one `git hash-object --stdin-paths` call. Each file is
    hashed as if added at its own path, so the same clean filters as `git add`
    apply (core.autocrlf, .gitattributes eol): comparing ids instead of raw bytes
    keeps a CRLF checkout of an untouched LF file from looking like a local edit.
    If the batch fails (a file vanished mid-run), each file is hashed on its own.
    """
    files = [p for p in paths if Path(p).is_file()]
    if not files:
        return {}
    r = subprocess.run(
        ["git", "hash-object", "--stdin-paths"],
        input="".join(_c_quote(p) + "\n" for p in files),
        check=False, capture_output=True, text=True, encoding="utf-8",
    )
    ids = r.stdout.split()
    if r.returncode == 0 and len(ids) == len(files):
        return dict(zip(files, ids))
    result: dict[str, str] = {}
    for p in files:
        one = subprocess.run(
            ["git", "hash-object", f"--path={p}", "--", p],
            check=False, capture_output=True, text=True,
        )
        if one.returncode == 0 and one.stdout.strip():
            result[p] = one.stdout.strip()
    return result


def _candidate_paths(baseline_sha: str, upstream_ref: str) -> set[str]:
    """Files that COULD have a non-UNCHANGED status. Everything else is guaranteed
    identical across baseline / local / upstream and can be skipped without classifying.

    Three sources combined:
      1. git diff baseline..upstream  (template files changed between baseline and upstream)
      2. git diff baseline..HEAD       (template files changed locally since baseline, committed)
      3. git status --porcelain        (uncommitted local edits + untracked files)
    """
    candidates: set[str] = set()

    # -z keeps paths verbatim: without it git quotes and octal-escapes any path
    # with non-ASCII characters (core.quotePath), which names no real file.
    # Git writes paths as UTF-8, so decode as UTF-8, not the Windows code page.
    def git_z(*args: str) -> Optional[list[str]]:
        r = subprocess.run(
            ["git", *args], check=False, capture_output=True, text=True, encoding="utf-8",
        )
        return r.stdout.split("\0") if r.returncode == 0 else None

    def diff_pair(left: str, right: str) -> None:
        for path in git_z("diff", "--name-only", "-z", left, right, "--", *TEMPLATE_PATHS) or []:
            if path:
                candidates.add(path)

    if baseline_sha != upstream_ref:
        diff_pair(baseline_sha, upstream_ref)
    diff_pair(baseline_sha, "HEAD")

    # Uncommitted + untracked. Each -z entry is `XY path`; a rename or copy
    # (R or C in XY) is followed by one more entry holding the original path.
    entries = git_z("status", "--porcelain", "-z", "--untracked-files=all", "--", *TEMPLATE_PATHS) or []
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) <= 3:
            continue
        candidates.add(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            if i < len(entries) and entries[i]:
                candidates.add(entries[i])
            i += 1

    return candidates


def compute_drift(baseline_sha: Optional[str], upstream_ref: str) -> dict[str, FileStatus]:
    """Return a {path: FileStatus} dict for every template file with non-UNCHANGED status.

    Optimized to only classify files that COULD have changed between any of the three
    revisions (baseline, working tree, upstream). Common case after a fresh pull is
    "no candidates" → returns empty dict in well under a second.

    If baseline_sha is None (first run), bootstrap with baseline = upstream so
    SAFE_OVERWRITE never fires until the user has a real baseline recorded.
    """
    if baseline_sha is None:
        # Bootstrap: pretend baseline IS upstream. No drift surfaces this run.
        baseline_sha = upstream_ref

    candidates = _candidate_paths(baseline_sha, upstream_ref)
    if not candidates:
        return {}
    # A fixed number of git calls however many files drifted (see tree_object_ids).
    baseline_ids = tree_object_ids(baseline_sha)
    upstream_ids = baseline_ids if upstream_ref == baseline_sha else tree_object_ids(upstream_ref)
    local_ids = working_tree_object_ids(sorted(candidates))
    result: dict[str, FileStatus] = {}
    for path in sorted(candidates):
        status = classify_per_file(
            baseline=baseline_ids.get(path),
            local=local_ids.get(path),
            upstream=upstream_ids.get(path),
        )
        if status != FileStatus.UNCHANGED:
            result[path] = status
    # A baseline file missing locally counts as deleted by the user only if this
    # clone ever tracked it. An older updater (one without agents/ and skills/ in
    # TEMPLATE_PATHS) can advance the baseline past files it never pulled; those
    # are new to this clone, not deleted from it.
    missing = [p for p, s in result.items() if s == FileStatus.LOCALLY_DELETED]
    if missing:
        r = subprocess.run(
            ["git", "log", "--format=", "--name-only", "--no-renames", "-z", "HEAD", "--", *TEMPLATE_PATHS],
            check=False, capture_output=True, text=True, encoding="utf-8",
        )
        if r.returncode == 0:
            ever_tracked = set(r.stdout.replace("\n", "\0").split("\0"))
            for path in missing:
                if path not in ever_tracked:
                    result[path] = FileStatus.NEW
    return result


def stage_and_commit(updated: list[str], upstream_sha: str) -> bool:
    """Stage the updated paths and commit only them.

    `git commit --only` keeps anything else the user had staged out of the
    update commit; it stays staged afterwards. The paths go to git on stdin
    (--pathspec-from-file), not the command line: a large first update lists
    hundreds of paths, which would pass Windows' ~32,000 character command-line
    limit. --literal-pathspecs keeps a name holding '*' or '[' to that one file.
    """
    pathspec = "".join(p + "\0" for p in updated)

    def git_with_paths(*args: str) -> int:
        return subprocess.run(
            ["git", "--literal-pathspecs", *args, "--pathspec-from-file=-", "--pathspec-file-nul"],
            input=pathspec, check=False, text=True, encoding="utf-8",
        ).returncode

    if git_with_paths("add") != 0:
        return False
    # Skip commit if nothing actually changed in the applied paths.
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
        check=False, capture_output=True, text=True, encoding="utf-8",
    )
    if staged.returncode == 0 and not set(updated) & set(staged.stdout.split("\0")):
        log("OK", "no template changes to commit (working tree already matches upstream)")
        return True
    msg = f"chore: pull Agentic-Z upstream ({upstream_sha[:8]})"
    if git_with_paths("commit", "--only", "-m", msg) != 0:
        log("WARN", "commit failed; staged changes left in index for manual handling")
        return False
    log("OK", f"committed: {msg}")
    return True


# Marker files git leaves in the git dir while an operation is half done.
# During any of these, `git commit --only` refuses, which would leave the
# applied files staged inside the user's operation.
GIT_OPERATION_MARKERS = (
    ("MERGE_HEAD", "merge"),
    ("rebase-merge", "rebase"),
    ("rebase-apply", "rebase"),
    ("CHERRY_PICK_HEAD", "cherry-pick"),
    ("REVERT_HEAD", "revert"),
)


def git_operation_in_progress() -> Optional[str]:
    """Name of the merge, rebase, cherry-pick or revert in progress, or None."""
    for marker, name in GIT_OPERATION_MARKERS:
        r = run(["git", "rev-parse", "--git-path", marker], check=False, capture=True)
        if r.returncode == 0 and r.stdout.strip() and Path(r.stdout.strip()).exists():
            return name
    return None


def upstream_head_sha() -> str:
    r = run(["git", "rev-parse", f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"], capture=True)
    return r.stdout.strip()


def merge_base_sha() -> Optional[str]:
    """The commit this clone shares with upstream main, or None with no shared history."""
    r = run(["git", "merge-base", "HEAD", f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"], check=False, capture=True)
    sha = r.stdout.strip()
    return sha if r.returncode == 0 and sha else None


def run_sync_skills() -> None:
    sync_script = Path(".claude/skills/sync-skills/sync.py")
    if not sync_script.exists():
        log("WARN", f"sync-skills script not found at {sync_script}; skipping")
        return
    log("INFO", "re-running /sync-skills to link new skills into agent CLI homes")
    r = run([sys.executable, str(sync_script)], check=False)
    if r.returncode != 0:
        log("WARN", "sync-skills returned non-zero; review its output above")


BASELINE_FILE = Path(".claude/.upstream-baseline")
LOCK_FILE = Path(".claude/.upstream-update.lock")
# Held for a moment while one run replaces a stale lock, so two runs that both
# found the same dead-PID lock cannot both replace it.
LOCK_TAKEOVER_FILE = Path(".claude/.upstream-update.lock.takeover")


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
    tmp = BASELINE_FILE.with_suffix(".tmp")
    tmp.write_text(sha.strip() + "\n", encoding="utf-8")
    tmp.replace(BASELINE_FILE)


def _pid_alive(pid: int) -> bool:
    """Return True if a process with this PID is still running. Cross-platform best-effort."""
    if pid <= 0:
        return False
    if os.name == "nt":
        # Windows: use tasklist as a portable check.
        # CSV output quotes the PID column ("1234") so we match the quoted form
        # to avoid substring collisions (e.g. PID 123 matching inside "1234").
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
            capture_output=True, text=True,
        )
        return f'"{pid}"' in (r.stdout or "")
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
    """Create the lock file with this process's PID and an ISO timestamp.

    The payload is written to a private temp file first and then hard-linked to
    the lock path. Linking fails with FileExistsError when the lock exists, so
    creating it is atomic (exactly one of two racing updates succeeds) and the
    lock is never visible half-written, where another run would read it as
    unreadable and therefore stale. On a filesystem without hard links it falls
    back to an O_CREAT | O_EXCL create, which is still exclusive.
    """
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({
        "pid": os.getpid(),
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    })
    tmp = LOCK_FILE.with_name(f"{LOCK_FILE.name}.{os.getpid()}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.link(tmp, LOCK_FILE)
    except FileExistsError:
        raise
    except OSError:
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
    finally:
        tmp.unlink(missing_ok=True)


def release_lock() -> None:
    """Best-effort lock removal; ignores missing file."""
    try:
        LOCK_FILE.unlink()
    except (FileNotFoundError, OSError):
        pass


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
    Returns None on any failure (offline, rate-limited, dropped connection,
    malformed reply, no matching asset)."""
    req = urllib.request.Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "agentic-z-update"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    # OSError covers URLError, timeouts, ssl.SSLError and connection resets
    # (http.client.RemoteDisconnected); HTTPException covers IncompleteRead;
    # ValueError covers bad JSON and bad UTF-8.
    except (OSError, http.client.HTTPException, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    tag = data.get("tag_name")
    assets = data.get("assets")
    if not isinstance(tag, str) or not isinstance(assets, list):
        return None
    for a in assets:
        if isinstance(a, dict) and str(a.get("name", "")).startswith(SEARCH_INDEX_ASSET_PREFIX):
            return tag
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
    """Naive tag comparison: strip a leading 'v', compare dot-separated parts.

    Numeric parts compare as ints and sort before non-numeric parts, which
    compare as strings, so an int is never compared against a str.
    """
    def parse(t: str) -> tuple:
        t = t.lstrip("v")
        parts = []
        for p in t.split("."):
            try:
                parts.append((0, int(p)))
            except ValueError:
                parts.append((1, p))
        return tuple(parts)
    return parse(latest) > parse(installed)


def format_preview(drift: dict[str, FileStatus], baseline_sha: Optional[str], upstream_sha: str, quiet: bool = False) -> str:
    """Format a drift dict into preview output. `quiet=True` returns a one-liner suitable for hooks."""
    sidx = search_index_update_available()

    if quiet:
        n = len(drift)
        n_conflict = sum(1 for s in drift.values() if s in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT))
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
        runs = []
        if n:
            runs.append("/agentic-z-update")
        if sidx:
            runs.append("/dayz-search-download")
        return f"agentic-z: {' + '.join(parts)} available. Run {' and '.join(runs)}."

    if not drift and not sidx:
        return ""

    by_status: dict[FileStatus, list[str]] = {}
    for path, status in drift.items():
        by_status.setdefault(status, []).append(path)

    lines = []
    baseline_label = baseline_sha[:7] if baseline_sha else "first-run"
    lines.append(f"Agentic-Z update preview (upstream: {upstream_sha[:7]}, baseline: {baseline_label})")
    lines.append("")

    # Order matters: safe stuff first, conflicts last.
    order = [
        (FileStatus.SAFE_OVERWRITE, "safe to apply"),
        (FileStatus.NEW, "new files added"),
        (FileStatus.DELETED_CLEAN, "deletions (clean)"),
        (FileStatus.LOCAL_ONLY_EDIT, "your local-only edits (left alone)"),
        (FileStatus.LOCALLY_DELETED, "deleted in this clone (left alone; --per-file to restore)"),
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

    # Search-index update check — append if applicable.
    if sidx:
        installed, latest = sidx
        lines.append(f"  Search index: newer prebuilt available (you have {installed}, latest {latest})")
        lines.append("                Run /dayz-search-download to fetch separately.")
        lines.append("")

    return "\n".join(lines)


# Statuses walked by --per-file. Without a "take" choice they are left alone.
PER_FILE_STATUSES = (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT, FileStatus.LOCALLY_DELETED)

# Local choices with no upstream change to bring in: they do not hold the
# baseline back and do not count as pending changes for --check.
LOCAL_CHOICE_STATUSES = (FileStatus.LOCAL_ONLY_EDIT, FileStatus.LOCALLY_DELETED)


def apply_drift(drift: dict[str, FileStatus], upstream_ref: str, conflict_choices: Optional[dict[str, str]] = None) -> tuple[list[str], list[str]]:
    """Apply changes from a drift dict.

    `conflict_choices` is an optional {path: 'keep'|'take'|'skip'} dict for
    resolving conflicts. Paths missing from conflict_choices are LEFT ALONE
    (default bulk-apply behavior).

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
        elif status in PER_FILE_STATUSES:
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
                # 'keep', 'skip' or no choice: leave alone
                skipped.append(path)
    return applied, skipped


def _print_diff(path: str, local: bytes, upstream: bytes) -> None:
    """Print a unified diff between two byte blobs."""
    import difflib
    try:
        local_text = local.decode("utf-8").splitlines(keepends=True)
        upstream_text = upstream.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        print("    (binary file, no diff)")
        return
    diff = difflib.unified_diff(
        local_text, upstream_text,
        fromfile=f"a/{path} (yours)",
        tofile=f"b/{path} (upstream)",
        n=3,
    )
    sys.stdout.writelines(diff)
    print()


def resolve_conflicts_per_file(drift: dict[str, FileStatus], upstream_ref: str) -> dict[str, str]:
    """Walk each conflict and locally deleted file interactively.

    Returns a {path: 'keep'|'take'|'skip'} dict. For a locally deleted file,
    keep leaves it deleted and take restores upstream's version. 'keep' is a
    decision (the baseline may move past the file); 'skip' defers it, so the
    file is offered again on the next run.
    """
    choices: dict[str, str] = {}
    conflicts = [p for p, s in drift.items() if s in PER_FILE_STATUSES]
    if not conflicts:
        return choices

    print()
    print(f"Walking {len(conflicts)} file(s). For each: k=keep mine, t=take upstream, d=diff, s=skip (decide later).")
    print("For a locally-deleted file, keep leaves it deleted and take restores it.")
    for path in conflicts:
        while True:
            try:
                ans = input(f"  {path} [k/t/d/s]: ").strip().lower()
            except EOFError:
                log("WARN", f"non-interactive; skipping {path} (offered again next run)")
                choices[path] = "skip"
                break
            if ans in ("k", "keep"):
                choices[path] = "keep"
                break
            if ans in ("s", "skip", ""):
                choices[path] = "skip"
                break
            if ans in ("t", "take"):
                choices[path] = "take"
                break
            if ans in ("d", "diff"):
                # Show a unified diff for the user.
                local = Path(path).read_bytes() if Path(path).exists() else b""
                upstream_blob = git_show_blob(upstream_ref, path) or b""
                _print_diff(path, local, upstream_blob)
                # Re-prompt after diff
                continue
            print("    invalid choice; try k/t/d/s")
    return choices


def per_file_command() -> str:
    """The --per-file rerun command, runnable from the cwd (main() has chdir'd to the repo root)."""
    script = Path(__file__).resolve()
    try:
        shown = script.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        shown = str(script)
    return f'python "{shown}" --per-file'


def finish_apply(
    drift: dict[str, FileStatus],
    applied: list[str],
    skipped: list[str],
    upstream_sha: str,
    kept: Iterable[str] = (),
) -> str:
    """Commit the applied paths, then advance the baseline only when that is safe.

    The baseline moves to upstream_sha only when the commit succeeded (or there
    was nothing to commit) and no path that still needs upstream's version was
    left behind: an unresolved conflict, or a safe/new/deleted path whose apply
    failed. Advancing past such a path would make the next run misclassify it
    and silently drop upstream's change. Paths in `kept` were explicitly kept
    in --per-file, so they do not hold the baseline back; after the advance
    they classify as local-only-edit.

    Returns "advanced" (baseline moved), "pending" (unapplied upstream changes
    remain) or "commit-failed" (git commit failed; changes left staged).
    """
    committed = stage_and_commit(applied, upstream_sha) if applied else True
    kept = set(kept)
    pending = [p for p in skipped if drift.get(p) not in LOCAL_CHOICE_STATUSES and p not in kept]
    if not committed:
        log("WARN", "Baseline not updated: the commit failed. Commit the staged files, then rerun.")
        return "commit-failed"
    if pending:
        log("WARN", "Baseline not updated: some upstream changes are still unapplied; rerun after resolving them.")
        return "pending"
    write_baseline(upstream_sha)
    log("OK", "Baseline updated.")
    return "advanced"


def _read_lock_bytes() -> Optional[bytes]:
    """Return the lock file's raw bytes, or None if there is no lock."""
    try:
        return LOCK_FILE.read_bytes()
    except FileNotFoundError:
        return None


def _remove_stale_lock(seen: bytes) -> str:
    """Remove the lock only if it still holds `seen`, the bytes judged stale.

    Runs under LOCK_TAKEOVER_FILE (created exclusively), so only one run at a
    time can replace a stale lock. Re-reading under that guard stops a run that
    read the stale lock earlier from deleting the fresh lock another run has
    just created in its place. Returns "removed", "changed" (the lock is no
    longer the stale one; re-check it) or "busy" (another run is taking over).
    """
    try:
        fd = os.open(LOCK_TAKEOVER_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return "busy"
    try:
        os.write(fd, str(os.getpid()).encode("ascii"))
        os.close(fd)
        if _read_lock_bytes() != seen:
            return "changed"
        LOCK_FILE.unlink(missing_ok=True)
        return "removed"
    finally:
        LOCK_TAKEOVER_FILE.unlink(missing_ok=True)


def acquire_lock() -> bool:
    """Acquire the update lock. Returns True if acquired, False if another live process holds it.

    The lock file is created atomically (see write_lock). A stale lock (PID dead
    or unreadable) is replaced through _remove_stale_lock, so when two runs find
    the same stale lock only one of them ends up holding the new one.
    """
    for _attempt in range(3):
        try:
            write_lock()
            return True
        except FileExistsError:
            pass
        seen = _read_lock_bytes()
        if seen is None:
            continue  # Released between our create and our read; try again.
        try:
            existing = json.loads(seen.decode("utf-8"))
            pid = int(existing.get("pid", 0))
        except (ValueError, TypeError, AttributeError):
            existing, pid = {}, 0
        if pid > 0 and _pid_alive(pid):
            log("FAIL", f"Another update is running (PID {pid}, started {existing.get('started_at', '?')}).")
            log("FAIL", "If you're sure it's stuck, delete .claude/.upstream-update.lock")
            return False
        result = _remove_stale_lock(seen)
        if result == "busy":
            log("FAIL", "Another update is taking over a stale lock right now. Rerun in a moment.")
            log("FAIL", "If this repeats, delete .claude/.upstream-update.lock.takeover")
            return False
        if result == "removed":
            log("WARN", f"Found stale lock from dead PID {pid}; taking over.")
    log("FAIL", "Could not take the update lock; another update grabbed it first.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull Agentic-Z upstream template updates.")
    parser.add_argument("--force", action="store_true", help="Skip the dirty-tree check.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change; apply nothing.")
    parser.add_argument("--no-sync", action="store_true", help="Skip the post-update sync-skills run.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Preview drift only: fetches upstream (adding the upstream remote if it is missing) and writes no files. Exits 1 if upstream changes are pending or no baseline exists yet, 0 if up to date (always 0 with --quiet).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="With --check: silent on no-change, single line on drift or setup problem, always exits 0. Used by SessionStart hook. Rejected without --check.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the apply confirmation prompt (CI / scripted use).",
    )
    parser.add_argument(
        "--per-file",
        action="store_true",
        help="Walk each conflict and locally-deleted file interactively: keep / take / diff / skip.",
    )
    args = parser.parse_args()
    if args.quiet and not args.check:
        parser.error("--quiet only works with --check")

    # Quiet mode (used by SessionStart hook): suppress all log() output and
    # capture git fetch's stderr. Only the final preview line (or nothing) prints.
    global _QUIET
    if args.quiet:
        _QUIET = True

    if not args.check and not args.quiet:
        print("Agentic-Z update")
        print()

    root = repo_root()
    if root is None:
        if args.quiet:
            # Hook: log() is muted, so print one line and exit 0 so it shows.
            print("agentic-z: not a git repo, update check skipped. Run /agentic-z-update from inside an Agentic-Z clone.")
            return 0
        log("ERR", "Not a git repo. Run from inside an Agentic-Z clone.")
        return 1
    # Template paths, the baseline and the lock are all relative to the repo root.
    os.chdir(root)

    # Checked before the dirty-tree gate: a merge leaves template paths dirty,
    # and that message's "--force" advice would not get past this refusal.
    if not args.check and not args.dry_run:
        op = git_operation_in_progress()
        if op:
            log("ERR", f"A git {op} is in progress. Finish or abort it first (git {op} --continue or --abort), then rerun.")
            return 1

    if not args.force and not args.check:
        clean, dirty = working_tree_clean_for(TEMPLATE_PATHS)
        if not clean:
            log("ERR", "Working tree has uncommitted changes in template paths:")
            for p in dirty:
                print(f"      {p}")
            log("ERR", "Commit or stash, or pass --force to override.")
            return 1

    if not ensure_upstream():
        if args.quiet:
            existing = remote_url(UPSTREAM_REMOTE)
            if existing is None:
                print(
                    f"agentic-z: could not add the {UPSTREAM_REMOTE} remote; "
                    f"run git remote add {UPSTREAM_REMOTE} {UPSTREAM_URL}"
                )
            else:
                print(
                    f"agentic-z: upstream remote points to {existing}; "
                    f"run git remote set-url {UPSTREAM_REMOTE} {UPSTREAM_URL}"
                )
            return 0
        return 1

    if not fetch_upstream():
        if args.check and args.quiet:
            # Hook: fail silently on network issues.
            return 0
        log("ERR", "git fetch failed. Network issue or upstream unreachable.")
        return 1

    upstream_sha = upstream_head_sha()
    baseline_sha = read_baseline()

    if args.check:
        # Read-only: --check never writes the baseline. Without one there is
        # nothing to compare against, so say so instead of reporting "Up to date".
        # With --quiet (the SessionStart hook) the nudge exits 0: Claude Code drops
        # plain stdout from a hook that exits non-zero, so the nudge would never show.
        if baseline_sha is None:
            print("agentic-z: no update baseline recorded yet. Run /agentic-z-update once to initialize it.")
            return 0 if args.quiet else 1
        drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
        drift = {p: st for p, st in drift.items() if st not in LOCAL_CHOICE_STATUSES}
        output = format_preview(drift, baseline_sha, upstream_sha, quiet=args.quiet)
        if output:
            print(output)
            return 0 if args.quiet else 1  # drift exists
        if not args.quiet:
            print("Up to date.")
        return 0

    # First run: record the commit the clone was made from (its merge base with
    # upstream main) as the baseline, so upstream changes made since the clone
    # are offered. A copy with no shared history ("Use this template") records
    # upstream HEAD instead, so nothing is overwritten or added on this run: a
    # template file missing locally is in the baseline, so it classifies as
    # locally-deleted and stays deleted unless restored with --per-file.
    # --dry-run previews against that same baseline but does not write it, so
    # its preview matches what the real first run would offer.
    if baseline_sha is None and args.dry_run:
        baseline_sha = merge_base_sha() or upstream_sha
    elif baseline_sha is None:
        if not acquire_lock():
            return 1
        first = merge_base_sha() or upstream_sha
        try:
            write_baseline(first)
        finally:
            release_lock()
        baseline_sha = first
        if first == upstream_sha:
            log("OK", f"Baseline initialized at upstream {upstream_sha[:7]}.")
        else:
            log("OK", f"Baseline initialized at {first[:7]}, the commit this clone shares with upstream.")

    # Default flow: preview, prompt, apply.
    drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
    # Local choices bring nothing in from upstream, so on their own they must
    # not prompt. The exception is --per-file with a locally deleted file,
    # which the user may want to restore.
    restorable = args.per_file and FileStatus.LOCALLY_DELETED in drift.values()
    if not restorable and all(st in LOCAL_CHOICE_STATUSES for st in drift.values()):
        if drift:
            print(format_preview(drift, baseline_sha, upstream_sha, quiet=False))
        log("INFO", "Up to date.")
        return 0

    print(format_preview(drift, baseline_sha, upstream_sha, quiet=False))

    if args.dry_run:
        log("INFO", "--dry-run: stopping before merge.")
        return 0

    if not args.yes:
        try:
            answer = input("Apply these changes? [y/N]: ").strip().lower()
        except EOFError:
            log("FAIL", "Non-interactive shell. Pass --yes to apply without prompting.")
            return 1
        if answer not in ("y", "yes"):
            log("INFO", "Cancelled by user.")
            return 0

    if not acquire_lock():
        return 1
    try:
        upstream_ref = f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"
        if args.per_file:
            choices = resolve_conflicts_per_file(drift, upstream_ref)
        else:
            choices = {}
        applied, skipped = apply_drift(drift, upstream_ref, conflict_choices=choices)
        kept = [p for p, c in choices.items() if c == "keep"]
        conflicted = [
            p for p in skipped
            if drift.get(p) in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT) and p not in kept
        ]

        if not applied:
            log("OK", "No template paths needed updating.")
        outcome = finish_apply(drift, applied, skipped, upstream_sha, kept=kept)

        if conflicted:
            print()
            log("WARN", "Conflicts left unresolved (your local versions kept):")
            for p in conflicted:
                print(f"      {p}")
            print()
            print("Resolve options:")
            print(f"      {per_file_command()}   # interactive per-file picker")
            print("      git checkout upstream/main -- <path>   # take upstream version")
            print("      git checkout HEAD -- <path>            # keep your version")

        if not args.no_sync and applied:
            run_sync_skills()
    finally:
        release_lock()

    if outcome == "commit-failed":
        return 1
    print()
    log("OK", "done. Restart your agent CLIs so they pick up new agents/skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
