"""Pull Agentic-Z template updates from upstream into the current clone.

What it touches:
    .claude/agents/, .claude/skills/, .claude/mcp/
    docs/, wiki/, scripts/
    CLAUDE.md, AGENTS.md, GEMINI.md, README.md

What it leaves alone:
    workspace/, output/, .claude/local-memory/, .claude/settings.local.json, .env

Usage:
    python update.py [--force] [--dry-run] [--no-sync]
"""
from __future__ import annotations

import argparse
import datetime
import enum
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

UPSTREAM_URL = "https://github.com/DayZ-n-Chill/Agentic-Z.git"
UPSTREAM_REMOTE = "upstream"
UPSTREAM_BRANCH = "main"

# Paths (relative to repo root) that get pulled from upstream. Anything outside
# this list is left alone.
TEMPLATE_PATHS = [
    ".claude/agents",
    ".claude/skills",
    ".claude/mcp",
    "docs",
    "wiki",
    "scripts",
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    "README.md",
]


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


def log(level: str, msg: str) -> None:
    print(f"[{level}]\t{msg}", flush=True)


def run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )


def is_git_repo() -> bool:
    try:
        r = run(["git", "rev-parse", "--is-inside-work-tree"], check=False, capture=True)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except FileNotFoundError:
        return False


def working_tree_clean_for(paths: list[str]) -> tuple[bool, list[str]]:
    """Check if any of the given paths have uncommitted changes."""
    r = run(["git", "status", "--porcelain", "--", *paths], capture=True)
    if not r.stdout.strip():
        return True, []
    dirty = [line[3:] for line in r.stdout.splitlines() if line.strip()]
    return False, dirty


def remote_url(name: str) -> str | None:
    r = run(["git", "remote", "get-url", name], check=False, capture=True)
    return r.stdout.strip() if r.returncode == 0 else None


def ensure_upstream() -> bool:
    existing = remote_url(UPSTREAM_REMOTE)
    if existing is None:
        log("INFO", f"Adding {UPSTREAM_REMOTE} remote = {UPSTREAM_URL}")
        run(["git", "remote", "add", UPSTREAM_REMOTE, UPSTREAM_URL])
        return True
    if existing.rstrip("/") != UPSTREAM_URL.rstrip("/").replace(".git", "").rstrip("/") and \
       existing.rstrip("/") != UPSTREAM_URL.rstrip("/"):
        # Allow .git vs no-.git but not a different repo
        if not existing.startswith(UPSTREAM_URL.rstrip(".git")):
            log("ERR", f"upstream remote points to {existing}, expected {UPSTREAM_URL}")
            log("ERR", f"Fix: git remote set-url {UPSTREAM_REMOTE} {UPSTREAM_URL}")
            return False
    log("OK", f"upstream remote already set: {existing}")
    return True


def fetch_upstream() -> bool:
    log("INFO", f"Fetching {UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}...")
    r = run(["git", "fetch", UPSTREAM_REMOTE, UPSTREAM_BRANCH], check=False)
    return r.returncode == 0


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


def stage_and_commit(updated: list[str], upstream_sha: str) -> bool:
    """Stage updated paths and create a single commit."""
    r = run(["git", "add", "--", *updated], check=False)
    if r.returncode != 0:
        return False
    # Skip commit if nothing actually changed.
    diff = run(["git", "diff", "--cached", "--quiet"], check=False)
    if diff.returncode == 0:
        log("OK", "no template changes to commit (working tree already matches upstream)")
        return True
    msg = f"chore: pull Agentic-Z upstream ({upstream_sha[:8]})"
    r = run(["git", "commit", "-m", msg], check=False)
    if r.returncode != 0:
        log("WARN", "commit failed; staged changes left in index for manual handling")
        return False
    log("OK", f"committed: {msg}")
    return True


def upstream_head_sha() -> str:
    r = run(["git", "rev-parse", f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}"], capture=True)
    return r.stdout.strip()


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
    """Write a lock file with this process's PID and an ISO timestamp."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "pid": os.getpid(),
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    LOCK_FILE.write_text(json.dumps(payload), encoding="utf-8")


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
        return f"agentic-z: {' + '.join(parts)} available. Run /agentic-z-update or /dayz-search-download."

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
                upstream_blob = git_show_blob(upstream_ref, path) or b""
                _print_diff(path, local, upstream_blob)
                # Re-prompt after diff
                continue
            print("    invalid choice; try k/t/d/s")
    return choices


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull Agentic-Z upstream template updates.")
    parser.add_argument("--force", action="store_true", help="Skip the dirty-tree check.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change; don't merge.")
    parser.add_argument("--no-sync", action="store_true", help="Skip the post-merge sync-skills run.")
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
    args = parser.parse_args()

    if not args.check and not args.quiet:
        print("Agentic-Z update")
        print()

    if not is_git_repo():
        log("ERR", "Not a git repo. Run from inside an Agentic-Z clone.")
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
        return 1

    if not fetch_upstream():
        if args.check and args.quiet:
            # Hook: fail silently on network issues.
            return 0
        log("ERR", "git fetch failed. Network issue or upstream unreachable.")
        return 1

    upstream_sha = upstream_head_sha()
    baseline_sha = read_baseline()

    # First-run bootstrap: if no baseline file exists, persist one immediately
    # at the current upstream HEAD. Without this, every subsequent run would
    # also see baseline=None, re-bootstrap to upstream, and silently report
    # "Up to date" forever — masking real drift. Safe to do even from --check
    # because it's idempotent and a one-time initialization.
    if baseline_sha is None:
        try:
            write_baseline(upstream_sha)
            baseline_sha = upstream_sha
        except OSError:
            # Read-only FS or permission issue — fall through; compute_drift's
            # in-memory bootstrap still produces correct first-run output.
            pass

    if args.check:
        drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
        output = format_preview(drift, baseline_sha, upstream_sha, quiet=args.quiet)
        if output:
            print(output)
            return 1  # drift exists
        if not args.quiet:
            print("Up to date.")
        return 0

    if args.dry_run:
        log("INFO", "--dry-run: stopping before merge.")
        return 0

    # Default flow: preview, prompt, apply.
    drift = compute_drift(baseline_sha, f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}")
    if not drift:
        log("INFO", "Up to date.")
        return 0

    print(format_preview(drift, baseline_sha, upstream_sha, quiet=False))

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
        conflicted = [
            p for p in skipped
            if drift.get(p) in (FileStatus.CONFLICT, FileStatus.DELETED_CONFLICT)
        ]

        if applied:
            stage_and_commit(applied, upstream_sha)
            # Record the upstream SHA as the new baseline so the next run starts fresh.
            write_baseline(upstream_head_sha())
            log("OK", "Baseline updated.")
        else:
            log("OK", "No template paths needed updating.")

        if conflicted:
            print()
            log("WARN", "Conflicts left unresolved (your local versions kept):")
            for p in conflicted:
                print(f"      {p}")
            print()
            print("Resolve options:")
            print("      python update.py --per-file   # interactive per-file picker")
            print("      git checkout upstream/main -- <path>   # take upstream version")
            print("      git checkout HEAD -- <path>            # keep your version")

        if not args.no_sync and applied:
            run_sync_skills()
    finally:
        release_lock()

    print()
    log("OK", "done. Restart your agent CLIs so they pick up new agents/skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
