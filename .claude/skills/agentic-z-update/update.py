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
import enum
import json
import subprocess
import sys
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


def show_changelog() -> None:
    """Print commits in upstream/main not in current branch, scoped to template paths."""
    r = run(
        [
            "git",
            "log",
            "--oneline",
            "--no-merges",
            f"HEAD..{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}",
            "--",
            *TEMPLATE_PATHS,
        ],
        check=False,
        capture=True,
    )
    out = r.stdout.strip()
    if not out:
        log("OK", "Already up to date — no template commits to pull.")
        return
    print()
    print("─── Incoming template commits ───────────────────────────────")
    print(out)
    print("──────────────────────────────────────────────────────────────")
    print()


def merge_template_paths() -> tuple[list[str], list[str]]:
    """Pull each template path from upstream/main into the working tree.

    Returns (updated_paths, conflicted_paths).
    """
    updated: list[str] = []
    conflicted: list[str] = []
    for path in TEMPLATE_PATHS:
        if not Path(path).exists() and not _exists_in_upstream(path):
            continue
        log("INFO", f"merging {path}")
        r = run(
            ["git", "checkout", f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}", "--", path],
            check=False,
            capture=True,
        )
        if r.returncode != 0:
            err = (r.stderr or "").strip()
            log("WARN", f"  conflict on {path}: {err}")
            conflicted.append(path)
        else:
            updated.append(path)
    return updated, conflicted


def _exists_in_upstream(path: str) -> bool:
    r = run(
        ["git", "cat-file", "-e", f"{UPSTREAM_REMOTE}/{UPSTREAM_BRANCH}:{path}"],
        check=False,
        capture=True,
    )
    return r.returncode == 0


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Pull Agentic-Z upstream template updates.")
    parser.add_argument("--force", action="store_true", help="Skip the dirty-tree check.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change; don't merge.")
    parser.add_argument("--no-sync", action="store_true", help="Skip the post-merge sync-skills run.")
    args = parser.parse_args()

    print("Agentic-Z update")
    print()

    if not is_git_repo():
        log("ERR", "Not a git repo. Run from inside an Agentic-Z clone.")
        return 1

    if not args.force:
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
        log("ERR", "git fetch failed. Network issue or upstream unreachable.")
        return 1

    show_changelog()

    if args.dry_run:
        log("INFO", "--dry-run: stopping before merge.")
        return 0

    upstream_sha = upstream_head_sha()
    updated, conflicted = merge_template_paths()

    if updated:
        stage_and_commit(updated, upstream_sha)
    else:
        log("OK", "no template paths needed updating")

    if conflicted:
        print()
        log("WARN", "Conflicts on these paths (left as-is, resolve manually):")
        for p in conflicted:
            print(f"      {p}")
        print()
        print("Resolve options per file:")
        print("      git checkout upstream/main -- <path>   # take upstream version")
        print("      git checkout HEAD -- <path>            # keep your version")
        print("      git diff upstream/main HEAD -- <path>  # see the difference")

    if not args.no_sync and updated and not conflicted:
        run_sync_skills()

    print()
    log("OK", "done. Restart your agent CLIs so they pick up new agents/skills.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
