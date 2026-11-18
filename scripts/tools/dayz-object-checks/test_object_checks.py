"""Tests for object_checks.py against a fake game that answers bridge commands. No DayZ."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("object_checks_under_test", HERE / "object_checks.py")
oc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oc)

sys.path.insert(0, str(oc.REPO / ".claude" / "mcp" / "dayz-testbridge"))
import allowlist  # noqa: E402

OBJ, CTRL = "100,0", "200,0"


class FakeGame:
    def __init__(self, solid=True, blocks=True, standable=True, tilted=False, ghost_negative=False, hovers=False):
        self.hovers = hovers
        self.solid, self.blocks, self.standable, self.tilted = solid, blocks, standable, tilted
        self.ghost_negative = ghost_negative
        self.calls: list[str] = []
        self.player_y = 338.6

    def __call__(self, cmd, args=None, peer=None):
        allowlist.validate(cmd, args)
        self.calls.append(cmd)
        a = args or {}
        ok = lambda **d: {"ok": True, "error": "", "data": d}  # noqa: E731
        if cmd == "spawn":
            net = OBJ if a["cls"] != oc.CONTROL_CLASS else CTRL
            return ok(net_id=net, type=a["cls"], pos=[a["pos"][0], 338.6, a["pos"][2]])
        if cmd == "object_state":
            return ok(ori=[0, 25 if self.tilted else 0, 0])
        if cmd == "surface":
            return ok(ground_y=338.6)
        if cmd == "raycast":
            x, z = a["from"][0], a["to"][2]
            if a["from"][1] > 350:  # the ray down onto the top
                return ok(hits=[{"terrain": False, "net_id": OBJ, "pos": [x, 340.0, z]}])
            if abs(x - 4203.0) < 1:  # the control
                return ok(hits=[{"terrain": False, "net_id": CTRL}])
            if abs(x - 4197.0) < 1:  # the empty spot
                return ok(hits=[{"terrain": False, "net_id": "9,9"}] if self.ghost_negative else [])
            return ok(hits=[{"terrain": False, "net_id": OBJ}] if self.solid else [])
        if cmd == "walk":
            if a["seconds"] < 1:  # the step after a drop: the player is where the drop left it
                return ok(pos=[4200, self.player_y, 10656], distance=0.5)
            return ok(pos=[4200, 338.6, 10655.0 if self.blocks else 10659.0], distance=3.0)
        if cmd == "teleport":
            if a.get("ground") is False:
                over_object = abs(a["pos"][0] - 4200) < 1
                self.player_y = a["pos"][1] if (self.standable and over_object) or self.hovers else 338.6
            return ok(pos=a["pos"])
        if cmd == "player_state":
            return ok(pos=[4200, self.player_y, 10656])
        if cmd == "clear_spawns":
            return ok(count=2, kept=[])
        return ok()


def capture_factory(same=False):
    n = [0]

    def capture(png: Path):
        n[0] += 1
        png.write_bytes(b"frame" if same else f"frame{n[0]}".encode())
    return capture


def run(game, tmp_path, item=False, same=False):
    return oc.verdict(oc.run_checks(game, capture_factory(same), "Land_Test", item, tmp_path, sleep=lambda s: None))


def test_a_solid_upright_object_passes_every_check_and_is_cleared(tmp_path):
    game = FakeGame()
    R = run(game, tmp_path)
    assert R["PASS"] and all(c["PASS"] for c in R["checks"].values())
    assert R["checks"]["4 collision"]["controls_valid"] and game.calls[-1] == "clear_spawns"
    assert sorted(p.name for p in tmp_path.glob("*.png")) == ["east.png", "north.png", "south.png", "west.png"]


def test_walking_through_and_falling_off_fail(tmp_path):
    R = run(FakeGame(blocks=False, standable=False), tmp_path)
    assert R["checks"]["5 walk_into"]["PASS"] is False and R["checks"]["6 stand_on"]["PASS"] is False and not R["PASS"]


def test_rays_through_the_object_fail_collision(tmp_path):
    R = run(FakeGame(solid=False), tmp_path)
    assert R["checks"]["4 collision"]["PASS"] is False and R["checks"]["4 collision"]["object_hits"] == 0


def test_a_negative_control_that_hits_makes_the_collision_check_worthless(tmp_path):
    R = run(FakeGame(ghost_negative=True), tmp_path)
    assert R["checks"]["4 collision"]["controls_valid"] is False and R["checks"]["4 collision"]["PASS"] is False


def test_stale_pictures_and_a_tilted_object_fail(tmp_path):
    R = run(FakeGame(tilted=True), tmp_path, same=True)
    assert R["checks"]["3 pictures"]["PASS"] is False and "stale" in R["checks"]["3 pictures"]["problems"][0]
    assert R["checks"]["2 placement"]["PASS"] is False


def test_an_item_skips_the_player_checks(tmp_path):
    game = FakeGame()
    R = run(game, tmp_path, item=True)
    assert R["checks"]["5 walk_into"]["PASS"] is None and "walk" not in game.calls and R["PASS"]


def test_a_player_that_never_falls_makes_stand_on_worthless(tmp_path):
    R = run(FakeGame(hovers=True), tmp_path)
    assert R["checks"]["6 stand_on"]["control_fell"] is False and R["checks"]["6 stand_on"]["PASS"] is False
