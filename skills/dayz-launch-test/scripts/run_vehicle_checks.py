#!/usr/bin/env python3
"""run_vehicle_checks.py - vehicle acceptance driver (skill dayz-launch-test,
references/mcp/vehicle-acceptance.md).

Drives steps R1..R6 against the ALREADY-RUNNING dayz-mcp daemon (:8765) via raw /enqueue + /await.
stdlib only; no MCP SDK, no game launch.

Scope: the script runs the OBJECTIVE (telemetry/raycast) steps that go through the bridge. The VISUAL
steps (R2 render look, R6 turn confirmation) need capture_screenshot, which is a host-side MCP tool
(window grab), NOT a bridge /enqueue command - so they stay with the agent (call capture_screenshot +
eyeball the PNG). This script flags them, it does not capture. The script's result is `objective_PASS`,
NOT acceptance: acceptance also needs the agent's visual steps (R2_visual, R6 calibration).

On a FAIL it maps the symptom to a known fix (the vehicles pack, skills/_shared/vehicles/) and writes
verdict.json. It does NOT apply fixes or rebuild - that is the agent/human loop (guardrail 1: a failure
outside the known taxonomy STOPS and escalates; no blind rebuild).

Hardening: R3 gates on the DRIVER seat
(crew_index 0), not any seat; R4_conditioned seats the player on the server and runs the car's
OnDebugSpawn there (vehicle_enter + a 0.5 s vehicle_drive), then requires wheel_count and fuel_fraction
from telemetry_read, because vehicle_get_in_client runs OnDebugSpawn on the client only and can report
vehicle_fixture_ready=1 on a car with no wheels and no fuel; R4 is fail-closed on
seated+is_owner+fixture_ready; a preflight aborts if the player is already in a vehicle (re-run would
measure the old car); R5 requires engine_on+is_owner and emits needs_clear_ground_retest instead of a
one-shot obstacle/drivetrain guess; every verb is checked for timeout/ok (a tool error is NOT a model
fix); R6 is reported uncalibrated.

Lease: the daemon's idle-run fence rejects every /enqueue on a run that has no owner, reads included
(run-lifecycle.md), and a raw /enqueue carries {identity, lease_token} in its body as well as ?key=
(vehicle-smoke.md). Adopt the run with session_acquire_wait from your MCP session first, pass the
identity and lease token it returned, and keep sending session_heartbeat from that session at least
every 90 s while the script runs: the lease lasts 120 s and this script does not renew it.

Usage:
  python run_vehicle_checks.py --vehicle <VehicleClass> --keyfile <dayz-mcp>\\tools\\.dayz_mcp.key \\
      --identity <identity> --lease-token <token> --journal <TargetMod>_dev\\_acceptance\\run_<n>

Pass a new run_<n> folder on each pass (vehicle-acceptance.md, guardrail 3). Without --journal the
verdict goes to ./_acceptance/<vehicle>/verdict.json and the next pass overwrites it.

The key file comes from --keyfile or the DAYZ_MCP_KEYFILE environment variable; there is no default path.
The identity and lease token come from --identity/--lease-token or the DAYZ_MCP_IDENTITY and
DAYZ_MCP_LEASE_TOKEN environment variables.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEF_KEYFILE = os.environ.get("DAYZ_MCP_KEYFILE", "")
DEF_IDENTITY = os.environ.get("DAYZ_MCP_IDENTITY", "")
DEF_LEASE_TOKEN = os.environ.get("DAYZ_MCP_LEASE_TOKEN", "")

# Rejections that waiting cannot cure: the run has no owner, or the lease is gone.
LEASE_ERRORS = ("run_not_owned", "lease_expired", "lease_invalid")

# first_block (MCPBridge.c:589-708) -> known fix anchor (the vehicles pack, skills/_shared/vehicles/).
FIRST_BLOCK_FIX = {
    "": "available",
    "componentNN": "componentNN dual-tag - vehicle-proxies.md 'Hub and seat selections share faces with a component' + rip-structural-lods.md (the DRIVER seat is not enumerated as a collision component)",
    "crew_can_get_through": "bare 'class X: CarScript' inherits Transport.CrewCanGetThrough()=false - fix: extends CarScript override CrewCanGetThrough+GetSeatAnimationType+GetAnimInstance + worldScriptModule (crew-get-in-geometry.md)",
    "area_blocked": "IsAreaAtDoorFree false -> door-area obstruction / door selection",
    "unreachable": "CanReachSeatFromDoors false -> seat<->door geometry, OR car too far from player (move adjacent before concluding a model fix)",
    "occupied": "seat taken -> get out with action_use('ActionGetOutTransport', target='self') or restart the client (test setup state, not a model bug)",
    "item_heavy": "drop the heavy item in hands (test setup state)",
    "already_in_vehicle": "exit the vehicle first (test setup state)",
    "no_component": "you passed component=-1: take a real component from a scene_raycast (partial, never PASS)",
}


def _truthy(v) -> bool:
    """Wire bools may arrive as JSON true OR int 1. Treat both as true."""
    return v is True or v == 1


def _bad(res: dict) -> bool:
    """A verb result that did NOT run cleanly: timed out, or ok is explicitly false/0.
    Absent `ok` is treated as ok (the gate drivers read business fields, not `ok`)."""
    return bool(res.get("_timeout")) or res.get("ok", 1) in (False, 0)


class Daemon:
    """Raw /enqueue + /await against the broker daemon. Mirrors tramoA_gate_driver.Daemon."""

    def __init__(self, port: int, key: str, identity: str, lease_token: str):
        self.base = f"http://127.0.0.1:{port}"
        self.key = key
        self.identity = identity
        self.lease_token = lease_token

    def _req(self, method: str, path: str, query: dict, body: dict | None):
        q = dict(query or {})
        q["key"] = self.key
        url = self.base + path + "?" + urllib.parse.urlencode(q)
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read().decode("utf-8"))
            except Exception:
                return exc.code, {}

    def enqueue(self, cmd: str, args: dict) -> int:
        body = {"cmd": cmd, "args": args, "identity": self.identity, "lease_token": self.lease_token}
        status, payload = self._req("POST", "/enqueue", {}, body)
        if status != 200 or "id" not in payload:
            raise RuntimeError(f"enqueue {cmd} -> {status} {payload}")
        return payload["id"]

    def await_result(self, cmd_id: int, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            status, payload = self._req("GET", "/await", {"id": cmd_id, "remove": "1"}, None)
            if status == 200 and payload.get("status") == "done":
                return payload.get("result", {})
            time.sleep(0.4)
        return {"_timeout": True}

    def run(self, cmd: str, args: dict, timeout: float = 30.0) -> dict:
        res = self.await_result(self.enqueue(cmd, args), timeout)
        print(f"  [{cmd}] -> {json.dumps(res, default=str)[:300]}", flush=True)
        return res


def extract_pos(res: dict):
    for key in ("pos_real", "pos"):
        v = res.get(key)
        if isinstance(v, list) and len(v) == 3:
            return [float(v[0]), float(v[1]), float(v[2])]
    st = res.get("state")
    if isinstance(st, dict) and isinstance(st.get("pos"), list) and len(st["pos"]) == 3:
        return [float(x) for x in st["pos"]]
    return None


def wait_ready(d: Daemon, timeout: float = 180.0):
    print("[acceptance] waiting for server peer + player...", flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            res = d.run("query_player_state", {}, timeout=8)
        except RuntimeError as e:
            if any(code in str(e) for code in LEASE_ERRORS):
                raise RuntimeError(f"the daemon rejected the enqueue ({e}); adopt the run with "
                                   "session_acquire_wait, pass its identity and lease token, and "
                                   "keep sending session_heartbeat") from e
            print(f"  enqueue err {e}", flush=True)
            time.sleep(2.0)
            continue
        if not res.get("_timeout") and res.get("ok", True) and extract_pos(res):
            print(f"[acceptance] player ready @ {extract_pos(res)}", flush=True)
            return extract_pos(res)
        time.sleep(2.5)
    raise RuntimeError("player never became ready")


def ring_components(d: Daemon, car, heights=(0.6, 1.0, 1.3)) -> dict:
    """Raycast a ring at the car center; collect hit components (mirrors tramoB_getin_gate)."""
    cx, cy, cz = car
    comps = {}
    for h in heights:
        for deg in range(0, 360, 30):
            a = math.radians(deg)
            frm = [cx + 3.0 * math.cos(a), cy + h, cz + 3.0 * math.sin(a)]
            rc = d.run("scene_raycast", {"from": frm, "to": [cx, cy + h, cz]}, timeout=15)
            hit = rc.get("raycast") or {}
            if hit.get("hit") and isinstance(hit.get("component"), int):
                comps.setdefault(hit["component"], hit)
    return comps


def run_checks(d, args) -> dict:
    """Drive R1..R6 against daemon `d`. Returns the report dict (does not write it).
    `d` is anything with .run(cmd, args, timeout) -> dict, so a FakeDaemon can drive offline fixtures."""
    R = {"vehicle": args.vehicle, "steps": {}, "fixes": [], "stop": None}

    def fail(step: str, symptom: str, fix: str, hard: bool):
        R["steps"].setdefault(step, {})["PASS"] = False
        R["steps"][step].update({"symptom": symptom, "fix": fix})
        R["fixes"].append({"step": step, "symptom": symptom, "fix": fix})
        print(f"[{step}] FAIL: {symptom}\n        -> FIX: {fix}", flush=True)
        return hard

    ppos = wait_ready(d)

    # ---- Preflight: abort if the player is ALREADY in a vehicle from a prior pass ----
    # vehicle_telemetry resolves the owned car; not-seated -> error="not_seated". A valid pos here =
    # the player is still in some car, so R4 would seat in IT and R5 would measure the WRONG car.
    pre = d.run("vehicle_telemetry", {}, timeout=15)
    if not pre.get("_timeout") and pre.get("error") != "not_seated" and extract_pos(pre) is not None:
        fail("preflight", f"player already seated in a vehicle (prior pass not cleaned up): {json.dumps(pre)[:160]}",
             "get out with action_use('ActionGetOutTransport', target='self') or restart the client before re-running, and spawn one car per run (player_respawn on a living player does nothing). Without this, R5 measures the OLD car while verdict.json names the new spawn.", hard=True)
        R["stop"] = "preflight"
        return R

    # ---- R1 spawns (hard) ----
    print(f"[R1] world_spawn {args.vehicle} @ player {ppos} rot={args.rotation}", flush=True)
    spawn = d.run("world_spawn", {"type": args.vehicle, "pos": ppos, "rotation": args.rotation}, timeout=30)
    car = extract_pos(spawn) or ppos
    # `found` is fail-closed (absent -> R1 fails; the success path always posts found=true).
    if spawn.get("_timeout") or not _truthy(spawn.get("ok")) or not _truthy(spawn.get("found")):
        fail("R1", f"world_spawn returned {json.dumps(spawn)[:160]}",
             "unknown_type/spawn_failed -> mod not mounted / CfgPatches; OR spawned-but-invisible -> componentNN dual-tag (vehicle-proxies.md)", hard=True)
        R["stop"] = "R1"
        return R
    R["steps"]["R1"] = {"PASS": True, "car_pos": car}
    print(f"[R1] PASS car @ {car}", flush=True)

    # ---- R2 collision: raycast presence (objective). Winding/coverage/orient = AGENT visual. ----
    # Solid>=6/12 is a COARSE "collision geometry responds at all" check (catches invisible /
    # no-ViewGeo). It does NOT verify winding or coverage - a half-missing car can still hit ~6. The
    # winding/orient/scale verdict is R2_visual (agent capture), which the script cannot close.
    cx, cy, cz = car
    solid = 0
    for h in (0.4, 0.8, 1.2):
        for ang in (0, 90, 180, 270):
            a = math.radians(ang)
            frm = [cx + 3.5 * math.cos(a), cy + h, cz + 3.5 * math.sin(a)]
            rc = d.run("scene_raycast", {"from": frm, "to": [cx, cy + h, cz]}, timeout=15)
            if (rc.get("raycast") or {}).get("hit"):
                solid += 1
    R["steps"]["R2_collision"] = {"PASS": solid >= 6, "solid_hits": solid, "of": 12}
    R["steps"]["R2_visual"] = {"PASS": None, "note": "AGENT (not scriptable): camera_set(cam_mode='lookat') + capture_screenshot, N angles; judge winding/orient/scale by eye. Required to close acceptance."}
    if solid < 6:
        fail("R2_collision", f"only {solid}/12 raycasts hit the car (no/sparse collision geometry)",
             "missing ViewGeo/FireGeo (vehicle-structural-parity.md) OR winding per-piece (visual-gates-and-winding.md); confirm winding with the visual step", hard=False)
    else:
        print(f"[R2] collision PASS {solid}/12 (winding/coverage = agent visual)", flush=True)

    # ---- R3 get-in diagnostic for the DRIVER seat (soft; does NOT block R4) ----
    # PASS only if the DRIVER seat (crew_index 0) is available. A car where only a PASSENGER
    # seat is reachable but the driver is unreachable is NOT drivable by a human.
    nc = d.run("query_get_in_condition", {"pos": car, "component": -1}, timeout=20).get("get_in") or {}
    partial_ok = bool(nc.get("partial")) and int(nc.get("crew_size", 0) or 0) > 0
    comps = ring_components(d, car)
    print(f"[R3] hit components: {sorted(comps)}", flush=True)
    crew_seats, driver_seat = [], None
    for comp in sorted(comps):
        g = d.run("query_get_in_condition", {"pos": car, "component": comp}, timeout=20).get("get_in") or {}
        cci = g.get("component_crew_index")
        if isinstance(cci, int) and cci >= 0:
            entry = {"component": comp, "crew_index": cci, "available": _truthy(g.get("available")),
                     "first_block": g.get("first_block")}
            crew_seats.append(entry)
            if cci == 0:
                driver_seat = entry
    r3_pass = partial_ok and driver_seat is not None and driver_seat["available"]
    R["steps"]["R3"] = {"PASS": r3_pass, "partial_ok": partial_ok, "crew_seats": crew_seats, "driver_seat": driver_seat}
    if not r3_pass:
        if driver_seat is not None:
            blk = driver_seat["first_block"] or "unknown"
            symptom = f"DRIVER seat (crew_index 0) not available (first_block={blk!r})"
        else:
            blk = "componentNN"
            symptom = "DRIVER seat (crew_index 0) not found among raycast components (seat island / not mapped)"
        if blk not in FIRST_BLOCK_FIX:
            fail("R3", f"driver first_block={blk!r} NOT in known taxonomy", "ESCALATE (guardrail 1)", hard=True)
            R["stop"] = "R3"
            return R
        fail("R3", symptom, FIRST_BLOCK_FIX[blk], hard=False)
    else:
        print("[R3] PASS (driver seat is available)", flush=True)

    # ---- R4_conditioned: server seat + server-side OnDebugSpawn (hard for R5/R6) ----
    # vehicle_get_in_client runs OnDebugSpawn on the client, which does nothing under server authority,
    # and can still report vehicle_fixture_ready=1 with wheel_count=0 and fuel=0 (vehicle-smoke.md).
    # vehicle_enter seats the player on the server; the preparation phase of vehicle_drive runs
    # OnDebugSpawn on the server, and the 0.01 throttle for 0.5 s is negligible. vehicle_drive needs
    # the server seat, so this runs before the owner seat of R4. A spawn without conditioning would
    # read pos_delta ~0 in R5 and look like a drivetrain defect.
    ent = d.run("vehicle_enter", {"pos": car, "timeout_s": 30}, timeout=40)
    drv = d.run("vehicle_drive", {"throttle": 0.01, "duration": 0.5}, timeout=20) \
        if not _bad(ent) and _truthy(ent.get("seated")) else {"ok": False, "error": "not_seated"}
    obj = d.run("telemetry_read", {"mode": "object_at", "type": args.vehicle, "pos": car, "radius": 2},
                timeout=20)
    wheels = obj.get("wheel_count")
    fuel = obj.get("fuel_fraction")
    cond = {"seated_server": ent.get("seated"), "wheel_count": wheels, "fuel_fraction": fuel,
            "expected_wheels": args.wheels}
    if _bad(ent) or not _truthy(ent.get("seated")) or _bad(drv) or _bad(obj) or not _truthy(obj.get("found")):
        R["steps"]["R4_conditioned"] = {"PASS": False, "inconclusive": True, **cond}
        fail("R4_conditioned", f"server seat or conditioning did not run: vehicle_enter={json.dumps(ent)[:120]} "
             f"vehicle_drive={json.dumps(drv)[:120]} telemetry_read found={obj.get('found')}",
             "test setup, not a model fix: retry vehicle_enter with timeout_s=30 and check the server seat with query_player_state", hard=True)
        R["stop"] = "R4_conditioned"
        return R
    r4c_pass = isinstance(wheels, int) and wheels >= args.wheels and float(fuel or 0.0) > 0.0
    R["steps"]["R4_conditioned"] = {"PASS": r4c_pass, **cond}
    if not r4c_pass:
        fail("R4_conditioned", f"after the server-side OnDebugSpawn wheel_count={wheels} (expected {args.wheels}), fuel_fraction={fuel}",
             "wheels missing -> the car's OnDebugSpawn attaches no wheels, or an Axles override lists only one axle "
             "(skills/_shared/vehicles/invariants-wheels-and-hubs.md); fuel 0 -> read telemetry_read again before concluding, "
             "then check that OnDebugSpawn fills the tank", hard=True)
        R["stop"] = "R4_conditioned"
        return R
    print(f"[R4_conditioned] PASS wheel_count={wheels} fuel_fraction={fuel}", flush=True)

    # ---- R4 seated through MCP (hard for R5/R6) ----
    # Fail-closed on the full contract: not timeout, ok, seated, is_owner, vehicle_fixture_ready.
    # vehicle_fixture_ready reflects the client-side conditioning only; R4_conditioned is the real check.
    gi = d.run("vehicle_get_in_client", {"pos": car}, timeout=40)
    r4_pass = (not gi.get("_timeout") and not _bad(gi)
               and _truthy(gi.get("seated")) and _truthy(gi.get("is_owner"))
               and _truthy(gi.get("vehicle_fixture_ready")))
    R["steps"]["R4"] = {"PASS": r4_pass, "seated": gi.get("seated"), "is_owner": gi.get("is_owner"),
                        "fixture_ready": gi.get("vehicle_fixture_ready"), "error": gi.get("error")}
    if not r4_pass:
        fail("R4", f"vehicle_get_in_client did not satisfy seated+is_owner+fixture_ready -> {json.dumps(gi)[:200]}",
             "not seated -> reachability / crew bone-selection / seat anim; not is_owner -> ownership not transferred (StartCommand_Vehicle client-side); not fixture_ready -> client-side OnDebugSpawn (the server-side conditioning already passed in R4_conditioned). See crew-get-in-geometry.md and vehicle-parts-and-start.md", hard=True)
        R["stop"] = "R4"
        return R
    print(f"[R4] PASS seated+owner+fixture", flush=True)

    # ---- R5 drives ----
    eng = d.run("engine_set", {"mode": "start"}, timeout=20)
    t0 = d.run("vehicle_telemetry", {}, timeout=20)
    pos0 = extract_pos(t0)
    ctrl = d.run("vehicle_control",
                 {"throttle": 1.0, "steer": 0.0, "brake": 0.0, "handbrake": 0.0, "hold_ttl_s": args.hold_ttl},
                 timeout=20)
    print(f"[R5] held-drive {args.drive_s}s (no re-call)...", flush=True)
    time.sleep(args.drive_s)
    t1 = d.run("vehicle_telemetry", {}, timeout=20)
    pos1 = extract_pos(t1)

    # A verb that timed out / returned ok:false is a test setup or bridge issue, NOT a model defect.
    if _bad(eng) or _bad(ctrl) or _bad(t0) or _bad(t1):
        R["steps"]["R5"] = {"PASS": False, "inconclusive": True}
        fail("R5", "a drive verb timed out or returned ok:false (test setup or bridge, NOT a model defect)",
             "reconcile bridge_status + retry; do NOT map to a drivetrain/model fix on an inconclusive run", hard=False)
        d.run("vehicle_release", {}, timeout=20)
        return _finish(R, d, args)

    # Defense: the seated car must BE the one we spawned (pos0 near car_pos), else we'd measure
    # the wrong car despite the preflight.
    if pos0 is not None and math.dist(pos0, car) > 8.0:
        R["steps"]["R5"] = {"PASS": False, "inconclusive": True, "seated_pos": pos0, "spawn_pos": car}
        fail("R5", f"seated car @ {pos0} is far from the spawn @ {car} (>8 m) -> measuring the WRONG car",
             "the player is in a different vehicle than the one R1 spawned; restart/cleanup before re-run", hard=False)
        d.run("vehicle_release", {}, timeout=20)
        return _finish(R, d, args)

    speedo = float(t1.get("speedo_max", 0.0) or 0.0)
    gear = t1.get("gear")
    engine_on = _truthy(t1.get("engine_on_server"))
    is_owner = _truthy(t1.get("is_owner"))
    pos_delta = math.dist(pos0, pos1) if (pos0 and pos1) else None
    # Require engine_on + is_owner so gravity/inertia on a dead drivetrain cannot PASS.
    r5_pass = (pos_delta is not None and pos_delta > 1.0 and speedo > 0.0 and engine_on and is_owner)
    R["steps"]["R5"] = {"PASS": r5_pass, "pos_delta": pos_delta, "speedo_max": speedo, "gear": gear,
                        "engine_on_server": engine_on, "is_owner": is_owner}
    if not r5_pass:
        if not (engine_on and is_owner):
            fail("R5", f"precondition broke: engine_on={engine_on} is_owner={is_owner} (pos_delta={pos_delta}, speedo={speedo})",
                 "not a drivetrain defect: engine never started or ownership lost -> re-check R4/engine_set, not the model", hard=False)
        else:
            # Engine on + owner but no motion is AMBIGUOUS (obstacle vs drivetrain). Do NOT emit a
            # one-shot drivetrain fix; require the clear-ground retest as ground-truth.
            R["steps"]["R5"]["verdict"] = "needs_clear_ground_retest"
            hint = f"speedo={speedo} gear={gear}"
            fail("R5", f"engine_on+owner but pos_delta={pos_delta}, speedo={speedo} -> AMBIGUOUS (obstacle vs drivetrain); {hint}",
                 "MANDATORY before any fix: re-run on CLEAR ground (relocate to a site with at least 150 m clear ahead; --rotation is a placement flag and does not set the heading). If it then moves -> was an obstacle (false FAIL). If still ~0 with the engine revving -> wheel sim (FireGeo) wheel-simulation-wiring.md / drivetrain config. Do NOT apply a model fix on this single reading.", hard=False)
    else:
        print(f"[R5] PASS pos_delta={pos_delta:.1f}m speedo={speedo} engine_on owner", flush=True)

    # ---- R6 wheel direction (INFO, UNCALIBRATED: DayZ steer sign not verified vs a vanilla ref) ----
    if r5_pass:
        pa = extract_pos(d.run("vehicle_telemetry", {}, timeout=20))
        c1 = d.run("vehicle_control", {"throttle": 0.6, "steer": 0.0, "hold_ttl_s": args.hold_ttl}, timeout=20)
        time.sleep(1.5)
        pb = extract_pos(d.run("vehicle_telemetry", {}, timeout=20))
        c2 = d.run("vehicle_control", {"throttle": 0.6, "steer": args.steer_left_sign, "hold_ttl_s": args.hold_ttl}, timeout=20)
        time.sleep(2.0)
        pc = extract_pos(d.run("vehicle_telemetry", {}, timeout=20))
        cross = None
        if pa and pb and pc and not (_bad(c1) or _bad(c2)):
            hx, hz = pb[0] - pa[0], pb[2] - pa[2]
            dx, dz = pc[0] - pb[0], pc[2] - pb[2]
            cross = hx * dz - hz * dx  # signed turn in the XZ plane; sign->left/right is UNCALIBRATED
        R["steps"]["R6"] = {"PASS": None, "steer_cmd": args.steer_left_sign, "signed_cross": cross,
                            "calibrated": False,
                            "note": "UNCALIBRATED: the sign->left/right mapping is NOT verified against a vanilla ref. Report signed_cross; do NOT map to a model.cfg wheel `angle`/naming fix (vehicle-proxies.md) on this alone."}
        print(f"[R6] INFO steer={args.steer_left_sign} signed_cross={cross} (UNCALIBRATED; visual=agent)", flush=True)

    d.run("vehicle_release", {}, timeout=20)
    return _finish(R, d, args)


def _finish(R: dict, d, args) -> dict:
    return R


def write_verdict(R: dict, args) -> int:
    stop = R.get("stop")
    # Objective_PASS = the scriptable steps only. Acceptance ALSO needs the agent visual steps
    # (R2_visual, R6 calibration), which this script cannot close -> acceptance_PASS stays None.
    objective = [v.get("PASS") for v in R["steps"].values() if v.get("PASS") is not None]
    R["objective_PASS"] = bool(objective) and all(objective)
    R["acceptance_PASS"] = None
    R["acceptance_note"] = "acceptance requires the agent's visual steps (R2_visual winding/orient/scale, R6 steer calibration); not closeable by this script"
    jdir = Path(args.journal) if args.journal else (Path.cwd() / "_acceptance" / args.vehicle)
    jdir.mkdir(parents=True, exist_ok=True)
    out = jdir / "verdict.json"
    out.write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")
    print(f"\n[acceptance] verdict: {out.resolve()}  objective_PASS={R['objective_PASS']}  stop={stop}", flush=True)
    if R["fixes"]:
        print("[acceptance] batched fixes to apply (one rebuild):", flush=True)
        for f in R["fixes"]:
            print(f"  - {f['step']}: {f['fix']}", flush=True)
    return 0 if R["objective_PASS"] else 2


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyfile", default=DEF_KEYFILE)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--vehicle", required=True, help="classname of the rip-under-test")
    ap.add_argument("--identity", default=DEF_IDENTITY,
                    help="identity from session_acquire_wait (or DAYZ_MCP_IDENTITY); sent in every /enqueue body")
    ap.add_argument("--lease-token", default=DEF_LEASE_TOKEN,
                    help="lease token from session_acquire_wait (or DAYZ_MCP_LEASE_TOKEN); sent in every /enqueue body")
    ap.add_argument("--rotation", type=int, default=0,
                    help="world_spawn rotation: a Central Economy RF_* placement flag passed to CreateObjectEx, "
                         "not a yaw (0 keeps RF_DEFAULT 512; see collision-probes.md)")
    ap.add_argument("--wheels", type=int, default=4, help="wheel_count the conditioned car must report (R4_conditioned)")
    ap.add_argument("--journal", default="", help="dir for verdict.json (default: ./_acceptance/<vehicle>)")
    ap.add_argument("--drive-s", type=float, default=5.0)
    ap.add_argument("--hold-ttl", type=float, default=12.0)
    ap.add_argument("--steer-left-sign", type=float, default=-1.0,
                    help="steer value tried for the LEFT turn (DayZ convention UNVERIFIED; R6 is uncalibrated INFO)")
    return ap


def main() -> int:
    args = build_arg_parser().parse_args()
    # The held-state deadman must outlast the measured window, else the car stops mid-measure.
    min_ttl = args.drive_s + 4.0
    if args.hold_ttl < min_ttl:
        print(f"[warn] hold_ttl {args.hold_ttl} < drive_s+margin {min_ttl}; raising hold_ttl to {min_ttl}", flush=True)
        args.hold_ttl = min_ttl
    if not args.keyfile:
        print("[FAIL] no key file: pass --keyfile or set DAYZ_MCP_KEYFILE (the .dayz_mcp.key of your dayz-mcp checkout)", flush=True)
        return 2
    if not (args.identity and args.lease_token):
        print("[FAIL] no identity or lease token: adopt the run with session_acquire_wait and pass the identity "
              "and lease token it returned (--identity/--lease-token or DAYZ_MCP_IDENTITY/DAYZ_MCP_LEASE_TOKEN)", flush=True)
        return 2
    key = Path(args.keyfile).read_text(encoding="utf-8").strip()
    d = Daemon(args.port, key, args.identity, args.lease_token)
    R = run_checks(d, args)
    return write_verdict(R, args)


if __name__ == "__main__":
    raise SystemExit(main())
