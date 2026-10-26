"""Tests for the visual gate: shots file, perceptual compare, baselines and gate.py visual.

Fixture images live in fixtures/visual/: baseline/ holds the expected look,
run_pass/ the same screens with render noise, run_fail/ a HUD whose icon is
gone. Nothing launches DayZ or grabs the screen: the full run uses a fake
runtime whose capture function copies fixture images.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "visual"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load("dayz_gate_visual_gate_under_test", HERE / "gate.py")
visual = gate.visual

SHOTS = json.loads((FIXTURES / "visual-shots.json").read_text(encoding="utf-8"))
SPEC = visual.validate_shots(SHOTS)
READY = r"SCRIPT       : Creating Mission: mpmissions\__cur_mp.chernarusplus\mission.c"


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project with a mod, the shots file and the fixture baselines."""
    proj = tmp_path / "proj"
    mod = proj / "workspace" / "MyMod"
    mod.mkdir(parents=True)
    (mod / "config.cpp").write_text(
        "class CfgPatches\n{\n\tclass MyMod\n\t{\n\t\trequiredAddons[] = {\"DZ_Data\"};\n\t};\n};\n", encoding="utf-8"
    )
    (proj / ".server" / "chernarus" / "Profiles").mkdir(parents=True)
    (proj / ".server" / "!ClientDiagLogs").mkdir(parents=True)
    plan = proj / "output" / "MyMod-plan"
    plan.mkdir(parents=True)
    shutil.copy2(FIXTURES / "visual-shots.json", plan / "visual-shots.json")
    shutil.copytree(FIXTURES / "baseline", proj / "output" / "MyMod-visual" / "baseline")
    monkeypatch.setattr(gate.h, "resolve_project_dir", lambda: proj)
    return proj


def run_dir_from(project: Path, source: str, stamp: str = "2026-10-21_12-00-00") -> Path:
    run = project / "output" / "MyMod-visual" / "runs" / stamp
    shutil.copytree(FIXTURES / source, run)
    return run


def run_main(argv, capsys, rt=None):
    rc = gate.main(argv, rt)
    out = capsys.readouterr().out
    first, _, rest = out.partition("\n")
    return rc, first, json.loads(rest) if "--json" in argv else rest


# --- shots file ---------------------------------------------------------------------

def test_fixture_shots_file_is_valid():
    assert [s["id"] for s in SPEC["shots"]] == ["hud", "menu"]
    # last_shot_at counts from the client joining: the last shot's 30 s plus the helper's settle time
    assert SPEC["threshold"] == 0.01 and visual.last_shot_at(SPEC) == 30 + visual.SCENE_SETTLE_S


@pytest.mark.parametrize("change, message", [
    (lambda d: d.update(shots=[]), "at least one shot"),
    (lambda d: d.update(extra=1), "unknown keys"),
    (lambda d: d["shots"][0].update(id="has space"), "id must be"),
    (lambda d: d["shots"][1].update(id="hud"), "duplicate id"),
    (lambda d: d["shots"][0].pop("at"), "at must be"),
    (lambda d: d["shots"][0].update(at=-1), "at must be"),
    (lambda d: d["shots"][0].update(threshold=2), "threshold must be"),
    (lambda d: d.update(threshold="1%"), "threshold must be"),
    (lambda d: d["shots"][0].update(ignore=[[0, 0, 0, 5]]), "ignore must be"),
    (lambda d: d["shots"][0].update(ignore=[0, 0, 5, 5]), "ignore must be"),
    (lambda d: d["shots"][0].update(colour="red"), "unknown keys"),
])
def test_bad_shots_files_are_refused(change, message):
    data = copy.deepcopy(SHOTS)
    change(data)
    with pytest.raises(visual.VisualError, match=message):
        visual.validate_shots(data)


def test_missing_shots_file_names_the_path(tmp_path):
    with pytest.raises(visual.VisualError, match="no shots file"):
        visual.load_shots(tmp_path / "visual-shots.json")


# --- compare --------------------------------------------------------------------------

def test_identical_images_pass_with_no_changed_pixels(tmp_path):
    base = FIXTURES / "baseline" / "hud.png"
    r = visual.compare_images(base, base, tmp_path / "d.png")
    assert (r["status"], r["changed"], r["ratio"]) == ("PASS", 0, 0.0)


def test_render_noise_passes(tmp_path):
    r = visual.compare_images(FIXTURES / "baseline" / "hud.png", FIXTURES / "run_pass" / "hud.png", tmp_path / "d.png")
    assert r["status"] == "PASS" and r["ratio"] < 0.001
    assert r["compared"] == 320 * 180


