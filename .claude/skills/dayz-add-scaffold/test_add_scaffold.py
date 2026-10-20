"""Tests for add_scaffold.py: every piece is idempotent and never touches existing files."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_add_scaffold_under_test", HERE / "add_scaffold.py")
scaf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scaf)

GPROJ = """GameProjectClass {
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
     Name "game"
     Paths {
      "scripts/3_Game"
     }
    }
   }
  }
 }
}
"""


@pytest.fixture
def fake_tools(monkeypatch, tmp_path):
    wb = tmp_path / "Tools" / "Bin" / "Workbench"
    wb.mkdir(parents=True)
    (wb / "dayz.gproj").write_text(GPROJ, encoding="utf-8")
    (wb / "DayZSetting.xml").write_text("<settings/>", encoding="utf-8")
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: tmp_path / "Tools")
    return wb


def _author():
    return "Tester"


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _run_piece(piece: str, target: Path) -> bool:
    return scaf.PIECE_FUNCS[piece](target, "MyMod", _author)


@pytest.mark.parametrize("piece", scaf.PIECES)
def test_second_run_changes_nothing(piece, tmp_path, fake_tools):
    target = tmp_path / "workspace" / "MyMod"
    target.mkdir(parents=True)
    assert _run_piece(piece, target) is True
    before = _snapshot(target)
    assert _run_piece(piece, target) is False
    assert _snapshot(target) == before


@pytest.mark.parametrize(
    "piece, rel",
    [("config", "config.cpp"), ("prefix", "$PBOPREFIX$"), ("readme", "README.md")],
)
def test_existing_file_is_left_untouched(piece, rel, tmp_path):
    target = tmp_path / "MyMod"
    target.mkdir()
    (target / rel).write_text("user content", encoding="utf-8")
    assert _run_piece(piece, target) is False
    assert (target / rel).read_text(encoding="utf-8") == "user content"


def test_existing_config_does_not_prompt_for_author(tmp_path):
    target = tmp_path / "MyMod"
    target.mkdir()
    (target / "config.cpp").write_text("mine", encoding="utf-8")
    assert scaf.add_config(target, "MyMod", lambda: pytest.fail("author must not be resolved")) is False


def test_skeleton_adds_only_missing_folders(tmp_path):
    target = tmp_path / "MyMod"
    (target / "data").mkdir(parents=True)
    (target / "data" / "model.p3d").write_bytes(b"p3d")
    assert scaf.add_skeleton(target) is True
    assert (target / "scripts" / "3_Game" / ".gitkeep").exists()
    assert not (target / "data" / ".gitkeep").exists()
    assert (target / "data" / "model.p3d").read_bytes() == b"p3d"


def test_workbench_keeps_existing_gproj_and_adds_missing_xml(tmp_path, fake_tools):
    target = tmp_path / "MyMod"
    (target / "workbench").mkdir(parents=True)
    (target / "workbench" / "dayz.gproj").write_text("custom gproj", encoding="utf-8")
    assert scaf.add_workbench(target, "MyMod") is True
    assert (target / "workbench" / "dayz.gproj").read_text(encoding="utf-8") == "custom gproj"
    assert (target / "workbench" / "DayZSetting.xml").read_text(encoding="utf-8") == "<settings/>"


def test_workbench_gproj_gets_mod_paths(tmp_path, fake_tools):
    target = tmp_path / "MyMod"
    target.mkdir()
    scaf.add_workbench(target, "MyMod")
    text = (target / "workbench" / "dayz.gproj").read_text(encoding="utf-8")
    assert '"MyMod/scripts/3_Game"' in text and 'Directory "P:/MyMod/"' in text


def test_workbench_skipped_without_tools(tmp_path, monkeypatch):
    monkeypatch.setattr(scaf._nm, "find_dayz_tools", lambda: None)
    target = tmp_path / "MyMod"
    target.mkdir()
    assert scaf.add_workbench(target, "MyMod") is False
    assert not (target / "workbench" / "dayz.gproj").exists()


def test_output_matches_new_mod_templates(tmp_path):
    target = tmp_path / "MyMod"
    target.mkdir()
    scaf.add_config(target, "MyMod", _author)
    expected = scaf._nm.CONFIG_CPP_TEMPLATE.substitute(modname="MyMod", author="Tester")
    assert (target / "config.cpp").read_text(encoding="utf-8") == expected
