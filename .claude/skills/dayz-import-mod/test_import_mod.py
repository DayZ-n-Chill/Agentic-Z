"""Tests for import_mod.py: source validation, mod naming, non-TTY refusals."""
from __future__ import annotations

import importlib.util
import io
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_import_mod_under_test", HERE / "import_mod.py")
imp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(imp)


class _NoTTY(io.StringIO):
    def isatty(self):
        return False


@pytest.fixture
def workspace(monkeypatch, tmp_path):
    ws = tmp_path / "project" / "workspace"
    ws.mkdir(parents=True)
    monkeypatch.setattr(imp, "WORKSPACE", ws)
    return ws


# --- resolve_source -----------------------------------------------------------

@pytest.mark.parametrize("raw", ["\\\\server\\share\\MyMod", "//server/share/MyMod"])
def test_unc_paths_refused(raw, workspace):
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(raw)
    assert "UNC" in str(exc.value.code)


def test_missing_source_refused(tmp_path, workspace):
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(str(tmp_path / "nope"))
    assert "does not exist" in str(exc.value.code)


def test_file_source_refused(tmp_path, workspace):
    f = tmp_path / "mod.zip"
    f.write_bytes(b"")
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(str(f))
    assert "not a directory" in str(exc.value.code)


def test_source_inside_workspace_refused(workspace):
    inside = workspace / "Already"
    inside.mkdir()
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(str(inside))
    assert "inside this project's workspace" in str(exc.value.code)
    assert "--piece junction" in str(exc.value.code)


def test_outside_source_accepted(tmp_path, workspace):
    src = tmp_path / "repos" / "MyMod"
    src.mkdir(parents=True)
    assert imp.resolve_source(str(src)) == src.resolve()


def test_missing_source_flag_refused_without_tty(monkeypatch, workspace):
    monkeypatch.setattr(imp.sys, "stdin", _NoTTY())
    with pytest.raises(SystemExit) as exc:
        imp.resolve_source(None)
    assert "--source is required" in str(exc.value.code)


# --- derive_modname -------------------------------------------------------------

def test_basename_used_when_valid():
    assert imp.derive_modname(Path("C:/repos/MyMod"), None) == "MyMod"


@pytest.mark.parametrize("basename", ["My Mod", "my-mod", "1stMod", "Mod.v2"])
def test_invalid_basename_asks_for_name(basename):
    with pytest.raises(SystemExit) as exc:
        imp.derive_modname(Path("C:/repos") / basename, None)
    assert "--name" in str(exc.value.code)


def test_override_wins_over_basename():
    assert imp.derive_modname(Path("C:/repos/my-mod"), "MyMod") == "MyMod"


def test_invalid_override_refused():
    with pytest.raises(SystemExit) as exc:
        imp.derive_modname(Path("C:/repos/MyMod"), "bad name")
    assert "Invalid mod name" in str(exc.value.code)


# --- missing pieces and the scaffold decision ------------------------------------

def test_detect_missing_pieces(tmp_path):
    (tmp_path / "config.cpp").write_text("", encoding="utf-8")
    assert [key for key, _rel, _why in imp.detect_missing_pieces(tmp_path)] == ["prefix", "workbench"]


def test_non_tty_without_flag_refused():
    missing = [("prefix", "$PBOPREFIX$", "why")]
    with pytest.raises(SystemExit) as exc:
        imp.require_scaffold_decision(missing, scaffold=False, no_scaffold=False, interactive=False)
    assert "--scaffold" in str(exc.value.code) and "$PBOPREFIX$" in str(exc.value.code)


@pytest.mark.parametrize(
    "scaffold, no_scaffold, interactive",
    [(True, False, False), (False, True, False), (False, False, True)],
)
def test_explicit_decision_or_tty_passes(scaffold, no_scaffold, interactive):
    imp.require_scaffold_decision([("prefix", "$PBOPREFIX$", "why")], scaffold, no_scaffold, interactive)


def test_nothing_missing_never_refuses():
    imp.require_scaffold_decision([], scaffold=False, no_scaffold=False, interactive=False)


