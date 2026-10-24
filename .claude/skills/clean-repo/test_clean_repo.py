"""Tests for clean-repo/clean.py: discovery, TTY refusal, dry-run-first ordering, plan pinning, project refusal."""
import importlib.util
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "clean_repo_clean", Path(__file__).resolve().parent / "clean.py"
)
clean = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(clean)


def _skill(root: Path, name: str, with_script: bool = True) -> Path:
    d = root / name
    d.mkdir(parents=True)
    if with_script:
        (d / "clean.py").write_text("", encoding="utf-8")
    return d


@pytest.fixture
def skills_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(clean, "SKILLS_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def calls(monkeypatch):
    """Record child invocations; return codes are looked up per (skill, mode).

    record["out"][skill] is the dry-run stdout: bytes, or a list of bytes used
    one per dry run (to simulate the plan changing between runs).
    """
    record = {"cmds": [], "rc": {}, "out": {}, "err": {}, "env": []}
    real_run = subprocess.run

    def fake_run(cmd, *a, **k):
        if cmd[0] == "git":  # versioned_server_files asks real git; only children are faked
            return real_run(cmd, *a, **k)
        record["cmds"].append(cmd)
        record["env"].append(k.get("env"))
        name = Path(cmd[1]).parent.name
        out = record["out"].get(name, b"Plan: 1 item(s) to remove\n")
        if isinstance(out, list):
            out = out.pop(0) if len(out) > 1 else out[0]
        dry = cmd[-1] == "--dry-run"
        return SimpleNamespace(
            returncode=record["rc"].get((name, cmd[-1]), 0),
            stdout=out if dry else None,
            stderr=record["err"].get(name, b"") if dry else None,
        )

    monkeypatch.setattr(clean.subprocess, "run", fake_run)
    return record


def _modes(record):
    return [(Path(c[1]).parent.name, c[-1]) for c in record["cmds"]]


def test_discovery_filters_by_name_script_and_underscore(skills_dir):
    _skill(skills_dir, "dayz-clean-workspace")
    _skill(skills_dir, "web-clean-workspace")
    _skill(skills_dir, "_shared-clean-workspace")
    _skill(skills_dir, "noscript-clean-workspace", with_script=False)
    _skill(skills_dir, "dayz-build-pbo")
    (skills_dir / "file-clean-workspace").write_text("", encoding="utf-8")
    assert [p.name for p in clean.find_cleanup_skills()] == [
        "dayz-clean-workspace",
        "web-clean-workspace",
    ]


def test_non_tty_without_yes_refuses_before_running_anything(skills_dir, calls, monkeypatch):
    _skill(skills_dir, "dayz-clean-workspace")
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: False)
    assert clean.main([]) == 2
    assert calls["cmds"] == []


def test_dry_run_runs_only_dry_runs_even_without_tty(skills_dir, calls, monkeypatch):
    _skill(skills_dir, "a-clean-workspace")
    _skill(skills_dir, "b-clean-workspace")
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: False)
    assert clean.main(["--dry-run"]) == 0
    assert _modes(calls) == [("a-clean-workspace", "--dry-run"), ("b-clean-workspace", "--dry-run")]
    assert all("--include-server" in c for c in calls["cmds"])


def test_yes_runs_all_dry_runs_before_any_removal(skills_dir, calls):
    _skill(skills_dir, "a-clean-workspace")
    _skill(skills_dir, "b-clean-workspace")
    assert clean.main(["--yes"]) == 0
    assert _modes(calls) == [
        ("a-clean-workspace", "--dry-run"),
        ("b-clean-workspace", "--dry-run"),
        ("a-clean-workspace", "--yes"),
        ("b-clean-workspace", "--yes"),
    ]


def test_failed_dry_run_aborts_before_removal(skills_dir, calls):
    _skill(skills_dir, "a-clean-workspace")
    calls["rc"][("a-clean-workspace", "--dry-run")] = 1
    assert clean.main(["--yes"]) == 1
    assert _modes(calls) == [("a-clean-workspace", "--dry-run")]


def test_dry_run_failure_exits_1(skills_dir, calls):
    _skill(skills_dir, "a-clean-workspace")
    calls["rc"][("a-clean-workspace", "--dry-run")] = 3
    assert clean.main(["--dry-run"]) == 1