def test_missing_icon_fails_and_the_diff_marks_it_red(tmp_path):
    diff = tmp_path / "hud.diff.png"
    r = visual.compare_images(FIXTURES / "baseline" / "hud.png", FIXTURES / "run_fail" / "hud.png", diff)
    assert r["status"] == "FAIL" and r["changed"] == 30 * 30
    assert "1.56% of pixels differ (threshold 1.00%)" == r["reason"]
    with Image.open(diff) as img:
        assert img.size == (320, 180)
        assert img.getpixel((155, 155)) == (255, 0, 0)  # inside the icon
        assert img.getpixel((20, 20))[0] == img.getpixel((20, 20))[1]  # untouched: grey


def test_a_higher_threshold_lets_the_change_pass(tmp_path):
    r = visual.compare_images(FIXTURES / "baseline" / "hud.png", FIXTURES / "run_fail" / "hud.png", tmp_path / "d.png", threshold=0.02)
    assert r["status"] == "PASS" and r["changed"] == 900


def test_ignored_area_is_left_out_and_drawn_blue(tmp_path):
    diff = tmp_path / "d.png"
    r = visual.compare_images(FIXTURES / "baseline" / "hud.png", FIXTURES / "run_fail" / "hud.png", diff, ignore=[[135, 135, 40, 40]])
    assert (r["status"], r["changed"], r["compared"]) == ("PASS", 0, 320 * 180 - 40 * 40)
    with Image.open(diff) as img:
        red, green, blue = img.getpixel((150, 150))
        assert blue == 255 and red < 255


def test_size_mismatch_fails_without_a_diff(tmp_path):
    r = visual.compare_images(FIXTURES / "baseline" / "hud.png", FIXTURES / "hud_small.png", tmp_path / "d.png")
    assert (r["status"], r["diff"]) == ("FAIL", None)
    assert r["reason"] == "capture is 160x90, baseline 320x180"
    assert not (tmp_path / "d.png").exists()


def test_large_captures_are_shrunk_so_pixel_noise_averages_out(tmp_path):
    flat = Image.new("RGB", (1280, 720), (120, 120, 120))
    checker = flat.copy()
    for y in range(0, 720, 2):  # 2 x 2 blocks: each holds two pixels 60 brighter and two 60 darker
        for x in range(0, 1280, 2):
            checker.putpixel((x, y), (180, 180, 180))
            checker.putpixel((x + 1, y + 1), (180, 180, 180))
            checker.putpixel((x + 1, y), (60, 60, 60))
            checker.putpixel((x, y + 1), (60, 60, 60))
    flat.save(tmp_path / "a.png")
    checker.save(tmp_path / "b.png")
    r = visual.compare_images(tmp_path / "a.png", tmp_path / "b.png", tmp_path / "d.png")
    assert r["status"] == "PASS" and r["compared"] == 640 * 360
    with Image.open(tmp_path / "d.png") as img:
        assert img.size == (1280, 720)  # drawn back at the capture's size


def test_compare_run_statuses_and_threshold_order(tmp_path):
    run = tmp_path / "run"
    shutil.copytree(FIXTURES / "run_fail", run)
    base = tmp_path / "base"
    base.mkdir()
    shutil.copy2(FIXTURES / "baseline" / "hud.png", base / "hud.png")
    results = {r["id"]: r for r in visual.compare_run(SPEC, run, base)}
    assert results["hud"]["status"] == "FAIL" and results["hud"]["threshold"] == 0.01
    assert results["hud"]["diff"] == run / "hud.diff.png"
    assert results["menu"]["status"] == "NEW"
    # --threshold beats the file's; a shot's own beats both
    assert visual.compare_run(SPEC, run, base, threshold=0.05)[0]["status"] == "PASS"
    spec = copy.deepcopy(SPEC)
    spec["shots"][0]["threshold"] = 0.001
    assert visual.compare_run(spec, run, base, threshold=0.05)[0]["status"] == "FAIL"
    (run / "hud.png").unlink()
    missing = visual.compare_run(SPEC, run, base, errors={"hud": "capture failed: no window"})[0]
    assert (missing["status"], missing["reason"]) == ("MISSING", "capture failed: no window")


# --- gate.py visual --compare / --accept -----------------------------------------------------