def test_existing_workspace_entry_refused(workspace):
    (workspace / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        imp.check_workspace_target(workspace / "MyMod")
    assert "already exists" in str(exc.value.code)


# --- add_missing_pieces (runs after the links exist) ---------------------------------

ALL_MISSING = list(imp.SCAFFOLD_CHECKS)


def test_scaffold_writes_in_process_without_rerunning_preflight(tmp_path, monkeypatch):
    monkeypatch.setattr(imp.h, "gate_on_preflight", lambda: pytest.fail("preflight must not re-run"))
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(imp._scaffold._nm, "resolve_author", lambda cli: "Tester")
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING[:2], scaffold=True, no_scaffold=False)
    assert rc == 0
    assert (tmp_path / "config.cpp").is_file() and (tmp_path / "$PBOPREFIX$").is_file()


def test_skipped_workbench_piece_fails_the_import(tmp_path, monkeypatch, capsys):
    """Without DayZ Tools the writer skips workbench/; that is a failure, not a success."""
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    workbench = [c for c in ALL_MISSING if c[0] == "workbench"]
    rc = imp.add_missing_pieces(tmp_path, "MyMod", workbench, scaffold=True, no_scaffold=False)
    out = capsys.readouterr().out
    assert rc == 1
    assert "Could not add workbench/dayz.gproj" in out
    assert "Retry: /dayz-add-scaffold MyMod --piece workbench" in out


def test_no_scaffold_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(imp._scaffold, "add_piece", lambda *a: pytest.fail("must not write"))
    assert imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=False, no_scaffold=True) == 0


def test_declined_prompt_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(imp, "prompt_yn", lambda prompt: False)
    monkeypatch.setattr(imp._scaffold, "add_piece", lambda *a: pytest.fail("must not write"))
    assert imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=False, no_scaffold=False) == 0


def test_failed_piece_reports_retry_and_keeps_going(tmp_path, monkeypatch, capsys):
    def no_author(cli):
        raise SystemExit("[FAIL] No author handle available.")

    monkeypatch.setattr(imp._scaffold._nm, "resolve_author", no_author)
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING, scaffold=True, no_scaffold=False)
    out = capsys.readouterr().out
    assert rc == 1
    assert "No author handle available" in out
    assert "Retry: /dayz-add-scaffold MyMod --piece config" in out
    assert "/dayz-clean-workspace --mod MyMod" in out
    assert (tmp_path / "$PBOPREFIX$").is_file()  # later pieces still written


def test_os_error_while_writing_is_reported(tmp_path, monkeypatch, capsys):
    def boom(*a):
        raise PermissionError("Access is denied")

    monkeypatch.setattr(imp._scaffold, "add_piece", boom)
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING[1:2], scaffold=True, no_scaffold=False)
    assert rc == 1
    assert "Access is denied" in capsys.readouterr().out


def test_author_flag_reaches_resolve_author(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(imp._scaffold._nm, "resolve_author", lambda cli: seen.append(cli) or cli)
    rc = imp.add_missing_pieces(tmp_path, "MyMod", ALL_MISSING[:1], scaffold=True, no_scaffold=False, author="Handle")
    assert rc == 0
    assert seen == ["Handle"]
    assert 'author = "Handle"' in (tmp_path / "config.cpp").read_text(encoding="utf-8")


# --- GitHub links and Workshop links ------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("https://github.com/Owner/MyMod", ("https://github.com/Owner/MyMod.git", "MyMod", None)),
    ("https://github.com/Owner/MyMod.git", ("https://github.com/Owner/MyMod.git", "MyMod", None)),
    ("github.com/Owner/MyMod/", ("https://github.com/Owner/MyMod.git", "MyMod", None)),
    ("https://www.github.com/Owner/MyMod/tree/dev", ("https://github.com/Owner/MyMod.git", "MyMod", "dev")),
    ("https://github.com/Owner/MyMod?tab=readme", ("https://github.com/Owner/MyMod.git", "MyMod", None)),
    ("https://gitlab.com/group/sub/MyMod.git", ("https://gitlab.com/group/sub/MyMod.git", "MyMod", None)),
    ("git@github.com:Owner/MyMod.git", ("git@github.com:Owner/MyMod.git", "MyMod", None)),
])
def test_parse_git_source(raw, expected):
    assert tuple(imp.parse_git_source(raw)) == expected


