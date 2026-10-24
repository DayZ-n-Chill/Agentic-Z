"""Tests for new_mod.py: name validation, gproj injection, P:\\ link pre-check."""
from __future__ import annotations

import importlib.util
import sys
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_new_mod_under_test", HERE / "new_mod.py")
nm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nm)
h = nm.h
REAL_RESOLVE_AUTHOR = nm.resolve_author

VANILLA_GPROJ = """GameProjectClass {
 ID "DayZ"
 Configurations {
  GameProjectConfigClass PC {
   FileSystem {
    FileSystemPathClass {
     Name "Game Root"
     Directory "./"
    }
   }
   ScriptModules {
    ScriptModulePathClass {
     Name "core"
     Paths {
      "scripts/1_Core"
     }
     EntryPoint ""
    }
    ScriptModulePathClass {
     Name "game"
     Paths {
      "scripts/3_Game"
     }
     EntryPoint "CreateGame"
    }
    ScriptModulePathClass {
     Name "world"
     Paths {
      "scripts/4_World"
     }
     EntryPoint ""
    }
    ScriptModulePathClass {
     Name "mission"
     Paths {
      "scripts/5_Mission"
     }
     EntryPoint "CreateMission"
    }
   }
  }
 }
}
"""


# --- validate_name -------------------------------------------------------------

@pytest.mark.parametrize("name", ["MyMod", "a", "Mod_2", "A" * 64])
def test_validate_name_accepts(name):
    nm.validate_name(name)


@pytest.mark.parametrize("name", ["", "1Mod", "_Mod", "My-Mod", "My Mod", "Mod.v2", "A" * 65, "Mod/../x"])
def test_validate_name_rejects(name):
    with pytest.raises(SystemExit) as exc:
        nm.validate_name(name)
    assert "Invalid mod name" in str(exc.value.code)


# --- gproj module injection ---------------------------------------------------

def _paths_block(text: str, module: str) -> list[str]:
    after = text.split(f'Name "{module}"', 1)[1]
    block = after.split("Paths {", 1)[1].split("}", 1)[0]
    return [line.strip() for line in block.strip().splitlines()]


def test_inject_appends_mod_path_to_each_script_module():
    out = nm.inject_mod_paths_into_gproj(VANILLA_GPROJ, "MyMod")
    assert _paths_block(out, "game") == ['"scripts/3_Game"', '"MyMod/scripts/3_Game"']
    assert _paths_block(out, "world") == ['"scripts/4_World"', '"MyMod/scripts/4_World"']
    assert _paths_block(out, "mission") == ['"scripts/5_Mission"', '"MyMod/scripts/5_Mission"']


def test_inject_leaves_other_modules_alone():
    out = nm.inject_mod_paths_into_gproj(VANILLA_GPROJ, "MyMod")
    assert _paths_block(out, "core") == ['"scripts/1_Core"']
    assert out.count("MyMod/") == 3


def test_inject_matches_existing_path_indentation():
    out = nm.inject_mod_paths_into_gproj(VANILLA_GPROJ, "MyMod")
    assert '      "MyMod/scripts/3_Game"\n' in out


def test_rewrite_filesystem_block_warns_when_nothing_matches(capsys):
    text = "GameProjectClass {\n Configurations {\n }\n}\n"
    assert nm.rewrite_filesystem_block(text, "MyMod") == text
    err = capsys.readouterr().err
    assert "no single-entry FileSystem block" in err and "P:/MyMod/" in err


def test_rewrite_filesystem_block_mounts_p_drive_and_mod():
    out = nm.rewrite_filesystem_block(VANILLA_GPROJ, "MyMod")
    assert 'Directory "./"' not in out
    assert 'Directory "P:/"' in out and 'Directory "P:/MyMod/"' in out
    assert 'Name "game"' in out  # the rest of the file survives


# A "game" module with no Paths block: the old scan ran on into "world" and
# put the game path there, and world's own path was never added.
GPROJ_GAME_WITHOUT_PATHS = VANILLA_GPROJ.replace(
    '     Paths {\n      "scripts/3_Game"\n     }\n     EntryPoint "CreateGame"\n',
    '     EntryPoint "CreateGame"\n',
)