def test_compare_mode_pass(project, capsys):
    run = run_dir_from(project, "run_pass")
    rc, first, data = run_main(["visual", "MyMod", "--compare", str(run), "--json"], capsys)
    assert (rc, first, data["verdict"], data["mode"]) == (0, "PASS", "PASS", "visual")
    assert [s["status"] for s in data["shots"]] == ["PASS", "PASS"]
    assert data["shots"][0]["diff"] == str(Path("output/MyMod-visual/runs/2026-10-21_12-00-00/hud.diff.png"))
    assert (run / "hud.diff.png").is_file() and (run / "menu.diff.png").is_file()


def test_compare_mode_fail_is_known_and_owned_by_the_user(project, capsys):
    run_dir_from(project, "run_fail")
    rc, first, data = run_main(["visual", "MyMod", "--compare", "--json"], capsys)  # no folder: the newest run
    assert (rc, first) == (1, "FAIL")
    [failure] = data["failures"]
    assert (failure["category"], failure["shot"]) == ("visual", "hud")
    assert failure["text"] == "[visual:diff] hud: 1.56% of pixels differ (threshold 1.00%)"
    assert (failure["triage"]["status"], failure["triage"]["id"], failure["triage"]["owner_agent"]) == ("known", "visual-diff", "user")
    assert any(c.startswith("diff: ") and c.endswith("hud.diff.png") for c in failure["context"])


def test_compare_mode_text_lists_each_shot(project, capsys):
    run_dir_from(project, "run_fail")
    rc, first, text = run_main(["visual", "MyMod", "--compare"], capsys)
    assert rc == 1 and first == "FAIL"
    assert "  FAIL hud  1.56% of pixels differ (threshold 1.00%)" in text
    assert "  PASS menu  0.00% of pixels differ" in text
    assert "known visual-diff -> user" in text


def test_compare_mode_without_baseline_or_capture(project, capsys):
    run = run_dir_from(project, "run_pass")
    (project / "output" / "MyMod-visual" / "baseline" / "menu.png").unlink()
    (run / "hud.png").unlink()
    rc, first, data = run_main(["visual", "MyMod", "--compare", str(run), "--json"], capsys)
    assert (rc, first) == (1, "FAIL")
    assert {f["shot"]: f["triage"]["id"] for f in data["failures"]} == {"hud": "visual-no-capture", "menu": "visual-no-baseline"}


def test_compare_mode_errors(project, capsys):
    rc, first, _ = run_main(["visual", "MyMod", "--compare"], capsys)  # no runs yet
    assert (rc, first) == (2, "ERROR")
    run_dir_from(project, "run_pass")
    rc, first, _ = run_main(["visual", "Other", "--compare"], capsys)  # no shots file for Other
    assert (rc, first) == (2, "ERROR")
    rc, first, _ = run_main(["visual", "MyMod", "--compare", "--threshold", "5"], capsys)
    assert (rc, first) == (2, "ERROR")


def test_accept_makes_a_failing_capture_the_baseline_and_keeps_the_old_one(project, capsys):
    run = run_dir_from(project, "run_fail")
    base = project / "output" / "MyMod-visual" / "baseline" / "hud.png"
    old = base.read_bytes()
    rc, first, data = run_main(["visual", "MyMod", "--accept", str(run), "--shot", "hud", "--replace-failed", "--json"], capsys)
    assert (rc, first, data["shots"]) == (0, "ACCEPTED", ["hud"])
    assert base.read_bytes() == (run / "hud.png").read_bytes()
    [backup] = (base.parent / ".prev").glob("hud.*.png")
    assert backup.read_bytes() == old
    assert data["backups"] == {"hud": str(backup.relative_to(project))}
    rc, first, _ = run_main(["visual", "MyMod", "--compare", str(run)], capsys)
    assert (rc, first) == (0, "PASS")


def test_accept_refuses_a_failing_capture_without_replace_failed(project, capsys):
    run = run_dir_from(project, "run_fail")
    base_dir = project / "output" / "MyMod-visual" / "baseline"
    before = {p.name: p.read_bytes() for p in base_dir.iterdir()}
    for argv in (["--accept", str(run)], ["--accept", str(run), "--shot", "hud"], ["--accept"]):
        rc, first, rest = run_main(["visual", "MyMod", *argv], capsys)
        assert (rc, first) == (2, "ERROR"), argv
        assert "hud (1.56% of pixels differ" in rest and "--replace-failed" in rest
        # nothing is copied, not even menu, whose capture passes
        assert {p.name: p.read_bytes() for p in base_dir.iterdir()} == before
    # the shot's compare uses --threshold like the gate does, so a looser one lets it through
    rc, first, _ = run_main(["visual", "MyMod", "--accept", str(run), "--threshold", "0.05"], capsys)
    assert (rc, first) == (0, "ACCEPTED")


