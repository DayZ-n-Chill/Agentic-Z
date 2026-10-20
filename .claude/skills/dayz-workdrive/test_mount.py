"""Tests for dayz-workdrive/mount.py: settings.ini parsing, resolution order, mount fallback."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "dayz_workdrive_mount", Path(__file__).resolve().parent / "mount.py"
)
mount = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mount)


# ---------- read_settings_ini_path ----------

def _write_ini(tools: Path, text: str) -> None:
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "settings.ini").write_text(text, encoding="utf-8")


def test_settings_ini_reads_projectdrive_path(tmp_path):
    _write_ini(tmp_path, "[Other]\npath=C:\\wrong\n[ProjectDrive]\npath=C:\\Work\\Drive\n")
    assert mount.read_settings_ini_path(tmp_path) == Path("C:\\Work\\Drive")


def test_settings_ini_is_case_insensitive_and_strips_quotes(tmp_path):
    _write_ini(tmp_path, '[projectdrive]\n  PATH = "D:\\P Drive"  \n')
    assert mount.read_settings_ini_path(tmp_path) == Path("D:\\P Drive")


def test_settings_ini_ignores_path_in_other_sections(tmp_path):
    _write_ini(tmp_path, "[Other]\npath=C:\\wrong\n")
    assert mount.read_settings_ini_path(tmp_path) is None


def test_settings_ini_empty_value_is_none(tmp_path):
    _write_ini(tmp_path, "[ProjectDrive]\npath=\n")
    assert mount.read_settings_ini_path(tmp_path) is None


def test_settings_ini_missing_file_is_none(tmp_path):
    assert mount.read_settings_ini_path(tmp_path) is None


# ---------- find_work_drive resolution order ----------

@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point every source at nothing; each test turns on the sources it needs."""
    monkeypatch.delenv("DAYZ_WORK_DRIVE", raising=False)
    monkeypatch.setattr(mount, "CACHE", tmp_path / "cache" / "dayz-work-drive.json")
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(mount, "read_registry_string", lambda *a: None)
    return tmp_path


def _dir(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir(parents=True)
    return d


def _tools_with_ini_and_default(root: Path, ini_target: Path | None) -> Path:
    tools = _dir(root, "tools")
    _dir(tools, "Bin/WorkDrive")
    if ini_target is not None:
        _write_ini(tools, f"[ProjectDrive]\npath={ini_target}\n")
    return tools


def test_nothing_resolves_to_none(isolated):
    assert mount.find_work_drive() is None


def test_env_var_wins_over_everything(isolated, monkeypatch):
    env = _dir(isolated, "env")
    cached = _dir(isolated, "cached")
    mount.set_cached_path(cached)
    tools = _tools_with_ini_and_default(isolated, _dir(isolated, "ini"))
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(env))
    assert mount.find_work_drive() == env


def test_cache_beats_settings_ini(isolated, monkeypatch):
    cached = _dir(isolated, "cached")
    mount.set_cached_path(cached)
    tools = _tools_with_ini_and_default(isolated, _dir(isolated, "ini"))
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == cached


def test_settings_ini_beats_registry_and_default(isolated, monkeypatch):
    ini = _dir(isolated, "ini")
    reg = _dir(isolated, "reg")
    tools = _tools_with_ini_and_default(isolated, ini)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setattr(mount, "read_registry_string", lambda *a: str(reg))
    assert mount.find_work_drive() == ini


@pytest.mark.skipif(mount.sys.platform != "win32", reason="registry lookup is Windows-only")
def test_registry_beats_tools_default(isolated, monkeypatch):
    reg = _dir(isolated, "reg")
    tools = _tools_with_ini_and_default(isolated, None)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setattr(mount, "read_registry_string", lambda *a: str(reg))
    assert mount.find_work_drive() == reg


def test_tools_default_is_last_resort(isolated, monkeypatch):
    tools = _tools_with_ini_and_default(isolated, None)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == tools / "Bin" / "WorkDrive"


def test_candidates_that_do_not_exist_are_skipped(isolated, monkeypatch):
    real = _dir(isolated, "real")
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(isolated / "missing"))
    mount.CACHE.parent.mkdir(parents=True)
    mount.CACHE.write_text(json.dumps({"work_drive_path": str(isolated / "gone")}), encoding="utf-8")
    tools = _tools_with_ini_and_default(isolated, real)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == real


# ---------- invoke_mount subst fallback ----------

def test_subst_failure_reports_exit_code(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(mount, "find_workdrive_exe", lambda: None)
    monkeypatch.setattr(mount, "is_p_mounted", lambda: False)
    monkeypatch.setattr(mount.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=5))
    assert mount.invoke_mount(tmp_path) is False
    assert "exited with code 5" in capsys.readouterr().err


def test_subst_success_returns_true(monkeypatch, tmp_path):
    state = {"mounted": False}

    def fake_run(*a, **k):
        state["mounted"] = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(mount, "find_workdrive_exe", lambda: None)
    monkeypatch.setattr(mount, "is_p_mounted", lambda: state["mounted"])
    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    assert mount.invoke_mount(tmp_path) is True