def test_inject_skips_module_without_paths_block():
    assert 'Name "game"\n     EntryPoint' in GPROJ_GAME_WITHOUT_PATHS  # fixture really dropped it
    out, injected = nm.inject_mod_paths(GPROJ_GAME_WITHOUT_PATHS, "MyMod")
    assert injected == ["world", "mission"]
    assert "MyMod/scripts/3_Game" not in out
    assert _paths_block(out, "world") == ['"scripts/4_World"', '"MyMod/scripts/4_World"']
    assert _paths_block(out, "mission") == ['"scripts/5_Mission"', '"MyMod/scripts/5_Mission"']


def test_inject_skips_module_whose_next_line_is_another_name():
    text = ' ScriptModulePathClass {\n  Name "game"\n  Name "world"\n  Paths {\n   "scripts/4_World"\n  }\n }\n'
    out, injected = nm.inject_mod_paths(text, "MyMod")
    assert injected == ["world"]
    assert "MyMod/scripts/3_Game" not in out and "MyMod/scripts/4_World" in out


def test_inject_reports_all_three_modules_on_vanilla_layout():
    _, injected = nm.inject_mod_paths(VANILLA_GPROJ, "MyMod")
    assert injected == ["game", "world", "mission"]


# --- scaffold_workbench(): OK only when every gproj piece went in -----------------------

@pytest.fixture
def fake_tools(monkeypatch, tmp_path):
    """A DayZ Tools root whose Bin/Workbench/ holds what the test writes."""
    root = tmp_path / "DayZ Tools"
    (root / "Bin" / "Workbench").mkdir(parents=True)
    monkeypatch.setattr(nm, "find_dayz_tools", lambda: root)
    return root / "Bin" / "Workbench"


def _run_workbench(tmp_path, capsys) -> tuple[str, str]:
    target = tmp_path / "MyMod"
    target.mkdir()
    nm.scaffold_workbench(target, "MyMod")
    captured = capsys.readouterr()
    return captured.out, captured.err


def test_workbench_ok_line_when_everything_injected(fake_tools, tmp_path, capsys):
    (fake_tools / "dayz.gproj").write_text(VANILLA_GPROJ, encoding="utf-8")
    (fake_tools / "DayZSetting.xml").write_text("<x/>", encoding="utf-8")
    out, err = _run_workbench(tmp_path, capsys)
    assert "[OK]    workbench/dayz.gproj written (mod paths + filesystem mounts injected)" in out
    assert "WARN" not in out + err


def test_workbench_warns_on_module_without_paths(fake_tools, tmp_path, capsys):
    (fake_tools / "dayz.gproj").write_text(GPROJ_GAME_WITHOUT_PATHS, encoding="utf-8")
    out, _ = _run_workbench(tmp_path, capsys)
    assert "injected)" not in out
    assert 'module "game" has no Paths block' in out and '"MyMod/scripts/3_Game"' in out
    assert 'module "world"' not in out and 'module "mission"' not in out
    assert "fix the pieces above by hand" in out


def test_workbench_warns_when_filesystem_block_unchanged(fake_tools, tmp_path, capsys):
    no_fs = VANILLA_GPROJ.replace("FileSystem {", "FileSystemX {")
    (fake_tools / "dayz.gproj").write_text(no_fs, encoding="utf-8")
    out, _ = _run_workbench(tmp_path, capsys)
    assert "injected)" not in out
    assert "no single-entry FileSystem block" in out and "P:/MyMod/" in out
    assert "fix the pieces above by hand" in out


def test_workbench_missing_gproj_writes_placeholder_and_hint(fake_tools, tmp_path, capsys):
    out, _ = _run_workbench(tmp_path, capsys)
    hint = "/dayz-add-scaffold MyMod --piece workbench"
    assert hint in out and "dayz.gproj missing" in out
    readme = (tmp_path / "MyMod" / "workbench" / "README.md").read_text(encoding="utf-8")
    assert hint in readme and "dayz.gproj was missing" in readme


# --- check_or_clean_p_drive_link -------------------------------------------------

def test_p_link_absent_passes(tmp_path):
    nm.check_or_clean_p_drive_link(tmp_path / "MyMod", tmp_path / "workspace" / "MyMod")


