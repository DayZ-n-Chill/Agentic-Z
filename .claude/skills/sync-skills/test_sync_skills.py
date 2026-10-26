"""Tests for sync.py: link, refresh, rollback, foreign, prune, unlink and config errors.

Everything happens under tmp_path: a fake repo and a fake agent home. The
real ~/.claude, ~/.agents and ~/.gemini folders are never touched.
"""
from __future__ import annotations

import importlib.util
import json
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
    skills = repo / "skills"
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


def test_repo_only_skills_in_dot_claude_are_listed_and_owned(env):
    repo, _, target_dir, cfg = env
    repo_only = repo / ".claude" / "skills" / "delta"
    repo_only.mkdir(parents=True)
    (repo_only / "SKILL.md").write_text("---\nname: delta\n---\n", encoding="utf-8")
    assert [p.name for p in sync.list_repo_skills()] == ["_shared", "alpha", "beta", "delta"]

    sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert _target(target_dir / "delta") == repo_only.resolve()
    assert sync.unlink_one(cfg, dry_run=False) == {"unlinked": 4, "failed": 0}


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


def _make_link_failing_for(target: Path, monkeypatch, also_restore: bool = False):
    """Make make_link fail when linking to `target` (and, if also_restore, always)."""
    real = sync.make_link

    def fake(src, dst):
        if also_restore or sync.paths_equal(Path(src).resolve(), target.resolve()):
            raise OSError("disk says no")
        return real(src, dst)

    monkeypatch.setattr(sync, "make_link", fake)


def test_failed_refresh_restores_the_previous_link(env, monkeypatch, capsys):
    _, skills, target_dir, cfg = env
    target_dir.mkdir(parents=True)
    sync.make_link(skills / "beta", target_dir / "alpha")  # stale
    _make_link_failing_for(skills / "alpha", monkeypatch)

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["failed"] == 1 and counts["refreshed"] == 0
    # The skill still has a link: the old one, not nothing.
    assert _target(target_dir / "alpha") == (skills / "beta").resolve()
    out = capsys.readouterr().out
    assert "[FAILED]  alpha: disk says no; previous link to" in out and "restored" in out


def test_failed_refresh_says_when_the_restore_also_failed(env, monkeypatch, capsys):
    _, skills, target_dir, cfg = env
    target_dir.mkdir(parents=True)
    sync.make_link(skills / "beta", target_dir / "alpha")
    sync.make_link(skills / "beta", target_dir / "beta")  # already correct
    sync.make_link(skills / "_shared", target_dir / "_shared")
    _make_link_failing_for(skills / "alpha", monkeypatch, also_restore=True)

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["failed"] == 1
    assert "could not be restored either: disk says no" in capsys.readouterr().out


def test_failed_removal_of_old_link_keeps_it(env, monkeypatch, capsys):
    _, skills, target_dir, cfg = env
    target_dir.mkdir(parents=True)
    sync.make_link(skills / "beta", target_dir / "alpha")

    def refuse(p):
        raise OSError("rmdir failed: in use")

    monkeypatch.setattr(sync, "remove_link", refuse)
    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["failed"] == 1
    assert _target(target_dir / "alpha") == (skills / "beta").resolve()
    assert "[FAILED]  alpha: cannot remove old link: rmdir failed: in use" in capsys.readouterr().out


def test_remove_link_on_windows_reports_rmdir_error(monkeypatch, tmp_path):
    def rmdir_fails(cmd, **kwargs):
        raise sync.subprocess.CalledProcessError(2, cmd, output="", stderr="The process cannot access the file.\n")

    monkeypatch.setattr(sync.os, "name", "nt")
    monkeypatch.setattr(sync.subprocess, "run", rmdir_fails)
    with pytest.raises(OSError, match="rmdir failed: The process cannot access the file."):
        sync.remove_link(tmp_path / "x")


# ---------- unlink ----------

