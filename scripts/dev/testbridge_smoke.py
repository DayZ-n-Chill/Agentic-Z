"""In-game smoke test of the dayz-testbridge (plan section 7). Run by hand on a machine with DayZ.

  python scripts/dev/testbridge_smoke.py [--server chernarus] [--port 2302]

Vanilla only, on the storage-free <server>-bridge copy, at the north-west
airfield driving bench near [4200, 0, 10650] (references/vehicle-in-game-facts.md):
twelve steps from session start to stop, then four negative controls that
must each come back refused. PASS needs every step and every control. The
report, with the run's -mod= line (references/in-game-check-validity.md), is
written to output/in-game-test-tool/smoke-<stamp>.json under the project.
The session is always stopped, and a session this script did not start is
never touched (session_start refuses to run next to one).

Exit codes: 0 PASS, 1 FAIL, 2 the session could not start.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / ".claude" / "mcp" / "dayz-testbridge"))
import bridge  # noqa: E402
import session  # noqa: E402
import window_capture  # noqa: E402

BENCH = [4200.0, 0.0, 10650.0]
CAR_CLASS = "Hatchback_02"
WRONG_TOKEN = "0" * 32


class Smoke:
    def __init__(self, project: Path, rt: session.Runtime):
        self.project, self.rt = project, rt
        self.steps: list[dict] = []
        self.b: bridge.Bridge | None = None
        self.state: dict = {}

    def step(self, name: str, fn) -> object:
        """Run one check; a failed assertion or an error marks the step FAIL and the run goes on."""
        entry = {"step": name, "result": "PASS"}
        try:
            entry["detail"] = fn()
        except AssertionError as e:
            entry.update(result="FAIL", detail=str(e))
        except Exception as e:  # noqa: BLE001 - one broken step must not hide the rest
            entry.update(result="FAIL", detail=f"{type(e).__name__}: {e}")
        print(f"[{entry['result']}] {name}: {json.dumps(entry.get('detail'), default=str)[:300]}", flush=True)
        self.steps.append(entry)
        return entry.get("detail")

    def call(self, cmd, args=None, peer=None):
        res = self.b.call(cmd, args, peer)
        session.remember(self.project, self.state, self.b)
        return res

    def ok(self, cmd, args=None, peer=None) -> dict:
        res = self.call(cmd, args, peer)
        assert res["ok"], f"{cmd} refused: {res['error']}"
        return res["data"]


def flat(a, b) -> float:
    return math.dist((a[0], a[2]), (b[0], b[2]))


def run(project: Path, server: str, port: int) -> dict:
    rt = session.real_runtime()
    report = {"started": datetime.now().isoformat(timespec="seconds"), "server": server, "steps": [], "controls": []}
    smoke = Smoke(project, rt)
    try:
        started = session.start(project, [], server=server, port=port, rt=rt)
    except session.SessionError as e:
        report.update(verdict="ERROR", error=str(e))
        return report
    report["mod_line"] = started["mod_line"]
    report["token"] = started["token"]
    smoke.state = session.load_state(project)
    smoke.b = session.bridge_of(project, smoke.state, rt)
    car: dict = {}
    try:
        def s1():
            pings = {p: smoke.ok("ping", peer=p) for p in ("server", "client")}
            assert pings["client"]["player_loaded"] and pings["server"]["player_count"] == 1, pings
            session.mark(project, "smoke", rt)
            return pings
        smoke.step("1 session, ping both peers, mark", s1)

        def s2():
            t = smoke.ok("set_time", {"year": 2026, "month": 6, "day": 21, "hour": 12, "minute": 0})
            w = smoke.ok("set_weather", {"overcast": 1.0, "fog": 0.0, "rain": 0.0, "wind": 0.0})
            assert t["hour"] == 12, t
            assert w["overcast"] >= 0.9 and w["rain"] <= 0.1, w
            return {"time": t, "weather": w}
        smoke.step("2 noon and full overcast, read back", s2)

        def s3():
            d = smoke.ok("teleport", {"pos": BENCH})
            assert flat(d["pos"], BENCH) < 2.0, d
            return d
        smoke.step("3 teleport to the bench", s3)

        def c4():
            res = smoke.call("drive", {"throttle": 1.0, "seconds": 1})
            assert not res["ok"] and res["error"] == "not_driver", res
            return res["error"]
        report["controls"].append({"control": "drive on foot is refused", **_control(c4)})

        def s4():
            spot = [BENCH[0], 0.0, BENCH[2] + 12.0]
            d = smoke.ok("spawn", {"cls": CAR_CLASS, "pos": spot})
            car.update(d)
            p = smoke.ok("vehicle_prepare", {"net_id": d["net_id"], "engine_on": True})
            car["entry_pos"] = p["entry_pos"]
            assert d["type"] == CAR_CLASS, d
            assert p["wheels_present"] == 4 and p["fuel"] > 0, p
            return {"spawn": d, "prepare": p}
        smoke.step("4 spawn Hatchback_02, prepare: 4 wheels and fuel", s4)

        def s5():
            assert car.get("net_id"), "no car"
            entry = car.get("entry_pos") or car["pos"]
            smoke.ok("teleport", {"pos": entry})
            res = smoke.call("get_in", {"net_id": car["net_id"], "seat": 0})
            assert res["ok"] and res["data"]["seated"], res
            server = smoke.ok("player_state")
            assert server["in_vehicle"] and server["seat"] == 0, server
            return {"client": res["data"], "server": server}
        smoke.step("5 get in as driver, seated on both peers", s5)

        def s6():
            d = smoke.ok("drive", {"throttle": 1.0, "seconds": 5})
            assert d["top_speed"] > 10 and d["distance"] > 10, {k: d[k] for k in ("top_speed", "distance")}
            return {"top_speed": d["top_speed"], "distance": d["distance"], "samples": len(d["samples"]),
                    "gears": sorted({s["gear"] for s in d["samples"]})}
        smoke.step("6 drive 5 s at full throttle", s6)

        def s7():
            smoke.ok("get_out")
            on_foot = smoke.ok("player_state")
            assert not on_foot["in_vehicle"], on_foot
            st = smoke.ok("object_state", {"net_id": car["net_id"]})
            car["pos"] = st["pos"]
            x, y, z = st["pos"]
            view = smoke.ok("raycast", {"from": [x, y + 10, z], "to": [x, y - 2, z], "mode": "view"})["hits"]
            bullet = smoke.ok("raycast", {"from": [x, y + 10, z], "to": [x, y - 2, z], "mode": "bullet"})["hits"]
            beside = smoke.ok("raycast", {"from": [x + 8, y + 10, z], "to": [x + 8, y - 5, z], "mode": "view"})["hits"]
            surf = smoke.ok("surface", {"x": x, "z": z})
            assert any(h["net_id"] == car["net_id"] for h in view or []), f"view ray missed the car: {view}"
            assert any(h["net_id"] == car["net_id"] for h in bullet or []), f"bullet ray missed the car: {bullet}"
            assert any(h["terrain"] for h in beside or []), f"no terrain beside the car: {beside}"
            assert surf["surface"], surf
            return {"view": view, "bullet": bullet, "beside": beside, "surface": surf}
        smoke.step("7 get out, rays at the car and beside it, surface", s7)

        def s8():
            from PIL import Image, ImageChops, ImageStat

            x, y, z = car["pos"]
            pid = smoke.state["pids"]["client"]
            folder = project / "output" / "in-game-test-tool"
            folder.mkdir(parents=True, exist_ok=True)
            before = folder / f"smoke-{report['token'][:8]}-player-view.png"
            out = folder / f"smoke-{report['token'][:8]}-top-down.png"
            window_capture.capture_window(pid, before)
            smoke.ok("hud", {"show": False})
            smoke.ok("camera_set", {"pos": [x + 3, y + 16, z], "look_at": [x, y + 0.5, z]})
            time.sleep(3)  # let the client draw a few frames from the new camera before the grab
            size = window_capture.capture_window(pid, out)
            with Image.open(before) as a, Image.open(out) as b:
                change = sum(ImageStat.Stat(ImageChops.difference(a.convert("L"), b.convert("L"))).mean)
            # A camera that never took the view leaves the player's own view: nearly the same frame.
            assert change > 10, f"the frame barely changed (mean difference {change:.1f} of 255): the camera did not take the view"
            return {"png": str(out), "size": size, "mean_change": round(change, 1)}
        smoke.step("8 camera 16 m above the car, screenshot not black and not the player's view", s8)

        def s9():
            smoke.ok("hud", {"show": True})
            return smoke.ok("camera_reset")
        smoke.step("9 camera back to the player", s9)

        def s10():
            d = smoke.ok("delete", {"net_id": car["net_id"]})
            near = smoke.ok("find_objects", {"pos": car["pos"], "radius": 10, "cls": CAR_CLASS})["objects"]
            assert d["removed"] and not [o for o in near if o["net_id"] == car["net_id"]], near
            return {"removed": d["removed"], "left_nearby": near}
        smoke.step("10 delete the car, confirm with find_objects", s10)

        def c_unknown():
            res = smoke.b.send("server", {"cmd": "teleport_everyone", "args": {}}, 15)
            assert not res["ok"] and res["error"] == "unknown_command", res
            return res["error"]
        report["controls"].append({"control": "unknown command is refused by the mod", **_control(c_unknown)})

        def c_class():
            res = smoke.call("spawn", {"cls": "AZB_NoSuchCar", "pos": BENCH})
            assert not res["ok"] and res["error"] == "spawn_failed", res
            return res["error"]
        report["controls"].append({"control": "spawn of an invented class fails", **_control(c_class)})

        def c_token():
            res = smoke.b.send("server", {"cmd": "spawn", "args": {**bridge.allowlist.wire_args(
                "spawn", {"cls": CAR_CLASS, "pos": BENCH})}}, 15, token=WRONG_TOKEN)
            assert not res["ok"] and res["error"] == "wrong_token", res
            near = smoke.ok("find_objects", {"pos": BENCH, "radius": 15, "cls": CAR_CLASS})["objects"]
            assert not near, f"a car exists after the wrong-token spawn: {near}"
            return res["error"]
        report["controls"].append({"control": "a command with the wrong token is never run", **_control(c_token)})

        def s11():
            got = session.logs_since(project, "smoke", kinds=("script",))
            marks = [ln for ln in got["lines"] if "[AZ-BRIDGE] MARK smoke" in ln["text"]]
            assert not got["bridge_errors"], got["bridge_errors"]
            return {"lines": len(got["lines"]), "marks_seen": len(marks), "bridge_errors": 0}
        smoke.step("11 logs since the mark: no bridge errors", s11)
    except Exception:  # noqa: BLE001
        report["crash"] = traceback.format_exc()
    finally:
        stopped = session.stop(project, rt)
        smoke.steps.append({"step": "12 stop the session", "result": "PASS" if stopped["stopped"] else "FAIL",
                            "detail": stopped})
        print(f"[{smoke.steps[-1]['result']}] 12 stop the session", flush=True)
    report["steps"] = smoke.steps
    all_ok = all(s["result"] == "PASS" for s in smoke.steps) and all(c["result"] == "PASS" for c in report["controls"])
    report["verdict"] = "PASS" if all_ok and len(report["controls"]) == 4 and "crash" not in report else "FAIL"
    return report


def _control(fn) -> dict:
    try:
        return {"result": "PASS", "detail": fn()}
    except AssertionError as e:
        return {"result": "FAIL", "detail": str(e)}
    except Exception as e:  # noqa: BLE001
        return {"result": "FAIL", "detail": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--server", default="chernarus")
    ap.add_argument("--port", type=int, default=2302)
    args = ap.parse_args()
    project = session.h.resolve_project_dir()
    report = run(project, args.server, args.port)
    out = project / "output" / "in-game-test-tool" / f"smoke-{datetime.now():%Y-%m-%d_%H-%M-%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    for c in report.get("controls", []):
        print(f"[{c['result']}] control: {c['control']}: {c['detail']}")
    print(f"{report['verdict']} (report: {out})")
    print(f"-mod={report.get('mod_line', '')}")
    return {"PASS": 0, "FAIL": 1}.get(report["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
