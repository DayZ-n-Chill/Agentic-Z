"""Sync repo-local skills/ and .claude/skills/ into the per-agent skill directories.

Reads .claude/skills/sync-skills/agents.json for the list of agent targets,
so adding a new agent CLI later is a config change, not a code change. An
entry with "default": false (Claude Code) is only synced when named in --agents.

Run from the repo root (or from anywhere — the script resolves paths relative
to its own location):

    python .claude/skills/sync-skills/sync.py
    python .claude/skills/sync-skills/sync.py --agents claude codex
    python .claude/skills/sync-skills/sync.py --dry-run
    python .claude/skills/sync-skills/sync.py --skip gemini
    python .claude/skills/sync-skills/sync.py --unlink --agents claude
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def repo_root() -> Path:
    # this file is .claude/skills/sync-skills/sync.py — repo root is 3 parents up
    return script_dir().parents[2]


def repo_skills_dirs() -> list[Path]:
    return [repo_root() / "skills", repo_root() / ".claude" / "skills"]


def is_own(path: Path) -> bool:
    return any(is_under(path, d.resolve()) for d in repo_skills_dirs())


def skills_dirs_label() -> str:
    return ", ".join(str(d) for d in repo_skills_dirs())


def load_agents_config() -> list[dict]:
    """Read agents.json. Exits 2 with a clear message if it is missing or malformed."""
    cfg_path = script_dir() / "agents.json"
    if not cfg_path.is_file():
        print(f"ERROR: agents config not found at {cfg_path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: {cfg_path} is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}",
              file=sys.stderr)
        sys.exit(2)
    agents = data.get("agents") if isinstance(data, dict) else None
    if not isinstance(agents, list) or not all(isinstance(a, dict) and a.get("name") for a in agents):
        print(f'ERROR: {cfg_path} must be {{"agents": [{{"name": ..., ...}}, ...]}}; '
              "every entry needs a \"name\".", file=sys.stderr)
        sys.exit(2)
    names = [a["name"] for a in agents]
    dupes = sorted({n for n in names if names.count(n) > 1})
    if dupes:
        print(f"ERROR: {cfg_path}: agent names must be unique (duplicated: {dupes}).", file=sys.stderr)
        sys.exit(2)

    def is_text(v, allow_empty: bool = False) -> bool:
        return isinstance(v, str) and (allow_empty or bool(v.strip()))

    # Each check: (agents that break it, what the field must be). An empty
    # "default_home" would make home_for return "" and put the links in a
    # skills folder under the current directory, so it is required.
    checks = [
        ([a["name"] for a in agents if not isinstance(a.get("default", True), bool)],
         '"default" must be true or false'),
        ([a["name"] for a in agents if not is_text(a.get("default_home"))],
         '"default_home" is required and must be a non-empty string (e.g. "~/.gemini")'),
        ([a["name"] for a in agents
          if not (isinstance(a.get("env_home_vars", []), list)
                  and all(is_text(v) for v in a.get("env_home_vars", [])))],
         '"env_home_vars" must be a list of environment variable names (e.g. ["GEMINI_CLI_HOME"])'),
        ([a["name"] for a in agents if not is_text(a.get("skills_subdir", "skills"))],
         '"skills_subdir" must be a non-empty string'),
        ([a["name"] for a in agents if not is_text(a.get("env_home_subdir", ""), allow_empty=True)],
         '"env_home_subdir" must be a string'),
    ]
    for bad, rule in checks:
        if bad:
            print(f"ERROR: {cfg_path}: {rule} (agents: {bad}).", file=sys.stderr)
            sys.exit(2)
    return agents


def home_for(agent_cfg: dict) -> Path:
    for env_var in agent_cfg.get("env_home_vars", []):
        v = os.environ.get(env_var)
        if v:
            return Path(os.path.expanduser(v)) / agent_cfg.get("env_home_subdir", "")
    return Path(os.path.expanduser(agent_cfg.get("default_home", "")))


def list_repo_skills() -> list[Path]:
    bases = [d for d in repo_skills_dirs() if d.is_dir()]
    if not bases:
        print(f"ERROR: repo skills folder not found: {skills_dirs_label()}", file=sys.stderr)
        sys.exit(2)
    out: list[Path] = []
    seen: set[str] = set()
    for child in sorted((c for b in bases for c in b.iterdir()), key=lambda c: c.name):
        # skills/ is listed first and the sort is stable, so on a duplicate
        # name skills/ wins over a stale folder an update left in .claude/skills/.
        if not child.is_dir() or child.name in seen:
            continue
        if child.name == "_shared":
            # Not a skill (no SKILL.md, so agent CLIs ignore it), but agents
            # reference ~/.claude/skills/_shared/*.md cross-project, so it
            # must be linked alongside the skills.
            out.append(child)
            seen.add(child.name)
            continue
        if child.name.startswith("_"):
            continue  # other underscore dirs are helpers, not skills
        if (child / "SKILL.md").is_file():
            out.append(child)
            seen.add(child.name)
    return out


def link_target(path: Path) -> Path | None:
    """Return the target a symlink/junction points to, or None if not a link.

    Strips Windows `\\\\?\\` long-path prefix so the returned Path compares
    equal to other Path representations of the same target. Without this,
    pass-2 prune logic would never fire (is_under() fails on the prefixed
    form) and pass-1 would treat every junction as "needs refresh".
    """
    try:
        target = os.readlink(path)
    except OSError:
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return Path(target)


def _norm(p: Path) -> str:
    return os.path.normcase(os.path.normpath(str(p)))


def paths_equal(a: Path, b: Path) -> bool:
    """True when two paths name the same location: case-insensitive on Windows
    (os.path.normcase), separators and `..` normalised. Same rule as
    dayz-preflight's paths_equal, kept local so this generic skill does not
    depend on a DayZ one."""
    return _norm(a) == _norm(b)


def is_under(path: Path, root: Path) -> bool:
    """True when path is root or inside it, compared the same way as paths_equal."""
    p, r = _norm(path), _norm(root)
    return p == r or p.startswith(r.rstrip(os.sep) + os.sep)


def make_link(src: Path, dst: Path) -> str:
    """Create a directory symlink. Falls back to junction on Windows."""
    try:
        os.symlink(src, dst, target_is_directory=True)
        return "symlink"
    except OSError:
        if os.name == "nt":
            try:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
                    check=True, capture_output=True, text=True,
                )
            except subprocess.CalledProcessError as e:
                # Keep mklink's own message (access denied, path in use) for the [FAILED] line.
                raise OSError(f"mklink /J failed: {(e.stderr or e.stdout or '').strip()}") from e
            return "junction"
        raise


def remove_link(p: Path) -> None:
    """Remove a symlink/junction without descending into the target."""
    if os.name == "nt":
        try:
            subprocess.run(["cmd", "/c", "rmdir", str(p)], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise OSError(f"rmdir failed: {(e.stderr or e.stdout or '').strip()}") from e
    else:
        p.unlink()


def resolved_target(link: Path) -> Path | None:
    """The absolute, resolved target of a link, or None if it is not a link."""
    t = link_target(link)
    if t is None:
        return None
    try:
        return t.resolve() if t.is_absolute() else (link.parent / t).resolve()
    except OSError:
        return None


def sync_one(agent_cfg: dict, skills: Iterable[Path], dry_run: bool, force: bool) -> dict[str, int]:
    name = agent_cfg["name"]
    home = home_for(agent_cfg)
    target_dir = home / agent_cfg.get("skills_subdir", "skills")
    print()
    print(f"[{name}] {target_dir}")

    # "link_failed" counts only failures of make_link itself (symlink and the
    # junction fallback both refused). main prints the junction note on that
    # alone, not on a failed mkdir, old-link removal or prune.
    counts = {"linked": 0, "ok": 0, "refreshed": 0, "skipped": 0, "pruned": 0, "failed": 0, "link_failed": 0}
    if not target_dir.exists():
        if dry_run:
            print(f"  DRY-RUN mkdir {target_dir}")
        else:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                print(f"  [FAILED]  cannot create {target_dir}: {e}")
                counts["failed"] += 1
                return counts

    # Ownership is decided against this checkout's skills folders, not the repo
    # root: git worktrees under <repo>/.claude/worktrees/ are other checkouts.
    expected_names = {s.name for s in skills}

    # Pass 1: link/refresh each repo skill
    for src in skills:
        src_resolved = src.resolve()
        dst = target_dir / src.name
        existing = link_target(dst)
        if existing is not None:
            try:
                existing_resolved = existing.resolve() if existing.is_absolute() else (dst.parent / existing).resolve()
            except OSError:
                existing_resolved = existing
            if paths_equal(existing_resolved, src_resolved):
                print(f"  [OK]      {src.name}")
                counts["ok"] += 1
                continue
            # Link points at another clone of this template. Refusing to steal
            # it silently — that breaks the other clone's sessions. --force
            # makes the takeover explicit.
            if not is_own(existing_resolved) and not force:
                print(f"  [FOREIGN] {src.name}: points at {existing}; rerun with --force to take ownership")
                counts["skipped"] += 1
                continue
            if dry_run:
                print(f"  DRY-RUN refresh {src.name} (was {existing} -> would point to {src_resolved})")
            else:
                try:
                    remove_link(dst)
                except Exception as e:
                    print(f"  [FAILED]  {src.name}: cannot remove old link: {e}")
                    counts["failed"] += 1
                    continue
                try:
                    kind = make_link(src_resolved, dst)
                    print(f"  [REFRESH] {src.name}  ({kind}, was {existing})")
                except Exception as e:
                    # The old link is already gone; put it back so the skill
                    # is not left with no link at all.
                    try:
                        make_link(existing_resolved, dst)
                        note = f"previous link to {existing_resolved} restored"
                    except Exception as e2:
                        note = f"previous link to {existing_resolved} could not be restored either: {e2}"
                    print(f"  [FAILED]  {src.name}: {e}; {note}")
                    counts["failed"] += 1
                    counts["link_failed"] += 1
                    continue
            counts["refreshed"] += 1
            continue
        if dst.exists():
            print(f"  [SKIP]    {src.name}: already exists as a real folder, not a link")
            counts["skipped"] += 1
            continue
        if dry_run:
            print(f"  DRY-RUN link {src.name} -> {src_resolved}")
            counts["linked"] += 1
            continue
        try:
            kind = make_link(src_resolved, dst)
            print(f"  [LINK]    {src.name}  ({kind})")
            counts["linked"] += 1
        except Exception as e:
            print(f"  [FAILED]  {src.name}: {e}")
            counts["failed"] += 1
            counts["link_failed"] += 1

    # Pass 2: prune orphan links pointing into this checkout's skills folders
    # at something that is no longer a skill. A deleted skill's folder often
    # survives a pull because git leaves the ignored __pycache__ behind, so
    # "no SKILL.md" is the test, not "folder gone". _shared is kept.
    shared = (repo_root() / "skills" / "_shared").resolve()
    if target_dir.exists():
        for child in target_dir.iterdir():
            if child.name in expected_names:
                continue
            t_resolved = resolved_target(child)
            if t_resolved is None:
                continue
            if not is_own(t_resolved):
                continue  # not pointing back into our repo, leave it alone
            if is_under(t_resolved, shared) or (t_resolved / "SKILL.md").is_file():
                continue  # still a skill (or the shared docs); not an orphan
            reason = "target has no SKILL.md" if t_resolved.exists() else "target gone"
            if dry_run:
                print(f"  DRY-RUN prune {child.name} (orphan; {reason}: {t_resolved})")
            else:
                try:
                    remove_link(child)
                    print(f"  [PRUNE]   {child.name}  (orphan)")
                except Exception as e:
                    print(f"  [FAILED]  prune {child.name}: {e}")
                    counts["failed"] += 1
                    continue
            counts["pruned"] += 1

    return counts


def unlink_one(agent_cfg: dict, dry_run: bool) -> dict[str, int]:
    """Remove every link in the agent's skills folder that points into this
    checkout's skills/ or .claude/skills/. Foreign links and real folders are left alone,
    and the repo's skill folders themselves are never touched."""
    name = agent_cfg["name"]
    target_dir = home_for(agent_cfg) / agent_cfg.get("skills_subdir", "skills")
    print()
    print(f"[{name}] {target_dir}")
    counts = {"unlinked": 0, "failed": 0}
    if not target_dir.is_dir():
        print("  nothing to unlink (folder does not exist)")
        return counts
    for child in sorted(target_dir.iterdir()):
        t_resolved = resolved_target(child)
        if t_resolved is None or not is_own(t_resolved):
            continue
        if dry_run:
            print(f"  DRY-RUN unlink {child.name} (-> {t_resolved})")
        else:
            try:
                remove_link(child)
                print(f"  [UNLINK]  {child.name}")
            except Exception as e:
                print(f"  [FAILED]  unlink {child.name}: {e}")
                counts["failed"] += 1
                continue
        counts["unlinked"] += 1
    return counts


