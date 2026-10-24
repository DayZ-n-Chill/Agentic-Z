"""Tests for dayz-statusline: the status line script and its installer."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------- statusline.py

@pytest.fixture
def sl(tmp_path, monkeypatch):
    mod = _load("dayz_statusline", "statusline.py")
    monkeypatch.setattr(mod, "CACHE_FILE", tmp_path / "cache.json")
    monkeypatch.setattr(mod, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(mod, "p_mounted", lambda: True)
    monkeypatch.setattr(mod, "diag_running", lambda: False)
    return mod


def _project(tmp_path: Path, mod_name: str | None) -> Path:
    project = tmp_path / "proj"
    mem = project / ".claude" / "local-memory"
    mem.mkdir(parents=True)
    (mem / "dayz-current-project.txt").write_text(str(project), encoding="utf-8")
    if mod_name:
        (mem / "dayz-init-state.json").write_text(json.dumps({"last_intent": {"mod_name": mod_name}}), encoding="utf-8")
    return project


def test_full_line(sl, tmp_path, monkeypatch, capsys):
    project = _project(tmp_path, "MyVest")
    (tmp_path / "manifest.json").write_text(json.dumps({"indexed_at": time.time() - 3 * 86400}), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", _stdin({"workspace": {"project_dir": str(project)}}))
    assert sl.main() == 0
    assert capsys.readouterr().out.strip() == "P: mounted | mod MyVest | Diag off | RAG 3d old"


def test_no_project_and_no_index(sl, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", _stdin({"cwd": str(tmp_path)}))
    sl.main()
    assert capsys.readouterr().out.strip() == "P: mounted | no project (/dayz-init) | Diag off | RAG not indexed"


def test_project_without_active_mod(sl, tmp_path, monkeypatch, capsys):
    project = _project(tmp_path, None)
    monkeypatch.setattr(sys, "stdin", _stdin({"workspace": {"project_dir": str(project)}}))
    sl.main()
    assert "| no active mod |" in capsys.readouterr().out


def test_cache_is_reused_within_ttl(sl, monkeypatch):
    calls = []
    monkeypatch.setattr(sl, "p_mounted", lambda: calls.append(1) or True)
    now = 1000.0
    sl.machine_state(now)
    sl.machine_state(now + 1)
    assert len(calls) == 1
    sl.machine_state(now + sl.CACHE_TTL + 1)
    assert len(calls) == 2


def test_failed_check_shows_unknown(sl, monkeypatch):
    def boom():
        raise OSError("drive not ready")

    monkeypatch.setattr(sl, "p_mounted", boom)
    line = sl.render(sl.machine_state(5.0), None, False, 5.0)
    assert line.startswith("P: ? |")


def test_corrupt_cache_is_ignored(sl):
    sl.CACHE_FILE.write_text("{not json", encoding="utf-8")
    assert sl.machine_state(10.0)["p"] is True


@pytest.mark.parametrize("seconds, text", [(30, "0m"), (125, "2m"), (7200, "2h"), (3 * 86400 + 5, "3d")])
def test_age(sl, seconds, text):
    assert sl.age(seconds) == text


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", '{"workspace": null}'])
def test_script_always_prints_one_line(stdin):
    r = subprocess.run(
        [sys.executable, str(HERE / "statusline.py")], input=stdin, capture_output=True, text=True, timeout=30
    )
    assert r.returncode == 0
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1 and lines[0]


def test_real_process_check_returns_a_bool():
    mod = _load("dayz_statusline_real", "statusline.py")
    assert mod.diag_running() in (True, False)


def _stdin(data: dict):
    return io.StringIO(json.dumps(data))


# ---------------------------------------------------------------- install.py

@pytest.fixture
def inst(tmp_path, monkeypatch):
    mod = _load("dayz_statusline_install", "install.py")
    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(mod, "SETTINGS_LOCAL", tmp_path / ".claude" / "settings.local.json")
    monkeypatch.setattr(mod, "RECORD", tmp_path / ".claude" / "local-memory" / "dayz-statusline.json")
    return mod


def _settings(inst) -> dict:
    return json.loads(inst.SETTINGS_LOCAL.read_text(encoding="utf-8"))


def test_install_into_missing_file_then_remove(inst):
    assert inst.main([]) == 0
    assert _settings(inst)["statusLine"] == inst.our_entry()
    assert inst.main(["--remove"]) == 0
    assert "statusLine" not in _settings(inst)
    assert not inst.RECORD.exists()


def test_install_keeps_other_settings_and_backs_up(inst):
    inst.SETTINGS_LOCAL.parent.mkdir(parents=True)
    inst.SETTINGS_LOCAL.write_text(json.dumps({"permissions": {"deny": ["Edit(/x/**)"]}}), encoding="utf-8")
    inst.main([])
    data = _settings(inst)
    assert data["permissions"] == {"deny": ["Edit(/x/**)"]}
    backup = inst.SETTINGS_LOCAL.with_name("settings.local.json.bak")
    assert json.loads(backup.read_text(encoding="utf-8")) == {"permissions": {"deny": ["Edit(/x/**)"]}}


def test_install_is_idempotent(inst, capsys):
    inst.main([])
    first = inst.SETTINGS_LOCAL.read_text(encoding="utf-8")
    inst.main([])
    assert inst.SETTINGS_LOCAL.read_text(encoding="utf-8") == first
    assert "already installed" in capsys.readouterr().out


def test_remove_restores_users_previous_status_line(inst):
    mine = {"type": "command", "command": "~/.claude/my-line.sh"}
    inst.SETTINGS_LOCAL.parent.mkdir(parents=True)
    inst.SETTINGS_LOCAL.write_text(json.dumps({"statusLine": mine}), encoding="utf-8")
    inst.main([])
    inst.main([])  # a second install must not overwrite the recorded original
    assert _settings(inst)["statusLine"] == inst.our_entry()
    inst.main(["--remove"])
    assert _settings(inst)["statusLine"] == mine


def test_reinstall_updates_old_plugin_path(inst):
    old = {"type": "command", "command": 'python "C:/old/plugin/.claude/skills/dayz-statusline/statusline.py"'}
    inst.SETTINGS_LOCAL.parent.mkdir(parents=True)
    inst.SETTINGS_LOCAL.write_text(json.dumps({"statusLine": old}), encoding="utf-8")
    inst.main([])
    assert _settings(inst)["statusLine"] == inst.our_entry()
    inst.main(["--remove"])
    assert "statusLine" not in _settings(inst)


def test_remove_leaves_foreign_status_line_alone(inst):
    mine = {"type": "command", "command": "~/.claude/my-line.sh"}
    inst.SETTINGS_LOCAL.parent.mkdir(parents=True)
    inst.SETTINGS_LOCAL.write_text(json.dumps({"statusLine": mine}), encoding="utf-8")
    assert inst.main(["--remove"]) == 0
    assert _settings(inst)["statusLine"] == mine


def test_invalid_settings_refuses_without_changes(inst):
    inst.SETTINGS_LOCAL.parent.mkdir(parents=True)
    inst.SETTINGS_LOCAL.write_text("{broken", encoding="utf-8")
    assert inst.main([]) == 1
    assert inst.SETTINGS_LOCAL.read_text(encoding="utf-8") == "{broken"


def test_command_points_at_this_script(inst):
    cmd = inst.our_entry()["command"]
    assert cmd.startswith(f'"{Path(sys.executable).as_posix()}" "') and cmd.endswith('dayz-statusline/statusline.py"')


def test_installed_command_runs_without_python_on_path(inst, tmp_path):
    # A bare `python "..."` fails here, as it does where `python` is only the
    # Microsoft Store alias: the status line would stay blank with no error.
    env = {k: v for k, v in os.environ.items() if k.upper() not in ("PATH", "PATHEXT")}
    empty = tmp_path / "empty-path"
    empty.mkdir()
    env["PATH"] = str(empty)
    r = subprocess.run(
        inst.our_entry()["command"], shell=True, input="{}", capture_output=True, text=True, env=env, timeout=30
    )
    assert r.returncode == 0, r.stderr
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1 and lines[0] and lines[0] != "DayZ status unavailable"
