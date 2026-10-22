"""Tests for sync.py: link, refresh, foreign, prune and config errors.

Everything happens under tmp_path: a fake repo and a fake agent home. The
real ~/.claude, ~/.agents and ~/.gemini folders are never touched.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("sync_skills_sync", Path(__file__).parent / "sync.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


@pytest.fixture
def env(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    skills = repo / ".claude" / "skills"
    for name in ("alpha", "beta"):
        (skills / name).mkdir(parents=True)
        (skills / name / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
    (skills / "_shared").mkdir()
    (skills / "_helper").mkdir()
    (skills / "no-skill-md").mkdir()
    monkeypatch.setattr(sync, "repo_root", lambda: repo)

    home = tmp_path / "home"
    cfg = {"name": "test", "env_home_vars": [], "default_home": str(home), "skills_subdir": "skills"}
    return repo, skills, home / "skills", cfg


def _target(link: Path) -> Path:
    return sync.link_target(link).resolve()


def test_list_repo_skills_includes_shared_and_skips_helpers(env):
    _, skills, _, _ = env
    assert [p.name for p in sync.list_repo_skills()] == ["_shared", "alpha", "beta"]


def test_first_run_links_everything_then_second_run_is_ok(env):
    _, skills, target_dir, cfg = env
    listed = sync.list_repo_skills()

    counts = sync.sync_one(cfg, listed, dry_run=False, force=False)
    assert counts["linked"] == 3 and counts["failed"] == 0
    assert _target(target_dir / "alpha") == (skills / "alpha").resolve()

    counts = sync.sync_one(cfg, listed, dry_run=False, force=False)
    assert counts["ok"] == 3 and counts["linked"] == 0


def test_failed_junction_shows_the_mklink_error(env, monkeypatch, capsys):
    _, _, target_dir, cfg = env

    def no_symlink(*a, **k):
        raise OSError("symlink needs elevation")

    def mklink_fails(cmd, **kwargs):
        raise sync.subprocess.CalledProcessError(1, cmd, output="", stderr="Access is denied.\n")

    monkeypatch.setattr(sync.os, "symlink", no_symlink)
    monkeypatch.setattr(sync.os, "name", "nt")
    monkeypatch.setattr(sync.subprocess, "run", mklink_fails)
    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["failed"] == 3 and counts["linked"] == 0
    assert "[FAILED]  alpha: mklink /J failed: Access is denied." in capsys.readouterr().out


def test_dry_run_writes_nothing(env):
    _, _, target_dir, cfg = env
    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=True, force=False)
    assert counts["linked"] == 3
    assert not target_dir.exists()


def test_stale_link_inside_repo_is_refreshed(env):
    _, skills, target_dir, cfg = env
    target_dir.mkdir(parents=True)
    sync.make_link(skills / "beta", target_dir / "alpha")  # wrong skill

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["refreshed"] == 1
    assert _target(target_dir / "alpha") == (skills / "alpha").resolve()


def test_foreign_link_is_left_alone_unless_forced(env, tmp_path):
    _, skills, target_dir, cfg = env
    other_clone = tmp_path / "other-clone" / "alpha"
    other_clone.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    sync.make_link(other_clone, target_dir / "alpha")
    listed = sync.list_repo_skills()

    counts = sync.sync_one(cfg, listed, dry_run=False, force=False)
    assert counts["skipped"] == 1 and counts["refreshed"] == 0
    assert _target(target_dir / "alpha") == other_clone.resolve()

    counts = sync.sync_one(cfg, listed, dry_run=False, force=True)
    assert counts["refreshed"] == 1
    assert _target(target_dir / "alpha") == (skills / "alpha").resolve()
    assert other_clone.is_dir()  # the other clone's files are untouched


def test_link_into_a_worktree_of_this_repo_is_foreign(env, capsys):
    repo, skills, target_dir, cfg = env
    worktree_skill = repo / ".claude" / "worktrees" / "x" / ".claude" / "skills" / "alpha"
    worktree_skill.mkdir(parents=True)
    target_dir.mkdir(parents=True)
    sync.make_link(worktree_skill, target_dir / "alpha")

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["skipped"] == 1 and counts["refreshed"] == 0
    assert "[FOREIGN] alpha" in capsys.readouterr().out
    assert _target(target_dir / "alpha") == worktree_skill.resolve()


def test_unwritable_skills_folder_fails_without_a_traceback(env, monkeypatch, capsys):
    _, _, target_dir, cfg = env

    def refuse(self, *a, **k):
        raise PermissionError("access denied")

    monkeypatch.setattr(sync.Path, "mkdir", refuse)
    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["failed"] == 1 and counts["linked"] == 0 and counts["mkdir_failed"] == 1
    assert f"[FAILED]  cannot create {target_dir}: access denied" in capsys.readouterr().out


@pytest.mark.parametrize("counts, note", [({"failed": 1, "mkdir_failed": 1}, False), ({"failed": 1}, True)])
def test_junction_note_only_follows_a_failed_link(monkeypatch, env, capsys, counts, note):
    monkeypatch.setattr(sync, "load_agents_config", lambda: [{"name": "codex"}])
    monkeypatch.setattr(sync, "sync_one", lambda cfg, *a: dict(counts))
    monkeypatch.setattr(sync.os, "name", "nt")
    monkeypatch.setattr(sync.sys, "argv", ["sync.py"])
    assert sync.main() == 1
    assert ("junction fallback" in capsys.readouterr().out) is note


def test_real_folder_is_never_clobbered(env):
    _, _, target_dir, cfg = env
    real = target_dir / "alpha"
    real.mkdir(parents=True)
    (real / "mine.txt").write_text("user file", encoding="utf-8")

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=True)
    assert counts["skipped"] == 1
    assert (real / "mine.txt").read_text(encoding="utf-8") == "user file"


def test_orphan_link_into_repo_is_pruned_but_others_kept(env, tmp_path):
    _, skills, target_dir, cfg = env
    gone = skills / "gone"
    gone.mkdir()
    outside = tmp_path / "outside" / "theirs"
    outside.mkdir(parents=True)
    sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    sync.make_link(gone, target_dir / "gone")
    sync.make_link(outside, target_dir / "theirs")
    shutil.rmtree(gone)

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=True, force=False)
    assert counts["pruned"] == 1
    assert sync.link_target(target_dir / "gone") is not None

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["pruned"] == 1
    assert sync.link_target(target_dir / "gone") is None
    assert not (target_dir / "gone").exists()
    assert sync.link_target(target_dir / "theirs") is not None


@pytest.mark.parametrize("content", ["{not json", '{"agents": {"name": "x"}}', '{"agents": [{"home": "x"}]}', "[]"])
def test_malformed_agents_json_exits_2(tmp_path, monkeypatch, capsys, content):
    (tmp_path / "agents.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(sync, "script_dir", lambda: tmp_path)
    with pytest.raises(SystemExit) as exc:
        sync.load_agents_config()
    assert exc.value.code == 2
    assert "agents.json" in capsys.readouterr().err


def test_shipped_agents_json_is_valid():
    agents = sync.load_agents_config()
    assert [a["name"] for a in agents] == ["claude", "codex", "gemini"]
    # Codex reads user skills from $HOME/.agents/skills, not ~/.codex/skills.
    codex = agents[1]
    assert (codex["default_home"], codex["skills_subdir"], codex["env_home_vars"]) == ("~/.agents", "skills", [])


def _run_main(monkeypatch, env, argv):
    """Run main() with sync_one stubbed out; return the agent names it was called for."""
    called = []
    monkeypatch.setattr(sync, "load_agents_config", lambda: [{"name": n} for n in ("claude", "codex", "gemini")])
    monkeypatch.setattr(sync, "sync_one", lambda cfg, *a: called.append(cfg["name"]) or {"failed": 0})
    monkeypatch.setattr(sync.sys, "argv", ["sync.py", *argv])
    return sync.main(), called


def test_default_syncs_every_agent_including_claude(monkeypatch, env):
    rc, called = _run_main(monkeypatch, env, [])
    assert rc == 0 and called == ["claude", "codex", "gemini"]


def test_skip_claude_leaves_claude_out(monkeypatch, env):
    rc, called = _run_main(monkeypatch, env, ["--skip", "claude"])
    assert rc == 0 and called == ["codex", "gemini"]


def test_skip_combines_with_agents(monkeypatch, env):
    rc, called = _run_main(monkeypatch, env, ["--agents", "claude", "codex", "--skip", "claude"])
    assert rc == 0 and called == ["codex"]


def test_skip_unknown_agent_exits_2(monkeypatch, env, capsys):
    rc, called = _run_main(monkeypatch, env, ["--skip", "claud"])
    assert rc == 2 and called == []
    assert "unknown agent" in capsys.readouterr().err


# ---------- path comparison ----------

@pytest.mark.skipif(sys.platform != "win32", reason="Windows paths are case-insensitive")
def test_paths_differing_only_in_case_are_equal():
    assert sync.paths_equal(Path("C:/Repo/.claude/skills/Alpha"), Path("c:/repo/.CLAUDE/skills/alpha"))
    assert sync.is_under(Path("C:/REPO/.claude/skills/x"), Path("c:/repo"))


def test_paths_equal_normalises_separators_and_dotdot(tmp_path):
    assert sync.paths_equal(tmp_path / "a" / ".." / "b", tmp_path / "b")
    assert not sync.paths_equal(tmp_path / "a", tmp_path / "b")


def test_is_under_needs_a_separator_boundary(tmp_path):
    assert sync.is_under(tmp_path / "repo" / "x", tmp_path / "repo")
    assert sync.is_under(tmp_path / "repo", tmp_path / "repo")
    assert not sync.is_under(tmp_path / "repo-other" / "x", tmp_path / "repo")


def test_claude_home_follows_claude_config_dir(tmp_path, monkeypatch):
    # Claude Code's documented config-dir override is CLAUDE_CONFIG_DIR.
    claude = next(a for a in sync.load_agents_config() if a["name"] == "claude")
    assert claude["env_home_vars"] == ["CLAUDE_CONFIG_DIR"]
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude-work"))
    assert sync.home_for(claude) == tmp_path / "claude-work"
    monkeypatch.delenv("CLAUDE_CONFIG_DIR")
    assert sync.home_for(claude) == Path.home() / ".claude"


def test_gemini_home_follows_gemini_cli_home(tmp_path, monkeypatch):
    # Gemini reads $GEMINI_CLI_HOME/.gemini/skills, not $GEMINI_CLI_HOME/skills.
    gemini = next(a for a in sync.load_agents_config() if a["name"] == "gemini")
    assert gemini["env_home_vars"] == ["GEMINI_CLI_HOME"]
    monkeypatch.setenv("GEMINI_CLI_HOME", str(tmp_path))
    assert sync.home_for(gemini) / gemini["skills_subdir"] == tmp_path / ".gemini" / "skills"
    monkeypatch.delenv("GEMINI_CLI_HOME")
    assert sync.home_for(gemini) / gemini["skills_subdir"] == Path.home() / ".gemini" / "skills"
