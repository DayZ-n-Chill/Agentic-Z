"""Tests for build.py: workspace, junction, ownership-marker and stale-PBO checks."""
from __future__ import annotations

import importlib.util
import os
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_build_pbo_under_test", HERE / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)
h = build.h


@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    drive.mkdir()
    monkeypatch.setattr(build, "P_DRIVE", drive)
    monkeypatch.setattr(build, "MODS_ROOT", drive / "Mods")
    return drive


def _scaffold(project: Path, name: str = "MyMod") -> Path:
    mod = project / "workspace" / name
    mod.mkdir(parents=True)
    (mod / "config.cpp").write_text("class CfgPatches {};", encoding="utf-8")
    (mod / "$PBOPREFIX$").write_text(name, encoding="utf-8")
    return mod


# --- workspace -------------------------------------------------------------

def test_verify_workspace_accepts_scaffold(tmp_path):
    mod = _scaffold(tmp_path)
    assert build.verify_workspace("MyMod", tmp_path) == mod


def test_verify_workspace_missing_folder(tmp_path):
    with pytest.raises(SystemExit) as exc:
        build.verify_workspace("MyMod", tmp_path)
    assert "not found" in str(exc.value.code)


@pytest.mark.parametrize("missing", ["config.cpp", "$PBOPREFIX$"])
def test_verify_workspace_missing_required_file(tmp_path, missing):
    mod = _scaffold(tmp_path)
    (mod / missing).unlink()
    with pytest.raises(SystemExit) as exc:
        build.verify_workspace("MyMod", tmp_path)
    assert missing in str(exc.value.code)


# --- junction ----------------------------------------------------------------

def test_verify_junction_missing(p_drive, tmp_path):
    with pytest.raises(SystemExit) as exc:
        build.verify_junction("MyMod", tmp_path / "workspace" / "MyMod")
    assert "junction is missing" in str(exc.value.code)
    assert "/dayz-add-scaffold MyMod --piece junction" in str(exc.value.code)


def test_verify_junction_real_folder(p_drive, tmp_path):
    (p_drive / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        build.verify_junction("MyMod", tmp_path / "workspace" / "MyMod")
    assert "real folder" in str(exc.value.code)


def test_verify_junction_points_elsewhere(p_drive, tmp_path, monkeypatch):
    (p_drive / "MyMod").mkdir()
    monkeypatch.setattr(h, "link_target", lambda p: tmp_path / "somewhere-else")
    with pytest.raises(SystemExit) as exc:
        build.verify_junction("MyMod", tmp_path / "workspace" / "MyMod")
    assert "points at" in str(exc.value.code)


def test_verify_junction_valid(p_drive, tmp_path, monkeypatch):
    workspace_mod = tmp_path / "workspace" / "MyMod"
    (p_drive / "MyMod").mkdir()
    monkeypatch.setattr(h, "link_target", lambda p: workspace_mod)
    assert build.verify_junction("MyMod", workspace_mod) == p_drive / "MyMod"


# --- ownership marker ---------------------------------------------------------

def test_marker_gate_refuses_existing_unmarked_deploy_dir(p_drive):
    deploy = build.MODS_ROOT / "@MyMod"
    (deploy / "Addons").mkdir(parents=True)
    with pytest.raises(SystemExit):
        h.gate_on_marker("MyMod", deploy)


def test_marker_gate_allows_first_build_and_marked_dir(p_drive):
    deploy = build.MODS_ROOT / "@MyMod"
    h.gate_on_marker("MyMod", deploy)  # absent: first build
    deploy.mkdir(parents=True)
    h.write_marker(deploy, "MyMod")
    h.gate_on_marker("MyMod", deploy)


# --- AddonBuilder command and output -----------------------------------------

def test_build_cmd_includes_include_list_and_clear(tmp_path):
    cmd = build.build_addon_builder_cmd(
        Path("AB.exe"), Path("P:/MyMod"), Path("P:/Mods/@MyMod/Addons"), "MyMod", Path("P:/temp/MyMod"), clean=True
    )
    assert f"-include={build.INCLUDE_LIST}" in cmd
    assert "-prefix=MyMod" in cmd
    assert cmd[-1] == "-clear"
    assert "-clear" not in build.build_addon_builder_cmd(
        Path("AB.exe"), Path("s"), Path("t"), "MyMod", Path("tmp"), clean=False
    )


def test_include_list_exists_and_covers_scripts():
    patterns = build.INCLUDE_LIST.read_text(encoding="utf-8").strip().split(";")
    assert "*.c" in patterns and "*.layout" in patterns


def test_check_pbo_output_missing(tmp_path):
    assert "missing" in build.check_pbo_output(tmp_path / "MyMod.pbo", time.time())


def test_check_pbo_output_stale(tmp_path):
    pbo = tmp_path / "MyMod.pbo"
    pbo.write_bytes(b"old")
    old = time.time() - 3600
    os.utime(pbo, (old, old))
    assert "stale" in build.check_pbo_output(pbo, time.time())


def test_check_pbo_output_fresh(tmp_path):
    started = time.time()
    pbo = tmp_path / "MyMod.pbo"
    pbo.write_bytes(b"new")
    assert build.check_pbo_output(pbo, started) is None


# --- --clean safety ----------------------------------------------------------

def test_other_pbos_lists_only_foreign_pbos(tmp_path):
    addons = tmp_path / "Addons"
    addons.mkdir()
    for name in ("MyMod.pbo", "mymod.pbo.bisign", "Payload.pbo", "Extra.PBO", "readme.txt"):
        (addons / name).write_text("x", encoding="utf-8")
    assert build.other_pbos(addons, "MyMod") == ["Extra.PBO", "Payload.pbo"]
    assert build.other_pbos(tmp_path / "missing", "MyMod") == []


def test_gate_clean_refuses_when_payload_pbos_present(tmp_path):
    addons = tmp_path / "Addons"
    addons.mkdir()
    (addons / "MyMod.pbo").write_text("x", encoding="utf-8")
    build.gate_clean(addons, "MyMod")  # only our own PBO: allowed
    (addons / "Payload.pbo").write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        build.gate_clean(addons, "MyMod")
    assert "Payload.pbo" in str(exc.value.code)


def test_main_clean_refuses_before_running_addonbuilder(p_drive, tmp_path, monkeypatch):
    project = tmp_path / "proj"
    _scaffold(project)
    deploy = p_drive / "Mods" / "@MyMod"
    (deploy / "Addons").mkdir(parents=True)
    h.write_marker(deploy, "MyMod")
    (deploy / "Addons" / "Payload.pbo").write_text("x", encoding="utf-8")
    ran = []
    monkeypatch.setattr(build.h, "resolve_project_dir", lambda: project)
    monkeypatch.setattr(build.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(build, "validate_p_mods", lambda: None)
    monkeypatch.setattr(build, "verify_junction", lambda m, w: None)
    monkeypatch.setattr(build, "resolve_addon_builder", lambda: Path("AB.exe"))
    monkeypatch.setattr(build.subprocess, "run", lambda *a, **k: ran.append(a))
    monkeypatch.setattr("sys.argv", ["build.py", "MyMod", "--clean"])
    with pytest.raises(SystemExit) as exc:
        build.main()
    assert "--clean would wipe" in str(exc.value.code)
    assert ran == []
