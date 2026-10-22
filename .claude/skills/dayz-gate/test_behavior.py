"""Tests for the behavior gate: checks file, mission injector, log parser and gate.py behavior.

Fixture mission folders and logs live in fixtures/behavior/. Nothing launches
DayZ: the full run uses a fake runtime whose launch writes the logs a real
session would.
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

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "behavior"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gate = _load("dayz_gate_behavior_gate_under_test", HERE / "gate.py")
behavior = gate.behavior
launch = _load("dayz_launch_for_behavior_test", HERE.parent / "dayz-launch-test" / "launch.py")

CHECKS = json.loads((FIXTURES / "checks.json").read_text(encoding="utf-8"))["checks"]
IDS = [c["id"] for c in CHECKS]
TEMPLATE = "dayzOffline.chernarusplus"
READY = r"SCRIPT       : Creating Mission: mpmissions\__cur_mp.chernarusplus\mission.c"


@pytest.fixture
def project(tmp_path, monkeypatch):
    """A project with the fixture instance at .server/chernarus/ and a mod with the checks file."""
    proj = tmp_path / "proj"
    mod = proj / "workspace" / "MyMod"
    (mod / "scripts" / "4_World").mkdir(parents=True)
    (mod / "config.cpp").write_text(
        "class CfgPatches\n{\n\tclass MyMod\n\t{\n\t\trequiredAddons[] = {\"DZ_Data\"};\n\t};\n};\n"
        "class CfgVehicles\n{\n\tclass Vest_Base;\n\tclass MyMod_Vest: Vest_Base {};\n\tclass MyMod_Knife: Inventory_Base {};\n};\n",
        encoding="utf-8",
    )
    (mod / "$PBOPREFIX$").write_text("MyMod", encoding="utf-8")
    shutil.copytree(FIXTURES / "instance", proj / ".server" / "chernarus")
    (proj / ".server" / "!ClientDiagLogs").mkdir(parents=True)
    plan = proj / "output" / "MyMod-plan"
    plan.mkdir(parents=True)
    shutil.copy2(FIXTURES / "checks.json", plan / "behavior-checks.json")
    monkeypatch.setattr(gate.h, "resolve_project_dir", lambda: proj)
    return proj


# --- checks file ---------------------------------------------------------------------

def test_fixture_checks_load():
    assert [c["id"] for c in behavior.load_checks(FIXTURES / "checks.json")] == IDS


def test_default_checks_path_is_the_architect_plan(tmp_path):
    assert behavior.default_checks_path(tmp_path, "MyVest") == tmp_path / "output" / "MyVest-plan" / "behavior-checks.json"


def _broken(index: int, **change) -> dict:
    checks = copy.deepcopy(CHECKS)
    for key, value in change.items():
        if value is None:
            checks[index].pop(key, None)
        else:
            checks[index][key] = value
    return {"checks": checks}


@pytest.mark.parametrize("data,message", [
    ([], "expected an object"),
    ({"checks": []}, "non-empty list"),
    ({"checks": CHECKS, "extra": 1}, "expected an object"),
    (_broken(0, id="vest spawns"), "no spaces"),
    (_broken(1, id="vest-spawns"), "duplicate id"),
    (_broken(0, feature=" "), "feature"),
    (_broken(0, action="drive"), "action must be one of"),
    (_broken(0, item='MyMod_Vest"); Evil("'), "item must be a config class name"),
    ({"checks": [{**CHECKS[0], "wiht": "MyMod_Pouch"}]}, "unknown keys"),
    (_broken(2, **{"with": None}), "with must be a config class name"),
    (_broken(0, **{"with": "MyMod_Pouch"}), "takes no 'with' class"),
], ids=["not-object", "empty", "extra-key", "space-in-id", "duplicate", "no-feature", "bad-action",
        "quote-in-item", "typo-key", "attach-without-with", "spawn-with-with"])
def test_bad_checks_are_refused(data, message):
    with pytest.raises(behavior.BehaviorError, match=re.escape(message)):
        behavior.validate_checks(data)


def test_missing_and_invalid_checks_files(tmp_path):
    with pytest.raises(behavior.BehaviorError, match="checks file not found"):
        behavior.load_checks(tmp_path / "nope.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(behavior.BehaviorError, match="not valid JSON"):
        behavior.load_checks(bad)


# --- injector ------------------------------------------------------------------------

FIXTURE_INIT = (FIXTURES / "instance" / "mission" / "init.c").read_text(encoding="utf-8")


def _main_body(text: str) -> str:
    start = text.index("void main()")
    return text[start:text.index("class CustomMission")]


def test_inject_puts_class_first_and_start_call_last_in_main():
    out = behavior.inject(FIXTURE_INIT, CHECKS)
    assert out.startswith(behavior.MARK_BEGIN)
    assert out.index("class AZ_BehaviorTest") < out.index("void main()")
    body = _main_body(out)
    # after the Print whose string holds a brace, before main's closing brace
    assert body.index('Print("fixture mission main } done");') < body.index(behavior.START_CALL)
    assert body.rstrip().endswith(behavior.START_CALL + "\n}")
    assert out.count(behavior.START_CALL) == 1
    # the original mission is kept whole
    assert out.endswith(FIXTURE_INIT[FIXTURE_INIT.index("}\n\nclass CustomMission"):])


def test_inject_adds_one_line_per_check():
    out = behavior.inject(FIXTURE_INIT, CHECKS)
    adds = re.findall(r's_Test\.Add\("([^"]*)", "([^"]*)", "([^"]*)", "([^"]*)"\);', out)
    assert adds == [(c["id"], c["item"], c["action"], c.get("with", "")) for c in CHECKS]


def test_injected_script_is_balanced_and_prints_only_the_line_format():
    script = behavior.render_script(CHECKS)
    masked = behavior._mask(script)
    assert masked.count("{") == masked.count("}")
    assert masked.count("(") == masked.count(")")
    prints = re.findall(r'Print\("([^"]*)"', script)
    assert prints and all(p.startswith("[AZ-BEHAVIOR] ") for p in prints)
    assert {p.split()[1] for p in prints} == {"START", "PASS", "FAIL", "DONE"}
    # the reasons must not look like engine errors to the in-game rules
    for reason in re.findall(r'return [^;]*"([^"]+)"', script):
        assert gate.triage.classify(reason) is None, reason


def test_inject_keeps_crlf_line_endings():
    crlf = FIXTURE_INIT.replace("\n", "\r\n")
    out = behavior.inject(crlf, CHECKS)
    assert "\n" not in out.replace("\r\n", "")


def test_inject_refuses_twice_and_without_main():
    once = behavior.inject(FIXTURE_INIT, CHECKS)
    with pytest.raises(behavior.BehaviorError, match="already holds"):
        behavior.inject(once, CHECKS)
    with pytest.raises(behavior.BehaviorError, match="no void main"):
        behavior.inject("// void main() { in a comment }\nclass X {};\n", CHECKS)


# --- instance copy -------------------------------------------------------------------

def test_prepare_instance_copies_and_injects(project):
    original = (project / ".server" / "chernarus" / "mission" / "init.c").read_text(encoding="utf-8")
    prepared = behavior.prepare_instance(project, "chernarus", CHECKS)
    dst = project / ".server" / "chernarus-behavior"
    assert prepared["instance"] == "chernarus-behavior" and prepared["template"] == TEMPLATE
    assert (dst / "serverDZ.cfg").read_text(encoding="utf-8") == (FIXTURES / "instance" / "serverDZ.cfg").read_text(encoding="utf-8")
    assert behavior.START_CALL in (dst / "mission" / "init.c").read_text(encoding="utf-8")
    assert (dst / "mission" / "db" / "globals.xml").is_file()
    assert not (dst / "mission" / "storage_1").exists()
    assert gate.h.is_link(dst / TEMPLATE) and (dst / TEMPLATE / "init.c").is_file()
    assert (dst / "Profiles").is_dir()
    # the user's instance is untouched
    assert (project / ".server" / "chernarus" / "mission" / "init.c").read_text(encoding="utf-8") == original


def test_prepared_copy_passes_launch_test_instance_check(project):
    behavior.prepare_instance(project, "chernarus", CHECKS)
    _, _, mission_path, _ = launch.verify_instance_environment("chernarus-behavior", project, dry_run=True)
    assert mission_path == project / ".server" / "chernarus-behavior" / TEMPLATE


def test_prepare_instance_twice_replaces_the_copy_and_keeps_logs(project):
    behavior.prepare_instance(project, "chernarus", CHECKS)
    log = project / ".server" / "chernarus-behavior" / "Profiles" / "script_old.log"
    log.write_text("old\n", encoding="utf-8")
    behavior.prepare_instance(project, "chernarus", CHECKS[:1])
    init = (project / ".server" / "chernarus-behavior" / "mission" / "init.c").read_text(encoding="utf-8")
    assert init.count("s_Test.Add(") == 1
    assert log.is_file()
    # removing the old junction did not delete through it
    assert (project / ".server" / "chernarus" / "mission" / "init.c").is_file()


def test_prepare_instance_refusals(project):
    with pytest.raises(behavior.BehaviorError, match="original instance"):
        behavior.prepare_instance(project, "chernarus-behavior", CHECKS)
    with pytest.raises(behavior.BehaviorError, match="/dayz-add-server livonia"):
        behavior.prepare_instance(project, "livonia", CHECKS)


def _tree(root: Path) -> set:
    return {p.relative_to(root) for p in root.rglob("*")}


@pytest.mark.parametrize("instance", ["../x", "a\\b", "..", "", "C:x"])
def test_prepare_instance_refuses_bad_instance_names(project, instance):
    before = _tree(project.parent)
    with pytest.raises(behavior.BehaviorError, match="not a valid instance name"):
        behavior.prepare_instance(project, instance, CHECKS)
    assert _tree(project.parent) == before


def test_log_lookups_refuse_bad_instance_names(project):
    with pytest.raises(behavior.BehaviorError, match="not a valid instance name"):
        behavior.server_script_logs(project, "../x")
    with pytest.raises(behavior.BehaviorError, match="not a valid instance name"):
        gate.gate_behavior_logs("MyMod", project, None, "a\\b", [])


@pytest.mark.parametrize("template", ["C:\\Something", "..\\..\\victim", "..", "x&calc", "a/b"])
def test_prepare_instance_refuses_bad_templates(project, template):
    cfg = project / ".server" / "chernarus" / "serverDZ.cfg"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace(TEMPLATE, template), encoding="utf-8")
    victim = project / "victim"
    victim.mkdir()
    before = _tree(project.parent)
    with pytest.raises(behavior.BehaviorError, match="one mission folder name"):
        behavior.prepare_instance(project, "chernarus", CHECKS)
    assert _tree(project.parent) == before


# --- parser --------------------------------------------------------------------------

def _parse(name: str) -> dict:
    return behavior.parse_lines(behavior.read_logs([FIXTURES / "logs" / name]), CHECKS)


def test_parse_all_pass():
    parsed = _parse("script_pass.log")
    assert parsed["started"] and parsed["done"]
    assert [(r["id"], r["status"]) for r in parsed["results"]] == [(i, "PASS") for i in IDS]
    assert parsed["results"][0]["line"] == 4


def test_parse_fail_reasons_missing_check_and_unexpected_ids():
    parsed = _parse("script_fail.log")
    by_id = {r["id"]: r for r in parsed["results"]}
    assert by_id["vest-spawns"]["status"] == "PASS"
    assert by_id["vest-wear"]["reason"] == "MyMod_Vest has no inventorySlot the player can wear"
    assert by_id["vest-pouch"]["reason"] == "MyMod_Pouch did not attach to MyMod_Vest"
    assert by_id["knife-hands"]["status"] == "FAIL"
    assert "stopped before this check" in by_id["knife-hands"]["reason"]
    assert parsed["unexpected"] == ["old-check"] and not parsed["done"]


def test_parse_newest_run_wins():
    parsed = _parse("script_two_runs.log")
    assert all(r["status"] == "PASS" for r in parsed["results"])
    assert parsed["results"][0]["line"] == 6


def test_parse_without_start_line():
    parsed = behavior.parse_lines([(Path("x.log"), 1, "SCRIPT : nothing here")], CHECKS)
    assert not parsed["started"]
    assert all("never started" in r["reason"] for r in parsed["results"])


# --- gate.py behavior ----------------------------------------------------------------

def run_main(argv: list[str], capsys, rt=None) -> tuple[int, str, dict | None]:
    rc = gate.main(argv, rt=rt)
    out = capsys.readouterr().out
    first, _, rest = out.partition("\n")
    return rc, first, json.loads(rest) if "--json" in argv else rest


def test_logs_mode_pass(project, capsys):
    rc, first, data = run_main(["behavior", "MyMod", "--logs", str(FIXTURES / "logs" / "script_pass.log"), "--json"], capsys)
    assert (rc, first, data["verdict"], data["mode"]) == (0, "PASS", "PASS", "behavior")
    assert [c["status"] for c in data["checks"]] == ["PASS"] * len(IDS)


def test_logs_mode_fail_keeps_one_failure_per_check(project, capsys):
    rc, first, data = run_main(["behavior", "MyMod", "--logs", str(FIXTURES / "logs" / "script_fail.log"), "--json"], capsys)
    assert (rc, first) == (1, "FAIL")
    assert [f["check"] for f in data["failures"]] == ["vest-wear", "vest-pouch", "knife-hands"]
    assert all(f["category"] == "behavior" and f["triage"]["status"] == "new" for f in data["failures"])
    assert data["failures"][0]["line"] == 4
    assert data["behavior"]["unexpected"] == ["old-check"]


def test_logs_mode_result_and_checks_reach_the_health_page(project, capsys):
    run_main(["behavior", "MyMod", "--logs", str(FIXTURES / "logs" / "script_fail.log"), "--json"], capsys)
    data = gate.health.health(project, "MyMod")
    assert (data["last_test"]["kind"], data["last_test"]["verdict"]) == ("behavior", "FAIL")
    assert [c["id"] for c in data["last_test"]["checks"] if c["status"] == "FAIL"] == ["vest-wear", "vest-pouch", "knife-hands"]
    page = (project / ".server" / "!Health" / "MyMod" / "health.md").read_text(encoding="utf-8")
    assert "## Behavior checks (latest run)" in page and "| vest-wear | FAIL |" in page


def test_logs_mode_text_lists_each_check(project, capsys):
    rc, first, text = run_main(["behavior", "MyMod", "--logs", str(FIXTURES / "logs" / "script_fail.log")], capsys)
    assert rc == 1 and first == "FAIL"
    assert "  PASS vest-spawns" in text
    assert "  FAIL vest-wear  MyMod_Vest has no inventorySlot the player can wear" in text


def test_logs_mode_defaults_to_the_copy_server_logs(project, capsys):
    profiles = project / ".server" / "chernarus-behavior" / "Profiles"
    profiles.mkdir(parents=True)
    shutil.copy2(FIXTURES / "logs" / "script_pass.log", profiles / "script_2026-10-20_12-00-02.log")
    rc, first, _ = run_main(["behavior", "MyMod", "--logs"], capsys)
    assert (rc, first) == (0, "PASS")


def test_logs_mode_without_logs_or_checks_is_an_error(project, capsys):
    rc, first, _ = run_main(["behavior", "MyMod", "--logs"], capsys)
    assert (rc, first) == (2, "ERROR")
    rc, first, _ = run_main(["behavior", "Other", "--logs", str(FIXTURES / "logs" / "script_pass.log")], capsys)
    assert (rc, first) == (2, "ERROR")


def test_prepare_only(project, capsys):
    rc, first, data = run_main(["behavior", "MyMod", "--prepare-only", "--json"], capsys)
    assert (rc, first, data["instance"], data["checks"]) == (0, "PREPARED", "chernarus-behavior", len(IDS))
    assert (project / ".server" / "chernarus-behavior" / TEMPLATE).is_dir()


class FakeSession:
    """No DayZ: the fake launch writes the client ready line and the test mission's lines."""

    def __init__(self, project: Path, server_lines: list[str], ready_line: str = READY):
        self.project = project
        self.server_lines = server_lines
        self.ready_line = ready_line
        self.calls: list[list[str]] = []
        self.running: list[int] = []
        self.now = 0.0

    def runtime(self):
        return gate.Runtime(run=self.run, diag_pids=lambda: list(self.running), pid_alive=lambda p: p in self.running,
                            sleep=self.sleep, clock=lambda: self.now)

    def run(self, cmd: list[str]) -> tuple[int, str]:
        self.calls.append(cmd)
        joined = " ".join(cmd)
        if "stop_test.bat" in joined:
            self.running = []
            return 0, "SUCCESS"
        assert "launch.py" in joined, cmd
        self.running = [111, 222]
        server = self.project / ".server" / "chernarus-behavior" / "Profiles"
        client = self.project / ".server" / "!ClientDiagLogs"
        (server / "DayZDiag_x64_2026-10-20_12-00-00.RPT").write_text("CLI params: server mod P:\\Mods\\@MyMod\n", encoding="utf-8")
        (server / "script_2026-10-20_12-00-02.log").write_text("\n".join(self.server_lines) + "\n", encoding="utf-8")
        (client / "script_2026-10-20_12-00-31.log").write_text(self.ready_line + "\n", encoding="utf-8")
        return 0, "[OK]    Server PID: 111\n[OK]    Client PID: 222\n"

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_full_run_launches_the_copy_and_stops_at_done(project, capsys):
    lines = (FIXTURES / "logs" / "script_pass.log").read_text(encoding="utf-8").splitlines()
    fake = FakeSession(project, lines)
    rc, first, data = run_main(["behavior", "MyMod", "--json"], capsys, fake.runtime())
    assert (rc, first) == (0, "PASS"), data["failures"]
    launch_cmd = next(c for c in fake.calls if "launch.py" in " ".join(c))
    assert launch_cmd[2:] == ["MyMod", "--server", "chernarus-behavior", "--port", "2302"]
    assert data["behavior"]["done"] and fake.now < 60  # the DONE line ended the wait, not the 600 s --done-timeout
    assert fake.running == []


