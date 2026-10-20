"""Tests for clean.py: managed-mod detection, link handling, ownership marker, plan order."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_clean_workspace_under_test", HERE / "clean.py")
clean = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clean)
h = clean.h


@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    (drive / "Mods").mkdir(parents=True)
    monkeypatch.setattr(clean, "P_DRIVE", drive)
    monkeypatch.setattr(clean, "MODS_ROOT", drive / "Mods")
    return drive


def _native(workspace: Path, name: str) -> Path:
    mod = workspace / name
    mod.mkdir(parents=True)
    (mod / "config.cpp").write_text("", encoding="utf-8")
    (mod / "$PBOPREFIX$").write_text(name, encoding="utf-8")
    return mod


# --- is_scaffolded_mod / link detection --------------------------------------

def test_native_scaffold_is_managed(tmp_path):
    assert clean.is_scaffolded_mod(_native(tmp_path, "MyMod"))


def test_folder_without_scaffold_files_is_not_managed(tmp_path):
    (tmp_path / "Random").mkdir()
    assert not clean.is_scaffolded_mod(tmp_path / "Random")


def test_file_is_not_managed(tmp_path):
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")
    assert not clean.is_scaffolded_mod(tmp_path / "notes.txt")


def test_link_without_scaffold_files_is_managed(tmp_path, monkeypatch):
    (tmp_path / "Imported").mkdir()
    monkeypatch.setattr(h, "is_link", lambda p: True)
    assert clean.is_scaffolded_mod(tmp_path / "Imported")


def test_discover_mods_skips_unmanaged(tmp_path):
    ws = tmp_path / "workspace"
    _native(ws, "B")
    _native(ws, "A")
    (ws / "Junk").mkdir()
    assert [p.name for p in clean.discover_mods(ws, None)] == ["A", "B"]


def test_discover_mods_missing_workspace(tmp_path):
    assert clean.discover_mods(tmp_path / "workspace", None) == []


def test_discover_mods_target_not_managed_names_both_kinds(tmp_path):
    (tmp_path / "workspace" / "Junk").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        clean.discover_mods(tmp_path / "workspace", "Junk")
    msg = str(exc.value.code)
    assert "imported mod link" in msg and "config.cpp" in msg


# --- find_artifacts: ownership + order ------------------------------------------

def test_plan_order_junction_deployed_workspace(p_drive, tmp_path, monkeypatch):
    mod = _native(tmp_path / "workspace", "MyMod")
    deployed = p_drive / "Mods" / "@MyMod"
    deployed.mkdir()
    h.write_marker(deployed, "MyMod")
    monkeypatch.setattr(h, "link_target", lambda p: mod if p == p_drive / "MyMod" else None)

    plan, warnings = clean.find_artifacts(mod)

    assert [kind for kind, _ in plan] == ["junction", "deployed", "workspace"]
    assert plan[0][1] == p_drive / "MyMod"
    assert warnings == []


def test_unmarked_deploy_dir_is_skipped_with_warning(p_drive, tmp_path):
    mod = _native(tmp_path / "workspace", "MyMod")
    (p_drive / "Mods" / "@MyMod").mkdir()

    plan, warnings = clean.find_artifacts(mod)

    assert [kind for kind, _ in plan] == ["workspace"]
    assert len(warnings) == 1 and h.SCAFFOLD_MARKER in warnings[0]


def test_mismatched_marker_is_skipped(p_drive, tmp_path):
    mod = _native(tmp_path / "workspace", "MyMod")
    deployed = p_drive / "Mods" / "@MyMod"
    deployed.mkdir()
    h.write_marker(deployed, "OtherMod")

    plan, warnings = clean.find_artifacts(mod)
    assert "deployed" not in [kind for kind, _ in plan]
    assert warnings


def test_junction_pointing_elsewhere_is_left_alone(p_drive, tmp_path, monkeypatch):
    mod = _native(tmp_path / "workspace", "MyMod")
    monkeypatch.setattr(h, "link_target", lambda p: tmp_path / "other-project" / "MyMod")
    plan, _ = clean.find_artifacts(mod)
    assert "junction" not in [kind for kind, _ in plan]


def test_imported_link_is_planned_as_workspace_link(p_drive, tmp_path, monkeypatch):
    mod = tmp_path / "workspace" / "Imported"
    mod.mkdir(parents=True)
    monkeypatch.setattr(h, "is_link", lambda p: p == mod)
    plan, _ = clean.find_artifacts(mod)
    assert plan[-1] == ("workspace-link", mod)


# --- remove_artifact never recurses into links -------------------------------

def test_remove_artifact_uses_rmdir_for_links(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(clean.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(clean.shutil, "rmtree", lambda p: pytest.fail("rmtree must not run on a link"))
    clean.remove_artifact("workspace-link", tmp_path / "Imported")
    clean.remove_artifact("junction", tmp_path / "P" / "MyMod")
    assert [c[:3] for c in calls] == [["cmd", "/c", "rmdir"]] * 2


def test_remove_artifact_rmtree_for_folders(tmp_path):
    mod = _native(tmp_path, "MyMod")
    clean.remove_artifact("workspace", mod)
    assert not mod.exists()
