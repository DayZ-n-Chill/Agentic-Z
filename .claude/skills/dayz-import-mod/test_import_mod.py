"""Tests for import_mod.py: source validation, mod naming, non-TTY refusals."""
from __future__ import annotations

import importlib.util
import sys
import io
import os
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
    ("https://github.com/Owner/MyMod/tree/feature/x", ("https://github.com/Owner/MyMod.git", "MyMod", "feature/x")),
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
    synced = []
    monkeypatch.setattr(imp._nm, "sync_project_cache", synced.append)
    monkeypatch.setattr(imp.sys, "stdin", _NoTTY())
    clones = []

    def fake_clone(src, target, files=("config.cpp", "$PBOPREFIX$")):
        clones.append((src, target))
        target.mkdir()
        for name in files:
            (target / name).write_text("x", encoding="utf-8")

    monkeypatch.setattr(imp, "clone_repo", fake_clone)
    return {"workspace": workspace, "p": p_drive, "clones": clones, "synced": synced}


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
    assert git_project["synced"] == ["MyMod"]  # the clone becomes the active /dayz-init mod
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


@pytest.fixture
def subfolder_project(git_project, monkeypatch, tmp_path):
    """A tree link to Owner/Mods/tree/main/<sub>: the remote has a head named main,
    and the fake clone holds MyVest/ with config.cpp but no $PBOPREFIX$."""
    imports = tmp_path / "project" / ".imports"
    monkeypatch.setattr(imp, "IMPORTS", imports)
    monkeypatch.setattr(imp.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(imp, "resolve_branch", lambda git, url, ref: "main")

    def fake_clone(src, target):
        git_project["clones"].append((src, target))
        (target / "MyVest").mkdir(parents=True)
        (target / "MyVest" / "config.cpp").write_text("x", encoding="utf-8")

    monkeypatch.setattr(imp, "clone_repo", fake_clone)
    return {**git_project, "imports": imports}


def test_subfolder_link_imports_the_subfolder_not_the_root(subfolder_project, monkeypatch, capsys):
    monkeypatch.setattr(imp._scaffold._nm, "find_dayz_tools", lambda: None)
    rc = _main(monkeypatch, "--source", "https://github.com/Owner/Mods/tree/main/MyVest", "--scaffold")
    out = capsys.readouterr().out
    clone = subfolder_project["imports"] / "Owner__Mods__main"
    target = subfolder_project["workspace"] / "MyVest"
    assert subfolder_project["clones"] == [(imp.GitSource("https://github.com/Owner/Mods.git", "Mods", "main"), clone)]
    # workspace/MyVest is the subfolder, and the scaffold check and writes happen there.
    assert target.resolve() == (clone / "MyVest").resolve()
    assert (git_project_p := subfolder_project["p"] / "MyVest").exists()
    assert (clone / "MyVest" / "$PBOPREFIX$").read_text(encoding="utf-8").strip() == "MyVest"
    assert not (clone / "$PBOPREFIX$").exists() and not (clone / "config.cpp").exists()
    assert "config.cpp present" in out
    assert rc == 1  # workbench/ cannot be written without DayZ Tools; the links stay
    assert git_project_p.exists()


def test_subfolder_link_with_a_missing_folder_removes_the_clone(subfolder_project, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", "https://github.com/Owner/Mods/tree/main/Other", "--no-scaffold")
    assert "Other is not in branch main" in str(exc.value.code)
    assert not (subfolder_project["imports"] / "Owner__Mods__main").exists()
    assert not (subfolder_project["workspace"] / "Other").exists()


@pytest.mark.parametrize("which", ["workspace", "p"])
def test_subfolder_link_failure_removes_the_new_clone(subfolder_project, monkeypatch, which):
    real = imp._nm.make_dir_link

    def failing(target, link):
        if which == "workspace" or link.parent == subfolder_project["p"]:
            raise OSError("link refused")
        return real(target, link)

    monkeypatch.setattr(imp._nm, "make_dir_link", failing)
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", "https://github.com/Owner/Mods/tree/main/MyVest", "--no-scaffold")
    assert "link refused" in str(exc.value.code)
    assert "Removed the clone" in str(exc.value.code)
    assert not (subfolder_project["imports"] / "Owner__Mods__main").exists()
    assert not (subfolder_project["workspace"] / "MyVest").exists()


def test_subfolder_link_failure_keeps_a_reused_clone(subfolder_project, monkeypatch):
    clone = subfolder_project["imports"] / "Owner__Mods__main"
    (clone / "MyVest").mkdir(parents=True)

    def failing(target, link):
        raise OSError("link refused")

    monkeypatch.setattr(imp._nm, "make_dir_link", failing)
    with pytest.raises(SystemExit):
        _main(monkeypatch, "--source", "https://github.com/Owner/Mods/tree/main/MyVest", "--no-scaffold")
    assert (clone / "MyVest").is_dir()
    assert subfolder_project["clones"] == []


@pytest.mark.parametrize("ref", ["main/../..", "main/MyVest/../../Other", "main/..\Other"])
def test_subfolder_with_dotdot_is_refused_before_cloning(subfolder_project, monkeypatch, ref):
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", f"https://github.com/Owner/Mods/tree/{ref}", "--name", "Escape", "--no-scaffold")
    assert "contains '..'" in str(exc.value.code)
    assert subfolder_project["clones"] == []
    assert not (subfolder_project["workspace"] / "Escape").exists()


def test_subfolder_resolving_outside_the_clone_is_refused(subfolder_project, monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "config.cpp").write_text("x", encoding="utf-8")

    def fake_clone(src, target):
        subfolder_project["clones"].append((src, target))
        target.mkdir(parents=True)
        imp._nm.make_dir_link(outside, target / "MyVest")

    monkeypatch.setattr(imp, "clone_repo", fake_clone)
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", "https://github.com/Owner/Mods/tree/main/MyVest", "--no-scaffold")
    assert "resolves outside the clone" in str(exc.value.code)
    assert not (subfolder_project["workspace"] / "MyVest").exists()
    assert not (subfolder_project["imports"] / "Owner__Mods__main").exists()
    assert (outside / "config.cpp").is_file()


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


class _Run:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


@pytest.fixture
def fake_git(monkeypatch):
    """subprocess.run for git with two heads on the remote: main and feature/x."""
    calls = []

    def run(cmd, **_kw):
        calls.append(cmd)
        if cmd[1] == "ls-remote":
            return _Run(stdout="abc\trefs/heads/main\ndef\trefs/heads/feature/x\n")
        Path(cmd[-1]).mkdir(parents=True)
        return _Run()

    monkeypatch.setattr(imp.shutil, "which", lambda _name: "git")
    monkeypatch.setattr(imp.subprocess, "run", run)
    return calls


def _clone_cmd(calls):
    return next(c for c in calls if c[1] == "clone")


def test_subfolder_tree_link_clones_the_real_branch(fake_git, tmp_path, capsys):
    src = imp.parse_git_source("https://github.com/Owner/Mods/tree/main/MyMod")
    assert src.branch == "main/MyMod"
    imp.clone_repo(src, tmp_path / "MyMod")
    assert _clone_cmd(fake_git)[:4] == ["git", "clone", "--branch", "main"]
    assert "MyMod inside branch main" in capsys.readouterr().out


def test_slash_branch_tree_link_keeps_the_whole_branch(fake_git, tmp_path):
    imp.clone_repo(imp.parse_git_source("https://github.com/Owner/MyMod/tree/feature/x"), tmp_path / "MyMod")
    assert _clone_cmd(fake_git)[:4] == ["git", "clone", "--branch", "feature/x"]


def test_slash_branch_with_a_subfolder(fake_git, tmp_path):
    imp.clone_repo(imp.parse_git_source("https://github.com/Owner/MyMod/tree/feature/x/addons"), tmp_path / "MyMod")
    assert _clone_cmd(fake_git)[:4] == ["git", "clone", "--branch", "feature/x"]


def test_single_segment_branch_skips_ls_remote(fake_git, tmp_path):
    imp.clone_repo(imp.parse_git_source("https://github.com/Owner/MyMod/tree/dev"), tmp_path / "MyMod")
    assert [c[1] for c in fake_git] == ["clone"]
    assert _clone_cmd(fake_git)[:4] == ["git", "clone", "--branch", "dev"]


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
    monkeypatch.setattr(fresh._nm, "sync_project_cache", lambda modname: None)
    monkeypatch.setattr(fresh.sys, "stdin", _NoTTY())
    monkeypatch.setattr("sys.argv", ["import_mod.py", "--source", str(source), "--no-scaffold"])
    assert fresh.main() == 0
    assert (project / "workspace" / "NewMod" / "config.cpp").is_file()
    assert not (other / "workspace").exists()
    assert (p_drive / "NewMod").exists()


@pytest.mark.parametrize("url, key", [
    ("https://github.com/Owner/Mods.git", "Owner__Mods__main"),
    ("https://github.com/Fork/Mods.git", "Fork__Mods__main"),
    ("git@github.com:Owner/Mods.git", "Owner__Mods__main"),
])
def test_clone_dir_is_keyed_by_owner_repo_and_branch(subfolder_project, url, key):
    assert imp.clone_dir(imp.GitSource(url, "Mods", "main")) == subfolder_project["imports"] / key
    slash = imp.clone_dir(imp.GitSource(url, "Mods", "feature/x"))
    assert slash == subfolder_project["imports"] / f"{key[:-len('main')]}feature__x"


def test_second_branch_and_fork_get_their_own_clones(subfolder_project, monkeypatch, capsys):
    # A clone of Owner/Mods on main already exists; another branch or a fork must not reuse it.
    (subfolder_project["imports"] / "Owner__Mods__main" / "MyVest").mkdir(parents=True)
    monkeypatch.setattr(imp, "resolve_branch", lambda git, url, ref: "dev")
    assert _main(monkeypatch, "--source", "https://github.com/Owner/Mods/tree/dev/MyVest", "--no-scaffold") == 0
    monkeypatch.setattr(imp, "resolve_branch", lambda git, url, ref: "main")
    assert _main(monkeypatch, "--source", "https://github.com/Fork/Mods/tree/main/MyVest",
                 "--name", "ForkVest", "--no-scaffold") == 0
    imports = subfolder_project["imports"]
    assert [target for _src, target in subfolder_project["clones"]] == [
        imports / "Owner__Mods__dev", imports / "Fork__Mods__main"]
    assert "Reusing the clone" not in capsys.readouterr().out


def test_reused_clone_missing_the_folder_says_to_update_it(subfolder_project, monkeypatch):
    clone = subfolder_project["imports"] / "Owner__Mods__main"
    (clone / "MyVest").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        _main(monkeypatch, "--source", "https://github.com/Owner/Mods/tree/main/Other", "--no-scaffold")
    msg = str(exc.value.code)
    assert "Other is not in branch main" in msg and "came from an earlier import" in msg and "pull" in msg
    assert clone.is_dir()  # an earlier import's clone is never deleted
    assert subfolder_project["clones"] == []


def test_folder_import_makes_the_imported_mod_the_hub_active_mod(tmp_path, monkeypatch, workspace):
    """/dayz-import-mod B with A active: the /dayz-init hub must then show B, not A."""
    project = workspace.parent.resolve()
    source = tmp_path / "src" / "ModB"
    (source / "workbench").mkdir(parents=True)
    for name in ("config.cpp", "$PBOPREFIX$", "workbench/dayz.gproj"):
        (source / name).write_text("ModB", encoding="utf-8")
    p_drive = tmp_path / "P"
    p_drive.mkdir()
    monkeypatch.setattr(imp, "P_DRIVE", p_drive)
    monkeypatch.setattr(imp, "PROJECT_DIR", project)
    monkeypatch.setattr(imp._nm, "PROJECT_DIR", project)
    monkeypatch.setattr(imp.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(imp.sys, "stdin", _NoTTY())
    imp._nm._state.write_state(project, {"last_intent": {"mod_name": "ModA"}})

    assert _main(monkeypatch, "--source", str(source), "--no-scaffold") == 0

    monkeypatch.syspath_prepend(str(HERE.parent / "dayz-init"))
    spec = importlib.util.spec_from_file_location(
        "dayz_init_hub_status_for_import", HERE.parent / "dayz-init" / "hub_status.py")
    hub = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "dayz_init_hub_status_for_import", hub)  # dataclasses look the module up
    spec.loader.exec_module(hub)
    monkeypatch.setattr(hub, "_diag_running", lambda: False)
    status = hub.gather_status(project, mods_root=tmp_path / "Mods")
    assert status.mod == "ModB"


# --- real console vs a null stdin ----------------------------------------------

class _TTYAtEOF(io.StringIO):
    """Claims to be a TTY but every read is end-of-file, like NUL on Windows."""
    def isatty(self):
        return True


def test_null_device_stdin_is_not_interactive(monkeypatch):
    # On Windows NUL is a character device, so isatty() is True; it is still not a console.
    with open(os.devnull, encoding="utf-8") as null:
        monkeypatch.setattr(imp.sys, "stdin", null)
        assert imp.stdin_is_interactive() is False


def test_tty_claiming_stream_without_a_handle_is_not_interactive(monkeypatch):
    monkeypatch.setattr(imp.sys, "stdin", _TTYAtEOF())
    assert imp.stdin_is_interactive() is False


@pytest.mark.parametrize("make_stdin", [_TTYAtEOF, lambda: open(os.devnull, encoding="utf-8")])
def test_eof_stdin_without_decision_refuses_before_linking(make_stdin, tmp_path, monkeypatch, workspace):
    """A null stdin used to pass the TTY check, link both folders, and read EOF as
    'no' at every prompt, finishing as a silent --no-scaffold."""
    source = tmp_path / "src" / "MyMod"
    source.mkdir(parents=True)
    (source / "config.cpp").write_text("x", encoding="utf-8")
    p_drive = tmp_path / "P"
    p_drive.mkdir()
    monkeypatch.setattr(imp, "P_DRIVE", p_drive)
    monkeypatch.setattr(imp, "PROJECT_DIR", workspace.parent)
    monkeypatch.setattr(imp.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(imp._nm, "sync_project_cache", lambda _name: None)
    stdin = make_stdin()
    monkeypatch.setattr(imp.sys, "stdin", stdin)
    try:
        with pytest.raises(SystemExit) as exc:
            _main(monkeypatch, "--source", str(source))
    finally:
        stdin.close()
    assert "--scaffold" in str(exc.value.code) and "--no-scaffold" in str(exc.value.code)
    assert not (workspace / "MyMod").exists()
    assert not (p_drive / "MyMod").exists()