def test_unlink_removes_only_this_checkouts_links(env, tmp_path):
    _, skills, target_dir, cfg = env
    sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    other = tmp_path / "other-clone" / "gamma"
    other.mkdir(parents=True)
    sync.make_link(other, target_dir / "gamma")
    real = target_dir / "mine"
    real.mkdir()
    (real / "keep.txt").write_text("user file", encoding="utf-8")

    counts = sync.unlink_one(cfg, dry_run=True)
    assert counts == {"unlinked": 3, "failed": 0}
    assert sync.link_target(target_dir / "alpha") is not None  # dry run wrote nothing

    counts = sync.unlink_one(cfg, dry_run=False)
    assert counts == {"unlinked": 3, "failed": 0}
    for name in ("_shared", "alpha", "beta"):
        assert not (target_dir / name).exists()
        assert (skills / name).is_dir()  # the repo folders are untouched
    assert (skills / "alpha" / "SKILL.md").is_file()
    assert _target(target_dir / "gamma") == other.resolve()
    assert (real / "keep.txt").read_text(encoding="utf-8") == "user file"


def test_unlink_with_no_skills_folder_is_a_no_op(env):
    _, _, target_dir, cfg = env
    assert sync.unlink_one(cfg, dry_run=False) == {"unlinked": 0, "failed": 0}
    assert not target_dir.exists()


def test_unlink_failure_is_counted(env, monkeypatch, capsys):
    _, _, target_dir, cfg = env
    sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)

    def refuse(p):
        raise OSError("rmdir failed: in use")

    monkeypatch.setattr(sync, "remove_link", refuse)
    counts = sync.unlink_one(cfg, dry_run=False)
    assert counts == {"unlinked": 0, "failed": 3}
    assert "[FAILED]  unlink alpha: rmdir failed: in use" in capsys.readouterr().out


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
    worktree_skill = repo / ".claude" / "worktrees" / "x" / "skills" / "alpha"
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
    assert counts["failed"] == 1 and counts["linked"] == 0 and counts["link_failed"] == 0
    assert f"[FAILED]  cannot create {target_dir}: access denied" in capsys.readouterr().out


@pytest.mark.parametrize("counts, note", [({"failed": 1}, False), ({"failed": 1, "link_failed": 1}, True)])
def test_junction_note_only_follows_a_failed_link(monkeypatch, env, capsys, counts, note):
    monkeypatch.setattr(sync, "load_agents_config", lambda: [{"name": "codex"}])
    monkeypatch.setattr(sync, "sync_one", lambda cfg, *a: dict(counts))
    monkeypatch.setattr(sync.os, "name", "nt")
    monkeypatch.setattr(sync.sys, "argv", ["sync.py"])
    assert sync.main() == 1
    assert ("junction fallback" in capsys.readouterr().out) is note


def _main_on_nt(monkeypatch, cfg):
    """Run the real sync_one through main() as if on Windows; os.name is patched
    only after setup so the helpers still use this platform's link calls."""
    monkeypatch.setattr(sync, "load_agents_config", lambda: [cfg])
    monkeypatch.setattr(sync.sys, "argv", ["sync.py"])
    monkeypatch.setattr(sync.os, "name", "nt")
    return sync.main()


def test_junction_note_skipped_when_only_old_link_removal_failed(env, monkeypatch, capsys):
    _, skills, target_dir, cfg = env
    target_dir.mkdir(parents=True)
    sync.make_link(skills / "beta", target_dir / "alpha")  # stale, so it needs a refresh

    def refuse(p):
        raise OSError("rmdir failed: in use")

    monkeypatch.setattr(sync, "remove_link", refuse)
    assert _main_on_nt(monkeypatch, cfg) == 1
    out = capsys.readouterr().out
    assert "cannot remove old link" in out and "junction fallback" not in out


def test_junction_note_skipped_when_only_prune_failed(env, monkeypatch, capsys):
    _, skills, target_dir, cfg = env
    target_dir.mkdir(parents=True)
    sync.make_link(skills / "no-skill-md", target_dir / "orphan")

    def refuse(p):
        raise OSError("rmdir failed: in use")

    monkeypatch.setattr(sync, "remove_link", refuse)
    assert _main_on_nt(monkeypatch, cfg) == 1
    out = capsys.readouterr().out
    assert "[FAILED]  prune orphan" in out and "junction fallback" not in out


def test_junction_note_shown_when_make_link_failed(env, monkeypatch, capsys):
    _, _, _, cfg = env

    def refuse(src, dst):
        raise OSError("mklink /J failed: Access is denied.")

    monkeypatch.setattr(sync, "make_link", refuse)
    assert _main_on_nt(monkeypatch, cfg) == 1
    out = capsys.readouterr().out
    assert "[FAILED]  alpha: mklink /J failed" in out and "junction fallback" in out


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


