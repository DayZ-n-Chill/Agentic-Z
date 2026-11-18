"""Tests for vehicle_checks.py against a fake game that answers bridge commands. No DayZ."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("vehicle_checks_under_test", HERE / "vehicle_checks.py")
vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vc)

sys.path.insert(0, str(vc.REPO / ".claude" / "mcp" / "dayz-testbridge"))
import allowlist  # noqa: E402

NET = "23207,0"


class FakeGame:
    """Answers like the bridge: every call is checked against the allowlist first."""

    def __init__(self, spawn_ok=True, wheels=4, fuel=1.0, seat_reason="", distance=13.0, engine_on=True, solid=True):
        self.spawn_ok, self.wheels, self.fuel = spawn_ok, wheels, fuel
        self.seat_reason, self.distance, self.engine_on, self.solid = seat_reason, distance, engine_on, solid
        self.in_car = False
        self.calls: list[str] = []
        self.drives = 0

    def __call__(self, cmd, args=None, peer=None):
        allowlist.validate(cmd, args)
        assert peer in allowlist.peers(cmd) or (peer is None and len(allowlist.peers(cmd)) == 1), (cmd, peer)
        self.calls.append(cmd)
        return getattr(self, cmd)(args or {})

    def ok(self, **data):
        return {"ok": True, "error": "", "data": data}

    def fail(self, error, **data):
        return {"ok": False, "error": error, "data": data}

    def teleport(self, a):
        return self.ok(pos=a["pos"])

    def spawn(self, a):
        return self.ok(net_id=NET, type=a["cls"], class_name=a["cls"], pos=[a["pos"][0], 338.4, a["pos"][2]]) \
            if self.spawn_ok else self.fail("spawn_failed")

    def raycast(self, a):
        self.rays = getattr(self, "rays", 0) + 1
        door = {"net_id": "99,0", "parent_net_id": NET, "terrain": False}  # an attached door names the car as parent
        return self.ok(hits=[door if self.rays % 2 else {"net_id": NET, "terrain": False}] if self.solid else [])

    def surface(self, a):
        return self.ok(ground_y=338.0, road_y=338.0, surface="cp_concrete1")

    def vehicle_prepare(self, a):
        return self.ok(wheels_present=self.wheels, wheels_declared=4, fuel=self.fuel, engine_on=True,
                       entry_pos=[4198.5, 338.7, 10662.4])

    def get_in(self, a):
        if self.seat_reason:
            return self.fail("not_seated", reason=self.seat_reason)
        self.in_car = True
        return self.ok(seated=True, tries=1)

    def player_state(self, a):
        return self.ok(in_vehicle=self.in_car, seat=0 if self.in_car else -1)

    def drive(self, a):
        self.drives += 1
        if self.drives == 1:
            return self.ok(distance=self.distance, top_speed=28.0, samples=[{"gear": 2, "pos": [0, 0, 0]}])
        if self.drives == 2:  # straight north
            return self.ok(samples=[{"pos": [0, 0, 0]}, {"pos": [0, 0, 10]}])
        return self.ok(samples=[{"pos": [0, 0, 10]}, {"pos": [-3, 0, 18]}])  # curving to -x

    def vehicle_state(self, a):
        return self.ok(engine_on=self.engine_on)

    def get_out(self, a):
        self.in_car = False
        return self.ok(on_foot=True)

    def delete(self, a):
        assert not self.in_car, "deleted a car with crew"
        return self.ok(removed=True)


def test_all_objective_checks_pass_and_acceptance_stays_open():
    game = FakeGame()
    R = vc.verdict(vc.run_checks(game, "Hatchback_02"))
    assert R["objective_PASS"] is True and R["acceptance_PASS"] is None and R["fixes"] == []
    assert [c["PASS"] for c in R["checks"].values()] == [True, True, True, True, True, None]
    assert R["checks"]["6 turns"]["signed_turn"] == 30.0 and R["checks"]["6 turns"]["calibrated"] is False
    assert game.calls[-3:] == ["player_state", "get_out", "delete"] and R["cleanup"] == "car deleted"


def test_a_class_that_does_not_spawn_ends_the_pass():
    game = FakeGame(spawn_ok=False)
    R = vc.verdict(vc.run_checks(game, "NoSuchCar"))
    assert R["stop"] == "1 spawns" and R["objective_PASS"] is False and "does not resolve" in R["fixes"][0]["fix"]
    assert game.calls == ["teleport", "spawn"]


def test_short_wheels_end_the_pass_and_the_car_is_removed():
    game = FakeGame(wheels=2)
    R = vc.verdict(vc.run_checks(game, "MyCar"))
    assert R["stop"] == "2 conditioned" and "Axles" in R["checks"]["2 conditioned"]["fix"]
    assert "get_in" not in game.calls and "raycast" not in game.calls and game.calls[-1] == "delete"


@pytest.mark.parametrize("reason, fix_word", [
    ("possible=true can=false through=false area_free=true reach=true", "CrewCanGetThrough"),
    ("possible=true can=false through=true area_free=false reach=true", "door area"),
    ("possible=true can=false through=true area_free=true reach=false", "CanReachSeatFromDoors"),
    ("possible=false can=true", "test's own state"),
])
def test_a_refused_get_in_points_at_the_condition_that_failed(reason, fix_word):
    R = vc.verdict(vc.run_checks(FakeGame(seat_reason=reason), "MyCar"))
    assert R["stop"] == "4 seated" and fix_word in R["checks"]["4 seated"]["fix"]


def test_engine_on_and_no_distance_asks_for_a_clear_ground_retest():
    R = vc.verdict(vc.run_checks(FakeGame(distance=0.2), "MyCar"))
    assert R["checks"]["5 drives"]["verdict"] == "needs_clear_ground_retest" and "6 turns" not in R["checks"]


def test_no_drive_with_the_engine_off_is_not_a_drivetrain_verdict():
    R = vc.verdict(vc.run_checks(FakeGame(distance=0.0, engine_on=False), "MyCar"))
    assert "engine never ran" in R["checks"]["5 drives"]["fix"] and "verdict" not in R["checks"]["5 drives"]


def test_rays_that_miss_fail_solid_but_do_not_end_the_pass():
    R = vc.verdict(vc.run_checks(FakeGame(solid=False), "MyCar"))
    assert R["checks"]["3 solid"]["PASS"] is False and R["checks"]["5 drives"]["PASS"] is True and R["stop"] is None


def test_no_outside_tool_is_named():
    text = (HERE / "vehicle_checks.py").read_text(encoding="utf-8").lower()
    for word in ("dayz-mcp", "dayz_mcp", "/enqueue", "lease", "keyfile"):
        assert word not in text, word