_DRY_RUN_LABELS = {"linked": "would link", "refreshed": "would refresh",
                   "pruned": "would prune", "unlinked": "would unlink"}


def summary_header(dry_run: bool) -> str:
    return "Summary (DRY-RUN: nothing was changed)" if dry_run else "Summary"


def summary_label(key: str, dry_run: bool) -> str:
    """Summary row label; a dry run says "would link" so a preview never reads as done."""
    return _DRY_RUN_LABELS.get(key, key) if dry_run else key


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--agents", nargs="+", default=None,
                    help='Agents to sync (by name in agents.json). Default: every agent not marked '
                         '"default": false, which leaves Claude Code out; name it here to include it.')
    ap.add_argument("--skip", nargs="+", default=[],
                    help="Agents to leave out (by name in agents.json), e.g. --skip gemini.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would happen, write nothing.")
    ap.add_argument("--force", action="store_true",
                    help="Take ownership of links currently pointing at a different clone of this template.")
    ap.add_argument("--unlink", action="store_true",
                    help="Remove this checkout's links from the selected agents instead of creating them.")
    args = ap.parse_args()

    all_agents = load_agents_config()
    if not all_agents:
        print("ERROR: no agents configured in agents.json", file=sys.stderr)
        return 2
    valid = {a["name"] for a in all_agents}
    bad = [a for a in (args.agents or []) + args.skip if a not in valid]
    if bad:
        print(f"ERROR: unknown agent(s): {bad}. Valid: {sorted(valid)}", file=sys.stderr)
        return 2
    agents = [
        a for a in all_agents
        if (a["name"] in args.agents if args.agents else a.get("default", True))
        and a["name"] not in args.skip
    ]
    if not agents:
        print("Nothing to do: every agent was excluded by --agents/--skip.")
        return 0

    if args.unlink:
        if not any(d.is_dir() for d in repo_skills_dirs()):
            print(f"ERROR: repo skills folder not found: {skills_dirs_label()}", file=sys.stderr)
            return 2
        unlinked = failed = 0
        for agent_cfg in agents:
            c = unlink_one(agent_cfg, args.dry_run)
            unlinked += c["unlinked"]
            failed += c["failed"]
        print()
        print(summary_header(args.dry_run))
        print(f"  {summary_label('unlinked', args.dry_run):>14}: {unlinked}")
        print(f"  {'failed':>14}: {failed}")
        return 1 if failed else 0

    skills = list_repo_skills()
    if not skills:
        print(f"WARNING: no skills with SKILL.md found under {skills_dirs_label()}")
        return 0

    print(f"Repo skills: {len(skills)}  ({skills_dirs_label()})")
    for s in skills:
        print(f"  - {s.name}")

    totals: dict[str, int] = {}
    failed_any = link_failed = False
    for agent_cfg in agents:
        c = sync_one(agent_cfg, skills, args.dry_run, args.force)
        for k, v in c.items():
            totals[k] = totals.get(k, 0) + v
        if c["failed"] > 0:
            failed_any = True
        if c.get("link_failed", 0) > 0:
            link_failed = True

    print()
    print(summary_header(args.dry_run))
    for k in ("linked", "ok", "refreshed", "skipped", "pruned", "failed"):
        print(f"  {summary_label(k, args.dry_run):>14}: {totals.get(k, 0)}")

    if link_failed and os.name == "nt":
        print()
        print("Note: a link only fails after the junction fallback has failed too, so Developer Mode")
        print("      is not the cause. Check that you can write to the target skills folder and that")
        print("      no other program has the path open, then run again.")

    return 1 if failed_any else 0


if __name__ == "__main__":
    sys.exit(main())