def test_replace_failed_needs_accept_and_shot(project, capsys):
    run = run_dir_from(project, "run_fail")
    for argv in (["--accept", str(run), "--replace-failed"], ["--compare", str(run), "--replace-failed"]):
        rc, first, rest = run_main(["visual", "MyMod", *argv], capsys)
        assert (rc, first) == (2, "ERROR") and "--replace-failed works with --accept --shot" in rest


def test_accept_backs_up_every_replaced_baseline(project, capsys):
    run = run_dir_from(project, "run_pass")
    base_dir = project / "output" / "MyMod-visual" / "baseline"
    old = {i: (base_dir / f"{i}.png").read_bytes() for i in ("hud", "menu")}
    (base_dir / "menu.png").unlink()  # menu is NEW: nothing to back up
    rc, first, text = run_main(["visual", "MyMod", "--accept", str(run)], capsys)
    assert (rc, first) == (0, "ACCEPTED")
    assert "previous hud kept at" in text and "previous menu" not in text
    [backup] = (base_dir / ".prev").iterdir()
    assert backup.name.startswith("hud.") and backup.read_bytes() == old["hud"]
    assert (base_dir / "menu.png").read_bytes() == (run / "menu.png").read_bytes()
    # a second accept keeps both earlier versions of hud
    result = visual.accept(SPEC, run, base_dir, ["hud"])
    assert result["accepted"] == ["hud"] and len(list((base_dir / ".prev").glob("hud.*.png"))) == 2


def test_accept_without_shot_names_the_shots_it_skipped(project, capsys):
    run = run_dir_from(project, "run_pass")
    base_dir = project / "output" / "MyMod-visual" / "baseline"
    old_menu = (base_dir / "menu.png").read_bytes()
    (run / "menu.png").unlink()  # menu was never captured
    rc, first, data = run_main(["visual", "MyMod", "--accept", str(run), "--json"], capsys)
    assert (rc, first, data["shots"], data["skipped"]) == (0, "ACCEPTED", ["hud"], ["menu"])
    assert (base_dir / "menu.png").read_bytes() == old_menu
    rc, first, text = run_main(["visual", "MyMod", "--accept", str(run)], capsys)
    assert (rc, first) == (0, "ACCEPTED")
    assert "skipped, no capture in" in text and "menu (baseline unchanged)" in text
    # nothing skipped: no skipped line, and an empty list in --json
    shutil.copy2(FIXTURES / "run_pass" / "menu.png", run / "menu.png")
    rc, first, text = run_main(["visual", "MyMod", "--accept", str(run)], capsys)
    assert rc == 0 and "skipped" not in text
    rc, first, data = run_main(["visual", "MyMod", "--accept", str(run), "--json"], capsys)
    assert data["skipped"] == []


def test_accept_refuses_unknown_shots_and_empty_runs(project, capsys):
    run = run_dir_from(project, "run_pass")
    rc, first, _ = run_main(["visual", "MyMod", "--accept", str(run), "--shot", "nope"], capsys)
    assert (rc, first) == (2, "ERROR")
    for png in run.glob("*.png"):
        png.unlink()
    rc, first, _ = run_main(["visual", "MyMod", "--accept"], capsys)
    assert (rc, first) == (2, "ERROR")
    rc, first, rest = run_main(["visual", "MyMod", "--accept", str(project / "nowhere")], capsys)
    assert (rc, first) == (2, "ERROR") and "no folder" in rest


# --- full run with a fake session and capture -----------------------------------------------