def test_p_link_real_folder_refused(tmp_path):
    (tmp_path / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        nm.check_or_clean_p_drive_link(tmp_path / "MyMod", tmp_path / "workspace" / "MyMod")
    assert "real folder" in str(exc.value.code)


def test_p_link_to_other_target_refused(tmp_path, monkeypatch):
    (tmp_path / "MyMod").mkdir()
    monkeypatch.setattr(h, "link_target", lambda p: tmp_path / "elsewhere")
    monkeypatch.setattr(nm, "_remove_link", lambda p: pytest.fail("must not remove a foreign link"))
    with pytest.raises(SystemExit) as exc:
        nm.check_or_clean_p_drive_link(tmp_path / "MyMod", tmp_path / "workspace" / "MyMod")
    assert "pointing at" in str(exc.value.code)


def test_p_link_to_our_workspace_is_cleaned(tmp_path, monkeypatch):
    workspace_target = tmp_path / "workspace" / "MyMod"
    (tmp_path / "MyMod").mkdir()
    removed = []
    monkeypatch.setattr(h, "link_target", lambda p: workspace_target)
    monkeypatch.setattr(nm, "_remove_link", removed.append)
    nm.check_or_clean_p_drive_link(tmp_path / "MyMod", workspace_target)
    assert removed == [tmp_path / "MyMod"]


def test_p_link_cleanup_failure_exits(tmp_path, monkeypatch):
    workspace_target = tmp_path / "workspace" / "MyMod"
    (tmp_path / "MyMod").mkdir()

    def boom(p):
        raise subprocess.CalledProcessError(1, "rmdir", stderr="Access is denied.")

    monkeypatch.setattr(h, "link_target", lambda p: workspace_target)
    monkeypatch.setattr(nm, "_remove_link", boom)
    with pytest.raises(SystemExit) as exc:
        nm.check_or_clean_p_drive_link(tmp_path / "MyMod", workspace_target)
    assert "Access is denied" in str(exc.value.code)


# --- resolve_author ----------------------------------------------------------------

class _TTY:
    def __init__(self, tty: bool):
        self._tty = tty

    def isatty(self):
        return self._tty


@pytest.fixture
def author_cache(monkeypatch, tmp_path):
    cache = tmp_path / ".claude" / "local-memory" / "dayz-author.txt"
    monkeypatch.setattr(nm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(nm, "AUTHOR_CACHE", cache)
    return cache


def test_author_flag_wins_and_is_cached_only_by_remember(author_cache, monkeypatch):
    author_cache.parent.mkdir(parents=True)
    author_cache.write_text("OldHandle\n", encoding="utf-8")
    monkeypatch.setattr(nm.sys, "stdin", _TTY(True))
    monkeypatch.setattr("builtins.input", lambda _p: pytest.fail("must not prompt"))
    assert nm.resolve_author("  NewHandle ") == "NewHandle"
    assert author_cache.read_text(encoding="utf-8") == "OldHandle\n"  # resolving writes nothing
    nm.remember_author("NewHandle")
    assert author_cache.read_text(encoding="utf-8") == "NewHandle\n"


def test_empty_author_flag_refused(author_cache):
    with pytest.raises(SystemExit) as exc:
        nm.resolve_author("   ")
    assert "cannot be empty" in str(exc.value.code)


def test_cached_author_used_before_prompt(author_cache, monkeypatch):
    author_cache.parent.mkdir(parents=True)
    author_cache.write_text("Cached\n", encoding="utf-8")
    monkeypatch.setattr(nm.sys, "stdin", _TTY(True))
    monkeypatch.setattr("builtins.input", lambda _p: pytest.fail("must not prompt"))
    assert nm.resolve_author(None) == "Cached"


def test_prompted_author_is_cached(author_cache, monkeypatch):
    monkeypatch.setattr(nm.sys, "stdin", _TTY(True))
    monkeypatch.setattr("builtins.input", lambda _p: " Typed ")
    assert nm.resolve_author(None) == "Typed"
    assert not author_cache.exists()  # resolving writes nothing
    nm.remember_author("Typed")
    assert author_cache.read_text(encoding="utf-8") == "Typed\n"


def test_no_author_without_tty_fails(author_cache, monkeypatch):
    monkeypatch.setattr(nm.sys, "stdin", _TTY(False))
    with pytest.raises(SystemExit) as exc:
        nm.resolve_author(None)
    assert "--author" in str(exc.value.code)
    assert not author_cache.exists()


def test_eof_on_tty_stdin_gives_author_hint(author_cache, monkeypatch):
    """A null stdin (the PowerShell tool) can report a TTY and then hit end-of-file at
    once; the failure must still name --author and the cache file."""
    monkeypatch.setattr(nm.sys, "stdin", _TTY(True))

    def eof(_prompt):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    with pytest.raises(SystemExit) as exc:
        nm.resolve_author(None)
    msg = str(exc.value.code)
    assert "No author handle provided" in msg
    assert "--author" in msg
    assert "dayz-author.txt" in msg
    assert not author_cache.exists()


@pytest.mark.parametrize("bad", ['Say "hi"', "Two\nLines", "Tab\there"])
def test_author_flag_with_quote_or_control_char_refused(author_cache, bad):
    with pytest.raises(SystemExit) as exc:
        nm.resolve_author(bad)
    assert "double quote, line break" in str(exc.value.code)
    assert not author_cache.exists()


def test_prompted_author_with_quote_refused(author_cache, monkeypatch):
    monkeypatch.setattr(nm.sys, "stdin", _TTY(True))
    monkeypatch.setattr("builtins.input", lambda _p: 'Evil"Handle')
    with pytest.raises(SystemExit):
        nm.resolve_author(None)
    assert not author_cache.exists()


def test_cached_author_with_quote_refused(author_cache, monkeypatch):
    author_cache.parent.mkdir(parents=True)
    author_cache.write_text('Bad"Cache\n', encoding="utf-8")
    monkeypatch.setattr(nm.sys, "stdin", _TTY(False))
    with pytest.raises(SystemExit) as exc:
        nm.resolve_author(None)
    assert "dayz-author.txt" in str(exc.value.code)


# --- sync_project_cache ----------------------------------------------------------------

def _cache(project):
    return project / ".claude" / "local-memory" / "dayz-current-project.txt"


def _seed_cache(monkeypatch, project, cached):
    """Point new_mod at `project` and seed its project cache with `cached` (None = no cache)."""
    monkeypatch.setattr(nm, "PROJECT_DIR", project)
    if cached is not None:
        _cache(project).parent.mkdir(parents=True)
        _cache(project).write_text(str(cached), encoding="utf-8")


def test_sync_cache_sets_when_empty(monkeypatch, tmp_path, capsys):
    _seed_cache(monkeypatch, tmp_path.resolve(), None)
    nm.sync_project_cache("MyMod")
    assert _cache(tmp_path).read_text(encoding="utf-8") == str(tmp_path.resolve())
    assert "Project cache set" in capsys.readouterr().out


def test_sync_cache_noop_when_already_current(monkeypatch, tmp_path, capsys):
    _seed_cache(monkeypatch, tmp_path.resolve(), tmp_path)
    nm._state.write_state(tmp_path.resolve(), {"last_intent": {"mod_name": "MyMod"}})
    nm.sync_project_cache("MyMod")
    assert capsys.readouterr().out == ""


def test_sync_cache_repoints_other_project(monkeypatch, tmp_path, capsys):
    _seed_cache(monkeypatch, tmp_path.resolve(), tmp_path / "other")
    nm.sync_project_cache("MyMod")
    assert _cache(tmp_path).read_text(encoding="utf-8") == str(tmp_path.resolve())
    assert "repointed" in capsys.readouterr().out


def _hub_status(monkeypatch):
    """dayz-init's hub_status module, the code /dayz-init's hub and dispatch defaults read."""
    monkeypatch.syspath_prepend(str(HERE.parent / "dayz-init"))
    spec = importlib.util.spec_from_file_location(
        "dayz_init_hub_status_for_new_mod", HERE.parent / "dayz-init" / "hub_status.py")
    hub = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "dayz_init_hub_status_for_new_mod", hub)  # dataclasses look the module up
    spec.loader.exec_module(hub)
    return hub


def test_sync_makes_the_new_mod_the_hub_active_mod(monkeypatch, tmp_path):
    """/dayz-new-mod B with A active: the /dayz-init hub must then show B, not A."""
    project = tmp_path.resolve()
    _seed_cache(monkeypatch, project, project)
    nm._state.write_state(project, {"last_intent": {"mod_name": "ModA"}})
    nm.sync_project_cache("ModB")
    hub = _hub_status(monkeypatch)
    monkeypatch.setattr(hub, "_diag_running", lambda: False)
    status = hub.gather_status(project, mods_root=tmp_path / "Mods")
    assert status.mod == "ModB"
    assert "/dayz-init: ModB" in hub.render_status(status)


def test_sync_keeps_other_state_keys(monkeypatch, tmp_path):
    project = tmp_path.resolve()
    _seed_cache(monkeypatch, project, project)
    nm._state.write_state(project, {"last_intent": {"mod_name": "ModA"}, "other": 1})
    nm.sync_project_cache("ModB")
    assert nm._state.read_state(project) == {"last_intent": {"mod_name": "ModB"}, "other": 1}


# --- main(): rollback on failure -------------------------------------------------------

@pytest.fixture
def main_env(monkeypatch, tmp_path):
    project = tmp_path / "project"
    (project / ".claude").mkdir(parents=True)  # a project folder, so check_project_dir() accepts it
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.setattr(nm, "PROJECT_DIR", project)
    monkeypatch.setattr(nm, "WORKSPACE", project / "workspace")
    monkeypatch.setattr(nm, "P_DRIVE", tmp_path / "P")
    monkeypatch.setattr(h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(nm, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(nm, "resolve_author", lambda cli: "Tester")
    monkeypatch.setattr(nm, "sync_project_cache", lambda modname: None)
    monkeypatch.setattr(nm.sys, "argv", ["new_mod.py", "MyMod"])
    return project / "workspace" / "MyMod"


def test_main_success_links_and_scaffolds(main_env, monkeypatch):
    links = []
    synced = []
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: links.append((src, dst)) or "junction")
    monkeypatch.setattr(nm, "sync_project_cache", synced.append)
    assert nm.main() == 0
    assert (main_env / "config.cpp").is_file()
    assert links == [(main_env, nm.P_DRIVE / "MyMod")]
    assert synced == ["MyMod"]  # the new mod becomes the active /dayz-init mod


def test_main_without_tools_points_at_add_scaffold(main_env, monkeypatch, capsys):
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: "junction")
    nm.main()
    assert "/dayz-add-scaffold MyMod --piece workbench" in capsys.readouterr().out
    assert "/dayz-add-scaffold MyMod --piece workbench" in (main_env / "workbench" / "README.md").read_text(encoding="utf-8")


def test_main_rolls_back_when_link_fails(main_env, monkeypatch):
    def fail_link(src, dst):
        raise subprocess.CalledProcessError(1, "mklink", stderr="Access is denied.\n")

    monkeypatch.setattr(nm, "make_dir_link", fail_link)
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "rolled back" in str(exc.value.code)
    assert "junction: Access is denied." in str(exc.value.code)  # mklink's own reason, not the exit status
    assert not main_env.exists()


def test_main_rolls_back_when_scaffold_fails_midway(main_env, monkeypatch):
    def broken_workbench(target, modname):
        raise OSError("disk full")

    monkeypatch.setattr(nm, "scaffold_workbench", broken_workbench)
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: pytest.fail("must not link after a failed scaffold"))
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "disk full" in str(exc.value.code) and "rolled back" in str(exc.value.code)
    assert not main_env.exists()