def test_declined_confirmation_removes_nothing(skills_dir, calls, monkeypatch):
    _skill(skills_dir, "a-clean-workspace")
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    assert clean.main([]) == 0
    assert _modes(calls) == [("a-clean-workspace", "--dry-run")]


def test_confirmed_run_reports_child_failure(skills_dir, calls, monkeypatch):
    _skill(skills_dir, "a-clean-workspace")
    calls["rc"][("a-clean-workspace", "--yes")] = 1
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert clean.main([]) == 1
    assert _modes(calls)[-1] == ("a-clean-workspace", "--yes")


def _plan_id(capsys) -> str:
    out = capsys.readouterr().out
    return next(line.split(": ", 1)[1] for line in out.splitlines() if line.startswith("Plan ID: "))


def test_dry_run_prints_child_output_and_a_plan_id(skills_dir, calls, capsys):
    _skill(skills_dir, "a-clean-workspace")
    calls["out"]["a-clean-workspace"] = b"  (mod) workspace/Foo\n"
    assert clean.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "=== /a-clean-workspace (--dry-run) ===\n  (mod) workspace/Foo\n" in out
    assert "--yes --plan " in out
    assert any(line.startswith("Plan ID: ") and len(line) == len("Plan ID: ") + 12 for line in out.splitlines())


def test_plan_id_changes_with_child_output_and_server_mode(skills_dir, calls, capsys):
    _skill(skills_dir, "a-clean-workspace")
    calls["out"]["a-clean-workspace"] = b"  (mod) workspace/Foo\n"
    clean.main(["--dry-run"])
    first = _plan_id(capsys)
    clean.main(["--dry-run"])
    assert _plan_id(capsys) == first
    clean.main(["--dry-run", "--keep-server"])
    assert _plan_id(capsys) != first
    calls["out"]["a-clean-workspace"] = b"  (mod) workspace/Foo\n  (mod) workspace/Bar\n"
    clean.main(["--dry-run"])
    assert _plan_id(capsys) != first


def test_yes_with_matching_plan_removes(skills_dir, calls, capsys):
    _skill(skills_dir, "a-clean-workspace")
    clean.main(["--dry-run"])
    plan = _plan_id(capsys)
    calls["cmds"].clear()
    assert clean.main(["--yes", "--plan", plan]) == 0
    assert _modes(calls) == [("a-clean-workspace", "--dry-run"), ("a-clean-workspace", "--yes")]


def test_yes_with_stale_plan_refuses_and_removes_nothing(skills_dir, calls, capsys):
    """Something appeared after the approved dry run: it must not be removed unseen."""
    _skill(skills_dir, "a-clean-workspace")
    calls["out"]["a-clean-workspace"] = b"  (mod) workspace/Foo\n"
    clean.main(["--dry-run"])
    plan = _plan_id(capsys)
    calls["out"]["a-clean-workspace"] = b"  (mod) workspace/Foo\n  (mod) workspace/NewMod\n"
    calls["cmds"].clear()
    assert clean.main(["--yes", "--plan", plan]) == 3
    assert ("a-clean-workspace", "--yes") not in _modes(calls)
    assert "The plan changed since it was approved" in capsys.readouterr().err


def test_plan_that_changes_at_the_prompt_is_not_removed(skills_dir, calls, monkeypatch, capsys):
    _skill(skills_dir, "a-clean-workspace")
    calls["out"]["a-clean-workspace"] = [b"  (mod) workspace/Foo\n", b"  (mod) workspace/Foo\n  (mod) workspace/New\n"]
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert clean.main([]) == 3
    assert _modes(calls) == [("a-clean-workspace", "--dry-run"), ("a-clean-workspace", "--dry-run")]
    assert "changed while waiting for confirmation" in capsys.readouterr().err


def test_confirmed_unchanged_plan_rechecks_then_removes(skills_dir, calls, monkeypatch):
    _skill(skills_dir, "a-clean-workspace")
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    assert clean.main([]) == 0
    assert _modes(calls) == [
        ("a-clean-workspace", "--dry-run"),
        ("a-clean-workspace", "--dry-run"),
        ("a-clean-workspace", "--yes"),
    ]


def test_children_get_utf8_output_encoding(skills_dir, calls):
    _skill(skills_dir, "a-clean-workspace")
    assert clean.main(["--yes"]) == 0
    assert all(env["PYTHONIOENCODING"] == "utf-8" for env in calls["env"])


