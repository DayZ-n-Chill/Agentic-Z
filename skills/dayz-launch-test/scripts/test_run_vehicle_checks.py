#!/usr/bin/env python3
"""Offline fixtures for run_vehicle_checks.run_checks (no daemon, no game).

A FakeDaemon feeds synthetic verb payloads through the step logic and asserts the verdict. These
fixtures prove the false-pass guards of the checks without burning an in-game cycle:
  - R3 false-PASS when only the passenger seat is available
  - R4 false-PASS when seated but not owner / not fixture-ready
  - re-run measures the old car when the player is already seated
  - R5 false-PASS by gravity/inertia with the engine off
  - R5 ambiguous obstacle/drivetrain -> needs_clear_ground_retest, not a one-shot fix
  - a verb timeout in R5 -> inconclusive, not a model fix
  - world_spawn without `found` -> R1 fails closed
  - a car the server reads with no wheels or fuel -> R4_conditioned stops the checks before R5
  - the identity and lease token travel in every /enqueue, and a fence rejection is reported at once

Run:  python -m pytest -q skills/dayz-launch-test/scripts/test_run_vehicle_checks.py, or python test_run_vehicle_checks.py
      (exit 0 = all pass)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_vehicle_checks  # noqa: E402


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    # Speed: no real waiting. run_checks/wait_ready use module-level time.sleep.
    monkeypatch.setattr(run_vehicle_checks.time, "sleep", lambda *a, **k: None)


class FakeDaemon:
    """`.run(cmd, args, timeout)` -> scripted dict. A script value is a dict (fixed), a list
    (consumed in order, clamped to the last), or a callable(args, call_index)."""

    def __init__(self, scripts: dict):
        self.scripts = scripts
        self.calls: dict = {}

    def run(self, cmd: str, args: dict, timeout: float = 30.0) -> dict:
        n = self.calls.get(cmd, 0)
        self.calls[cmd] = n + 1
        s = self.scripts.get(cmd)
        if callable(s):
            return s(args, n)
        if isinstance(s, list):
            return s[min(n, len(s) - 1)] if s else {"ok": True}
        if s is None:
            return {"ok": True}
        return s


def mkargs(**over):
    base = dict(vehicle="TEST_CAR", rotation=0, journal="", drive_s=0.0, hold_ttl=12.0,
                steer_left_sign=-1.0, port=8765, keyfile="", wheels=4, identity="id", lease_token="tok")
    base.update(over)
    return argparse.Namespace(**base)


def raycast_ring(args, n):
    # Always hit; alternate two components so ring_components collects a driver (10) + passenger (11).
    return {"raycast": {"hit": True, "component": 10 if (n % 2 == 0) else 11}}


def getin_responder(driver_available, driver_block, passenger_available=True):
    def resp(args, n):
        comp = args.get("component", -1)
        if comp == -1:
            return {"get_in": {"partial": True, "crew_size": 2, "first_block": "no_component"}}
        if comp == 10:  # driver seat, crew_index 0
            return {"get_in": {"component_crew_index": 0, "available": driver_available,
                               "first_block": driver_block}}
        # passenger seat, crew_index 1
        return {"get_in": {"component_crew_index": 1, "available": passenger_available, "first_block": ""}}
    return resp


def base_scripts(**over):
    s = {
        "query_player_state": {"ok": True, "pos": [100.0, 0.0, 100.0]},
        "world_spawn": {"ok": True, "found": True, "pos": [100.0, 0.0, 100.0]},
        "scene_raycast": raycast_ring,
        "query_get_in_condition": getin_responder(driver_available=True, driver_block=""),
        "vehicle_enter": {"ok": True, "seated": True},
        "vehicle_drive": {"ok": True},
        "telemetry_read": {"ok": True, "found": True, "wheel_count": 4, "fuel_fraction": 1.0},
        "vehicle_get_in_client": {"ok": True, "seated": True, "is_owner": True, "vehicle_fixture_ready": True},
        "engine_set": {"ok": True, "engine_on_server": True},
        "vehicle_control": {"ok": True},
        "vehicle_release": {"ok": True},
        # [preflight=not_seated, R5 t0 @spawn, R5 t1 moved+fast, R6 pa, pb, pc]
        "vehicle_telemetry": [
            {"ok": False, "error": "not_seated"},
            {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [130.0, 0.0, 100.0], "speedo_max": 40.0, "gear": 5, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [130.0, 0.0, 100.0], "speedo_max": 38.0, "gear": 5, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [133.0, 0.0, 100.0], "speedo_max": 38.0, "gear": 5, "engine_on_server": True, "is_owner": True},
            {"ok": True, "pos_real": [135.0, 0.0, 103.0], "speedo_max": 38.0, "gear": 5, "engine_on_server": True, "is_owner": True},
        ],
    }
    s.update(over)
    return s


def run(scripts, **argover):
    return run_vehicle_checks.run_checks(FakeDaemon(scripts), mkargs(**argover))


def step(R, key):
    return R["steps"].get(key, {})


def objective_pass(R):
    # objective_PASS is set in write_verdict; recompute the same way here
    obj = [v.get("PASS") for v in R["steps"].values() if v.get("PASS") is not None]
    return bool(obj) and all(obj)


def test_happy():
    """HAPPY: all objective steps PASS."""
    R = run(base_scripts())
    assert step(R, "R1").get("PASS") is True, "R1 PASS"
    assert step(R, "R2_collision").get("PASS") is True, "R2_collision PASS"
    assert step(R, "R3").get("PASS") is True, "R3 PASS (driver available)"
    assert step(R, "R4").get("PASS") is True, "R4 PASS"
    assert step(R, "R5").get("PASS") is True, f"R5 PASS -- {step(R, 'R5')}"
    assert R.get("stop") is None, "no step stopped the checks"
    assert objective_pass(R), "objective all True"


def test_r3_passenger_only():
    """R3 passenger-only (driver unreachable)."""
    sc = base_scripts(query_get_in_condition=getin_responder(driver_available=False, driver_block="unreachable",
                                                             passenger_available=True))
    R = run(sc)
    assert step(R, "R3").get("PASS") is False, f"R3 NOT PASS -- {step(R, 'R3')}"
    ds = step(R, "R3").get("driver_seat") or {}
    assert ds.get("first_block") == "unreachable", f"driver_seat first_block=unreachable -- {ds}"
    assert not objective_pass(R), "objective_PASS False"


def test_r4_seated_no_owner():
    """R4 seated but not owner."""
    sc = base_scripts(vehicle_get_in_client={"ok": True, "seated": True, "is_owner": False, "vehicle_fixture_ready": True})
    R = run(sc)
    assert step(R, "R4").get("PASS") is False, f"R4 NOT PASS -- {step(R, 'R4')}"
    assert R.get("stop") == "R4", f"stop == R4 -- {R.get('stop')}"
    assert "R5" not in R["steps"], "R5 not run"


def test_r4_no_fixture():
    """R4 seated+owner but fixture not ready."""
    sc = base_scripts(vehicle_get_in_client={"ok": True, "seated": True, "is_owner": True, "vehicle_fixture_ready": False})
    R = run(sc)
    assert step(R, "R4").get("PASS") is False, f"R4 NOT PASS -- {step(R, 'R4')}"
    assert R.get("stop") == "R4", "stop == R4"


def test_rerun_already_in_vehicle():
    """Re-run, player already seated."""
    sc = base_scripts(vehicle_telemetry=[
        {"ok": True, "pos_real": [50.0, 0.0, 50.0], "speedo_max": 0.0, "engine_on_server": False, "is_owner": True},
    ])
    R = run(sc)
    assert R.get("stop") == "preflight", f"stop == preflight -- {R.get('stop')}"
    assert step(R, "preflight").get("PASS") is False, "preflight NOT PASS"
    assert "R1" not in R["steps"], "R1 not run"


def test_r5_engine_off_moving():
    """R5 moves with engine OFF (gravity/inertia)."""
    sc = base_scripts(vehicle_telemetry=[
        {"ok": False, "error": "not_seated"},
        {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": False, "is_owner": True},
        {"ok": True, "pos_real": [130.0, 0.0, 100.0], "speedo_max": 40.0, "gear": 1, "engine_on_server": False, "is_owner": True},
    ])
    R = run(sc)
    assert step(R, "R5").get("PASS") is False, f"R5 NOT PASS (engine off) -- {step(R, 'R5')}"
    fixtext = " ".join(f["fix"] for f in R["fixes"] if f["step"] == "R5")
    assert "engine" in fixtext.lower(), f"R5 fix cites engine, not drivetrain -- {fixtext}"


def test_r5_blocked_retest():
    """R5 engine+owner but no motion -> needs_clear_ground_retest."""
    sc = base_scripts(vehicle_telemetry=[
        {"ok": False, "error": "not_seated"},
        {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": True, "is_owner": True},
        {"ok": True, "pos_real": [100.1, 0.0, 100.0], "speedo_max": 0.2, "gear": 1, "engine_on_server": True, "is_owner": True},
    ])
    R = run(sc)
    assert step(R, "R5").get("PASS") is False, "R5 NOT PASS"
    assert step(R, "R5").get("verdict") == "needs_clear_ground_retest", \
        f"R5 verdict needs_clear_ground_retest -- {step(R, 'R5')}"


def test_r5_timeout():
    """A verb times out in R5 -> inconclusive."""
    sc = base_scripts(vehicle_telemetry=[
        {"ok": False, "error": "not_seated"},
        {"ok": True, "pos_real": [100.0, 0.0, 100.0], "speedo_max": 0.0, "gear": 1, "engine_on_server": True, "is_owner": True},
        {"_timeout": True},
    ])
    R = run(sc)
    assert step(R, "R5").get("PASS") is False, "R5 NOT PASS"
    assert step(R, "R5").get("inconclusive") is True, f"R5 inconclusive -- {step(R, 'R5')}"


def test_r1_found_failclosed():
    """world_spawn omits `found` -> R1 fail-closed."""
    sc = base_scripts(world_spawn={"ok": True, "pos": [100.0, 0.0, 100.0]})  # no 'found'
    R = run(sc)
    assert step(R, "R1").get("PASS") is False, f"R1 NOT PASS (found absent) -- {step(R, 'R1')}"
    assert R.get("stop") == "R1", "stop == R1"


def test_unconditioned_car_stops_before_r5():
    """vehicle_fixture_ready=1 on the client, but the server reads no wheels and no fuel."""
    sc = base_scripts(telemetry_read={"ok": True, "found": True, "wheel_count": 0, "fuel_fraction": 0.0})
    R = run(sc)
    assert step(R, "R4_conditioned").get("PASS") is False, f"R4_conditioned NOT PASS -- {step(R, 'R4_conditioned')}"
    assert R.get("stop") == "R4_conditioned", f"stop == R4_conditioned -- {R.get('stop')}"
    assert "R5" not in R["steps"], "R5 not run on an unconditioned car"


def test_enqueue_sends_identity_and_lease_token(monkeypatch):
    """Every /enqueue body carries the identity and lease token from session_acquire."""
    d = run_vehicle_checks.Daemon(8765, "k", "agent-1", "tok-1")
    sent = {}

    def fake_req(method, path, query, body):
        sent.update(body or {})
        return 200, {"id": 7}

    monkeypatch.setattr(d, "_req", fake_req)
    assert d.enqueue("query_player_state", {}) == 7
    assert sent["identity"] == "agent-1" and sent["lease_token"] == "tok-1", sent


def test_wait_ready_stops_on_run_not_owned():
    """A fence rejection is reported at once, not as 'player never became ready' after 180 s."""
    class Rejecting:
        def run(self, cmd, args, timeout=30.0):
            raise RuntimeError("enqueue query_player_state -> 409 {'error': 'run_not_owned'}")

    with pytest.raises(RuntimeError, match="session_acquire_wait"):
        run_vehicle_checks.wait_ready(Rejecting())


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
