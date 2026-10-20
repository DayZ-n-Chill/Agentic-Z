"""Tests for skill_helpers.py (preflight gate, project cache, links, ownership marker)."""
from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("skill_helpers_under_test", HERE / "skill_helpers.py")
h = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(h)


def test_load_module_loads_by_path(tmp_path):
    src = tmp_path / "thing.py"
    src.write_text("VALUE = 42\n", encoding="utf-8")
    assert h.load_module("thing_mod", src).VALUE == 42


def test_load_module_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        h.load_module("missing_mod", tmp_path / "nope.py")


def test_gate_on_preflight_passes_on_zero(monkeypatch):
    calls = []
    monkeypatch.setattr(h.subprocess, "run", lambda cmd: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0))
    h.gate_on_preflight()
    assert calls and calls[0][-1] == str(h.PREFLIGHT)


def test_gate_on_preflight_exits_with_preflight_code(monkeypatch):
    monkeypatch.setattr(h.subprocess, "run", lambda cmd: subprocess.CompletedProcess(cmd, 1))
    with pytest.raises(SystemExit) as exc:
        h.gate_on_preflight()
    assert exc.value.code == 1


def _fake_state(monkeypatch, cached):
    class FakeState:
        @staticmethod
        def cached_project_root():
            return cached

    monkeypatch.setattr(h, "load_module", lambda name, path: FakeState)


def test_resolve_project_dir_uses_cache(monkeypatch, tmp_path):
    _fake_state(monkeypatch, tmp_path)
    assert h.resolve_project_dir() == tmp_path.resolve()


def test_resolve_project_dir_exits_2_without_cache(monkeypatch):
    _fake_state(monkeypatch, None)
    with pytest.raises(SystemExit) as exc:
        h.resolve_project_dir()
    assert exc.value.code == 2


def test_resolve_project_dir_reads_dayz_init_state():
    assert h.DAYZ_INIT_STATE.is_file()
    assert hasattr(h.load_module("state_probe", h.DAYZ_INIT_STATE), "cached_project_root")


def test_link_target_strips_extended_prefix(monkeypatch):
    monkeypatch.setattr(h.os, "readlink", lambda p: "\\\\?\\C:\\proj\\workspace\\MyMod")
    assert h.link_target(Path("P:/MyMod")) == Path("C:\\proj\\workspace\\MyMod")


def test_link_target_none_for_plain_folder(tmp_path):
    assert h.link_target(tmp_path) is None


def test_paths_equal_ignores_case_and_trailing_separators():
    if os.name == "nt":
        assert h.paths_equal(Path("C:/Proj/Workspace/MyMod/"), Path("c:\\proj\\workspace\\mymod"))
    assert h.paths_equal(Path("a/b/../b/c"), Path("a/b/c"))
    assert not h.paths_equal(Path("a/b"), Path("a/c"))


def test_is_link_false_for_plain_folder(tmp_path):
    assert h.is_link(tmp_path) is False


def test_is_link_true_for_symlink(monkeypatch, tmp_path):
    monkeypatch.setattr(h.os.path, "islink", lambda p: True)
    assert h.is_link(tmp_path) is True


@pytest.mark.skipif(os.name != "nt", reason="junction attribute only exists on Windows")
def test_is_link_true_for_reparse_point(monkeypatch, tmp_path):
    class FakeStat:
        st_file_attributes = 0x400

    monkeypatch.setattr(h.os.path, "islink", lambda p: False)
    monkeypatch.setattr(h.os, "lstat", lambda p: FakeStat())
    assert h.is_link(tmp_path) is True


def test_owns_deploy_dir(tmp_path):
    assert h.owns_deploy_dir(tmp_path, "MyMod") is False
    (tmp_path / h.SCAFFOLD_MARKER).write_text("OtherMod\n", encoding="utf-8")
    assert h.owns_deploy_dir(tmp_path, "MyMod") is False
    (tmp_path / h.SCAFFOLD_MARKER).write_text("MyMod\n", encoding="utf-8")
    assert h.owns_deploy_dir(tmp_path, "MyMod") is True


def test_gate_on_marker_passes_when_dir_absent(tmp_path):
    h.gate_on_marker("MyMod", tmp_path / "@MyMod")


def test_gate_on_marker_refuses_unmarked_dir(tmp_path):
    deploy = tmp_path / "@MyMod"
    deploy.mkdir()
    with pytest.raises(SystemExit) as exc:
        h.gate_on_marker("MyMod", deploy)
    assert "ownership marker" in str(exc.value.code)


def test_gate_on_marker_passes_marked_dir(tmp_path):
    deploy = tmp_path / "@MyMod"
    deploy.mkdir()
    h.write_marker(deploy, "MyMod")
    h.gate_on_marker("MyMod", deploy)
    assert (deploy / h.SCAFFOLD_MARKER).read_text(encoding="utf-8") == "MyMod\n"


def test_write_marker_failure_only_warns(tmp_path, capsys):
    h.write_marker(tmp_path / "missing-dir", "MyMod")
    assert "Could not write ownership marker" in capsys.readouterr().out
