"""Tests for clean-repo/clean.py: discovery, TTY refusal, dry-run-first ordering."""
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
    """Record child invocations; return codes are looked up per (skill, mode)."""
    record = {"cmds": [], "rc": {}}
    real_run = subprocess.run

    def fake_run(cmd, *a, **k):
        if cmd[0] == "git":  # versioned_server_files asks real git; only children are faked
            return real_run(cmd, *a, **k)
        record["cmds"].append(cmd)
        key = (Path(cmd[1]).parent.name, cmd[-1])
        return SimpleNamespace(returncode=record["rc"].get(key, 0))

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


def _cache_project(skills_dir: Path, project: Path) -> None:
    """A dayz-init/state.py stand in whose cached project root is `project`."""
    d = skills_dir / "dayz-init"
    d.mkdir()
    (d / "state.py").write_text(
        "from pathlib import Path\n"
        f"def cached_project_root():\n    return Path({str(project)!r})\n",
        encoding="utf-8",
    )


def test_other_cached_project_warns_and_is_named_in_the_prompt(skills_dir, calls, monkeypatch, tmp_path, capsys):
    _skill(skills_dir, "a-clean-workspace")
    other = tmp_path / "other-clone"
    other.mkdir()
    _cache_project(skills_dir, other)
    prompts = []
    monkeypatch.setattr(clean.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "n")
    assert clean.main([]) == 0
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


@pytest.fixture
def server_repo(tmp_path):
    """A git repo with the template's .server/ ignore rules and one instance."""
    repo = tmp_path / "proj"
    repo.mkdir()
    _git(repo, "init", "-q")
    gitignore = (clean.REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    rules = [line for line in gitignore.splitlines() if line.lstrip("!").startswith(".server/")]
    assert "!.server/*/serverDZ.cfg" in rules
    (repo / ".gitignore").write_text("".join(rule + "\n" for rule in rules), encoding="utf-8")
    inst = repo / ".server" / "chernarus"
    for rel in ("serverDZ.cfg", "mission/init.c", "mission/storage_1/data.bin", "Profiles/server.RPT"):
        (inst / rel).parent.mkdir(parents=True, exist_ok=True)
        (inst / rel).write_text("x", encoding="utf-8")
    return repo


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
