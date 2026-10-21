"""Tests for apply_drift (overwrite, delete, keep/take on conflicts) and the dirty-tree refusal.

git is not called by the apply tests: subprocess.run is replaced with a fake that
records each `git checkout <ref> -- <path>` and writes the "upstream" bytes to disk.
The commit test uses a throwaway git repo under tmp_path.
"""
import importlib.util
import shutil
import subprocess
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
    monkeypatch.setattr(update, "repo_root", lambda: Path.cwd())
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
    monkeypatch.setattr(update, "repo_root", lambda: Path.cwd())

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


# ---------- baseline advance after apply ----------

@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_baseline_advances_when_commit_succeeds_and_nothing_pending(in_tmp, monkeypatch):
    monkeypatch.setattr(update, "stage_and_commit", lambda applied, sha: True)
    drift = {"docs/a.md": S.SAFE_OVERWRITE, "docs/mine.md": S.LOCAL_ONLY_EDIT}
    assert update.finish_apply(drift, ["docs/a.md"], ["docs/mine.md"], "a" * 40) == "advanced"
    assert update.read_baseline() == "a" * 40


@pytest.mark.parametrize("status", [S.CONFLICT, S.DELETED_CONFLICT, S.SAFE_OVERWRITE])
def test_baseline_kept_when_upstream_change_left_unapplied(in_tmp, monkeypatch, status):
    monkeypatch.setattr(update, "stage_and_commit", lambda applied, sha: True)
    update.write_baseline("b" * 40)
    drift = {"docs/a.md": S.NEW, "docs/c.md": status}
    assert update.finish_apply(drift, ["docs/a.md"], ["docs/c.md"], "a" * 40) == "pending"
    assert update.read_baseline() == "b" * 40


def test_baseline_kept_when_commit_fails(in_tmp, monkeypatch):
    monkeypatch.setattr(update, "stage_and_commit", lambda applied, sha: False)
    update.write_baseline("b" * 40)
    assert update.finish_apply({"docs/a.md": S.NEW}, ["docs/a.md"], [], "a" * 40) == "commit-failed"
    assert update.read_baseline() == "b" * 40


def test_nothing_applied_skips_commit_but_advances(in_tmp, monkeypatch):
    def must_not_commit(applied, sha):
        raise AssertionError("no commit without applied paths")

    monkeypatch.setattr(update, "stage_and_commit", must_not_commit)
    assert update.finish_apply({"docs/m.md": S.LOCAL_ONLY_EDIT}, [], ["docs/m.md"], "a" * 40) == "advanced"
    assert update.read_baseline() == "a" * 40


# ---------- --check is read-only; main() runs from the repo root ----------

def _stub_remote(monkeypatch, root):
    monkeypatch.setattr(update, "repo_root", lambda: root)
    monkeypatch.setattr(update, "ensure_upstream", lambda: True)
    monkeypatch.setattr(update, "fetch_upstream", lambda: True)
    monkeypatch.setattr(update, "upstream_head_sha", lambda: "c" * 40)
    monkeypatch.setattr(update, "search_index_update_available", lambda: None)


def test_check_without_baseline_writes_nothing(in_tmp, monkeypatch, capsys):
    _stub_remote(monkeypatch, in_tmp)
    monkeypatch.setattr(update, "_QUIET", False)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check"])
    assert update.main() == 1
    assert "no update baseline" in capsys.readouterr().out
    assert not (in_tmp / update.BASELINE_FILE).exists()


def test_quiet_check_without_baseline_prints_nudge_and_exits_0(in_tmp, monkeypatch, capsys):
    """The SessionStart hook output is dropped on a non-zero exit, so quiet mode exits 0."""
    _stub_remote(monkeypatch, in_tmp)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check", "--quiet"])
    assert update.main() == 0
    assert "no update baseline" in capsys.readouterr().out
    assert not (in_tmp / update.BASELINE_FILE).exists()