def test_deleted_skill_whose_folder_kept_pycache_is_pruned(env):
    # git deletes SKILL.md and sync.py on a pull but leaves the ignored
    # __pycache__, so the folder survives; the link must still be pruned.
    _, skills, target_dir, cfg = env
    gone = skills / "gone"
    gone.mkdir()
    (gone / "SKILL.md").write_text("---\nname: gone\n---\n", encoding="utf-8")
    sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert sync.link_target(target_dir / "gone") is not None
    (gone / "SKILL.md").unlink()
    (gone / "__pycache__").mkdir()
    (gone / "__pycache__" / "sync.cpython-314.pyc").write_bytes(b"pyc")

    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["pruned"] == 1
    assert sync.link_target(target_dir / "gone") is None
    assert (gone / "__pycache__").is_dir()  # the repo folder itself is never touched
    assert sync.link_target(target_dir / "_shared") is not None  # _shared has no SKILL.md but stays


def test_alias_link_to_a_live_skill_is_not_pruned(env):
    _, skills, target_dir, cfg = env
    sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    sync.make_link(skills / "alpha", target_dir / "alpha-alias")
    counts = sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    assert counts["pruned"] == 0
    assert sync.link_target(target_dir / "alpha-alias") is not None


def _summary(out: str) -> str:
    return out[out.index("Summary"):]


def test_dry_run_summary_says_would(env, monkeypatch, capsys):
    _, _, _, cfg = env
    monkeypatch.setattr(sync, "load_agents_config", lambda: [cfg])
    monkeypatch.setattr(sync.sys, "argv", ["sync.py", "--dry-run"])
    assert sync.main() == 0
    summary = _summary(capsys.readouterr().out)
    assert summary.startswith("Summary (DRY-RUN: nothing was changed)")
    assert "would link: 3" in summary and "would refresh: 0" in summary and "would prune: 0" in summary
    assert " linked:" not in summary and " refreshed:" not in summary


def test_real_run_summary_has_plain_labels(env, monkeypatch, capsys):
    _, _, _, cfg = env
    monkeypatch.setattr(sync, "load_agents_config", lambda: [cfg])
    monkeypatch.setattr(sync.sys, "argv", ["sync.py"])
    assert sync.main() == 0
    summary = _summary(capsys.readouterr().out)
    assert summary.splitlines()[0] == "Summary"
    assert " linked: 3" in summary and "would" not in summary


def test_dry_run_unlink_summary_says_would(env, monkeypatch, capsys):
    _, _, _, cfg = env
    sync.sync_one(cfg, sync.list_repo_skills(), dry_run=False, force=False)
    monkeypatch.setattr(sync, "load_agents_config", lambda: [cfg])
    monkeypatch.setattr(sync.sys, "argv", ["sync.py", "--unlink", "--dry-run"])
    assert sync.main() == 0
    summary = _summary(capsys.readouterr().out)
    assert summary.startswith("Summary (DRY-RUN") and "would unlink: 3" in summary


@pytest.mark.parametrize("content", ["{not json", '{"agents": {"name": "x"}}', '{"agents": [{"home": "x"}]}', "[]",
                                     '{"agents": [{"name": "x", "default_home": "~/.x", "default": "false"}]}'])