def test_full_run_fails_on_checks_and_on_mod_script_errors(project, capsys):
    lines = (FIXTURES / "logs" / "script_fail.log").read_text(encoding="utf-8").splitlines()
    fake = FakeSession(project, lines)
    rc, first, data = run_main(["behavior", "MyMod", "--json", "--done-timeout", "6"], capsys, fake.runtime())
    assert (rc, first) == (1, "FAIL")
    categories = [f["category"] for f in data["failures"]]
    assert "null_pointer" in categories  # the in-game rules still apply
    assert [f["check"] for f in data["failures"] if f["category"] == "behavior"] == ["vest-wear", "vest-pouch", "knife-hands"]


def test_full_run_uses_the_ready_pattern(project, capsys):
    """A mod that replaces CreateMission prints its own ready line; --ready-pattern finds it."""
    lines = (FIXTURES / "logs" / "script_pass.log").read_text(encoding="utf-8").splitlines()
    fake = FakeSession(project, lines, ready_line="SCRIPT : [MyMod] ready")
    rc, first, data = run_main(["behavior", "MyMod", "--json", "--ready-pattern", r"\[MyMod\] ready"],
                               capsys, fake.runtime())
    assert (rc, first) == (0, "PASS"), data["failures"]
    assert data["ready"]["text"] == "SCRIPT : [MyMod] ready"