def test_main_rolls_back_when_scaffold_interrupted(main_env, monkeypatch):
    def interrupted_workbench(target, modname):
        raise KeyboardInterrupt

    monkeypatch.setattr(nm, "scaffold_workbench", interrupted_workbench)
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: pytest.fail("must not link after an interrupt"))
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "interrupted" in str(exc.value.code) and "rolled back" in str(exc.value.code)
    assert not main_env.exists()


def test_main_rolls_back_when_link_interrupted(main_env, monkeypatch):
    def interrupted_link(src, dst):
        raise KeyboardInterrupt

    monkeypatch.setattr(nm, "make_dir_link", interrupted_link)
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "interrupted" in str(exc.value.code) and "rolled back" in str(exc.value.code)
    assert not main_env.exists()


def test_main_refuses_existing_workspace_entry(main_env, monkeypatch):
    main_env.mkdir(parents=True)
    (main_env / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "already exists" in str(exc.value.code)
    assert (main_env / "keep.txt").read_text(encoding="utf-8") == "mine"


# --- main(): checks before side effects, author cached only on success ------------------

@pytest.fixture
def real_author(main_env, monkeypatch):
    """main_env with the real resolve_author and an author cache holding OldHandle."""
    cache = nm.PROJECT_DIR / ".claude" / "local-memory" / "dayz-author.txt"
    cache.parent.mkdir(parents=True)
    cache.write_text("OldHandle\n", encoding="utf-8")
    monkeypatch.setattr(nm, "AUTHOR_CACHE", cache)
    monkeypatch.setattr(nm, "resolve_author", REAL_RESOLVE_AUTHOR)
    monkeypatch.setattr(nm.sys, "argv", ["new_mod.py", "MyMod", "--author", "NewHandle"])
    return cache


def test_refused_existing_workspace_keeps_cached_author(main_env, real_author, monkeypatch):
    """A run refused because workspace/<Mod> exists must not replace the cached handle,
    and is refused before preflight runs."""
    main_env.mkdir(parents=True)
    monkeypatch.setattr(h, "gate_on_preflight", lambda: pytest.fail("preflight before the target check"))
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "already exists" in str(exc.value.code)
    assert real_author.read_text(encoding="utf-8") == "OldHandle\n"


def test_invalid_name_refused_before_preflight(main_env, real_author, monkeypatch):
    monkeypatch.setattr(h, "gate_on_preflight", lambda: pytest.fail("preflight before the name check"))
    monkeypatch.setattr(nm.sys, "argv", ["new_mod.py", "1Bad-Name", "--author", "NewHandle"])
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "Invalid mod name" in str(exc.value.code)
    assert real_author.read_text(encoding="utf-8") == "OldHandle\n"


def test_refused_real_p_folder_keeps_cached_author(main_env, real_author):
    (nm.P_DRIVE / "MyMod").mkdir(parents=True)  # a real folder where the link would go
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "real folder" in str(exc.value.code)
    assert real_author.read_text(encoding="utf-8") == "OldHandle\n"
    assert not main_env.exists()


def test_failed_link_keeps_cached_author(main_env, real_author, monkeypatch):
    def fail_link(src, dst):
        raise subprocess.CalledProcessError(1, "mklink", stderr="Access is denied.\n")

    monkeypatch.setattr(nm, "make_dir_link", fail_link)
    with pytest.raises(SystemExit):
        nm.main()
    assert real_author.read_text(encoding="utf-8") == "OldHandle\n"


def test_successful_run_caches_new_author(main_env, real_author, monkeypatch):
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: "junction")
    assert nm.main() == 0
    assert real_author.read_text(encoding="utf-8") == "NewHandle\n"
    assert 'author = "NewHandle";' in (main_env / "config.cpp").read_text(encoding="utf-8")


