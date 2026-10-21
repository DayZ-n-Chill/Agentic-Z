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
    assert SPEC["threshold"] == 0.01 and visual.last_shot_at(SPEC) == 30


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


def test_accept_makes_a_failing_capture_the_baseline(project, capsys):
    run = run_dir_from(project, "run_fail")
    rc, first, data = run_main(["visual", "MyMod", "--accept", str(run), "--shot", "hud", "--json"], capsys)
    assert (rc, first, data["shots"]) == (0, "ACCEPTED", ["hud"])
    base = project / "output" / "MyMod-visual" / "baseline" / "hud.png"
    assert base.read_bytes() == (run / "hud.png").read_bytes()
    rc, first, _ = run_main(["visual", "MyMod", "--compare", str(run)], capsys)
    assert (rc, first) == (0, "PASS")


def test_accept_refuses_unknown_shots_and_empty_runs(project, capsys):
    run = run_dir_from(project, "run_pass")
    rc, first, _ = run_main(["visual", "MyMod", "--accept", str(run), "--shot", "nope"], capsys)
    assert (rc, first) == (2, "ERROR")
    for png in run.glob("*.png"):
        png.unlink()
    rc, first, _ = run_main(["visual", "MyMod", "--accept"], capsys)
    assert (rc, first) == (2, "ERROR")


# --- full run with a fake session and capture -----------------------------------------------

class FakeSession:
    """No DayZ: the fake launch writes the client ready line; the fake capture copies fixture images."""

    def __init__(self, project: Path, source: str = "run_pass", fail_capture: bool = False):
        self.project = project
        self.source = source
        self.fail_capture = fail_capture
        self.calls: list[list[str]] = []
        self.captures: list[tuple[float, int, str]] = []
        self.running: list[int] = []
        self.now = 0.0

    def runtime(self):
        return gate.Runtime(run=self.run, diag_pids=lambda: list(self.running), pid_alive=lambda p: p in self.running,
                            sleep=self.sleep, clock=lambda: self.now, capture=self.capture)

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
        (client / "script_2026-10-21_12-00-31.log").write_text(READY + "\n", encoding="utf-8")
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
    assert [round(t) for t, _, _ in fake.captures] == [20, 30]  # the ready line was read at 0 s
    assert fake.now <= 34 and fake.running == []  # stopped soon after the last shot
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


def test_full_run_without_shots_file_is_an_error(project, capsys):
    (project / "output" / "MyMod-plan" / "visual-shots.json").unlink()
    fake = FakeSession(project)
    rc, first, _ = run_main(["visual", "MyMod"], capsys, fake.runtime())
    assert (rc, first) == (2, "ERROR")
    assert fake.calls == []


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