def test_bad_ready_pattern_is_an_error_before_launch(project, capsys):
    fake = FakeSession(project, [])
    rc, first, _ = run_main(["behavior", "MyMod", "--ready-pattern", "("], capsys, fake.runtime())
    assert (rc, first) == (2, "ERROR")
    assert fake.calls == []


def test_full_run_without_checks_file_is_an_error(project, capsys):
    (project / "output" / "MyMod-plan" / "behavior-checks.json").unlink()
    fake = FakeSession(project, [])
    rc, first, _ = run_main(["behavior", "MyMod"], capsys, fake.runtime())
    assert (rc, first) == (2, "ERROR")
    assert fake.calls == []


# --- the test mission never started ------------------------------------------------

def test_unstarted_mission_with_a_clean_session_is_an_error_not_a_fail(project, capsys):
    fake = FakeSession(project, ["12:00:01.204 SCRIPT       : Module: Game; loaded 415x files"])
    rc, first, text = run_main(["behavior", "MyMod", "--done-timeout", "6"], capsys, fake.runtime())
    assert (rc, first) == (2, "ERROR")
    assert "not a verdict on the mod" in text and ".server/chernarus-behavior/Profiles/" in text
    assert fake.running == []  # the session was still stopped
    assert not (project / ".server" / "!Health" / "MyMod").exists()  # nothing stored for /dayz-health