def test_malformed_agents_json_exits_2(tmp_path, monkeypatch, capsys, content):
    (tmp_path / "agents.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(sync, "script_dir", lambda: tmp_path)
    with pytest.raises(SystemExit) as exc:
        sync.load_agents_config()
    assert exc.value.code == 2
    assert "agents.json" in capsys.readouterr().err


# Without these checks an entry missing "default_home" made home_for() return
# "" and the links went into ./skills under the current directory, and a string
# "env_home_vars" was read one character at a time and silently ignored.
@pytest.mark.parametrize("entry, field", [
    ({"name": "x"}, "default_home"),
    ({"name": "x", "default_home": ""}, "default_home"),
    ({"name": "x", "default_home": "   "}, "default_home"),
    ({"name": "x", "default_home": 5}, "default_home"),
    ({"name": "x", "default_home": "~/.x", "env_home_vars": "X_HOME"}, "env_home_vars"),
    ({"name": "x", "default_home": "~/.x", "env_home_vars": ["X_HOME", 3]}, "env_home_vars"),
    ({"name": "x", "default_home": "~/.x", "env_home_vars": [""]}, "env_home_vars"),
    ({"name": "x", "default_home": "~/.x", "skills_subdir": ""}, "skills_subdir"),
    ({"name": "x", "default_home": "~/.x", "env_home_subdir": None}, "env_home_subdir"),
])
def test_bad_agent_field_exits_2_naming_it(tmp_path, monkeypatch, capsys, entry, field):
    (tmp_path / "agents.json").write_text(json.dumps({"agents": [entry]}), encoding="utf-8")
    monkeypatch.setattr(sync, "script_dir", lambda: tmp_path)
    with pytest.raises(SystemExit) as exc:
        sync.load_agents_config()
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert f'"{field}"' in err and "agents: ['x']" in err


def test_duplicate_agent_names_exit_2(tmp_path, monkeypatch, capsys):
    entry = {"name": "x", "default_home": "~/.x"}
    (tmp_path / "agents.json").write_text(json.dumps({"agents": [entry, entry]}), encoding="utf-8")
    monkeypatch.setattr(sync, "script_dir", lambda: tmp_path)
    with pytest.raises(SystemExit) as exc:
        sync.load_agents_config()
    assert exc.value.code == 2
    assert "unique" in capsys.readouterr().err


def test_minimal_valid_entry_is_accepted(tmp_path, monkeypatch):
    (tmp_path / "agents.json").write_text('{"agents": [{"name": "x", "default_home": "~/.x"}]}', encoding="utf-8")
    monkeypatch.setattr(sync, "script_dir", lambda: tmp_path)
    assert sync.load_agents_config() == [{"name": "x", "default_home": "~/.x"}]


def test_shipped_agents_json_is_valid():
    agents = sync.load_agents_config()
    assert [a["name"] for a in agents] == ["claude", "codex", "gemini"]
    # Claude Code loads the repo's skills/ and .claude/skills/ itself; linking into
    # ~/.claude/skills would make every skill global and duplicate the plugin's.
    assert [a.get("default", True) for a in agents] == [False, True, True]
    # Codex reads user skills from $HOME/.agents/skills, not ~/.codex/skills.
    codex = agents[1]
    assert (codex["default_home"], codex["skills_subdir"], codex["env_home_vars"]) == ("~/.agents", "skills", [])


def _run_main(monkeypatch, env, argv, unlink_result=None):
    """Run main() with sync_one and unlink_one stubbed out; return the agent names called."""
    called = []
    monkeypatch.setattr(sync, "load_agents_config",
                        lambda: [{"name": "claude", "default": False}, {"name": "codex"}, {"name": "gemini"}])
    monkeypatch.setattr(sync, "sync_one", lambda cfg, *a: called.append(cfg["name"]) or {"failed": 0})
    monkeypatch.setattr(sync, "unlink_one", lambda cfg, *a: called.append("unlink:" + cfg["name"])
                        or dict(unlink_result or {"unlinked": 1, "failed": 0}))
    monkeypatch.setattr(sync.sys, "argv", ["sync.py", *argv])
    return sync.main(), called


def test_default_leaves_claude_out(monkeypatch, env):
    rc, called = _run_main(monkeypatch, env, [])
    assert rc == 0 and called == ["codex", "gemini"]


def test_agents_claude_opts_in(monkeypatch, env):
    rc, called = _run_main(monkeypatch, env, ["--agents", "claude"])
    assert rc == 0 and called == ["claude"]


def test_unlink_uses_the_same_agent_selection(monkeypatch, env):
    rc, called = _run_main(monkeypatch, env, ["--unlink", "--agents", "claude"])
    assert rc == 0 and called == ["unlink:claude"]
    rc, called = _run_main(monkeypatch, env, ["--unlink"])
    assert rc == 0 and called == ["unlink:codex", "unlink:gemini"]


def test_unlink_failure_exits_1(monkeypatch, env, capsys):
    rc, _ = _run_main(monkeypatch, env, ["--unlink", "--agents", "codex"], {"unlinked": 0, "failed": 2})
    assert rc == 1
    assert "failed: 2" in capsys.readouterr().out


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