def test_project_dir_found_from_subfolder(monkeypatch, tmp_path):
    """Loaded from inside workspace/ with no CLAUDE_PROJECT_DIR, new_mod resolves
    the project the way every skill does (the cache above cwd), so workspace/ and
    the author cache are not created under the subfolder."""
    project = tmp_path.resolve() / "project"
    _cache(project).parent.mkdir(parents=True)
    _cache(project).write_text(str(project), encoding="utf-8")
    (project / "workspace").mkdir()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(project / "workspace")
    spec = importlib.util.spec_from_file_location("dayz_new_mod_subfolder", HERE / "new_mod.py")
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    assert fresh.PROJECT_DIR == project
    assert fresh.WORKSPACE == project / "workspace"
    assert fresh.AUTHOR_CACHE == project / ".claude" / "local-memory" / "dayz-author.txt"


# --- project folder: refuse a bare working-directory fallback ---------------------------

@pytest.fixture
def outside(main_env, monkeypatch, tmp_path):
    """A first run from a shell outside the clone: no CLAUDE_PROJECT_DIR, no project
    cache anywhere, and the clone that holds the script (a stand-in) has no cache
    either, so the lookup falls back to the working directory."""
    clone = tmp_path / "clone"
    (clone / ".claude").mkdir(parents=True)
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    monkeypatch.setattr(nm._state, "SCRIPT_CLONE", clone)
    monkeypatch.setattr(nm._state.Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.chdir(cwd)
    found = nm._state.find_project_dir()
    assert found == cwd.resolve()  # really the working-directory fallback
    for name in ("PROJECT_DIR", "WORKSPACE", "LOCAL_MEMORY", "AUTHOR_CACHE"):
        monkeypatch.setattr(nm, name, getattr(nm, name))  # restored after the test
    nm.set_project_dir(found)
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: pytest.fail("must not link"))
    return clone, cwd


