"""Tests for bootstrap.py: mod chain, per-player permission edits, PID-scoped stop."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
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


def test_dedup_is_case_insensitive():
    """Windows folder names ignore case, so `cf` must not load @CF twice."""
    assert cot.dedup_with_cf_cot(["cf", "community-online-tools", "MyMod", "mymod"]) == [
        "CF", "Community-Online-Tools", "MyMod",
    ]


# --- mod name and numeric argument parsing ----------------------------------------

@pytest.mark.parametrize("raw, expected", [("MyMod", "MyMod"), ("@MyMod", "MyMod"), (" @Dabs Framework ", "Dabs Framework")])
def test_mod_name_strips_leading_at(raw, expected):
    assert cot.mod_name(raw) == expected


@pytest.mark.parametrize("raw", ["", "@", "..", "a;b", "a\\b", "a/b", "P:\\Mods\\@x", "x*"])
def test_mod_name_rejects_paths_and_separators(raw):
    with pytest.raises(cot.argparse.ArgumentTypeError):
        cot.mod_name(raw)


def test_main_accepts_at_prefixed_and_lowercase_names(monkeypatch, tmp_path):
    """`@MyMod` used to look for P:\\Mods\\@@MyMod; `cf` used to load @CF twice."""
    checked = []
    _patch_main(monkeypatch, tmp_path, [tmp_path / "Profiles" / "abc.json"], argv=("@MyMod", "cf"))
    monkeypatch.setattr(cot, "verify_built_mods", lambda mods: checked.extend(mods))
    assert cot.main() == 0
    assert checked == ["CF", "Community-Online-Tools", "MyMod"]


@pytest.mark.parametrize("argv", [("a;b",), ("--port", "0"), ("--port", "70000"), ("--timeout", "0")])
def test_main_rejects_bad_arguments_before_preflight(monkeypatch, tmp_path, argv):
    _patch_main(monkeypatch, tmp_path, [], argv=argv)
    monkeypatch.setattr(cot.h, "gate_on_preflight", lambda: pytest.fail("preflight ran"))
    with pytest.raises(SystemExit) as exc:
        cot.main()
    assert exc.value.code == 2


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


@pytest.mark.parametrize("payload", ["[1]", '"admin"', "null", "42"])
def test_non_object_json_reports_failure(tmp_path, capsys, payload):
    f = tmp_path / "abc.json"
    f.write_text(payload, encoding="utf-8")
    assert cot.grant_admin_role(f) is None
    assert "Could not parse abc.json" in capsys.readouterr().out
    assert f.read_text(encoding="utf-8") == payload
    assert not (tmp_path / "abc.json.bak").exists()


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


def test_flip_keeps_lf(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_bytes(b"A 0\nB 0\n")
    assert cot.flip_zeros_to_twos(f) == 2
    assert f.read_bytes() == b"A 2\nB 2\n"


def test_flip_keeps_mixed_line_endings(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_bytes(b"A 0\r\nB 0\nC 0")
    assert cot.flip_zeros_to_twos(f) == 3
    assert f.read_bytes() == b"A 2\r\nB 2\nC 2"


def test_flip_handles_trailing_whitespace(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_bytes(b"Admin.X 0 \nAdmin.Y 0\t\r\nAdmin.Z 0  ")
    assert cot.flip_zeros_to_twos(f) == 3
    assert f.read_bytes() == b"Admin.X 2 \nAdmin.Y 2\t\r\nAdmin.Z 2  "


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


def test_edit_permissions_leaves_perms_untouched_when_json_unparseable(tmp_path):
    fw = _framework(tmp_path)
    player = fw / "Players" / "abc.json"
    player.write_text("{not json", encoding="utf-8")
    perms = fw / "Permissions" / "abc.txt"
    perms.write_text("A 0\n", encoding="utf-8")
    assert cot.edit_permissions(tmp_path, [player]) is False
    assert perms.read_text(encoding="utf-8") == "A 0\n"
    assert not (fw / "Permissions" / "abc.txt.bak").exists()


def test_edit_permissions_skips_only_the_failed_player(tmp_path):
    fw = _framework(tmp_path)
    bad, good = fw / "Players" / "bad.json", fw / "Players" / "good.json"
    bad.write_text("{not json", encoding="utf-8")
    good.write_text(json.dumps({"Roles": []}), encoding="utf-8")
    (fw / "Permissions" / "bad.txt").write_text("A 0\n", encoding="utf-8")
    (fw / "Permissions" / "good.txt").write_text("A 0\n", encoding="utf-8")
    assert cot.edit_permissions(tmp_path, [bad, good]) is False
    assert (fw / "Permissions" / "bad.txt").read_text(encoding="utf-8") == "A 0\n"
    assert (fw / "Permissions" / "good.txt").read_text(encoding="utf-8") == "A 2\n"


def test_grant_admin_reads_json_with_byte_order_mark(tmp_path):
    player = tmp_path / "abc.json"
    player.write_bytes(b"\xef\xbb\xbf" + json.dumps({"Roles": []}).encode("utf-8"))
    assert cot.grant_admin_role(player) is True
    assert json.loads(player.read_text(encoding="utf-8-sig"))["Roles"] == ["admin"]


def test_admin_players_reads_json_with_byte_order_mark(tmp_path):
    (tmp_path / "abc.json").write_bytes(b"\xef\xbb\xbf" + json.dumps({"Roles": ["admin"]}).encode("utf-8"))
    assert cot.admin_players(tmp_path) == ["abc"]


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

def _patch_main(monkeypatch, tmp_path, triggered, edit_ok=True, argv=("MyMod",), port_released=True):
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
    monkeypatch.setattr(cot, "wait_for_port_release", lambda port: port_released)
    monkeypatch.setattr(cot.sys, "argv", ["bootstrap.py", *argv])
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
    monkeypatch.setattr(cot.h, "gate_on_steam", lambda: order.append("steam"))
    flags = []

    def fake_popen(cmd, cwd=None, creationflags=0):
        flags.append(creationflags)
        order.append("spawn")
        return FakeProc(len(order))

    monkeypatch.setattr(cot.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(cot, "wait_for_server_port", lambda port, proc, timeout_s: True)
    procs = cot.launch_pair(
        Path("C:/DayZ/DayZDiag_x64.exe"), "P:/Mods/@CF", 2302, tmp_path / "serverDZ.cfg",
        tmp_path / "Profiles", tmp_path / "m", tmp_path / "logs", {}, "Pass 1",
    )
    assert order == ["check", "steam", "spawn", "spawn"] and len(procs) == 2
    # Detached like /dayz-launch-test, so closing the shell leaves pass 2 running.
    assert flags == [cot.h.DETACH_FLAGS, cot.h.DETACH_FLAGS]


def _launch_pair_with(monkeypatch, tmp_path, popen, wait_for_port):
    monkeypatch.setattr(cot.h, "udp_port_free", lambda port: True)
    monkeypatch.setattr(cot.h, "gate_on_steam", lambda: None)
    monkeypatch.setattr(cot.subprocess, "Popen", popen)
    monkeypatch.setattr(cot, "wait_for_server_port", wait_for_port)
    return lambda: cot.launch_pair(
        Path("C:/DayZ/DayZDiag_x64.exe"), "P:/Mods/@CF", 2302, tmp_path / "serverDZ.cfg",
        tmp_path / "Profiles", tmp_path / "m", tmp_path / "logs", {}, "Pass 1",
    )


def test_launch_pair_stops_server_on_ctrl_c_during_bind_wait(monkeypatch, tmp_path):
    server = FakeProc(1)

    def interrupted(port, proc, timeout_s):
        raise KeyboardInterrupt

    run = _launch_pair_with(monkeypatch, tmp_path, lambda *a, **k: server, interrupted)
    with pytest.raises(KeyboardInterrupt):
        run()
    assert server.killed


def test_launch_pair_stops_server_when_client_fails_to_spawn(monkeypatch, tmp_path):
    server = FakeProc(1)
    spawned = []

    def popen(*a, **k):
        if spawned:
            raise OSError("client exe missing")
        spawned.append(server)
        return server

    run = _launch_pair_with(monkeypatch, tmp_path, popen, lambda port, proc, timeout_s: True)
    with pytest.raises(SystemExit) as exc:
        run()
    assert server.killed
    assert "Failed to spawn" in str(exc.value.code)


def test_main_ctrl_c_during_pass1_wait_stops_both_processes(monkeypatch, tmp_path, capsys):
    procs = [FakeProc(1), FakeProc(2)]
    real_stop = cot.stop_session
    _patch_main(monkeypatch, tmp_path, [])
    monkeypatch.setattr(cot, "launch_pair", lambda *a: procs)
    monkeypatch.setattr(cot, "stop_session", real_stop)

    def interrupted(*a):
        raise KeyboardInterrupt

    monkeypatch.setattr(cot, "wait_for_cot_player", interrupted)
    monkeypatch.setattr(cot, "edit_permissions", lambda *a: pytest.fail("edited after Ctrl+C"))
    assert cot.main() == 130
    assert all(p.killed for p in procs)
    assert "Interrupted" in capsys.readouterr().out


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



# --- backups before in-place edits -----------------------------------------------

def test_grant_admin_writes_backup_of_original(tmp_path):
    f = tmp_path / "abc.json"
    original = json.dumps({"Roles": ["everyone"]})
    f.write_text(original, encoding="utf-8")
    assert cot.grant_admin_role(f) is True
    assert (tmp_path / "abc.json.bak").read_text(encoding="utf-8") == original


def test_flip_writes_backup_of_original(tmp_path):
    f = tmp_path / "abc.txt"
    f.write_bytes(b"A 0\r\nB 2\r\n")
    assert cot.flip_zeros_to_twos(f) == 1
    assert (tmp_path / "abc.txt.bak").read_bytes() == b"A 0\r\nB 2\r\n"


def test_unchanged_files_get_no_backup(tmp_path):
    j, t = tmp_path / "abc.json", tmp_path / "abc.txt"
    j.write_text(json.dumps({"Roles": ["admin"]}), encoding="utf-8")
    t.write_text("A 2\n", encoding="utf-8")
    cot.grant_admin_role(j)
    cot.flip_zeros_to_twos(t)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["abc.json", "abc.txt"]


def test_backup_is_not_picked_up_as_a_player_file(tmp_path):
    players = tmp_path / "Players"
    players.mkdir()
    f = players / "abc.json"
    f.write_text(json.dumps({"Roles": []}), encoding="utf-8")
    cot.grant_admin_role(f)
    assert set(cot.snapshot_player_files(players)) == {"abc"}


# --- port release between pass 1 and pass 2 --------------------------------------

def test_wait_for_port_release_polls_until_free(monkeypatch):
    answers = iter([False, False, True])
    monkeypatch.setattr(cot.h, "udp_port_free", lambda port: next(answers))
    sleeps = []
    monkeypatch.setattr(cot.time, "sleep", sleeps.append)
    assert cot.wait_for_port_release(2302, timeout_s=30) is True
    assert len(sleeps) == 2


def test_wait_for_port_release_gives_up_at_deadline(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(cot.time, "time", lambda: now[0])
    monkeypatch.setattr(cot.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))
    monkeypatch.setattr(cot.h, "udp_port_free", lambda port: False)
    assert cot.wait_for_port_release(2302, timeout_s=30) is False
    assert now[0] == 30


def test_main_waits_for_port_before_pass_two(monkeypatch, tmp_path, capsys):
    launches = _patch_main(monkeypatch, tmp_path, [tmp_path / "Profiles" / "abc.json"], port_released=False)
    assert cot.main() == 1
    assert launches == ["Pass 1"]
    assert "--skip-pass1" in capsys.readouterr().out


# --- --skip-pass1 goes straight to the relaunch ----------------------------------

def test_skip_pass1_relaunches_without_pass_one_or_edit(monkeypatch, tmp_path):
    players = tmp_path / "Profiles" / "PermissionsFramework" / "Players"
    players.mkdir(parents=True)
    (players / "abc.json").write_text(json.dumps({"Roles": ["admin"]}), encoding="utf-8")
    launches = _patch_main(monkeypatch, tmp_path, [], argv=("MyMod", "--skip-pass1"))
    monkeypatch.setattr(cot, "wait_for_cot_player", lambda *a: pytest.fail("pass 1 wait ran"))
    monkeypatch.setattr(cot, "edit_permissions", lambda *a: pytest.fail("edit ran"))
    assert cot.main() == 0
    assert launches == ["Pass 2"]


def test_skip_pass1_refuses_when_no_player_is_admin(monkeypatch, tmp_path, capsys):
    players = tmp_path / "Profiles" / "PermissionsFramework" / "Players"
    players.mkdir(parents=True)
    (players / "abc.json").write_text(json.dumps({"Roles": []}), encoding="utf-8")
    launches = _patch_main(monkeypatch, tmp_path, [], argv=("--skip-pass1",))
    assert cot.main() == 1
    assert launches == []
    assert "no Players JSON" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [("MyMod",), ("MyMod", "--skip-pass1")])
def test_pass_two_gate_failure_prints_skip_pass1_hint(monkeypatch, tmp_path, capsys, argv):
    players = tmp_path / "Profiles" / "PermissionsFramework" / "Players"
    players.mkdir(parents=True)
    (players / "abc.json").write_text(json.dumps({"Roles": ["admin"]}), encoding="utf-8")
    launches = _patch_main(monkeypatch, tmp_path, [players / "abc.json"], argv=argv)

    def launch_pair(*args):
        launches.append(args[-1])
        if args[-1] == "Pass 2":
            sys.exit("[FAIL] Steam is not running.")
        return [FakeProc(1), FakeProc(2)]

    monkeypatch.setattr(cot, "launch_pair", launch_pair)
    assert cot.main() == 1
    assert launches[-1] == "Pass 2"
    out = capsys.readouterr().out
    assert "Steam is not running" in out and "--skip-pass1" in out