class FakeSession:
    """No DayZ: the fake launch writes the client ready line; the fake capture copies fixture images."""

    def __init__(self, project: Path, source: str = "run_pass", fail_capture: bool = False, ready_line: str = READY,
                 scene: bool = True):
        self.project = project
        self.scene = scene  # whether the helper's SCENE and CAMERA lines appear
        self.helper: list[str] = []  # "install" / "remove", in order
        self.ready_line = ready_line
        self.source = source
        self.fail_capture = fail_capture
        self.calls: list[list[str]] = []
        self.captures: list[tuple[float, int, str]] = []
        self.running: list[int] = []
        self.now = 0.0

    def runtime(self):
        return gate.Runtime(run=self.run, diag_pids=lambda: list(self.running), pid_alive=lambda p: p in self.running,
                            sleep=self.sleep, clock=lambda: self.now, capture=self.capture,
                            install_helper=lambda: self.helper.append("install"),
                            remove_helper=lambda: self.helper.append("remove"))

    def run(self, cmd: list[str]) -> tuple[int, str]:
        self.calls.append(cmd)
        joined = " ".join(cmd)
        if "stop_test.bat" in joined:
            self.running = []
            return 0, "SUCCESS"
        assert "launch.py" in joined, cmd
        self.running = [111, 222]
        server = self.project / ".server" / "chernarus" / "Profiles"
        client = self.project / ".server" / "!ClientDiagLogs"
        (server / "DayZDiag_x64_2026-10-21_12-00-00.RPT").write_text("CLI params: server mod P:\\Mods\\@MyMod\n", encoding="utf-8")
        assert visual.HELPER_NAME in cmd and self.helper == ["install"], (cmd, self.helper)
        client_lines = [self.ready_line]
        if self.scene:
            (server / "script_2026-10-21_12-00-05.log").write_text(
                "SCRIPT       : [AZ-VISUAL] SCENE noon, clear weather, no wind\n", encoding="utf-8")
            client_lines.append("SCRIPT       : [AZ-VISUAL] CAMERA <7680, 346, 7680> facing north")
        (client / "script_2026-10-21_12-00-31.log").write_text("\n".join(client_lines) + "\n", encoding="utf-8")
        return 0, "[OK]    Server PID: 111\n[OK]    Client PID: 222\n"

    def capture(self, pid: int, out: Path) -> None:
        self.captures.append((self.now, pid, out.name))
        if self.fail_capture:
            raise visual.VisualError(f"DayZ client PID {pid} has no visible window")
        shutil.copy2(FIXTURES / self.source / out.name, out)

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_full_run_captures_each_shot_at_its_second_and_passes(project, capsys):
    fake = FakeSession(project)
    rc, first, data = run_main(["visual", "MyMod", "--json"], capsys, fake.runtime())
    assert (rc, first) == (0, "PASS"), data["failures"]
    assert [(pid, name) for _, pid, name in fake.captures] == [(222, "hud.png"), (222, "menu.png")]
    # The ready line was read at 0 s; each shot waits the helper's settle time on top of its own second,
    # and is taken on the first poll at or after that.
    settle = visual.SCENE_SETTLE_S
    for (t, _, _), due in zip(fake.captures, [20 + settle, 30 + settle]):
        assert due <= t < due + gate.POLL_S
    # Stopped soon after the last shot: one poll to notice, one for the stop, one of poll rounding.
    assert fake.now < visual.last_shot_at(SPEC) + 3 * gate.POLL_S and fake.running == []
    assert fake.helper == ["install", "remove"]  # loaded for the session only
    assert data["steps"][0]["step"] == "helper"
    run = project / data["visual"]["run"]
    assert (run / "hud.png").is_file() and (run / "hud.diff.png").is_file()


def test_full_run_fails_on_a_changed_screen(project, capsys):
    fake = FakeSession(project, "run_fail")
    rc, first, data = run_main(["visual", "MyMod", "--json"], capsys, fake.runtime())
    assert (rc, first) == (1, "FAIL")
    assert [f["shot"] for f in data["failures"]] == ["hud"]


def test_full_run_capture_failure_is_a_missing_shot(project, capsys):
    fake = FakeSession(project, fail_capture=True)
    rc, first, data = run_main(["visual", "MyMod", "--json"], capsys, fake.runtime())
    assert (rc, first) == (1, "FAIL")
    assert {f["triage"]["id"] for f in data["failures"]} == {"visual-no-capture"}
    assert data["shots"][0]["reason"] == "capture failed: DayZ client PID 222 has no visible window"


def test_full_run_uses_the_ready_pattern(project, capsys):
    fake = FakeSession(project, ready_line="SCRIPT : [MyMod] ready")
    rc, first, data = run_main(["visual", "MyMod", "--json", "--ready-pattern", r"\[MyMod\] ready"],
                               capsys, fake.runtime())
    assert (rc, first) == (0, "PASS"), data["failures"]
    assert data["ready"]["text"] == "SCRIPT : [MyMod] ready"