def _cache_project(skills_dir: Path, project: Path) -> None:
    """A dayz-init/state.py stand in whose cached project root is `project`."""
    d = skills_dir / "dayz-init"
    d.mkdir()
    (d / "state.py").write_text(
        "from pathlib import Path\n"
        f"def cached_project_root():\n    return Path({str(project)!r})\n",
        encoding="utf-8",
    )


def test_other_cached_project_refuses_without_flag(skills_dir, calls, tmp_path, capsys):
    _skill(skills_dir, "a-clean-workspace")
    other = tmp_path / "other-clone"
    other.mkdir()
    _cache_project(skills_dir, other)
    assert clean.main(["--yes"]) == 2
    assert calls["cmds"] == []
    err = capsys.readouterr().err
    assert f"Cleanup would target the cached project {other.resolve()}, not this checkout {clean.REPO_ROOT}" in err
    assert "--other-project" in err


def test_other_cached_project_dry_run_warns_only(skills_dir, calls, tmp_path, capsys):
    _skill(skills_dir, "a-clean-workspace")
    other = tmp_path / "other-clone"
    other.mkdir()
    _cache_project(skills_dir, other)
    assert clean.main(["--dry-run"]) == 0
    assert _modes(calls) == [("a-clean-workspace", "--dry-run")]
    assert f"[WARN] Cleanup targets the cached project {other.resolve()}" in capsys.readouterr().out


def test_other_cached_project_with_flag_warns_and_is_named_in_the_prompt(skills_dir, calls, monkeypatch, tmp_path, capsys):
    _skill(skills_dir, "a-clean-workspace")
    other = tmp_path / "other-clone"
    other.mkdir()
    _cache_project(skills_dir, other)
    prompts = []
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "n")
    assert clean.main(["--other-project"]) == 0
    out = capsys.readouterr().out
    assert f"[WARN] Cleanup targets the cached project {other.resolve()}, not this checkout {clean.REPO_ROOT}" in out
    assert prompts == [f"Remove everything listed above from {other.resolve()}? [y/N]: "]


def test_cached_project_equal_to_this_checkout_does_not_warn(skills_dir, calls, monkeypatch, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, clean.REPO_ROOT)
    # This checkout's real .server/ may hold versioned files; that warning is tested below.
    monkeypatch.setattr(clean, "versioned_server_files", lambda project: [])
    assert clean.main(["--dry-run"]) == 0
    assert "[WARN]" not in capsys.readouterr().out


def test_unloadable_state_module_means_no_cached_project(skills_dir, tmp_path, monkeypatch):
    _cache_project(skills_dir, tmp_path)
    monkeypatch.setattr(clean.importlib.util, "spec_from_file_location", lambda *a, **k: None)
    assert clean.cached_project() is None


def test_status_lines_have_a_single_space_after_the_label(skills_dir, calls, capsys):
    assert clean.main(["--yes"]) == 0
    assert "[OK]   No domain cleanup skills found." in capsys.readouterr().out


def test_no_cleanup_skills_is_ok(skills_dir, calls):
    assert clean.main(["--yes"]) == 0
    assert calls["cmds"] == []


def test_keep_server_drops_include_server_from_every_child(skills_dir, calls):
    _skill(skills_dir, "a-clean-workspace")
    _skill(skills_dir, "b-clean-workspace")
    assert clean.main(["--yes", "--keep-server"]) == 0
    assert len(calls["cmds"]) == 4
    assert not any("--include-server" in c for c in calls["cmds"])


def test_default_passes_include_server_to_removal_runs_too(skills_dir, calls):
    _skill(skills_dir, "a-clean-workspace")
    assert clean.main(["--yes"]) == 0
    assert [c for c in calls["cmds"] if c[-1] == "--yes"][0][2] == "--include-server"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


# A clone that versions its server settings: the template ignores all of .server/,
# and these are the exceptions such a clone adds.
VERSIONING_RULES = [".server/*/*", "!.server/*/serverDZ.cfg", "!.server/*/mission/", ".server/*/mission/storage_*/"]


def _server_files(repo):
    inst = repo / ".server" / "chernarus"
    for rel in ("serverDZ.cfg", "mission/init.c", "mission/storage_1/data.bin", "Profiles/server.RPT"):
        (inst / rel).parent.mkdir(parents=True, exist_ok=True)
        (inst / rel).write_text("x", encoding="utf-8")