def test_first_run_outside_clone_is_refused_before_anything(outside, monkeypatch):
    clone, cwd = outside
    monkeypatch.setattr(h, "gate_on_preflight", lambda: pytest.fail("preflight before the project check"))
    with pytest.raises(SystemExit) as exc:
        nm.main()
    msg = str(exc.value.code)
    assert "No DayZ project found" in msg and str(cwd.resolve()) in msg and "--project" in msg
    assert list(cwd.iterdir()) == []  # no workspace/, no local-memory/


def test_project_flag_scaffolds_in_the_named_folder(outside, monkeypatch):
    clone, cwd = outside
    links = []
    synced = []
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: links.append(src) or "junction")
    monkeypatch.setattr(nm, "sync_project_cache", synced.append)
    monkeypatch.setattr(nm.sys, "argv", ["new_mod.py", "MyMod", "--project", str(clone)])
    assert nm.main() == 0
    assert (clone / "workspace" / "MyMod" / "config.cpp").is_file()
    assert links == [clone.resolve() / "workspace" / "MyMod"]
    assert nm.PROJECT_DIR == clone.resolve() and synced == ["MyMod"]
    assert list(cwd.iterdir()) == []


def test_missing_project_flag_folder_refused(outside, monkeypatch, tmp_path):
    monkeypatch.setattr(nm.sys, "argv", ["new_mod.py", "MyMod", "--project", str(tmp_path / "nope")])
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "--project folder not found" in str(exc.value.code)