def test_quiet_check_with_drift_prints_nudge_and_exits_0(in_tmp, monkeypatch, capsys):
    _stub_remote(monkeypatch, in_tmp)
    update.write_baseline("b" * 40)
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: {"docs/a.md": S.SAFE_OVERWRITE})
    monkeypatch.setattr(sys, "argv", ["update.py", "--check", "--quiet"])
    assert update.main() == 0
    assert capsys.readouterr().out.strip()


def test_check_with_drift_exits_1_without_quiet(in_tmp, monkeypatch, capsys):
    _stub_remote(monkeypatch, in_tmp)
    update.write_baseline("b" * 40)
    monkeypatch.setattr(update, "_QUIET", False)
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: {"docs/a.md": S.SAFE_OVERWRITE})
    monkeypatch.setattr(sys, "argv", ["update.py", "--check"])
    assert update.main() == 1


def test_check_with_baseline_leaves_it_unchanged(in_tmp, monkeypatch, capsys):
    _stub_remote(monkeypatch, in_tmp)
    update.write_baseline("b" * 40)
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: {})
    monkeypatch.setattr(sys, "argv", ["update.py", "--check"])
    assert update.main() == 0
    assert "Up to date." in capsys.readouterr().out
    assert update.read_baseline() == "b" * 40


def _stub_apply_flow(monkeypatch, root):
    _stub_remote(monkeypatch, root)
    monkeypatch.setattr(update, "_QUIET", False)  # an earlier --quiet test sets the global
    monkeypatch.setattr(update, "working_tree_clean_for", lambda paths: (True, []))
    monkeypatch.setattr(update, "run_sync_skills", lambda: None)


def test_first_run_records_baseline_and_restores_no_missing_files(in_tmp, monkeypatch, capsys):
    """On the first run the baseline is upstream, so a missing template file is locally-deleted."""
    _stub_apply_flow(monkeypatch, in_tmp)
    seen = {}

    def fake_drift(baseline, ref):
        seen["baseline"] = baseline
        return {"docs/missing.md": update.classify_per_file(b"x", None, b"x")}

    monkeypatch.setattr(update, "compute_drift", fake_drift)
    monkeypatch.setattr(update.subprocess, "run", lambda *a, **k: pytest.fail("nothing may be checked out"))
    monkeypatch.setattr(sys, "argv", ["update.py", "--yes"])
    assert update.main() == 0
    assert seen["baseline"] == "c" * 40
    assert update.read_baseline() == "c" * 40
    assert not (in_tmp / "docs/missing.md").exists()
    assert "deleted in this clone" in capsys.readouterr().out


def test_first_run_baseline_write_happens_under_the_lock(in_tmp, monkeypatch):
    _stub_apply_flow(monkeypatch, in_tmp)
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: {})
    real_write = update.write_baseline

    def checked_write(sha):
        assert (in_tmp / update.LOCK_FILE).exists(), "baseline written without the lock"
        real_write(sha)

    monkeypatch.setattr(update, "write_baseline", checked_write)
    monkeypatch.setattr(sys, "argv", ["update.py", "--yes"])
    assert update.main() == 0
    assert update.read_baseline() == "c" * 40
    assert not (in_tmp / update.LOCK_FILE).exists()


