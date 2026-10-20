"""Tests for the Object Builder launcher: flag exclusivity and target resolution."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_launch_objectbuilder_under_test", HERE / "launch.py")
ob = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ob)


def test_file_and_mod_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit) as exc:
        ob.build_parser().parse_args(["--file", "a.p3d", "--mod", "MyMod"])
    assert exc.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [[], ["--file", "a.p3d"], ["--mod", "MyMod"]])
def test_one_or_neither_flag_parses(argv):
    ob.build_parser().parse_args(argv)


def test_no_flags_means_no_target():
    assert ob.resolve_target(None, None) is None


def test_absolute_file_target(tmp_path):
    model = tmp_path / "model.p3d"
    model.write_bytes(b"")
    assert ob.resolve_target(str(model), None) == model


def test_relative_file_resolves_against_project(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "PROJECT_DIR", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "model.p3d").write_bytes(b"")
    assert ob.resolve_target("data/model.p3d", None) == (tmp_path / "data" / "model.p3d").resolve()


def test_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(str(tmp_path / "nope.p3d"), None)
    assert "does not exist" in str(exc.value.code)


def test_non_p3d_file_warns(tmp_path, capsys):
    other = tmp_path / "model.obj"
    other.write_bytes(b"")
    assert ob.resolve_target(str(other), None) == other
    assert "not a .p3d" in capsys.readouterr().out


def test_mod_target_is_p_drive_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    (tmp_path / "MyMod").mkdir()
    assert ob.resolve_target(None, "MyMod") == tmp_path / "MyMod"


def test_missing_mod_folder_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, "MyMod")
    assert "/dayz-new-mod MyMod" in str(exc.value.code)


def test_bad_file_fails_before_preflight(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ob.h, "gate_on_preflight", lambda: calls.append("preflight"))
    monkeypatch.setattr(ob, "registry_has_objectbuilder_settings", lambda: calls.append("registry") or True)
    monkeypatch.setattr("sys.argv", ["launch.py", "--file", str(tmp_path / "missing.p3d")])
    with pytest.raises(SystemExit) as exc:
        ob.main()
    assert "does not exist" in str(exc.value.code)
    assert calls == []


def test_launch_uses_shared_detach_flags(tmp_path, monkeypatch):
    exe = tmp_path / "Bin" / "ObjectBuilder" / "ObjectBuilder.exe"
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

    monkeypatch.setattr(ob.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(ob.h, "preflight", FakePreflight, raising=False)
    monkeypatch.setattr(ob, "registry_has_objectbuilder_settings", lambda: True)
    monkeypatch.setattr(ob.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert ob.main() == 0
    assert spawned["cmd"] == [str(exe)]
    assert spawned["creationflags"] == ob.h.DETACH_FLAGS
    assert spawned["cwd"] == str(exe.parent)
