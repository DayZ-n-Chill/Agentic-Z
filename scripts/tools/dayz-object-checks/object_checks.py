"""dayz-object-checks: ready-made in-game checks of a static object or an item, driven through the dayz-testbridge.

    python scripts/tools/dayz-object-checks/object_checks.py --cls <Class> [--item]
        [--start [--mods MyMod ...] [--deps CF ...] [--server chernarus]] [--at X Z] [--out DIR]

  1 spawns       the class spawns 6 m north of the player and reads back as itself          (ends the pass)
  2 placement    it sits on the ground (within 0.5 m) and upright (pitch and roll within 10 degrees)
  3 pictures     four captures from north, east, south and west; none black, none stale
  4 collision    the nine-ray set (three heights by three offsets, Geometry rays from 4 m south): the
                 object takes at least one ray, a vanilla WoodenCrate beside it takes at least one
                 (the positive control), and the same nine rays at an empty spot take none (the negative
                 control); a set whose controls fail proves nothing (references/test-cell-evidence.md)
  5 walk_into    not for --item: the player, facing the object from 4 m, walks 6 s; PASS when it stops
                 short of the object's centre (rays alone can pass while the player walks through)
  6 stand_on     not for --item: the player is put 0.2 m above the object's top (a ray down) and must
                 still be up there after a half-second step, while the same drop over empty ground beside
                 it falls

The controls (the WoodenCrate, the empty spot and the control drop) sit a fixed 3 m east or west of the
object's centre, so the object must fit within 2.5 m of its centre east and west; a wider building puts
the empty spot inside itself and fails checks 4 and 6 however good its model is.

Writes output/<Class>-object-checks/<time>/report.json with the captures beside it.
Exit codes: 0 every check passed, 1 one failed, 2 the run could not happen.
Every object it spawns is removed with clear_spawns; a session it started is always stopped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / ".claude" / "mcp" / "dayz-testbridge"))

BENCH = (4200.0, 10650.0)
AHEAD_M = 6.0
CONTROL_CLASS = "WoodenCrate"
RAY_OUT_M = 4.0
RAY_HEIGHTS = (0.15, 0.5, 1.0)
RAY_OFFSETS = (-0.25, 0.0, 0.25)
CAMERA_DIST_M = 5.0
CAMERA_HEIGHT_M = 1.6


def run_checks(call: Callable[..., dict], capture: Callable[[Path], None], cls: str, item: bool, out: Path,
               at=BENCH, sleep: Callable[[float], None] = time.sleep) -> dict:
    """Run the checks through `call` and `capture`; return the report (nothing else is written)."""
    R: dict = {"class": cls, "item": item, "checks": {}, "stop": None}

    def result(name: str, passed: Optional[bool], **detail) -> bool:
        R["checks"][name] = {"PASS": passed, **detail}
        print(f"[{'PASS' if passed else 'SKIP' if passed is None else 'FAIL'}] {name}: {json.dumps(detail, default=str)[:240]}",
              flush=True)
        return bool(passed)

    call("teleport", {"pos": [at[0], 0.0, at[1]]})
    spawn = call("spawn", {"cls": cls, "pos": [at[0], 0.0, at[1] + AHEAD_M]})
    try:
        data = spawn.get("data") or {}
        if not result("1 spawns", bool(spawn.get("ok")) and data.get("type") == cls, error=spawn.get("error"), pos=data.get("pos")):
            R["stop"] = "1 spawns"
            return R
        net_id, pos = data["net_id"], data["pos"]

        # 2 placement
        state = call("object_state", {"net_id": net_id}).get("data") or {}
        ground = (call("surface", {"x": pos[0], "z": pos[2]}).get("data") or {}).get("ground_y", pos[1])
        ori = state.get("ori") or [0, 0, 0]
        pitch, roll = _signed(ori[1]), _signed(ori[2])
        result("2 placement", abs(pos[1] - ground) <= 0.5 and abs(pitch) <= 10 and abs(roll) <= 10,
               height_above_ground=round(pos[1] - ground, 3), pitch=round(pitch, 2), roll=round(roll, 2))

        # 3 pictures
        call("hud", {"show": False})
        shots, problems, last = [], [], None
        for side, (dx, dz) in (("north", (0, 1)), ("east", (1, 0)), ("south", (0, -1)), ("west", (-1, 0))):
            call("camera_set", {"pos": [pos[0] + dx * CAMERA_DIST_M, ground + CAMERA_HEIGHT_M, pos[2] + dz * CAMERA_DIST_M],
                                "look_at": [pos[0], ground + 0.5, pos[2]]})
            sleep(2.0)  # let the client draw from the new camera
            png = out / f"{side}.png"
            try:
                capture(png)
            except Exception as e:  # noqa: BLE001 - a failed capture is a failed check, not a crash
                problems.append(f"{side}: {e}")
                continue
            digest = hashlib.sha256(png.read_bytes()).hexdigest()
            if digest == last:
                problems.append(f"{side}: stale, byte for byte the previous capture")
            last = digest
            shots.append(str(png))
        call("camera_reset")
        call("hud", {"show": True})
        result("3 pictures", not problems and len(shots) == 4, captures=shots, problems=problems,
               note="look at the four pictures for winding, scale and orientation")

        # 4 collision, with a positive and a negative control
        control = (call("spawn", {"cls": CONTROL_CLASS, "pos": [pos[0] + 3.0, 0.0, pos[2]]}).get("data") or {})
        hits = _nine_rays(call, pos, ground, net_id)
        positive = _nine_rays(call, control.get("pos") or pos, ground, control.get("net_id", "-")) if control else 0
        negative = _nine_rays(call, [pos[0] - 3.0, ground, pos[2]], ground, None)
        controls_ok = positive >= 1 and negative == 0
        result("4 collision", controls_ok and hits >= 1, object_hits=hits, positive_control_hits=positive,
               negative_control_hits=negative, of=9, controls_valid=controls_ok)

        # 5 walk_into and 6 stand_on (statics only)
        if item:
            result("5 walk_into", None, note="skipped for an item")
            result("6 stand_on", None, note="skipped for an item")
        else:
            call("teleport", {"pos": [pos[0], 0.0, pos[2] - 4.0]})
            call("look_at", {"pos": [pos[0], ground + 1.5, pos[2]]})
            walk = call("walk", {"seconds": 6, "speed": 1})
            end = (walk.get("data") or {}).get("pos") or [0, 0, pos[2] + 9]
            result("5 walk_into", end[2] < pos[2] - 0.2, player_end=end, object_centre=pos,
                   note="a player that passes the centre walked through the object")
            top = _top(call, pos)
            if top is None:
                result("6 stand_on", False, note="no surface found by a ray down onto the object")
            else:
                # Measured: a player put in mid-air reads back at that height until it moves, so each
                # drop is followed by a half-second step before the height is read.
                call("teleport", {"pos": [pos[0], top + 0.2, pos[2]], "ground": False})
                y = (call("walk", {"seconds": 0.5, "speed": 1}).get("data") or {}).get("pos", [0, 0, 0])[1]
                # The control: the same drop over empty ground beside it must fall, or the read proves nothing.
                call("teleport", {"pos": [pos[0] - 3.0, top + 0.2, pos[2]], "ground": False})
                fell = (call("walk", {"seconds": 0.5, "speed": 1}).get("data") or {}).get("pos", [0, 0, 0])[1]
                control_ok = fell < top - 0.5
                result("6 stand_on", control_ok and y >= top - 0.3, top=round(top, 3), player_y=round(y, 3),
                       control_player_y=round(fell, 3), control_fell=control_ok)
    finally:
        # Every path after the spawn, an early stop or a raised bridge error included, removes what it spawned.
        R["cleanup"] = call("clear_spawns").get("data")
    return R


def _signed(deg: float) -> float:
    """An angle folded into -180..180."""
    return (deg + 180.0) % 360.0 - 180.0


def _nine_rays(call, target, ground: float, net_id: Optional[str]) -> int:
    """Rays from RAY_OUT_M south of `target` toward it; hits on `net_id` or any object when net_id is None."""
    hits = 0
    for height in RAY_HEIGHTS:
        for offset in RAY_OFFSETS:
            start = [target[0] + offset, ground + height, target[2] - RAY_OUT_M]
            end = [target[0] + offset, ground + height, target[2] + 0.5]
            found = (call("raycast", {"from": start, "to": end, "mode": "geom"}).get("data") or {}).get("hits") or []
            if any((not h.get("terrain")) and (net_id is None or net_id in (h.get("net_id"), h.get("parent_net_id")))
                   for h in found):
                hits += 1
    return hits


def _top(call, pos) -> Optional[float]:
    found = (call("raycast", {"from": [pos[0], pos[1] + 20, pos[2]], "to": [pos[0], pos[1] - 1, pos[2]], "mode": "geom"})
             .get("data") or {}).get("hits") or []
    tops = [h["pos"][1] for h in found if not h.get("terrain") and h.get("pos")]
    return max(tops) if tops else None


def verdict(R: dict) -> dict:
    judged = [c["PASS"] for c in R["checks"].values() if c["PASS"] is not None]
    R["PASS"] = bool(judged) and all(judged) and R["stop"] is None
    return R


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cls", required=True, help="the class to check")
    ap.add_argument("--item", action="store_true", help="an item: skip walk_into and stand_on")
    ap.add_argument("--start", action="store_true", help="start a dayz-testbridge session first, and stop it at the end")
    ap.add_argument("--mods", nargs="*", default=[])
    ap.add_argument("--deps", nargs="*", default=[])
    ap.add_argument("--server", default="chernarus")
    ap.add_argument("--at", nargs=2, type=float, default=BENCH, metavar=("X", "Z"))
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    import session
    import window_capture

    project = session.h.resolve_project_dir()
    out = args.out or project / "output" / f"{args.cls}-object-checks" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out.mkdir(parents=True, exist_ok=True)
    started = False
    try:
        if args.start:
            session.start(project, args.mods, args.deps, args.server)
            started = True
        state = session.load_state(project)
        if state is None:
            raise RuntimeError("no dayz-testbridge session is running: pass --start, or start one with session_start")
        rt = session.real_runtime()
        bridge = session.bridge_of(project, state, rt)

        def call(cmd, a=None, peer=None):
            res = bridge.call(cmd, a, peer)
            session.remember(project, state, bridge)
            return res

        report = verdict(run_checks(call, lambda png: window_capture.capture_window(state["pids"]["client"], png),
                                    args.cls, args.item, out, tuple(args.at)))
    except Exception as e:  # noqa: BLE001 - no session or a bridge fault: the run did not happen
        print(f"ERROR {type(e).__name__}: {e}")
        return 2
    finally:
        if started:
            session.stop(project)
    (out / "report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"{'PASS' if report['PASS'] else 'FAIL'} -> {out / 'report.json'}")
    return 0 if report["PASS"] else 1


if __name__ == "__main__":
    sys.exit(main())
