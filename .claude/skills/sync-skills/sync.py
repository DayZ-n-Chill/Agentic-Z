"""Sync repo-local .claude/skills/ into the per-agent skill directories.

Reads .claude/skills/sync-skills/agents.json for the list of agent targets,
so adding a new agent CLI later is a config change, not a code change.

Run from the repo root (or from anywhere — the script resolves paths relative
to its own location):

    python .claude/skills/sync-skills/sync.py
    python .claude/skills/sync-skills/sync.py --agents claude codex
    python .claude/skills/sync-skills/sync.py --dry-run
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


def repo_skills_dir() -> Path:
    return repo_root() / ".claude" / "skills"


def load_agents_config() -> list[dict]:
    cfg_path = script_dir() / "agents.json"
    if not cfg_path.is_file():
        print(f"ERROR: agents config not found at {cfg_path}", file=sys.stderr)
        sys.exit(2)
    return json.loads(cfg_path.read_text(encoding="utf-8")).get("agents", [])


def home_for(agent_cfg: dict) -> Path:
    for env_var in agent_cfg.get("env_home_vars", []):
        v = os.environ.get(env_var)
        if v:
            return Path(os.path.expanduser(v))
    return Path(os.path.expanduser(agent_cfg.get("default_home", "")))


def list_repo_skills() -> list[Path]:
    base = repo_skills_dir()
    if not base.is_dir():
        print(f"ERROR: repo skills folder not found: {base}", file=sys.stderr)
        sys.exit(2)
    out: list[Path] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue  # skip _shared/ etc — helpers, not skills
        if (child / "SKILL.md").is_file():
            out.append(child)
    return out


def link_target(path: Path) -> Path | None:
    """Return the target a symlink/junction points to, or None if not a link.

    Strips Windows `\\\\?\\` long-path prefix so the returned Path compares
    equal to other Path representations of the same target. Without this,
    pass-2 prune logic would never fire (relative_to() fails on the prefixed
    form) and pass-1 would treat every junction as "needs refresh".
    """
    try:
        target = os.readlink(path)
    except OSError:
        return None
    if target.startswith("\\\\?\\"):
        target = target[4:]
    return Path(target)


def make_link(src: Path, dst: Path) -> str:
    """Create a directory symlink. Falls back to junction on Windows."""
    try:
        os.symlink(src, dst, target_is_directory=True)
        return "symlink"
    except OSError:
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(dst), str(src)],
                check=True, capture_output=True, text=True,
            )
            return "junction"
        raise


def remove_link(p: Path) -> None:
    """Remove a symlink/junction without descending into the target."""
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "rmdir", str(p)], check=True, capture_output=True, text=True)
    else:
        p.unlink()


def sync_one(agent_cfg: dict, skills: Iterable[Path], dry_run: bool) -> dict[str, int]:
    name = agent_cfg["name"]
    home = home_for(agent_cfg)
    target_dir = home / agent_cfg.get("skills_subdir", "skills")
    print()
    print(f"[{name}] {target_dir}")

    if not target_dir.exists():
        if dry_run:
            print(f"  DRY-RUN mkdir {target_dir}")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)

    counts = {"linked": 0, "ok": 0, "refreshed": 0, "skipped": 0, "pruned": 0, "failed": 0}
    repo = repo_root().resolve()
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
            if str(existing_resolved).lower() == str(src_resolved).lower():
                print(f"  [OK]      {src.name}")
                counts["ok"] += 1
                continue
            if dry_run:
                print(f"  DRY-RUN refresh {src.name} (was {existing} -> would point to {src_resolved})")
            else:
                try:
                    remove_link(dst)
                    kind = make_link(src_resolved, dst)
                    print(f"  [REFRESH] {src.name}  ({kind}, was {existing})")
                except Exception as e:
                    print(f"  [FAILED]  {src.name}: {e}")
                    counts["failed"] += 1
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

    # Pass 2: prune orphan links pointing back into this repo at gone paths
    if target_dir.exists():
        for child in target_dir.iterdir():
            if child.name in expected_names:
                continue
            t = link_target(child)
            if t is None:
                continue
            try:
                t_resolved = t.resolve() if t.is_absolute() else (child.parent / t).resolve()
            except OSError:
                continue
            try:
                t_resolved.relative_to(repo)
            except ValueError:
                continue  # not pointing back into our repo, leave it alone
            if t_resolved.exists():
                continue  # repo target still exists; not an orphan
            if dry_run:
                print(f"  DRY-RUN prune {child.name} (orphan; target {t_resolved} gone)")
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--agents", nargs="+", default=None,
                    help="Subset of agents to sync (by name in agents.json). Default: all.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would happen, write nothing.")
    args = ap.parse_args()

    all_agents = load_agents_config()
    if not all_agents:
        print("ERROR: no agents configured in agents.json", file=sys.stderr)
        return 2
    if args.agents:
        valid = {a["name"] for a in all_agents}
        bad = [a for a in args.agents if a not in valid]
        if bad:
            print(f"ERROR: unknown agent(s): {bad}. Valid: {sorted(valid)}", file=sys.stderr)
            return 2
        agents = [a for a in all_agents if a["name"] in args.agents]
    else:
        agents = all_agents

    skills = list_repo_skills()
    if not skills:
        print(f"WARNING: no skills with SKILL.md found under {repo_skills_dir()}")
        return 0

    print(f"Repo skills: {len(skills)}  ({repo_skills_dir()})")
    for s in skills:
        print(f"  - {s.name}")

    totals: dict[str, int] = {}
    failed_any = False
    for agent_cfg in agents:
        c = sync_one(agent_cfg, skills, args.dry_run)
        for k, v in c.items():
            totals[k] = totals.get(k, 0) + v
        if c["failed"] > 0:
            failed_any = True

    print()
    print("Summary")
    for k in ("linked", "ok", "refreshed", "skipped", "pruned", "failed"):
        print(f"  {k:>10}: {totals.get(k, 0)}")

    if failed_any and os.name == "nt":
        print()
        print("Note: symlink failures on Windows usually mean Developer Mode is off.")
        print("      The script falls back to junctions automatically; junctions don't need admin.")

    return 1 if failed_any else 0


if __name__ == "__main__":
    sys.exit(main())