def test_unstarted_mission_in_logs_mode_is_an_error(project, capsys, tmp_path):
    log = tmp_path / "script.log"
    log.write_text("12:00:01.204 SCRIPT       : Module: Game; loaded 415x files\n", encoding="utf-8")
    rc, first, _ = run_main(["behavior", "MyMod", "--logs", str(log)], capsys)
    assert (rc, first) == (2, "ERROR")


def test_unstarted_mission_with_a_mod_error_still_fails(project, capsys):
    lines = (FIXTURES / "logs" / "script_fail.log").read_text(encoding="utf-8").splitlines()
    lines = [t for t in lines if "[AZ-BEHAVIOR]" not in t]
    fake = FakeSession(project, lines)
    rc, first, data = run_main(["behavior", "MyMod", "--json", "--done-timeout", "6"], capsys, fake.runtime())
    assert (rc, first) == (1, "FAIL")
    assert "null_pointer" in [f["category"] for f in data["failures"]]
    assert not data["behavior"]["started"]


def test_behavior_wait_flag_is_not_called_settle(project, capsys):
    # --settle means "extra seconds after ready" in ingame; behavior uses its own name.
    assert gate.main(["behavior", "MyMod", "--settle", "6"]) == 2
    assert "unrecognized arguments: --settle" in capsys.readouterr().err

