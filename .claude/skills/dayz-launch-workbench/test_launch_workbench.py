"""Tests for the Workbench launcher: flag exclusivity and gproj resolution."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_launch_workbench_under_test", HERE / "launch.py")
wb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wb)


@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    drive.mkdir()
    monkeypatch.setattr(wb, "P_DRIVE", drive)
    return drive


def test_mod_and_gproj_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc:
        wb.build_parser().parse_args(["--mod", "MyMod", "--gproj", "x.gproj"])
    assert exc.value.code == 2


def test_no_flags_means_bundled_gproj():
    assert wb.resolve_gproj(None, None) is None


def test_mod_resolves_to_workbench_gproj(p_drive):
    gproj = p_drive / "MyMod" / "workbench" / "dayz.gproj"
    gproj.parent.mkdir(parents=True)
    gproj.write_text("", encoding="utf-8")
    assert wb.resolve_gproj("MyMod", None) == gproj


def test_missing_mod_folder_points_at_new_mod(p_drive):
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj("MyMod", None)
    assert "/dayz-new-mod MyMod" in str(exc.value.code)


def test_missing_gproj_points_at_add_scaffold(p_drive):
    (p_drive / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj("MyMod", None)
    assert "/dayz-add-scaffold MyMod --piece workbench" in str(exc.value.code)


def test_relative_gproj_resolves_against_project(tmp_path, monkeypatch):
    monkeypatch.setattr(wb, "PROJECT_DIR", tmp_path)
    (tmp_path / "custom.gproj").write_text("", encoding="utf-8")
    assert wb.resolve_gproj(None, "custom.gproj") == (tmp_path / "custom.gproj").resolve()


def test_missing_gproj_path_exits(tmp_path):
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj(None, str(tmp_path / "nope.gproj"))
    assert "does not exist" in str(exc.value.code)


def test_wrong_extension_warns(tmp_path, capsys):
    other = tmp_path / "project.txt"
    other.write_text("", encoding="utf-8")
    assert wb.resolve_gproj(None, str(other)) == other
    assert "not a .gproj" in capsys.readouterr().out


def test_launch_uses_shared_detach_flags_and_workbench_cwd(tmp_path, monkeypatch):
    exe = tmp_path / "Bin" / "Workbench" / "workbenchApp.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    spawned = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            spawned.update(cmd=cmd, **kwargs)

    class FakePreflight:
        @staticmethod
        def find_dayz_tools():
            return tmp_path

    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", FakePreflight, raising=False)
    monkeypatch.setattr(wb.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 0
    assert spawned["cmd"] == [str(exe)]
    assert spawned["creationflags"] == wb.h.DETACH_FLAGS
    assert spawned["cwd"] == str(exe.parent)
