"""Tests for new_mod.py: name validation, gproj injection, P:\\ link pre-check."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_new_mod_under_test", HERE / "new_mod.py")
nm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nm)
h = nm.h

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


def test_rewrite_filesystem_block_mounts_p_drive_and_mod():
    out = nm.rewrite_filesystem_block(VANILLA_GPROJ, "MyMod")
    assert 'Directory "./"' not in out
    assert 'Directory "P:/"' in out and 'Directory "P:/MyMod/"' in out
    assert 'Name "game"' in out  # the rest of the file survives


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


def test_author_flag_wins_and_is_cached(author_cache, monkeypatch):
    author_cache.parent.mkdir(parents=True)
    author_cache.write_text("OldHandle\n", encoding="utf-8")
    monkeypatch.setattr(nm.sys, "stdin", _TTY(True))
    monkeypatch.setattr("builtins.input", lambda _p: pytest.fail("must not prompt"))
    assert nm.resolve_author("  NewHandle ") == "NewHandle"
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
    assert author_cache.read_text(encoding="utf-8") == "Typed\n"


def test_no_author_without_tty_fails(author_cache, monkeypatch):
    monkeypatch.setattr(nm.sys, "stdin", _TTY(False))
    with pytest.raises(SystemExit) as exc:
        nm.resolve_author(None)
    assert "--author" in str(exc.value.code)
    assert not author_cache.exists()


# --- sync_project_cache ----------------------------------------------------------------

def _fake_state(monkeypatch, cached):
    written = []

    class FakeState:
        @staticmethod
        def cached_project_root():
            return cached

        @staticmethod
        def write_cached_project_root(path):
            written.append(path)

    monkeypatch.setattr(h, "load_module", lambda name, path: FakeState)
    return written


def test_sync_cache_sets_when_empty(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(nm, "PROJECT_DIR", tmp_path.resolve())
    written = _fake_state(monkeypatch, None)
    nm.sync_project_cache()
    assert written == [tmp_path.resolve()]
    assert "Project cache set" in capsys.readouterr().out


def test_sync_cache_noop_when_already_current(monkeypatch, tmp_path):
    monkeypatch.setattr(nm, "PROJECT_DIR", tmp_path.resolve())
    assert _fake_state(monkeypatch, tmp_path) == []
    nm.sync_project_cache()


def test_sync_cache_repoints_other_project(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(nm, "PROJECT_DIR", tmp_path.resolve())
    written = _fake_state(monkeypatch, tmp_path / "other")
    nm.sync_project_cache()
    assert written == [tmp_path.resolve()]
    assert "repointed" in capsys.readouterr().out


# --- main(): rollback on failure -------------------------------------------------------

@pytest.fixture
def main_env(monkeypatch, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(nm, "PROJECT_DIR", project)
    monkeypatch.setattr(nm, "WORKSPACE", project / "workspace")
    monkeypatch.setattr(nm, "P_DRIVE", tmp_path / "P")
    monkeypatch.setattr(h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(nm, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(nm, "resolve_author", lambda cli: "Tester")
    monkeypatch.setattr(nm, "sync_project_cache", lambda: None)
    monkeypatch.setattr(nm.sys, "argv", ["new_mod.py", "MyMod"])
    return project / "workspace" / "MyMod"


def test_main_success_links_and_scaffolds(main_env, monkeypatch):
    links = []
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: links.append((src, dst)) or "junction")
    assert nm.main() == 0
    assert (main_env / "config.cpp").is_file()
    assert links == [(main_env, nm.P_DRIVE / "MyMod")]


def test_main_without_tools_points_at_add_scaffold(main_env, monkeypatch, capsys):
    monkeypatch.setattr(nm, "make_dir_link", lambda src, dst: "junction")
    nm.main()
    assert "/dayz-add-scaffold MyMod --piece workbench" in capsys.readouterr().out
    assert "/dayz-add-scaffold MyMod --piece workbench" in (main_env / "workbench" / "README.md").read_text(encoding="utf-8")


def test_main_rolls_back_when_link_fails(main_env, monkeypatch):
    def fail_link(src, dst):
        raise subprocess.CalledProcessError(1, "mklink")

    monkeypatch.setattr(nm, "make_dir_link", fail_link)
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "rolled back" in str(exc.value.code)
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


def test_main_refuses_existing_workspace_entry(main_env, monkeypatch):
    main_env.mkdir(parents=True)
    (main_env / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        nm.main()
    assert "already exists" in str(exc.value.code)
    assert (main_env / "keep.txt").read_text(encoding="utf-8") == "mine"