def test_shot_without_accept_is_refused(project, capsys):
    fake = FakeSession(project)
    rc, first, rest = run_main(["visual", "MyMod", "--shot", "hud"], capsys, fake.runtime())
    assert (rc, first) == (2, "ERROR")
    assert "--shot works with --accept only" in rest
    assert fake.calls == []


def test_full_run_without_shots_file_is_an_error(project, capsys):
    (project / "output" / "MyMod-plan" / "visual-shots.json").unlink()
    fake = FakeSession(project)
    rc, first, _ = run_main(["visual", "MyMod"], capsys, fake.runtime())
    assert (rc, first) == (2, "ERROR")
    assert fake.calls == []


def test_full_run_without_the_helper_scene_fails(project, capsys):
    fake = FakeSession(project, scene=False)
    rc, first, data = run_main(["visual", "MyMod", "--json"], capsys, fake.runtime())
    assert (rc, first) == (1, "FAIL")
    assert sum("[visual:no-scene]" in f["text"] for f in data["failures"]) == 2  # server and client
    assert fake.helper == ["install", "remove"]


def test_helper_is_removed_even_when_the_launch_fails(project, capsys):
    fake = FakeSession(project)
    original = fake.run

    def failing(cmd):
        if "launch.py" in " ".join(cmd):
            fake.calls.append(cmd)
            return 1, "[FAIL]  Steam is not running.\n"
        return original(cmd)

    fake.run = failing
    rc, first, data = run_main(["visual", "MyMod", "--json"], capsys, fake.runtime())
    assert rc == 1 and fake.helper == ["install", "remove"]


def test_capturer_marks_shots_the_session_never_reached(tmp_path):
    taken = []
    cap = visual.Capturer(SPEC["shots"], tmp_path, lambda pid, out: taken.append(out.name))
    cap(None, 222)
    cap(25, 222)
    cap.finish()
    assert taken == ["hud.png"]
    assert cap.errors == {"menu": "not captured: the session ended before 30 s after the client joined"}


def test_the_real_capture_is_the_default():
    rt = gate.real_runtime()
    assert rt.capture is visual.capture_window
    assert sys.platform != "win32" or callable(visual.capture_window)


class _NoShcore:
    def SetProcessDpiAwareness(self, level):
        raise OSError("no shcore")


class _FakeUser32:
    """Just enough of user32 for the background capture: one visible client window.

    It has no SetForegroundWindow, SetCursorPos or keybd_event, so a capture
    that tried to take the mouse or pull the window forward fails here.
    """

    def __init__(self, pid: int, minimized: bool = False, prints: bool = True):
        self.pid, self.minimized, self.prints = pid, minimized, prints
        self.print_flags: list[int] = []

    def SetProcessDPIAware(self):
        return 1

    def EnumWindows(self, callback, _):
        callback(42, 0)
        return 1

    def GetWindowThreadProcessId(self, hwnd, out):
        out._obj.value = self.pid
        return 1

    def IsWindowVisible(self, hwnd):
        return 1

    def GetClientRect(self, hwnd, rect):
        rect._obj.right, rect._obj.bottom = 64, 48
        return 1

    def IsIconic(self, hwnd):
        return int(self.minimized)

    def GetDC(self, hwnd):
        return 7

    def ReleaseDC(self, hwnd, dc):
        return 1

    def PrintWindow(self, hwnd, dc, flags):
        self.print_flags.append(flags)
        return int(self.prints)


