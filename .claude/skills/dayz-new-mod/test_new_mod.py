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
