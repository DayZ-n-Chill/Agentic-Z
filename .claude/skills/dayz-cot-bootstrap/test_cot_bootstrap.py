"""Tests for bootstrap.py: mod chain, per-player permission edits, PID-scoped stop."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_cot_bootstrap_under_test", HERE / "bootstrap.py")
cot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cot)


# --- dedup_with_cf_cot -----------------------------------------------------------

def test_cf_and_cot_prepended_in_order():
    assert cot.dedup_with_cf_cot(["MyMod"]) == ["CF", "Community-Online-Tools", "MyMod"]


def test_user_supplied_cf_cot_deduplicated():
    assert cot.dedup_with_cf_cot(["Community-Online-Tools", "MyMod", "CF", "MyMod"]) == [
        "CF", "Community-Online-Tools", "MyMod",
    ]


def test_no_user_mods():
    assert cot.dedup_with_cf_cot([]) == ["CF", "Community-Online-Tools"]


# --- grant_admin_role -------------------------------------------------------------

def test_admin_added_and_other_fields_kept(tmp_path):
    f = tmp_path / "abc.json"
    f.write_text(json.dumps({"Name": "me", "Roles": ["everyone"]}), encoding="utf-8")
    assert cot.grant_admin_role(f) is True
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data == {"Name": "me", "Roles": ["everyone", "admin"]}
    assert f.read_text(encoding="utf-8").endswith("\n")


def test_admin_grant_is_idempotent(tmp_path):
    f = tmp_path / "abc.json"
    f.write_text(json.dumps({"Roles": ["admin"]}), encoding="utf-8")
    before = f.read_text(encoding="utf-8")
    assert cot.grant_admin_role(f) is False
    assert f.read_text(encoding="utf-8") == before


def test_missing_or_bad_roles_replaced_with_admin(tmp_path):
    f = tmp_path / "abc.json"
    f.write_text(json.dumps({"Roles": "oops"}), encoding="utf-8")
    assert cot.grant_admin_role(f) is True
    assert json.loads(f.read_text(encoding="utf-8"))["Roles"] == ["admin"]


def test_unparseable_json_reports_failure(tmp_path):
    f = tmp_path / "abc.json"
    f.write_text("{not json", encoding="utf-8")
    assert cot.grant_admin_role(f) is None
    assert f.read_text(encoding="utf-8") == "{not json"


# --- flip_zeros_to_twos -----------------------------------------------------------

def test_flip_counts_and_preserves_layout(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_text("Admin.Teleport 0\nAdmin.Kick 2\nAdmin.Ban 0", encoding="utf-8")
    assert cot.flip_zeros_to_twos(f) == 2
    assert f.read_text(encoding="utf-8") == "Admin.Teleport 2\nAdmin.Kick 2\nAdmin.Ban 2"


def test_flip_keeps_crlf(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_bytes(b"A 0\r\nB 0\r\n")
    assert cot.flip_zeros_to_twos(f) == 2
    assert f.read_bytes() == b"A 2\r\nB 2\r\n"


def test_flip_only_touches_trailing_zero(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_text("Item.Spawn10 1\nThing 0 extra\nX 10\n", encoding="utf-8")
    assert cot.flip_zeros_to_twos(f) == 0
    assert f.read_text(encoding="utf-8") == "Item.Spawn10 1\nThing 0 extra\nX 10\n"


def test_flip_is_idempotent(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_text("A 0\n", encoding="utf-8")
    cot.flip_zeros_to_twos(f)
    assert cot.flip_zeros_to_twos(f) == 0


def test_edit_permissions_never_touches_roles(tmp_path):
    fw = tmp_path / "PermissionsFramework"
    (fw / "Players").mkdir(parents=True)
    (fw / "Permissions").mkdir()
    (fw / "Roles").mkdir()
    player = fw / "Players" / "abc.json"
    player.write_text(json.dumps({"Roles": []}), encoding="utf-8")
    (fw / "Permissions" / "abc.txt").write_text("A 0\n", encoding="utf-8")
    (fw / "Roles" / "everyone.txt").write_text("A 0\n", encoding="utf-8")

    assert cot.edit_permissions(tmp_path, [player]) is True

    assert (fw / "Permissions" / "abc.txt").read_text(encoding="utf-8") == "A 2\n"
    assert (fw / "Roles" / "everyone.txt").read_text(encoding="utf-8") == "A 0\n"


def _framework(tmp_path):
    fw = tmp_path / "PermissionsFramework"
    (fw / "Players").mkdir(parents=True)
    (fw / "Permissions").mkdir()
    return fw


def test_edit_permissions_fails_when_player_json_unreadable(tmp_path):
    fw = _framework(tmp_path)
    player = fw / "Players" / "abc.json"
    player.write_text("{not json", encoding="utf-8")
    (fw / "Permissions" / "abc.txt").write_text("A 0\n", encoding="utf-8")
    assert cot.edit_permissions(tmp_path, [player]) is False


def test_edit_permissions_fails_when_perms_file_missing(monkeypatch, tmp_path):
    fw = _framework(tmp_path)
    player = fw / "Players" / "abc.json"
    player.write_text(json.dumps({"Roles": []}), encoding="utf-8")
    monkeypatch.setattr(cot, "wait_for_personal_perms", lambda f, timeout_s: False)
    assert cot.edit_permissions(tmp_path, [player]) is False


def test_edit_permissions_already_admin_counts_as_success(tmp_path):
    fw = _framework(tmp_path)
    player = fw / "Players" / "abc.json"
    player.write_text(json.dumps({"Roles": ["admin"]}), encoding="utf-8")
    (fw / "Permissions" / "abc.txt").write_text("A 2\n", encoding="utf-8")
    assert cot.edit_permissions(tmp_path, [player]) is True


# --- main: pass 2 only after a successful edit ---------------------------------------

def _patch_main(monkeypatch, tmp_path, triggered, edit_ok=True):
    """Stub everything main() touches; returns the list of launched pass labels."""
    profile = tmp_path / "Profiles"
    monkeypatch.setattr(cot.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(cot.h, "resolve_project_dir", lambda: tmp_path)
    monkeypatch.setattr(cot, "verify_cf_cot_subscribed", lambda: None)
    monkeypatch.setattr(cot, "verify_built_mods", lambda mods: None)
    monkeypatch.setattr(cot, "resolve_diag_client", lambda: Path("C:/DayZ/DayZDiag_x64.exe"))
    monkeypatch.setattr(
        cot, "verify_instance_environment",
        lambda inst, proj: (tmp_path / "serverDZ.cfg", profile, tmp_path / "m", tmp_path / "!ClientDiagLogs"),
    )
    monkeypatch.setattr(cot, "read_client_display_prefs", lambda proj: {})
    launches = []

    def fake_launch_pair(*args):
        launches.append(args[-1])
        return [FakeProc(1), FakeProc(2)]

    monkeypatch.setattr(cot, "launch_pair", fake_launch_pair)
    monkeypatch.setattr(cot, "wait_for_cot_player", lambda d, b, t, s: triggered)
    monkeypatch.setattr(cot, "stop_session", lambda procs: None)
    monkeypatch.setattr(cot.time, "sleep", lambda s: None)
    monkeypatch.setattr(cot, "edit_permissions", lambda p, t: edit_ok)
    monkeypatch.setattr(cot, "wait_for_perms_files", lambda p, t: None)
    monkeypatch.setattr(cot.sys, "argv", ["bootstrap.py", "MyMod"])
    return launches


@pytest.mark.parametrize("edit_ok, expected_rc, expected_launches", [(False, 1, 1), (True, 0, 2)])
def test_main_runs_pass_two_only_after_successful_edit(
    monkeypatch, tmp_path, edit_ok, expected_rc, expected_launches
):
    launches = _patch_main(monkeypatch, tmp_path, [tmp_path / "Profiles" / "abc.json"], edit_ok)
    assert cot.main() == expected_rc
    assert len(launches) == expected_launches


def test_main_failed_wait_points_at_script_logs(monkeypatch, tmp_path, capsys):
    launches = _patch_main(monkeypatch, tmp_path, [])
    assert cot.main() == 1
    assert launches == ["Pass 1"]
    out = capsys.readouterr().out
    assert "script.log" in out and "!ClientDiagLogs" in out


# --- stop_session only touches our own processes --------------------------------

class FakeProc:
    def __init__(self, pid, running=True, hangs=False):
        self.pid, self._running, self._hangs, self.killed = pid, running, hangs, False

    def poll(self):
        return None if self._running else 0

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        if self._hangs:
            raise subprocess.TimeoutExpired("diag", timeout)
        self._running = False
        return 0


def test_stop_session_kills_only_running_handles(monkeypatch):
    monkeypatch.setattr(cot.subprocess, "run", lambda *a, **k: pytest.fail("must not shell out to taskkill"))
    running, exited = FakeProc(1), FakeProc(2, running=False)
    cot.stop_session([running, exited])
    assert running.killed and not exited.killed


def test_stop_session_warns_on_hang(capsys):
    cot.stop_session([FakeProc(7, hangs=True)])
    assert "PID 7 did not exit" in capsys.readouterr().out


# --- player file detection --------------------------------------------------------

def test_snapshot_and_detection_of_new_player(tmp_path):
    players = tmp_path / "Players"
    players.mkdir()
    (players / "old.json").write_text("{}", encoding="utf-8")
    baseline = cot.snapshot_player_files(players)
    (players / "new.json").write_text("{}", encoding="utf-8")
    triggered = cot.wait_for_cot_player(players, baseline, timeout_s=5, session=[FakeProc(1), FakeProc(2)])
    assert [p.name for p in triggered] == ["new.json"]


@pytest.mark.parametrize("dead, label", [(0, "server"), (1, "client")])
def test_wait_ends_early_when_a_process_exits(tmp_path, monkeypatch, capsys, dead, label):
    session = [FakeProc(1), FakeProc(2)]
    session[dead]._running = False
    monkeypatch.setattr(cot.time, "sleep", lambda s: pytest.fail("kept waiting after a process exited"))
    assert cot.wait_for_cot_player(tmp_path / "Players", {}, timeout_s=600, session=session) == []
    assert f"The {label} exited (code 0)" in capsys.readouterr().out


def test_wait_reports_timeout(tmp_path, monkeypatch, capsys):
    now = [0.0]
    monkeypatch.setattr(cot.time, "time", lambda: now[0])
    monkeypatch.setattr(cot.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))
    assert cot.wait_for_cot_player(tmp_path / "Players", {}, timeout_s=10, session=[FakeProc(1), FakeProc(2)]) == []
    assert "Timed out after 10s" in capsys.readouterr().out


def test_server_bind_timeout_comes_from_launch_test():
    assert cot.SERVER_BIND_TIMEOUT_S == cot._launch.SERVER_BIND_TIMEOUT_S


# --- the port is checked before each server spawn ---------------------------------

def test_launch_pair_refuses_taken_port_before_spawning(monkeypatch, tmp_path):
    checked = []
    monkeypatch.setattr(cot.h, "udp_port_free", lambda port: checked.append(port) or False)
    monkeypatch.setattr(cot.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned despite a taken port"))
    with pytest.raises(SystemExit) as exc:
        cot.launch_pair(
            Path("C:/DayZ/DayZDiag_x64.exe"), "P:/Mods/@CF", 2402, tmp_path / "serverDZ.cfg",
            tmp_path / "Profiles", tmp_path / "m", tmp_path / "logs", {}, "Pass 1",
        )
    assert checked == [2402]
    assert "port 2402 in use; run /dayz-stop-test or pass --port" in str(exc.value.code)


def test_launch_pair_spawns_server_after_free_port_check(monkeypatch, tmp_path):
    order = []
    monkeypatch.setattr(cot.h, "udp_port_free", lambda port: order.append("check") or True)
    monkeypatch.setattr(cot.subprocess, "Popen", lambda cmd, cwd=None: order.append("spawn") or FakeProc(len(order)))
    monkeypatch.setattr(cot, "wait_for_server_port", lambda port, proc, timeout_s: True)
    procs = cot.launch_pair(
        Path("C:/DayZ/DayZDiag_x64.exe"), "P:/Mods/@CF", 2302, tmp_path / "serverDZ.cfg",
        tmp_path / "Profiles", tmp_path / "m", tmp_path / "logs", {}, "Pass 1",
    )
    assert order == ["check", "spawn", "spawn"] and len(procs) == 2


def test_perms_file_written_after_the_json_is_waited_for_before_stop(monkeypatch, tmp_path):
    """COT writes Permissions/<id>.txt a little after the JSON; the wait must run while the server is up."""
    profile = tmp_path / "Profiles"
    fw = profile / "PermissionsFramework"
    (fw / "Players").mkdir(parents=True)
    (fw / "Permissions").mkdir()
    player = fw / "Players" / "abc.json"
    player.write_text(json.dumps({"Roles": []}), encoding="utf-8")
    perms = fw / "Permissions" / "abc.txt"
    real_edit, real_wait = cot.edit_permissions, cot.wait_for_perms_files
    launches = _patch_main(monkeypatch, tmp_path, [player])
    monkeypatch.setattr(cot, "edit_permissions", real_edit)
    monkeypatch.setattr(cot, "wait_for_perms_files", real_wait)
    events = []
    server_up = {"running": True}

    def fake_sleep(s):
        # The running server writes the perms file on the second poll.
        if server_up["running"] and len(events) >= 1 and not perms.exists():
            perms.write_text("A 0\n", encoding="utf-8")
        events.append("sleep")

    def fake_stop(procs):
        events.append("stop")
        server_up["running"] = False

    monkeypatch.setattr(cot.time, "sleep", fake_sleep)
    monkeypatch.setattr(cot, "stop_session", fake_stop)
    assert cot.main() == 0
    assert launches == ["Pass 1", "Pass 2"]
    assert "stop" in events and events.index("stop") > 0  # waited before the stop
    assert perms.read_text(encoding="utf-8") == "A 2\n"
    assert "admin" in json.loads(player.read_text(encoding="utf-8"))["Roles"]