class _FakeGdi32:
    """Hands back a bitmap of one colour (BGRA bytes)."""

    def __init__(self, bgra: bytes):
        self.bgra = bgra

    def CreateCompatibleDC(self, dc):
        return 8

    def CreateCompatibleBitmap(self, dc, width, height):
        return 9

    def SelectObject(self, dc, obj):
        return 1

    def GetDIBits(self, dc, bitmap, start, lines, buffer, info, usage):
        size = len(buffer)
        ctypes_buffer = (self.bgra * (size // 4))[:size]
        import ctypes

        ctypes.memmove(buffer, ctypes_buffer, size)
        return lines

    def DeleteObject(self, obj):
        return 1

    def DeleteDC(self, dc):
        return 1


def _fake_windows(monkeypatch, user32, bgra=b"\x40\x80\xc0\xff"):
    import ctypes

    monkeypatch.setattr(ctypes.windll, "user32", user32, raising=False)
    monkeypatch.setattr(ctypes.windll, "gdi32", _FakeGdi32(bgra), raising=False)
    monkeypatch.setattr(ctypes.windll, "shcore", _NoShcore(), raising=False)


@pytest.mark.skipif(sys.platform != "win32", reason="capture_window is Windows only")
def test_capture_works_in_the_background_without_the_mouse_or_focus(monkeypatch, tmp_path):
    # The owner's rule: the picture check never takes the mouse or needs the DayZ
    # window in front. PrintWindow(PW_CLIENTONLY | PW_RENDERFULLCONTENT) reads the
    # window's own content wherever it sits on screen.
    fake = _FakeUser32(222)
    _fake_windows(monkeypatch, fake)
    visual.capture_window(222, tmp_path / "hud.png")
    assert fake.print_flags == [visual.PW_CLIENTONLY | visual.PW_RENDERFULLCONTENT]
    image = Image.open(tmp_path / "hud.png")
    assert image.size == (64, 48) and image.getpixel((0, 0)) == (0xC0, 0x80, 0x40)  # BGRA turned into RGB


@pytest.mark.skipif(sys.platform != "win32", reason="capture_window is Windows only")
@pytest.mark.parametrize("user32, bgra, message", [
    (_FakeUser32(222, minimized=True), b"\x40\x80\xc0\xff", "minimized"),
    (_FakeUser32(222, prints=False), b"\x40\x80\xc0\xff", "PrintWindow could not read"),
    (_FakeUser32(222), b"\x00\x00\x00\xff", "all black"),
    (_FakeUser32(999), b"\x40\x80\xc0\xff", "has no visible window"),
])
def test_capture_refuses_a_window_it_cannot_read(monkeypatch, tmp_path, user32, bgra, message):
    _fake_windows(monkeypatch, user32, bgra)
    with pytest.raises(visual.VisualError, match=message):
        visual.capture_window(222, tmp_path / "hud.png")
    assert not (tmp_path / "hud.png").exists()


def test_visual_code_never_takes_the_mouse_or_the_window():
    source = (HERE / "visual.py").read_text(encoding="utf-8") + (HERE / "gate.py").read_text(encoding="utf-8")
    for call in ("SetForegroundWindow", "SetCursorPos", "keybd_event", "SendInput", "ImageGrab"):
        assert call not in source, f"{call} would need the mouse or the window in front"


# Every engine name the helper mod calls, with where it is declared on P:.
HELPER_CALLS = {
    "OnUpdate": r"P:\scripts\5_mission\mission\missionserver.c:108 and missiongameplay.c:287",
    "GetGame": r"P:\scripts\3_game\gameplay.c:636",
    "GetWorld": r"P:\scripts\3_game\global\game.c:931",
    "SetDate": r"P:\scripts\3_game\global\world.c:46",
    "GetWeather": r"P:\scripts\3_game\global\game.c:1370",
    "SetWeatherUpdateFreeze": r"P:\scripts\3_game\weather.c:397",
    "GetOvercast": r"P:\scripts\3_game\weather.c:183",
    "GetFog": r"P:\scripts\3_game\weather.c:186",
    "GetRain": r"P:\scripts\3_game\weather.c:189",
    "GetSnowfall": r"P:\scripts\3_game\weather.c:192",
    "Set": r"P:\scripts\3_game\weather.c:49",
    "SetDynVolFogDistanceDensity": r"P:\scripts\3_game\weather.c:360",
    "SetDynVolFogHeightDensity": r"P:\scripts\3_game\weather.c:370",
    "SetDynVolFogHeightBias": r"P:\scripts\3_game\weather.c:381",
    "SetWindMaximumSpeed": r"P:\scripts\3_game\weather.c:269",
    "SetWindFunctionParams": r"P:\scripts\3_game\weather.c:285",
    "GetWindMagnitude": r"P:\scripts\3_game\weather.c:205",
    "Print": r"P:\scripts\1_core\proto\endebug.c:96",
    "Cast": r"P:\scripts\1_core\proto\enscript.c:94",
    "GetPlayer": r"P:\scripts\3_game\global\game.c:944",
    "IsPlayerLoaded": r"P:\scripts\4_world\entities\manbase\playerbase.c:8967",
    "IsPaused": r"P:\scripts\5_mission\mission\missiongameplay.c:1294",
    "Continue": r"P:\scripts\5_mission\mission\missiongameplay.c:1334",
    "GetWorldSize": r"P:\scripts\3_game\global\world.c:82",
    "Vector": r"P:\scripts\1_core\proto\enmath3d.c:18",
    "SurfaceY": r"P:\scripts\3_game\global\game.c:1176",
    "CastTo": r"P:\scripts\1_core\proto\enscript.c:110",
    "CreateObject": r"P:\scripts\3_game\global\game.c:691 ('staticcamera' as in 5_mission\dayzintroscene.c:62)",
    "SetOrientation": r"P:\scripts\3_game\entities\object.c:311",
    "SetActive": r"P:\scripts\3_game\entities\camera.c:45",
    "ToString": r"P:\scripts\1_core\proto\enconvert.c:138",
    "GetHud": r"P:\scripts\3_game\gameplay.c:720",
    "ShowHud": r"P:\scripts\3_game\gameplay.c:672",
    "ShowQuickBar": r"P:\scripts\3_game\gameplay.c:670",
}


def test_helper_mod_calls_only_vanilla_checked_engine_names():
    script = (visual.HELPER_SOURCE / "scripts" / "5_Mission" / "az_visual_helper.c").read_text(encoding="utf-8")
    masked = gate.behavior._mask(script)
    called = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", masked)) - {"if"}
    assert called == set(HELPER_CALLS), (
        f"unchecked engine calls {sorted(called - set(HELPER_CALLS))}; no longer used {sorted(set(HELPER_CALLS) - called)}"
    )
    # The menu flag it clears is vanilla's (missiongameplay.c:45), set when the window is not active (:298).
    assert "m_PauseQueued = false;" in script


def test_helper_mod_files_pack_as_one_addon():
    config = (visual.HELPER_SOURCE / "config.cpp").read_text(encoding="utf-8")
    assert f"class {visual.HELPER_NAME}" in config and f"{visual.HELPER_NAME}/scripts/5_Mission" in config
    assert (visual.HELPER_SOURCE / "$PBOPREFIX$").read_text(encoding="utf-8").strip() == visual.HELPER_NAME


def test_install_and_remove_helper_keep_to_their_own_folder(tmp_path):
    p_drive = tmp_path / "P"
    ran = []

    def fake_addon_builder(cmd):
        ran.append(cmd)
        (Path(cmd[2]) / f"{visual.HELPER_NAME}.pbo").write_bytes(b"pbo")
        return 0, "done"

    root = visual.install_helper(p_drive, Path("AddonBuilder.exe"), ".agentic-z-scaffold", fake_addon_builder)
    assert root == p_drive / "Mods" / "@AZ_VisualHelper"
    assert "-packonly" in ran[0] and f"-prefix={visual.HELPER_NAME}" in ran[0]
    assert (root / "Addons" / "AZ_VisualHelper.pbo").is_file()
    assert not (p_drive / "temp" / "_azvisual").exists()  # the stage is cleaned up
    visual.remove_helper(p_drive, ".agentic-z-scaffold")
    assert not root.exists()


def test_install_helper_refuses_a_folder_it_does_not_own(tmp_path):
    root = tmp_path / "P" / "Mods" / "@AZ_VisualHelper"
    root.mkdir(parents=True)
    (root / "keep.txt").write_text("someone else's", encoding="utf-8")
    with pytest.raises(visual.VisualError, match="not the gate's helper folder"):
        visual.install_helper(tmp_path / "P", Path("AB.exe"), ".agentic-z-scaffold", lambda cmd: (0, ""))
    visual.remove_helper(tmp_path / "P", ".agentic-z-scaffold")
    assert (root / "keep.txt").is_file()  # never deleted without the marker


def test_install_helper_reports_a_failed_pack(tmp_path):
    with pytest.raises(visual.VisualError, match="could not pack the visual helper"):
        visual.install_helper(tmp_path / "P", Path("AB.exe"), ".agentic-z-scaffold", lambda cmd: (1, "[FATAL] boom"))


def test_full_run_refuses_a_session_it_did_not_start_without_yes(project, capsys):
    # The gate used to kill a user's own DayZDiag session with no prompt.
    fake = FakeSession(project)
    fake.running = [42]
    rc, first, data = run_main(["visual", "MyMod", "--json"], capsys, fake.runtime())
    assert (rc, first) == (2, "ERROR") and "--yes" in data["error"]
    assert fake.calls == [] and fake.captures == [] and fake.running == [42]


def test_full_run_with_yes_stops_a_session_it_did_not_start(project, capsys):
    fake = FakeSession(project)
    fake.running = [42]
    rc, first, data = run_main(["visual", "MyMod", "--json", "--yes"], capsys, fake.runtime())
    assert (rc, first) == (0, "PASS"), data["failures"]
    assert "stop_test.bat" in " ".join(fake.calls[0])