def test_first_run_refused_while_another_update_holds_the_lock(in_tmp, monkeypatch):
    _stub_apply_flow(monkeypatch, in_tmp)
    update.write_lock()
    monkeypatch.setattr(update, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(sys, "argv", ["update.py", "--yes"])
    assert update.main() == 1
    assert update.read_baseline() is None
    update.release_lock()


# ---------- the template path list covers every tracked template folder ----------

# Tracked top-level folders that belong to the upstream repo itself, not the template.
NOT_TEMPLATE = {".github"}


def test_template_paths_cover_every_tracked_top_level_folder():
    root = Path(__file__).resolve().parents[3]
    files = subprocess.run(
        ["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    folders = {f.split("/", 1)[0] for f in files if "/" in f}
    folders |= {"/".join(f.split("/", 2)[:2]) for f in files if f.startswith(".claude/")}
    folders.discard(".claude")

    def covered(path):
        return any(path == t or path.startswith(t + "/") for t in update.TEMPLATE_PATHS)

    missing = sorted(f for f in folders if f not in NOT_TEMPLATE and not covered(f))
    assert not missing, f"tracked template folders missing from TEMPLATE_PATHS: {missing}"
    for f in ("hooks", ".claude/settings.json", "mods", "evals", ".claude-plugin", ".mcp.json"):
        assert f in update.TEMPLATE_PATHS


# ---------- locally-deleted ----------

def test_locally_deleted_classification():
    assert update.classify_per_file(baseline=b"v1", local=None, upstream=b"v1") == S.LOCALLY_DELETED
    assert update.classify_per_file(baseline=b"v1", local=None, upstream=b"v2") == S.LOCALLY_DELETED
    assert update.classify_per_file(baseline=None, local=None, upstream=b"v1") == S.NEW


def test_locally_deleted_left_alone_by_default(repo):
    applied, skipped = update.apply_drift({"docs/gone.md": S.LOCALLY_DELETED}, REF)
    assert (applied, skipped) == ([], ["docs/gone.md"])
    assert not Path("docs/gone.md").exists()
    assert repo["checkouts"] == []


def test_locally_deleted_take_restores_upstream(repo):
    applied, _ = update.apply_drift({"docs/gone.md": S.LOCALLY_DELETED}, REF, {"docs/gone.md": "take"})
    assert applied == ["docs/gone.md"]
    assert _read("docs/gone.md") == "UPSTREAM:docs/gone.md"


def test_per_file_offers_locally_deleted(monkeypatch):
    answers = iter(["t", "k"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    drift = {"docs/gone.md": S.LOCALLY_DELETED, "docs/c.md": S.CONFLICT, "docs/x.md": S.SAFE_OVERWRITE}
    assert update.resolve_conflicts_per_file(drift, REF) == {"docs/gone.md": "take", "docs/c.md": "keep"}


def test_locally_deleted_does_not_hold_baseline(in_tmp, monkeypatch):
    monkeypatch.setattr(update, "stage_and_commit", lambda applied, sha: True)
    drift = {"docs/gone.md": S.LOCALLY_DELETED}
    assert update.finish_apply(drift, [], ["docs/gone.md"], "a" * 40) == "advanced"


def test_check_ignores_local_choices(in_tmp, monkeypatch, capsys):
    _stub_remote(monkeypatch, in_tmp)
    update.write_baseline("b" * 40)
    drift = {"docs/gone.md": S.LOCALLY_DELETED, "docs/mine.md": S.LOCAL_ONLY_EDIT}
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: dict(drift))
    monkeypatch.setattr(update, "_QUIET", False)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check"])
    assert update.main() == 0
    assert "Up to date." in capsys.readouterr().out


# ---------- the update commit contains only the applied paths ----------

def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_commit_excludes_other_staged_changes(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    for key, val in [("user.name", "t"), ("user.email", "t@example.com"),
                     ("commit.gpgsign", "false"), ("core.hooksPath", ".no-hooks")]:
        _git(tmp_path, "config", key, val)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/a.md").write_text("old", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("v1", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "init")

    (tmp_path / "notes.txt").write_text("user's staged edit", encoding="utf-8")
    _git(tmp_path, "add", "notes.txt")
    (tmp_path / "docs/a.md").write_text("upstream", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update, "_QUIET", True)
    assert update.stage_and_commit(["docs/a.md"], "d" * 40) is True
    assert _git(tmp_path, "show", "--name-only", "--format=", "HEAD").split() == ["docs/a.md"]
    assert _git(tmp_path, "diff", "--cached", "--name-only").split() == ["notes.txt"]


def test_later_run_applies_new_files(in_tmp, monkeypatch):
    _stub_apply_flow(monkeypatch, in_tmp)
    update.write_baseline("b" * 40)
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: {"docs/new.md": S.NEW})
    seen = []
    monkeypatch.setattr(update, "apply_drift", lambda drift, ref, conflict_choices=None: (seen.extend(drift) or (list(drift), [])))
    monkeypatch.setattr(update, "stage_and_commit", lambda applied, sha: True)
    monkeypatch.setattr(sys, "argv", ["update.py", "--yes"])
    assert update.main() == 0
    assert seen == ["docs/new.md"]


def test_main_exits_1_when_commit_fails(in_tmp, monkeypatch):
    _stub_apply_flow(monkeypatch, in_tmp)
    update.write_baseline("b" * 40)
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: {"docs/a.md": S.SAFE_OVERWRITE})
    monkeypatch.setattr(update, "apply_drift", lambda drift, ref, conflict_choices=None: (["docs/a.md"], []))
    monkeypatch.setattr(update, "stage_and_commit", lambda applied, sha: False)
    monkeypatch.setattr(sys, "argv", ["update.py", "--yes"])
    assert update.main() == 1
    assert update.read_baseline() == "b" * 40
    assert not (in_tmp / update.LOCK_FILE).exists()


def test_main_chdirs_to_repo_root(tmp_path, monkeypatch):
    root = tmp_path / "clone"
    sub = root / "workspace" / "MyMod"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    seen = []
    monkeypatch.setattr(update, "repo_root", lambda: root)
    monkeypatch.setattr(update, "ensure_upstream", lambda: seen.append(Path.cwd()) or False)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check"])
    assert update.main() == 1
    assert seen == [root]


def test_not_a_repo_exits_1(monkeypatch):
    monkeypatch.setattr(update, "repo_root", lambda: None)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check"])
    assert update.main() == 1


# ---------- upstream remote check ----------

@pytest.mark.parametrize("url", [
    "https://github.com/DayZ-n-Chill/Agentic-Z.git",
    "https://github.com/DayZ-n-Chill/Agentic-Z",
    "https://github.com/DayZ-n-Chill/Agentic-Z/",
    "https://github.com/dayz-n-chill/agentic-z.git",
])
def test_ensure_upstream_accepts_equivalent_urls(monkeypatch, url):
    monkeypatch.setattr(update, "remote_url", lambda name: url)
    assert update.ensure_upstream() is True


@pytest.mark.parametrize("url", [
    "https://github.com/DayZ-n-Chill/Agentic-Z-fork.git",
    "https://github.com/someone/Agentic-Z.git",
    "https://github.com/DayZ-n-Chill/Agentic",
])
def test_ensure_upstream_rejects_other_repos(monkeypatch, url):
    monkeypatch.setattr(update, "remote_url", lambda name: url)
    assert update.ensure_upstream() is False


def test_is_newer_handles_mixed_tags():
    assert update._is_newer("v1.10", "v1.9")
    assert not update._is_newer("v1.2", "v1.2")
    assert update._is_newer("v1.2.rc", "v1.2.1")  # non-numeric part sorts after numbers


# ---------- drift compares git blob ids, not raw bytes ----------

@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_crlf_working_copy_is_not_a_local_edit(tmp_path, monkeypatch):
    """With core.autocrlf=true, an untouched file checked out as CRLF still
    matches its LF baseline blob, so an upstream change is SAFE_OVERWRITE (raw
    byte comparison would call it a CONFLICT)."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_bytes(b"one\ntwo\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "baseline")
    baseline = _git(tmp_path, "rev-parse", "HEAD").strip()
    _git(tmp_path, "checkout", "-q", "-b", "up")
    (tmp_path / "docs" / "a.md").write_bytes(b"one\ntwo\nthree\n")
    _git(tmp_path, "commit", "-q", "-am", "upstream change")
    _git(tmp_path, "checkout", "-q", baseline)
    _git(tmp_path, "config", "core.autocrlf", "true")
    (tmp_path / "docs" / "a.md").write_bytes(b"one\r\ntwo\r\n")  # what a CRLF checkout writes

    monkeypatch.chdir(tmp_path)
    assert update.compute_drift(baseline, "up") == {"docs/a.md": S.SAFE_OVERWRITE}

    (tmp_path / "docs" / "a.md").write_bytes(b"one\r\nlocal\r\n")  # a real local edit
    assert update.compute_drift(baseline, "up") == {"docs/a.md": S.CONFLICT}
