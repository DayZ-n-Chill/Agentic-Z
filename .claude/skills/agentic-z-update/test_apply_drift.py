"""Tests for apply_drift (overwrite, delete, keep/take on conflicts) and the dirty-tree refusal.

git is never called: subprocess.run is replaced with a fake that records each
`git checkout <ref> -- <path>` and writes the "upstream" bytes to disk.
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "agentic_z_update_mod", Path(__file__).resolve().parent / "update.py"
)
update = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(update)
S = update.FileStatus
REF = "upstream/main"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Temp cwd plus a fake `git checkout` that writes UPSTREAM:<path> into the file."""
    monkeypatch.chdir(tmp_path)
    state = {"checkouts": [], "fail": set()}

    def fake_run(cmd, *a, **k):
        assert cmd[:2] == ["git", "checkout"], cmd
        ref, path = cmd[2], cmd[4]
        state["checkouts"].append((ref, path))
        if path in state["fail"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="pathspec error")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(f"UPSTREAM:{path}", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(update.subprocess, "run", fake_run)
    return state


def _write(path: str, text: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(text, encoding="utf-8")


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_safe_overwrite_and_new_take_upstream(repo):
    _write("docs/a.md", "old")
    applied, skipped = update.apply_drift({"docs/a.md": S.SAFE_OVERWRITE, "docs/b.md": S.NEW}, REF)
    assert applied == ["docs/a.md", "docs/b.md"]
    assert skipped == []
    assert _read("docs/a.md") == "UPSTREAM:docs/a.md"
    assert _read("docs/b.md") == "UPSTREAM:docs/b.md"
    assert repo["checkouts"] == [(REF, "docs/a.md"), (REF, "docs/b.md")]


def test_failed_checkout_is_skipped(repo):
    _write("docs/a.md", "old")
    repo["fail"].add("docs/a.md")
    applied, skipped = update.apply_drift({"docs/a.md": S.SAFE_OVERWRITE}, REF)
    assert (applied, skipped) == ([], ["docs/a.md"])
    assert _read("docs/a.md") == "old"


def test_deleted_clean_removes_file(repo):
    _write("scripts/old.py", "x")
    applied, skipped = update.apply_drift({"scripts/old.py": S.DELETED_CLEAN}, REF)
    assert applied == ["scripts/old.py"]
    assert not Path("scripts/old.py").exists()


def test_deleted_clean_already_gone_counts_as_applied(repo):
    applied, skipped = update.apply_drift({"scripts/gone.py": S.DELETED_CLEAN}, REF)
    assert (applied, skipped) == (["scripts/gone.py"], [])


def test_local_only_edit_is_left_alone(repo):
    _write("CLAUDE.md", "mine")
    applied, skipped = update.apply_drift({"CLAUDE.md": S.LOCAL_ONLY_EDIT}, REF)
    assert (applied, skipped) == ([], ["CLAUDE.md"])
    assert _read("CLAUDE.md") == "mine"
    assert repo["checkouts"] == []


def test_conflicts_kept_by_default(repo):
    _write("docs/c.md", "mine")
    _write("docs/d.md", "mine")
    drift = {"docs/c.md": S.CONFLICT, "docs/d.md": S.DELETED_CONFLICT}
    applied, skipped = update.apply_drift(drift, REF)
    assert (applied, skipped) == ([], ["docs/c.md", "docs/d.md"])
    assert _read("docs/c.md") == "mine"
    assert Path("docs/d.md").exists()
    assert repo["checkouts"] == []


def test_conflicts_explicit_keep_leaves_files(repo):
    _write("docs/c.md", "mine")
    _write("docs/d.md", "mine")
    drift = {"docs/c.md": S.CONFLICT, "docs/d.md": S.DELETED_CONFLICT}
    applied, skipped = update.apply_drift(drift, REF, {"docs/c.md": "keep", "docs/d.md": "keep"})
    assert applied == []
    assert _read("docs/c.md") == "mine"
    assert Path("docs/d.md").exists()


def test_conflict_take_checks_out_upstream(repo):
    _write("docs/c.md", "mine")
    applied, skipped = update.apply_drift({"docs/c.md": S.CONFLICT}, REF, {"docs/c.md": "take"})
    assert applied == ["docs/c.md"]
    assert _read("docs/c.md") == "UPSTREAM:docs/c.md"


def test_deleted_conflict_take_deletes_file(repo):
    _write("docs/d.md", "mine")
    applied, skipped = update.apply_drift({"docs/d.md": S.DELETED_CONFLICT}, REF, {"docs/d.md": "take"})
    assert applied == ["docs/d.md"]
    assert not Path("docs/d.md").exists()
    assert repo["checkouts"] == []


# ---------- dirty-tree refusal in main() ----------

def test_dirty_tree_refuses_before_touching_remote(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["update.py", "--yes"])
    monkeypatch.setattr(update, "is_git_repo", lambda: True)
    monkeypatch.setattr(update, "working_tree_clean_for", lambda paths: (False, [".claude/skills/x/SKILL.md"]))

    def must_not_run():
        raise AssertionError("ensure_upstream should not run on a dirty tree")

    monkeypatch.setattr(update, "ensure_upstream", must_not_run)
    assert update.main() == 1
    out = capsys.readouterr().out
    assert "uncommitted changes" in out
    assert ".claude/skills/x/SKILL.md" in out


def test_force_skips_dirty_tree_check(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["update.py", "--force", "--yes"])
    monkeypatch.setattr(update, "is_git_repo", lambda: True)

    def must_not_check(paths):
        raise AssertionError("--force should skip the dirty-tree check")

    monkeypatch.setattr(update, "working_tree_clean_for", must_not_check)
    monkeypatch.setattr(update, "ensure_upstream", lambda: False)  # stop right after the check
    assert update.main() == 1


def test_working_tree_clean_for_parses_porcelain(monkeypatch):
    out = " M .claude/skills/a/SKILL.md\n?? docs/new.md\n"
    monkeypatch.setattr(update, "run", lambda *a, **k: SimpleNamespace(stdout=out, returncode=0))
    assert update.working_tree_clean_for(update.TEMPLATE_PATHS) == (
        False,
        [".claude/skills/a/SKILL.md", "docs/new.md"],
    )
    monkeypatch.setattr(update, "run", lambda *a, **k: SimpleNamespace(stdout="", returncode=0))
    assert update.working_tree_clean_for(update.TEMPLATE_PATHS) == (True, [])
