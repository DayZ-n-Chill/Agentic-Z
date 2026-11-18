"""Tests for dayz_test.py: commands per mode, the record of what it started, the build guard. No DayZ."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_test_under_test", HERE / "dayz_test.py")
dt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dt)

DIAG = Path("C:/DayZ/DayZDiag_x64.exe")


@pytest.fixture
def env(tmp_path, monkeypatch):
    inst = tmp_path / ".server" / "chernarus"
    mission = inst / "dayzOffline.chernarusplus"

    def verify(instance, project, dry_run=False):
        return inst / "serverDZ.cfg", inst / "Profiles", mission, tmp_path / ".server" / "!ClientDiagLogs"

    monkeypatch.setattr(dt.launch, "verify_instance_environment", verify)
    monkeypatch.setattr(dt.launch, "read_client_display_prefs", lambda project, create=True: {"windowed": True, "width": 1280, "height": 720})
    monkeypatch.setattr(dt.launch, "MODS_ROOT", Path("P:/Mods"))
    monkeypatch.setattr(dt.h, "gate_on_steam", lambda: None)
    monkeypatch.setattr(dt.h, "gate_on_free_port", lambda port: None)
    return tmp_path


def args(**kw):
    base = dict(mod="MyMod", mode="all", deps=["CF"], server_only=[], server="chernarus", port=2302, build=False,
                dry_run=False, kill=False)
    return SimpleNamespace(**{**base, **kw})


def test_server_command_is_the_one_dayz_launch_test_builds(env):
    cmd = dt.server_cmd(DIAG, env, args(server_only=["Srv"]))
    assert cmd[1] == "-server" and f"-mod={Path('P:/Mods/@CF')};{Path('P:/Mods/@MyMod')}" in cmd
    assert f"-serverMod={Path('P:/Mods/@Srv')}" in cmd and "-filePatching" in cmd and "-port=2302" in cmd


def test_offline_has_a_mission_and_no_server_to_join(env):
    cmd = dt.offline_cmd(DIAG, env, args())
    assert not any(p.startswith(("-connect=", "-port=")) for p in cmd)
    assert cmd[-1].startswith("-mission=") and cmd[-1].endswith("dayzOffline.chernarusplus")
    assert "-filePatching" in cmd and "-window" in cmd and not any(p == "-server" for p in cmd)


def test_client_refuses_without_a_server_this_tool_started(env, monkeypatch):
    monkeypatch.setattr(dt, "diag_pids", lambda: [999])  # someone else's DayZDiag
    with pytest.raises(dt.Refused, match="no server started by this tool"):
        dt.run_one("client", args(), env, DIAG, {"pids": {}}, start=lambda cmd: pytest.fail("started"))


def test_client_joins_the_recorded_server(env, monkeypatch, capsys):
    monkeypatch.setattr(dt, "diag_pids", lambda: [111])
    started = []
    out = dt.run_one("client", args(), env, DIAG, {"pids": {"server": 111}}, start=lambda cmd: started.append(cmd) or 222)
    assert out == {"client": 222} and "-connect=127.0.0.1" in started[0]


def test_dry_run_prints_and_starts_nothing(env, capsys):
    assert dt.run_one("offline", args(dry_run=True), env, DIAG, {"pids": {}}, start=lambda c: pytest.fail("started")) == {}
    assert "[DRY-RUN] Offline cmd:" in capsys.readouterr().out


def test_kill_ends_only_what_this_tool_recorded(tmp_path):
    dt.save_record(tmp_path, {"pids": {"server": 111, "client": 222}})
    killed = []
    out = dt.kill_own(tmp_path, running=lambda: [111, 555], kill=killed.append)
    assert out == [111] and killed == [111] and not dt.record_path(tmp_path).exists()


def test_build_refuses_while_the_deployed_pbo_is_held_open(env, monkeypatch):
    monkeypatch.setattr(dt, "pbo_held_open", lambda pbo: True)
    with pytest.raises(dt.Refused, match="held open"):
        dt.build(args(), run=lambda cmd: pytest.fail("built"))


def test_a_failed_build_launches_nothing(env, monkeypatch):
    monkeypatch.setattr(dt, "pbo_held_open", lambda pbo: False)
    ran = []
    with pytest.raises(dt.Refused, match="exited 1"):
        dt.build(args(), run=lambda cmd: ran.append(cmd) or 1)
    assert ran[0][-1] == "MyMod" and ran[0][-2].endswith("build.py")


def test_a_free_pbo_is_not_held_open_and_stays_in_place(tmp_path):
    pbo = tmp_path / "MyMod.pbo"
    assert dt.pbo_held_open(pbo) is False  # no file yet
    pbo.write_bytes(b"pbo")
    assert dt.pbo_held_open(pbo) is False and pbo.read_bytes() == b"pbo"
    assert not list(tmp_path.glob("*.dayz-test-probe"))


def test_all_mode_runs_dayz_launch_test_and_reads_its_pids(env, monkeypatch, capsys):
    seen = []

    def fake_run(cmd, **kw):
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "[OK]    Server PID: 111\n[OK]    Client PID: 222\n  Server PID: 111    Client PID: 222\n", "")

    monkeypatch.setattr(dt.subprocess, "run", fake_run)
    pids = dt.run_all(args(server_only=["Srv"]), env)
    assert pids == {"server": 111, "client": 222}
    assert seen[0][2:] == ["CF", "MyMod", "--server", "chernarus", "--port", "2302", "--server-only", "Srv"]


@pytest.mark.parametrize("name, mode, builds", [("server.bat", "all", True), ("client.bat", "client", False),
                                                 ("offline.bat", "offline", True)])
def test_launch_templates_call_this_tool(name, mode, builds):
    text = (HERE / name).read_text(encoding="utf-8")
    assert f'"%~dp0dayz_test.py" %* --mode {mode}' in text and ("--build" in text) == builds
    assert "mcp" not in text.lower() and "lease" not in text.lower()


def test_no_outside_tool_is_named():
    for path in HERE.iterdir():
        if path.suffix in (".py", ".bat", ".md") and path.name != Path(__file__).name:
            text = path.read_text(encoding="utf-8").lower()
            assert "dayz-mcp" not in text and "dayz_mcp" not in text, path.name
