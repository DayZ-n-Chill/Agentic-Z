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

@pytest.mark.parametrize("edit_ok, expected_rc, expected_launches", [(False, 1, 1), (True, 0, 2)])
def test_main_runs_pass_two_only_after_successful_edit(
    monkeypatch, tmp_path, edit_ok, expected_rc, expected_launches
):
    profile = tmp_path / "Profiles"
    monkeypatch.setattr(cot.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(cot.h, "resolve_project_dir", lambda: tmp_path)
    monkeypatch.setattr(cot, "verify_cf_cot_subscribed", lambda: None)
    monkeypatch.setattr(cot, "verify_built_mods", lambda mods: None)
    monkeypatch.setattr(cot, "resolve_diag_client", lambda: Path("C:/DayZ/DayZDiag_x64.exe"))
    monkeypatch.setattr(
        cot, "verify_instance_environment",
        lambda inst, proj: (tmp_path / "serverDZ.cfg", profile, tmp_path / "m", tmp_path / "logs"),
    )
    monkeypatch.setattr(cot, "read_client_display_prefs", lambda proj: {})
    launches = []

    def fake_launch_pair(*args):
        launches.append(args[-1])
        return [FakeProc(1), FakeProc(2)]

    monkeypatch.setattr(cot, "launch_pair", fake_launch_pair)
    monkeypatch.setattr(cot, "wait_for_cot_player", lambda d, b, t: [profile / "abc.json"])
    monkeypatch.setattr(cot, "stop_session", lambda procs: None)
    monkeypatch.setattr(cot.time, "sleep", lambda s: None)
    monkeypatch.setattr(cot, "edit_permissions", lambda p, t: edit_ok)
    monkeypatch.setattr(cot.sys, "argv", ["bootstrap.py", "MyMod"])

    assert cot.main() == expected_rc
    assert len(launches) == expected_launches


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
    triggered = cot.wait_for_cot_player(players, baseline, timeout_s=5)
    assert [p.name for p in triggered] == ["new.json"]
