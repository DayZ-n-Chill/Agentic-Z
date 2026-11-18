"""dayz-vehicle-checks: six in-game acceptance checks of a car, driven through the dayz-testbridge.

    python scripts/tools/dayz-vehicle-checks/vehicle_checks.py --vehicle <CarClass>
        [--start [--mods MyCar ...] [--deps CF ...] [--server chernarus]]
        [--at X Z] [--wheels 4] [--drive-s 5] [--out DIR]

The checks follow skills/dayz-launch-test/references/vehicle-acceptance-checks.md; conditioning runs before
the solid rays, so they meet the car with its doors, trunk and wheels on:

  0 site         no other vehicle within 30 m and nothing in the 16 m lane ahead             (ends the pass)
  1 spawns       the class spawns 12 m north of the player and reads back as itself     (ends the pass)
  2 conditioned  server-side OnDebugSpawn: the expected wheels present and fuel above 0   (ends the pass)
  3 solid        12 level view rays from 3.5 m out at 0.4, 0.8 and 1.2 m above the ground: at least 6 hit
                 the car or a part on it (a vanilla Hatchback_02 scored 9 with its parts on, 6 bare)
  4 seated       the real get-in as driver: seated on the client, seat 0 on the server    (ends the pass)
  5 drives       full throttle for --drive-s: more than 1 m and a speed above 0, engine on
  6 turns        a straight stretch, then full left steer: the signed turn, NOT calibrated (information only)

Each car failure is mapped to the row of that reference's "Failure to fix table";
the site failure and the engine-off drive failure are this tool's own additions
and have no row there.
Solid, oriented and turning the right way also need eyes on the car: the
verdict says so and never claims acceptance. The run uses the session the
dayz-testbridge recorded (.server/!TestBridge/session.json), or starts one with
--start and then always stops it. The car is spawned at --at (default the
north-west airfield driving bench, [4200, 10650] on Chernarus), which must have
clear ground ahead (vehicle-in-game-facts.md, "A driving bench").

Writes output/<CarClass>-vehicle-checks/<time>/verdict.json. Exit codes: 0 every
objective check passed, 1 one failed, 2 the run could not happen (no session,
a bridge error).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / ".claude" / "mcp" / "dayz-testbridge"))

REFERENCE = "skills/dayz-launch-test/references/vehicle-acceptance-checks.md"
BENCH = (4200.0, 10650.0)
SPAWN_AHEAD_M = 12.0
RAY_OUT_M = 3.5
RAY_HEIGHTS = (0.4, 0.8, 1.2)
SOLID_MIN = 6
SITE_VEHICLE_M = 30.0    # no other vehicle this close (vehicle-in-game-facts.md)
LANE_LENGTH_M = 16       # the lane ahead: a 5 s full-throttle drive covered 13 to 14 m on the bench
LANE_STEP_M = 4          # with a 2 m search radius, no gap along the lane
LANE_HALF_WIDTH_M = 2.0  # half a car's width plus a margin

# The rows of the reference's "Failure to fix table" each failure points to.
FIX = {
    "site": "The driving site is not clear: another vehicle within 30 m or an object in the lane ahead. Not a car fault; "
            "pick clear ground with --at (vehicle-in-game-facts.md, \"A driving bench\").",
    "no_class": "The class does not resolve: the mod is not mounted (windows-build-and-mount.md, absolute mod paths) "
                "or CfgPatches does not register it. Not a model fault.",
    "invisible": "Spawns but rays pass through: the componentNN double tag (vehicle-structural-parity.md, rip-import.md), "
                 "or per-part winding (rip-import.md). Confirm with a capture before fixing.",
    "conditioning": "Wheel count short or fuel 0 after conditioning: OnDebugSpawn attaches no wheels, or an Axles override "
                    "lists one axle (invariants-wheels-and-hubs.md). For fuel, read again a tick later first.",
    "through": "CrewCanGetThrough false: a bare class X: CarScript inherits Transport.CrewCanGetThrough()=false "
               "(rip-import.md), or the driver door is shut.",
    "area": "The door area is not free: something blocks it, or the door selection is wrong.",
    "reach": "CanReachSeatFromDoors false: seat and door geometry (door condition point), or the player is too far.",
    "not_seated": "The client is not seated: the crew bone or selection, or the seat animation type "
                  "(vehicle-config-crew-lights-sounds.md).",
    "test_state": "The test's own state (the action manager refused: an action running, a menu, or the player busy). "
                  "Not a model fix; run the checks again.",
    "no_distance": "Engine on and no distance: test again on clear ground first; then the wheel simulation (rip-import.md, "
                   "vehicle-structural-parity.md) or the drivetrain in config.cpp.",
    "engine_off": "The engine never ran: not a drivetrain verdict. Check vehicle-parts-and-start.md (battery, spark plug, "
                  "fuel) before the model.",
}


class BridgeCalls:
    """The bridge of the running session: call(cmd, args, peer) -> result."""

    def __init__(self, project: Path, started: bool = False):
        import session

        self.session = session
        self.project = project
        self.started = started
        self.rt = session.real_runtime()
        state = session.load_state(project)
        if state is None:
            raise RuntimeError("no dayz-testbridge session is running: pass --start, or start one with session_start")
        self.state = state
        self.bridge = session.bridge_of(project, state, self.rt)

    def __call__(self, cmd: str, args: Optional[dict] = None, peer: Optional[str] = None) -> dict:
        res = self.bridge.call(cmd, args, peer)
        self.session.remember(self.project, self.state, self.bridge)
        return res


def _pos(res: dict) -> Optional[list]:
    p = (res.get("data") or {}).get("pos")
    return p if isinstance(p, list) and len(p) == 3 else None


def run_checks(call: Callable[..., dict], vehicle: str, at=BENCH, wheels: int = 4, drive_s: float = 5.0) -> dict:
    """Run the six checks through `call`; return the report (nothing is written)."""
    R: dict = {"vehicle": vehicle, "reference": REFERENCE, "checks": {}, "fixes": [], "stop": None}

    def result(name: str, passed: Optional[bool], fix: str = "", **detail) -> bool:
        R["checks"][name] = {"PASS": passed, **detail}
        if passed is False:
            R["checks"][name]["fix"] = FIX[fix]
            R["fixes"].append({"check": name, "fix": FIX[fix]})
        print(f"[{'PASS' if passed else 'INFO' if passed is None else 'FAIL'}] {name}: {json.dumps(detail, default=str)[:240]}",
              flush=True)
        return bool(passed)

    # 0 site: no other vehicle within 30 m, and nothing in the lane the car drives up
    # (vehicle-in-game-facts.md, "A driving bench"), so a blocked car is never read as a broken drivetrain.
    player = call("teleport", {"pos": [at[0], 0.0, at[1]]})
    spot = [at[0], 0.0, at[1] + SPAWN_AHEAD_M]
    cars = [o for o in (call("find_objects", {"pos": spot, "radius": SITE_VEHICLE_M, "cls": "Transport"}).get("data") or {})
            .get("objects") or []]
    lane = []
    for ahead in range(LANE_STEP_M, LANE_LENGTH_M + 1, LANE_STEP_M):
        found = (call("find_objects", {"pos": [spot[0], 0.0, spot[2] + ahead], "radius": LANE_HALF_WIDTH_M}).get("data") or {})
        lane += [o for o in found.get("objects") or [] if o.get("class_name") not in ("SurvivorBase", "PlayerBase")]
    if not result("0 site", not cars and not lane, "site", vehicles=[o.get("type") for o in cars],
                  in_lane=[(o.get("type") or o.get("class_name"), o.get("pos")) for o in lane][:10]):
        R["stop"] = "0 site"
        return R

    # 1 spawns
    spawn = call("spawn", {"cls": vehicle, "pos": spot})
    data = spawn.get("data") or {}
    if not result("1 spawns", bool(spawn.get("ok")) and data.get("type") == vehicle, "no_class",
                  error=spawn.get("error"), net_id=data.get("net_id"), pos=data.get("pos"), player=_pos(player)):
        R["stop"] = "1 spawns"
        return R
    car, net_id = data["pos"], data["net_id"]

    # 2 conditioned: first, so the solid check sees the car with its doors, trunk and wheels on.
    prep = call("vehicle_prepare", {"net_id": net_id, "engine_on": True})
    pd = prep.get("data") or {}
    if not result("2 conditioned", bool(prep.get("ok")) and (pd.get("wheels_present") or 0) >= wheels and (pd.get("fuel") or 0) > 0,
                  "conditioning", wheels_present=pd.get("wheels_present"), wheels_declared=pd.get("wheels_declared"),
                  fuel=pd.get("fuel"), engine_on=pd.get("engine_on"), expected_wheels=wheels, error=prep.get("error")):
        R["stop"] = "2 conditioned"
        return _cleanup(call, R, net_id)

    # 3 solid: heights above the ground under the car, not above its origin; a hit on a door,
    # the trunk or another attached part counts for the car (its parent_net_id is the car).
    # Measured on a vanilla Hatchback_02: 9 of 12 with its parts on, 6 of 12 bare.
    ground = (call("surface", {"x": car[0], "z": car[2]}).get("data") or {}).get("ground_y", car[1])
    hits = 0
    for height in RAY_HEIGHTS:
        for angle in (0, 90, 180, 270):
            a = math.radians(angle)
            start = [car[0] + RAY_OUT_M * math.cos(a), ground + height, car[2] + RAY_OUT_M * math.sin(a)]
            ray = call("raycast", {"from": start, "to": [car[0], ground + height, car[2]], "mode": "view"})
            if any(net_id in (h.get("net_id"), h.get("parent_net_id")) for h in (ray.get("data") or {}).get("hits") or []):
                hits += 1
    result("3 solid", hits >= SOLID_MIN, "invisible", ray_hits=hits, of=12,
           note="coarse: says collision answers at all; winding, orientation and scale need a capture and eyes")

    # 4 seated
    entry = pd.get("entry_pos") or car
    call("teleport", {"pos": entry})
    get_in = call("get_in", {"net_id": net_id, "seat": 0})
    server = call("player_state")
    sd = server.get("data") or {}
    seated = bool(get_in.get("ok")) and bool(sd.get("in_vehicle")) and sd.get("seat") == 0
    reason = (get_in.get("data") or {}).get("reason", "")
    if not result("4 seated", seated, _seat_fix(reason), client=get_in.get("error") or "seated", reason=reason,
                  server_seat=sd.get("seat")):
        R["stop"] = "4 seated"
        return _cleanup(call, R, net_id)

    # 5 drives
    drive = call("drive", {"throttle": 1.0, "seconds": drive_s})
    dd = drive.get("data") or {}
    state = call("vehicle_state", {"net_id": net_id}, "client")
    engine_on = bool((state.get("data") or {}).get("engine_on"))
    moved = bool(drive.get("ok")) and (dd.get("distance") or 0) > 1.0 and (dd.get("top_speed") or 0) > 0
    fix = "no_distance" if engine_on else "engine_off"  # moved with the engine off (rolled) is still not a drive
    drives = result("5 drives", moved and engine_on, fix, distance=dd.get("distance"), top_speed=dd.get("top_speed"),
                    engine_on=engine_on, gears=sorted({s.get("gear") for s in dd.get("samples") or []}), error=drive.get("error"))
    if not drives and engine_on:
        R["checks"]["5 drives"]["verdict"] = "needs_clear_ground_retest"

    # 6 turns (information: the sign of steer against the turn is not calibrated against a vanilla car)
    if drives:
        straight = call("drive", {"throttle": 0.6, "seconds": 1.5})
        left = call("drive", {"throttle": 0.6, "steer": -1.0, "seconds": 2.0})
        cross = _signed_turn((straight.get("data") or {}).get("samples"), (left.get("data") or {}).get("samples"))
        result("6 turns", None, signed_turn=cross, steer=-1.0, calibrated=False,
               note="compare the sign with a vanilla car driven the same way before reading it as left or right")

    return _cleanup(call, R, net_id)


def _seat_fix(reason: str) -> str:
    if "possible=false" in reason:
        return "test_state"
    for key, fix in (("through=false", "through"), ("area_free=false", "area"), ("reach=false", "reach")):
        if key in reason:
            return fix
    return "not_seated"


def _signed_turn(straight: Optional[list], left: Optional[list]) -> Optional[float]:
    """Cross product (XZ) of the straight stretch's heading and the steered stretch's travel."""
    if not straight or not left or len(straight) < 2:
        return None
    a, b, c = straight[0]["pos"], straight[-1]["pos"], left[-1]["pos"]
    hx, hz = b[0] - a[0], b[2] - a[2]
    dx, dz = c[0] - b[0], c[2] - b[2]
    return round(hx * dz - hz * dx, 3)


def _cleanup(call, R: dict, net_id: str) -> dict:
    """Out of the car on the client first, then delete it: a car deleted with crew crashed 1.30."""
    try:
        state = call("player_state")
        if (state.get("data") or {}).get("in_vehicle"):
            call("get_out")
        R["cleanup"] = call("delete", {"net_id": net_id}).get("error") or "car deleted"
    except Exception as e:  # noqa: BLE001 - a cleanup error must not hide the checks
        R["cleanup"] = f"not cleaned up: {e}"
    return R


def verdict(R: dict) -> dict:
    objective = [c["PASS"] for c in R["checks"].values() if c["PASS"] is not None]
    R["objective_PASS"] = bool(objective) and all(objective) and R["stop"] is None
    R["acceptance_PASS"] = None
    R["acceptance_note"] = ("acceptance also needs eyes: captures from several angles for winding, orientation and scale, "
                            "and the turn sign compared with a vanilla car")
    return R


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vehicle", required=True, help="the car class to check")
    ap.add_argument("--start", action="store_true", help="start a dayz-testbridge session first, and stop it at the end")
    ap.add_argument("--mods", nargs="*", default=[], help="with --start: built mods to load (the car's mod)")
    ap.add_argument("--deps", nargs="*", default=[], help="with --start: dependency mods in load order")
    ap.add_argument("--server", default="chernarus", help="with --start: the instance to copy (default chernarus)")
    ap.add_argument("--at", nargs=2, type=float, default=BENCH, metavar=("X", "Z"), help="where the player stands")
    ap.add_argument("--wheels", type=int, default=4, help="wheels the conditioned car must have (default 4)")
    ap.add_argument("--drive-s", type=float, default=5.0, help="seconds of full throttle (default 5, at most 60)")
    ap.add_argument("--out", type=Path, help="folder for verdict.json (default output/<CarClass>-vehicle-checks/<time>/)")
    args = ap.parse_args(argv)

    import session

    project = session.h.resolve_project_dir()
    started = False
    try:
        if args.start:
            session.start(project, args.mods, args.deps, args.server)
            started = True
        report = verdict(run_checks(BridgeCalls(project), args.vehicle, tuple(args.at), args.wheels, args.drive_s))
    except Exception as e:  # noqa: BLE001 - no session or a bridge fault: the run did not happen
        print(f"ERROR {type(e).__name__}: {e}")
        return 2
    finally:
        if started:
            session.stop(project)
    out = args.out or project / "output" / f"{args.vehicle}-vehicle-checks" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out.mkdir(parents=True, exist_ok=True)
    (out / "verdict.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"{'PASS' if report['objective_PASS'] else 'FAIL'} (objective checks; acceptance needs eyes) -> {out / 'verdict.json'}")
    for f in report["fixes"]:
        print(f"  {f['check']}: {f['fix']}")
    return 0 if report["objective_PASS"] else 1


if __name__ == "__main__":
    sys.exit(main())