def test_fallback_that_is_the_script_clone_is_accepted(outside, monkeypatch):
    clone, cwd = outside
    nm.set_project_dir(clone)  # a fresh clone run from its own root
    nm.check_project_dir()


@pytest.mark.parametrize("marker", [".claude", "workspace"])
def test_fallback_with_project_folder_is_accepted(outside, marker):
    clone, cwd = outside
    (cwd / marker).mkdir()
    nm.check_project_dir()


def test_fallback_with_claude_project_dir_set_is_accepted(outside, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(outside[1]))
    nm.check_project_dir()


# --- sync_project_cache: an unreadable state file is backed up, not silently replaced ---

@pytest.mark.parametrize("content", ["{not json", "[1, 2]", '{"last_intent": "ModA", "other": 1'])
def test_sync_backs_up_unreadable_state(monkeypatch, tmp_path, capsys, content):
    project = tmp_path.resolve()
    _seed_cache(monkeypatch, project, project)
    state_file = project / ".claude" / "local-memory" / "dayz-init-state.json"
    state_file.write_text(content, encoding="utf-8")
    nm.sync_project_cache("ModB")
    backups = list(state_file.parent.glob("dayz-init-state.*.bak.json"))
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == content
    assert nm._state.read_state(project) == {"last_intent": {"mod_name": "ModB"}}
    out = capsys.readouterr().out
    assert "could not be read" in out and backups[0].name in out


def test_sync_replaces_non_object_last_intent(monkeypatch, tmp_path):
    project = tmp_path.resolve()
    _seed_cache(monkeypatch, project, project)
    nm._state.write_state(project, {"last_intent": "ModA", "other": 1})
    nm.sync_project_cache("ModB")
    assert nm._state.read_state(project) == {"last_intent": {"mod_name": "ModB"}, "other": 1}