@pytest.mark.parametrize("raw", [r"C:\repos\MyMod", "D:/mods/MyMod", "~/MyMod", "MyMod", "https://example.com/MyMod"])
def test_local_paths_are_not_git_sources(raw):
    assert imp.parse_git_source(raw) is None


@pytest.mark.parametrize("raw", [
    "https://steamcommunity.com/sharedfiles/filedetails/?id=1559212036",
    "steamcommunity.com/workshop/filedetails/?id=1559212036",
    "steam://url/CommunityFilePage/1559212036",
])
def test_workshop_link_is_refused_before_preflight(raw, monkeypatch):
    monkeypatch.setattr(imp.h, "gate_on_preflight", lambda: pytest.fail("refuse before preflight"))
    monkeypatch.setattr("sys.argv", ["import_mod.py", "--source", raw])
    with pytest.raises(SystemExit) as exc:
        imp.main()
    message = str(exc.value.code)
    assert "Steam Workshop links are not imported" in message
    assert "binarized" in message and "protected" in message
    assert "--source <path>" in message


@pytest.fixture
def git_project(monkeypatch, tmp_path, workspace):
    """main() with preflight, the P: drive and the project cache pointed at tmp_path."""
    p_drive = tmp_path / "P"
    p_drive.mkdir()
    monkeypatch.setattr(imp, "P_DRIVE", p_drive)
    monkeypatch.setattr(imp, "PROJECT_DIR", workspace.parent)
    monkeypatch.setattr(imp.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(imp._nm, "sync_project_cache", lambda: None)
    monkeypatch.setattr(imp.sys, "stdin", _NoTTY())
    clones = []

    def fake_clone(src, target, files=("config.cpp", "$PBOPREFIX$")):
        clones.append((src, target))
        target.mkdir()
        for name in files:
            (target / name).write_text("x", encoding="utf-8")

    monkeypatch.setattr(imp, "clone_repo", fake_clone)
    return {"workspace": workspace, "p": p_drive, "clones": clones}


def _main(monkeypatch, *argv):
    monkeypatch.setattr("sys.argv", ["import_mod.py", *argv])
    return imp.main()


def test_github_link_clones_into_workspace_and_links_p(git_project, monkeypatch, capsys):
    rc = _main(monkeypatch, "--source", "https://github.com/Owner/MyMod/tree/dev", "--no-scaffold")
    out = capsys.readouterr().out
    target = git_project["workspace"] / "MyMod"
    assert rc == 0
    assert git_project["clones"] == [(imp.GitSource("https://github.com/Owner/MyMod.git", "MyMod", "dev"), target)]
    assert (target / "config.cpp").is_file()
    assert (git_project["p"] / "MyMod").exists()
    assert "workbench/dayz.gproj missing" in out
    assert "skipping workbench/dayz.gproj (--no-scaffold)" in out
    # clean-workspace refuses folders that hold .git, so the hint must not send the user there.
    assert "/dayz-clean-workspace --mod MyMod" not in out
    assert "holds .git, so /dayz-clean-workspace refuses it" in out
    assert "cmd /c rmdir /s /q" in out


def test_github_link_with_invalid_repo_name_needs_name(git_project, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", "https://github.com/Owner/my-mod", "--no-scaffold")
    assert "--name" in str(exc.value.code)
    assert git_project["clones"] == []
    assert _main(monkeypatch, "--source", "https://github.com/Owner/my-mod", "--name", "MyMod", "--no-scaffold") == 0
    assert (git_project["workspace"] / "MyMod").is_dir()


def test_github_link_refuses_existing_workspace_folder_before_cloning(git_project, monkeypatch):
    (git_project["workspace"] / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", "https://github.com/Owner/MyMod", "--no-scaffold")
    assert "already exists" in str(exc.value.code)
    assert git_project["clones"] == []


def test_non_tty_git_import_without_decision_removes_the_clone(git_project, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", "https://github.com/Owner/MyMod")
    assert "--scaffold" in str(exc.value.code)
    assert not (git_project["workspace"] / "MyMod").exists()
    assert not (git_project["p"] / "MyMod").exists()


def test_clone_repo_runs_git_and_failed_clone_leaves_nothing(tmp_path):
    import shutil
    import subprocess
    if shutil.which("git") is None:
        pytest.skip("git not installed")
    origin = tmp_path / "origin"
    origin.mkdir()
    (origin / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    run = lambda *a: subprocess.run(["git", *a], cwd=origin, check=True, capture_output=True,  # noqa: E731
                                    env={**__import__("os").environ, **env})
    run("init", "-q")
    run("add", ".")
    run("commit", "-q", "-m", "init")

    target = tmp_path / "ws" / "MyMod"
    target.parent.mkdir()
    imp.clone_repo(imp.GitSource(str(origin), "MyMod", None), target)
    assert (target / "config.cpp").is_file() and (target / ".git").is_dir()
    imp.remove_clone(target)  # read-only git objects are removed too
    assert not target.exists()

    with pytest.raises(SystemExit) as exc:
        imp.clone_repo(imp.GitSource(str(tmp_path / "missing"), "MyMod", None), target)
    assert "git clone failed" in str(exc.value.code)
    assert not target.exists()


# --- finish: an existing $PBOPREFIX$ must be the mod name ----------------------------

def _finish(tmp_path, prefix):
    import argparse
    (tmp_path / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    (tmp_path / "$PBOPREFIX$").write_text(prefix, encoding="utf-8")
    (tmp_path / "workbench").mkdir()
    (tmp_path / "workbench" / "dayz.gproj").write_text("x", encoding="utf-8")
    args = argparse.Namespace(scaffold=False, no_scaffold=True, author=None)
    return imp.finish(tmp_path, tmp_path, "MyMod", [], args, "Remove: /dayz-clean-workspace --mod MyMod")


def test_finish_warns_when_prefix_is_not_the_mod_name(tmp_path, capsys):
    assert _finish(tmp_path, "Author\\MyMod\n") == 0
    out = capsys.readouterr().out
    assert "$PBOPREFIX$ is 'Author\\\\MyMod', not 'MyMod', so /dayz-build-pbo will refuse it." in out
    assert "Build: set $PBOPREFIX$ to MyMod, then /dayz-build-pbo MyMod" in out


def test_finish_accepts_prefix_equal_to_the_mod_name(tmp_path, capsys):
    assert _finish(tmp_path, "﻿MyMod\r\n") == 0
    out = capsys.readouterr().out
    assert "will refuse" not in out
    assert "  - Build: /dayz-build-pbo MyMod" in out


def test_project_found_from_subfolder_without_claude_project_dir(tmp_path, monkeypatch):
    """Without CLAUDE_PROJECT_DIR, a run from workspace/Other still links into the
    cached project's workspace/, the same root dayz-new-mod and the cache use."""
    project = tmp_path / "project"
    memory = project / ".claude" / "local-memory"
    memory.mkdir(parents=True)
    (memory / "dayz-current-project.txt").write_text(str(project), encoding="utf-8")
    other = project / "workspace" / "Other"
    other.mkdir(parents=True)
    source = tmp_path / "src" / "NewMod"
    (source / "workbench").mkdir(parents=True)
    for name in ("config.cpp", "$PBOPREFIX$", "workbench/dayz.gproj"):
        (source / name).write_text("NewMod", encoding="utf-8")
    p_drive = tmp_path / "P"
    p_drive.mkdir()

    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(other)
    spec = importlib.util.spec_from_file_location("dayz_import_mod_subfolder", HERE / "import_mod.py")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    assert fresh.PROJECT_DIR == project.resolve()

    monkeypatch.setattr(fresh, "P_DRIVE", p_drive)
    monkeypatch.setattr(fresh.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(fresh._nm, "sync_project_cache", lambda: None)
    monkeypatch.setattr(fresh.sys, "stdin", _NoTTY())
    monkeypatch.setattr("sys.argv", ["import_mod.py", "--source", str(source), "--no-scaffold"])
    assert fresh.main() == 0
    assert (project / "workspace" / "NewMod" / "config.cpp").is_file()
    assert not (other / "workspace").exists()
    assert (p_drive / "NewMod").exists()