@pytest.fixture
def server_repo(tmp_path):
    """A git repo that versions its server settings, with one instance."""
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text("".join(rule + "\n" for rule in VERSIONING_RULES), encoding="utf-8")
    _server_files(repo)
    return repo


def test_template_gitignore_keeps_no_server_file(tmp_path):
    # The template's own rules: every machine's test server is its own, so nothing under .server/ is trackable.
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text((clean.REPO_ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
    _server_files(repo)
    assert clean.versioned_server_files(repo) == []


def test_versioned_server_files_lists_only_what_gitignore_keeps(server_repo):
    assert sorted(clean.versioned_server_files(server_repo)) == [
        ".server/chernarus/mission/init.c",
        ".server/chernarus/serverDZ.cfg",
    ]


def test_versioned_server_files_empty_without_server_dir(tmp_path):
    assert clean.versioned_server_files(tmp_path) == []


def test_plan_warns_about_versioned_server_files(skills_dir, calls, server_repo, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    assert clean.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "[WARN] .server/ holds 2 file(s)" in out
    assert ".server/chernarus/serverDZ.cfg" in out
    assert "--keep-server" in out


def test_keep_server_plan_does_not_warn_about_server_files(skills_dir, calls, server_repo, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    assert clean.main(["--dry-run", "--keep-server"]) == 0
    assert ".server/ holds" not in capsys.readouterr().out


def test_plan_id_changes_with_child_stderr(skills_dir, calls, capsys):
    _skill(skills_dir, "a-clean-workspace")
    clean.main(["--dry-run"])
    first = _plan_id(capsys)
    calls["err"]["a-clean-workspace"] = b"[WARN] something new\n"
    clean.main(["--dry-run"])
    assert _plan_id(capsys) != first


def test_plan_with_dry_run_is_refused(skills_dir, calls, capsys):
    _skill(skills_dir, "a-clean-workspace")
    assert clean.main(["--dry-run", "--plan", "abc123abc123"]) == 2
    assert calls["cmds"] == []
    assert "cannot be combined with --dry-run" in capsys.readouterr().err


def test_state_module_error_is_a_clean_fail(skills_dir, calls, capsys):
    _skill(skills_dir, "a-clean-workspace")
    d = skills_dir / "dayz-init"
    d.mkdir()
    (d / "state.py").write_text(
        "def cached_project_root():\n    raise PermissionError('cache is unreadable')\n", encoding="utf-8"
    )
    assert clean.main(["--yes"]) == 1
    assert calls["cmds"] == []
    err = capsys.readouterr().err
    assert "[FAIL] Could not read the project cached by /dayz-init (PermissionError: cache is unreadable)" in err
    assert "Traceback" not in err


def test_unchanged_server_files_keep_the_plan_id(skills_dir, calls, server_repo, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    clean.main(["--dry-run"])
    plan = _plan_id(capsys)
    assert clean.main(["--yes", "--plan", plan, "--other-project"]) == 0
    assert ("a-clean-workspace", "--yes") in _modes(calls)


def test_mission_file_added_after_dry_run_refuses_plan(skills_dir, calls, server_repo, capsys):
    """The child lists .server/ as one item, so only the server stamp can catch new work in it."""
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    clean.main(["--dry-run"])
    plan = _plan_id(capsys)
    (server_repo / ".server" / "chernarus" / "mission" / "new_event.xml").write_text("<x/>", encoding="utf-8")
    calls["cmds"].clear()
    assert clean.main(["--yes", "--plan", plan, "--other-project"]) == 3
    assert ("a-clean-workspace", "--yes") not in _modes(calls)


def test_server_cfg_edited_after_dry_run_refuses_plan(skills_dir, calls, server_repo, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    clean.main(["--dry-run"])
    plan = _plan_id(capsys)
    (server_repo / ".server" / "chernarus" / "serverDZ.cfg").write_text("hostname = \"mine\";\n", encoding="utf-8")
    calls["cmds"].clear()
    assert clean.main(["--yes", "--plan", plan, "--other-project"]) == 3
    assert ("a-clean-workspace", "--yes") not in _modes(calls)


def test_server_file_added_at_the_prompt_is_not_removed(skills_dir, calls, server_repo, monkeypatch, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)

    def answer(prompt):
        (server_repo / ".server" / "chernarus" / "mission" / "late.c").write_text("x", encoding="utf-8")
        return "y"

    monkeypatch.setattr("builtins.input", answer)
    assert clean.main(["--other-project"]) == 3
    assert ("a-clean-workspace", "--yes") not in _modes(calls)
    assert "changed while waiting for confirmation" in capsys.readouterr().err


def _break_git(monkeypatch, failure):
    """Make the git call in versioned_server_files fail; children still go to the `calls` fake."""
    fake = clean.subprocess.run

    def run(cmd, *a, **k):
        if cmd[0] == "git":
            if isinstance(failure, BaseException):
                raise failure
            return failure
        return fake(cmd, *a, **k)

    monkeypatch.setattr(clean.subprocess, "run", run)


def test_versioned_server_files_raises_when_git_is_missing(server_repo, monkeypatch):
    _break_git(monkeypatch, FileNotFoundError("git"))
    with pytest.raises(clean.ServerCheckError, match="git could not be run"):
        clean.versioned_server_files(server_repo)


def test_versioned_server_files_raises_when_git_fails(server_repo, monkeypatch):
    _break_git(monkeypatch, SimpleNamespace(returncode=128, stdout="", stderr="fatal: not a git repository\n"))
    with pytest.raises(clean.ServerCheckError, match="git exited 128: fatal: not a git repository"):
        clean.versioned_server_files(server_repo)


def test_missing_git_refuses_removal_of_server_files(skills_dir, calls, server_repo, monkeypatch, capsys):
    """Without git the versioned files are neither warned about nor pinned, so nothing may be removed."""
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    _break_git(monkeypatch, FileNotFoundError("git"))
    assert clean.main(["--yes", "--other-project"]) == 1
    assert calls["cmds"] == []
    err = capsys.readouterr().err
    assert "[FAIL] Could not check which files under" in err
    assert "--keep-server" in err


def test_missing_git_dry_run_warns_and_offers_no_removal_command(skills_dir, calls, server_repo, monkeypatch, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    _break_git(monkeypatch, FileNotFoundError("git"))
    assert clean.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "[WARN] Could not check which files under" in out
    assert "--yes --plan" not in out
    assert "--dry-run --keep-server" in out


def test_missing_git_with_keep_server_still_cleans(skills_dir, calls, server_repo, monkeypatch):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    _break_git(monkeypatch, FileNotFoundError("git"))
    assert clean.main(["--yes", "--keep-server", "--other-project"]) == 0
    assert ("a-clean-workspace", "--yes") in _modes(calls)


def test_git_failing_at_the_prompt_removes_nothing(skills_dir, calls, server_repo, monkeypatch, capsys):
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)

    def answer(prompt):
        _break_git(monkeypatch, FileNotFoundError("git"))
        return "y"

    monkeypatch.setattr("builtins.input", answer)
    assert clean.main(["--other-project"]) == 3
    assert ("a-clean-workspace", "--yes") not in _modes(calls)


def _hint_args(capsys) -> list[str]:
    out = capsys.readouterr().out
    line = next(line for line in out.splitlines() if "To remove exactly this plan, run:" in line)
    return line.split('" ', 1)[1].split()


@pytest.mark.parametrize("extra", [[], ["--keep-server"]])
def test_dry_run_hint_for_another_project_works_word_for_word(skills_dir, calls, server_repo, capsys, extra):
    """The dry run of another project needs no --other-project, but the removal does: the hint must say so."""
    _skill(skills_dir, "a-clean-workspace")
    _cache_project(skills_dir, server_repo)
    assert clean.main(["--dry-run", *extra]) == 0
    args = _hint_args(capsys)
    assert "--other-project" in args
    assert ("--keep-server" in args) == bool(extra)
    calls["cmds"].clear()
    assert clean.main(args) == 0
    assert ("a-clean-workspace", "--yes") in _modes(calls)


def test_dry_run_hint_for_this_checkout_has_no_other_project_flag(skills_dir, calls, capsys):
    _skill(skills_dir, "a-clean-workspace")
    assert clean.main(["--dry-run"]) == 0
    args = _hint_args(capsys)
    assert args[:2] == ["--yes", "--plan"] and "--other-project" not in args
    calls["cmds"].clear()
    assert clean.main(args) == 0
    assert ("a-clean-workspace", "--yes") in _modes(calls)
