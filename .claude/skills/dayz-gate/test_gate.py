"""Tests for gate.py. Everything is mocked: no DayZ, no P:\\, no processes.

A FakeRuntime stands in for subprocesses, tasklist, sleep and the clock; the
fake launch writes server and client logs under tmp_path, and timed events
append lines as the fake clock advances.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Callable

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_gate_under_test", HERE / "gate.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

READY = r"SCRIPT       : Creating Mission: mpmissions\__cur_mp.chernarusplus\mission.c"


class FakeRuntime:
    """Scripted subprocess results, DayZDiag process list and a fake clock."""

    def __init__(self, results: dict[str, tuple[int, str]] | None = None, running: list[int] | None = None):
        self.results = results or {}
        self.calls: list[list[str]] = []
        self.running = list(running or [])
        self.dead: set[int] = set()
        self.now = 0.0
        self.events: list[tuple[float, Callable[[], None]]] = []
        self.on_launch: Callable[[], None] | None = None
        self.stop_rc = 0
        self.stop_leaves: list[int] = []

    def runtime(self) -> gate.Runtime:
        return gate.Runtime(run=self.run, diag_pids=lambda: list(self.running), pid_alive=self.alive,
                            sleep=self.sleep, clock=lambda: self.now)

    def run(self, cmd: list[str]) -> tuple[int, str]:
        self.calls.append(cmd)
        joined = " ".join(cmd)
        if "stop_test.bat" in joined:
            self.running = list(self.stop_leaves)
            return self.stop_rc, "SUCCESS: terminated" if self.stop_rc == 0 else "ERROR: Access is denied."
        for key, result in self.results.items():
            if key in joined:
                if key == "launch.py":
                    self.running = [111, 222]
                    if self.on_launch:
                        self.on_launch()
                return result
        raise AssertionError(f"unexpected command {cmd}")

    def alive(self, pid: int) -> bool:
        return pid in self.running and pid not in self.dead

    def sleep(self, seconds: float) -> None:
        self.now += seconds
        due = [e for e in self.events if e[0] <= self.now]
        self.events = [e for e in self.events if e[0] > self.now]
        for _, action in due:
            action()

    def at(self, t: float, action: Callable[[], None]) -> None:
        self.events.append((t, action))

    def ran(self, name: str) -> bool:
        return any(name in " ".join(c) for c in self.calls)

    def stops(self) -> int:
        return sum("stop_test.bat" in " ".join(c) for c in self.calls)


@pytest.fixture
def project(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    mod = proj / "workspace" / "MyMod"
    (mod / "scripts" / "4_World").mkdir(parents=True)
    (mod / "config.cpp").write_text(
        "class CfgPatches\n{\n\tclass MyMod\n\t{\n\t\tunits[] = {};\n\t\tweapons[] = {};\n"
        "\t\trequiredAddons[] = {\"DZ_Data\"};\n\t};\n};\n"
        "class CfgMods\n{\n\tclass MyMod\n\t{\n\t\ttype = \"mod\";\n\t\tclass defs\n\t\t{\n"
        "\t\t\tclass worldScriptModule\n\t\t\t{\n\t\t\t\tvalue = \"\";\n\t\t\t\tfiles[] = {\"MyMod/scripts/4_World\"};\n"
        "\t\t\t};\n\t\t};\n\t};\n};\n"
        "class CfgVehicles\n{\n\tclass Vest_Base;\n\tclass MyMod_Vest: Vest_Base\n\t{\n"
        "\t\tclass DamageSystem {};\n\t};\n};\n",
        encoding="utf-8",
    )
    (mod / "$PBOPREFIX$").write_text("MyMod", encoding="utf-8")
    (mod / "scripts" / "4_World" / "vest.c").write_text(
        "class MyModVestHelper\n{\n}\nmodded class PlayerBase\n{\n}\n", encoding="utf-8"
    )
    (proj / ".server" / "chernarus" / "Profiles").mkdir(parents=True)
    (proj / ".server" / "!ClientDiagLogs").mkdir(parents=True)
    monkeypatch.setattr(gate.h, "resolve_project_dir", lambda: proj)
    # No P:\ in tests: lint then skips the link and vanilla-name checks with a warning.
    monkeypatch.setattr(gate.lint, "P_DRIVE", tmp_path / "no-P")
    return proj


def server_dir(proj: Path) -> Path:
    return proj / ".server" / "chernarus" / "Profiles"


def client_dir(proj: Path) -> Path:
    return proj / ".server" / "!ClientDiagLogs"


def append(path: Path, *lines: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def launch_ok() -> tuple[int, str]:
    return 0, "[OK]    Server PID: 111\n[OK]    Client PID: 222\n  Server PID: 111    Client PID: 222\n"


BUILD_OK = (
    "DayZ preflight\n[WARN] Workshop folder not writable\nPreflight complete.\n"
    "[AddonBuilder] AddonBuilder.exe P:\\MyMod P:\\Mods\\@MyMod\\Addons -prefix=MyMod\n\n"
    "Packing MyMod...\nBinarizing 3 files, 0 errors\n\n[OK]    Built: P:\\Mods\\@MyMod\\Addons\\MyMod.pbo (12,345 bytes)\n"
)


def run_main(argv: list[str], fake: FakeRuntime, capsys) -> tuple[int, str, dict | None]:
    rc = gate.main(argv, rt=fake.runtime())
    out = capsys.readouterr().out
    first, _, rest = out.partition("\n")
    data = json.loads(rest) if "--json" in argv else None
    return rc, first, data


# --- tasklist ------------------------------------------------------------------

def test_parse_tasklist():
    out = '"DayZDiag_x64.exe","1234","Console","1","500,000 K"\r\n"DayZDiag_x64.exe","99","Console","1","1 K"\r\n'
    assert gate.parse_tasklist(out) == [1234, 99]
    assert gate.parse_tasklist(out, 99) == [99]
    assert gate.parse_tasklist("INFO: No tasks are running which match the specified criteria.") == []


# --- stop session ----------------------------------------------------------------

def test_stop_session_noop_when_nothing_runs():
    fake = FakeRuntime()
    assert gate.stop_session(fake.runtime())["result"] == "no DayZDiag session running"
    assert fake.calls == []


def test_stop_session_runs_stop_test_bat():
    fake = FakeRuntime(running=[5])
    step = gate.stop_session(fake.runtime())
    assert "stopped PIDs [5]" in step["result"]
    assert fake.calls[0][:2] == ["cmd", "/c"] and fake.calls[0][2].endswith("stop_test.bat")


def test_stop_session_failure_is_gate_error():
    fake = FakeRuntime(running=[5])
    fake.stop_rc = 1
    with pytest.raises(gate.GateError, match="exited 1"):
        gate.stop_session(fake.runtime())


def test_stop_session_survivors_are_gate_error():
    fake = FakeRuntime(running=[5])
    fake.stop_leaves = [5]
    with pytest.raises(gate.GateError, match="still running"):
        gate.stop_session(fake.runtime())


# --- build gate --------------------------------------------------------------------

def test_build_pass(project, capsys):
    fake = FakeRuntime({"build.py": (0, BUILD_OK)})
    rc, first, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert (rc, first, data["verdict"]) == (0, "PASS", "PASS")
    assert data["failures"] == []
    build_cmd = next(c for c in fake.calls if "build.py" in " ".join(c))
    assert build_cmd[0] == sys.executable and build_cmd[-1] == "MyMod"
    assert not fake.ran("deploy.py")


def test_build_runs_lint_first_and_stops_on_errors(project, capsys):
    cfg = project / "workspace" / "MyMod" / "config.cpp"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("\t\tunits[] = {};\n", "\t\tunits = \"\";\n"), encoding="utf-8")
    fake = FakeRuntime({"build.py": (0, BUILD_OK)}, running=[42])
    rc, first, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert (rc, first) == (1, "FAIL")
    assert fake.calls == []  # no stop, no build: a running session is left alone
    assert data["lint"] == {"verdict": "FAIL", "errors": 1, "warnings": 1}
    [f] = data["failures"]
    assert (f["category"], f["rule"], f["file"], f["line"]) == ("lint", "cfgpatches-field", "workspace/MyMod/config.cpp", 5)
    assert f["triage"]["id"] == "lint-cfgpatches-field"
    assert f["triage"]["owner_agent"] == "dayz-config-specialist"
    assert [w["rule"] for w in data["warnings"]] == ["p-not-mounted"]


def test_build_stores_lint_and_build_results_for_health(project, capsys):
    fake = FakeRuntime({"build.py": (0, BUILD_OK)})
    rc, _, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert rc == 0
    folder = project / ".server" / "!Health" / "MyMod"
    assert data["health"] == str(Path(".server") / "!Health" / "MyMod" / "health.md")
    kinds = sorted(json.loads(p.read_text(encoding="utf-8"))["kind"] for p in (folder / "results").glob("*.json"))
    assert kinds == ["build", "lint"]
    assert "* Last build: PASS" in (folder / "health.md").read_text(encoding="utf-8")
    assert (folder / "health.html").is_file()


def test_failed_lint_stop_is_stored_as_a_failed_build(project, capsys):
    cfg = project / "workspace" / "MyMod" / "config.cpp"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("\t\tunits[] = {};\n", "\t\tunits = \"\";\n"), encoding="utf-8")
    run_main(["build", "MyMod", "--json"], FakeRuntime(), capsys)
    data = gate.health.health(project, "MyMod")
    assert data["last_build"]["verdict"] == "FAIL"
    assert data["latest"]["lint"]["verdict"] == "FAIL"
    assert any("cfgpatches" in f["text"].lower() for f in data["open_findings"])


def test_visual_result_is_stored_for_health(project):
    run = project / "output" / "MyMod-visual" / "runs" / "2026-10-21_12-00-00"
    results = [
        {"id": "hud", "status": gate.visual.FAIL, "ratio": 0.0156, "threshold": 0.01, "reason": "1.56% of pixels differ",
         "capture": run / "hud.png", "baseline": None, "diff": None},
        {"id": "menu", "status": gate.visual.PASS, "ratio": 0.0, "threshold": 0.01, "reason": "",
         "capture": run / "menu.png", "baseline": None, "diff": None},
    ]
    report = gate.new_report("visual", "MyMod")
    gate.add_visual_results(report, results, run, project)
    gate.finish(report, project)
    gate.save_health(report, project)
    assert "health" in report and "health_error" not in report
    [stored] = gate.health.load_results(project, "MyMod")
    assert (stored["kind"], stored["verdict"]) == ("visual", "FAIL")
    assert [s["status"] for s in stored["shots"]] == ["FAIL", "PASS"]
    assert gate.health.health(project, "MyMod")["last_test"]["kind"] == "visual"


def test_health_store_failure_keeps_the_verdict(project, capsys, monkeypatch):
    def broken(*_):
        raise OSError("disk full")
    monkeypatch.setattr(gate.health, "record_gate", broken)
    rc, first, data = run_main(["build", "MyMod", "--json"], FakeRuntime({"build.py": (0, BUILD_OK)}), capsys)
    assert (rc, first) == (0, "PASS")
    assert data["health_error"] == "disk full" and "health" not in data


def test_gate_error_is_not_stored(project, capsys):
    run_main(["build", "NoSuchMod", "--json"], FakeRuntime(), capsys)
    assert not (project / ".server" / "!Health").exists()


def test_build_lint_pass_is_reported_in_text(project, capsys):
    fake = FakeRuntime({"build.py": (0, BUILD_OK)})
    assert gate.main(["build", "MyMod"], rt=fake.runtime()) == 0
    assert "  dayz-lint: PASS, 0 error(s), 1 warning(s)" in capsys.readouterr().out.splitlines()


def test_build_missing_mod_folder_is_a_gate_error(project, capsys):
    rc, first, _ = run_main(["build", "NoSuchMod", "--json"], FakeRuntime(), capsys)
    assert (rc, first) == (2, "ERROR")


def test_build_stops_running_session_first(project, capsys):
    fake = FakeRuntime({"build.py": (0, BUILD_OK)}, running=[42])
    rc, _, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert rc == 0
    assert "stop_test.bat" in " ".join(fake.calls[0]) and "build.py" in " ".join(fake.calls[1])
    assert data["steps"][0]["result"] == "stopped PIDs [42]"


def test_build_failing_exit_code_quotes_fail_lines_and_triages(project, capsys):
    out = "[OK]    P:\\Mods junction valid\n[FAIL] workspace\\MyMod\\$PBOPREFIX$ is 'Other', expected 'MyMod'.\n       Set the file's content.\n"
    fake = FakeRuntime({"build.py": (1, out)})
    rc, first, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert (rc, first) == (1, "FAIL")
    [f] = data["failures"]
    assert f["category"] == "script_fail"
    assert f["context"] == ["Set the file's content."]
    assert f["triage"]["id"] == "pboprefix-mismatch"
    assert f["triage"]["owner_agent"] == "dayz-config-specialist"
    assert "workspace/MyMod/$PBOPREFIX$" in f["triage"]["fix"]


def test_build_nonzero_without_fail_lines_still_fails(project, capsys):
    fake = FakeRuntime({"build.py": (3, "[AddonBuilder] x\nsomething odd\n")})
    rc, _, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert rc == 1
    assert data["failures"][0]["text"] == "dayz-build-pbo exited 3"
    assert data["failures"][0]["triage"]["status"] == "new"


@pytest.mark.parametrize("line,category", [
    ("Error: In File P:\\MyMod\\config.cpp: Line 12 Undefined base class 'Vest_Bse'", "build_error"),
    ("Build failed. Result code=1", "build_error"),
    ("Warning: File P:\\MyMod\\data\\vest_co.paa not found", "build_warning"),
    ("warning: unknown class MyMod_Vest2 in CfgVehicles", "build_warning"),
    ("Cannot open P:\\MyMod\\data\\vest.p3d", "build_warning"),
])
def test_build_exit_zero_with_addonbuilder_problem_fails(project, capsys, line, category):
    out = BUILD_OK.replace("Packing MyMod...", f"Packing MyMod...\n{line}")
    fake = FakeRuntime({"build.py": (0, out)})
    rc, _, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert rc == 1
    [f] = data["failures"]
    assert (f["category"], f["text"]) == (category, line)


def test_build_finding_points_to_files(project):
    findings = gate.parse_build_output("[AddonBuilder] x\nError: In File P:\\MyMod\\config.cpp: Line 12 something\n")
    assert findings[0]["points_to"] == ["P:\\MyMod\\config.cpp"]
    assert findings[0]["line"] == 2


def test_build_ignores_preflight_warnings_and_zero_error_summaries(project):
    assert gate.parse_build_output(BUILD_OK) == []


def test_payload_only_bundle_skips_build_and_deploys(project, capsys):
    mod = project / "workspace" / "MyMod"
    (mod / "config.cpp").unlink()
    (mod / "Addons").mkdir()
    (mod / "Addons" / "payload.pbo").write_bytes(b"x")
    fake = FakeRuntime({"deploy.py": (0, "[OK]    Deployed to P:\\Mods\\@MyMod\\ - 1 copied\n")})
    rc, first, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert (rc, first) == (0, "PASS")
    assert not fake.ran("build.py")
    assert data["steps"][1]["result"].startswith("skipped: payload-only bundle")


def test_bundle_missing_bisign_fails(project, capsys):
    mod = project / "workspace" / "MyMod"
    (mod / "config.cpp").unlink()
    (mod / "Addons").mkdir()
    (mod / "Addons" / "payload.pbo").write_bytes(b"x")
    out = "[WARN] Workshop folder\n[WARN] payload.pbo has no matching .bisign - clients with signature verification enabled will reject it.\n[OK] Deployed\n"
    fake = FakeRuntime({"deploy.py": (0, out)})
    rc, _, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert rc == 1
    [f] = data["failures"]
    assert (f["category"], f["triage"]["id"]) == ("unsigned", "unsigned-payload")


def test_bundle_with_linker_config_builds_then_deploys(project, capsys):
    mod = project / "workspace" / "MyMod"
    (mod / "Addons").mkdir()
    (mod / "Addons" / "payload.pbo").write_bytes(b"x")
    fake = FakeRuntime({"build.py": (0, BUILD_OK), "deploy.py": (0, "[OK] Deployed\n")})
    rc, _, _ = run_main(["build", "MyMod"], fake, capsys)
    assert rc == 0
    names = [" ".join(c) for c in fake.calls]
    assert names.index(next(n for n in names if "build.py" in n)) < names.index(next(n for n in names if "deploy.py" in n))


def test_build_deploy_failure_fails(project, capsys):
    mod = project / "workspace" / "MyMod"
    (mod / "Addons").mkdir()
    (mod / "Addons" / "payload.pbo").write_bytes(b"x")
    fake = FakeRuntime({"build.py": (0, BUILD_OK), "deploy.py": (1, "[FAIL] could not copy payload.pbo: in use\n")})
    rc, _, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert rc == 1
    assert data["failures"][0]["text"].startswith("[FAIL] could not copy")


def test_build_text_output_first_line_is_verdict(project, capsys):
    out = "[FAIL] P:\\ is NOT mounted\n"
    fake = FakeRuntime({"build.py": (1, out)})
    rc = gate.main(["build", "MyMod"], rt=fake.runtime())
    text = capsys.readouterr().out.splitlines()
    assert rc == 1 and text[0] == "FAIL"
    assert any("known p-drive-not-mounted -> user" in line for line in text)


def test_build_fail_adds_source_findings(project, capsys):
    vest = project / "workspace" / "MyMod" / "scripts" / "4_World" / "vest.c"
    vest.write_text("modded class PlayerBase extends PlayerBase\n{\n}\n", encoding="utf-8")
    fake = FakeRuntime({"build.py": (1, "[FAIL] boom\n")})
    _, _, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert [s["id"] for s in data["source_findings"]] == ["modded-class-extends"]


def test_stop_failure_exits_2_with_error_line(project, capsys):
    fake = FakeRuntime({"build.py": (0, BUILD_OK)}, running=[1])
    fake.stop_rc = 5
    rc, first, data = run_main(["build", "MyMod", "--json"], fake, capsys)
    assert (rc, first, data["verdict"]) == (2, "ERROR", "ERROR")
    assert not fake.ran("build.py")


def test_no_project_exits_2(monkeypatch, capsys):
    def refuse():
        raise SystemExit(2)
    monkeypatch.setattr(gate.h, "resolve_project_dir", refuse)
    assert gate.main(["build", "MyMod"], rt=FakeRuntime().runtime()) == 2
    assert capsys.readouterr().out.startswith("ERROR")


def test_usage_error_exits_2(capsys):
    assert gate.main(["frobnicate"], rt=FakeRuntime().runtime()) == 2
    assert gate.main(["ingame", "MyMod", "--ready-pattern", "("], rt=FakeRuntime().runtime()) == 2


def test_unexpected_crash_is_error_exit_2(project, monkeypatch, capsys):
    """Any exception the gate does not expect is ERROR (exit 2), never Python's exit 1 (FAIL)."""
    def crash(*a, **k):
        raise KeyError("verdict")

    monkeypatch.setattr(gate, "gate_build", crash)
    rc, first, data = run_main(["build", "MyMod", "--json"], FakeRuntime(), capsys)
    assert (rc, first) == (2, "ERROR")
    assert data["error"] == "gate crashed: KeyError: 'verdict'"


# --- in-game gate ------------------------------------------------------------------

def session(fake: FakeRuntime, proj: Path, server_lines=(), client_lines=(), ready_at: float | None = 4,
            later_client: tuple[float, tuple[str, ...]] | None = None) -> None:
    """Fake launch: create this session's logs; the ready line shows up at `ready_at`."""
    srpt = server_dir(proj) / "DayZDiag_x64_2026-10-20_12-00-00.RPT"
    crpt = client_dir(proj) / "DayZDiag_x64_2026-10-20_12-00-30.RPT"
    cscript = client_dir(proj) / "script_2026-10-20_12-00-31.log"

    def launch():
        append(srpt, "CLI params: server filePatching mod P:\\Mods\\@MyMod", *server_lines)
        append(crpt, "CLI params: connect 127.0.0.1 mod P:\\Mods\\@MyMod")
        append(cscript, "SCRIPT       : Module: Game; loaded 415x files", *client_lines)

    fake.on_launch = launch
    if ready_at is not None:
        fake.at(ready_at, lambda: append(cscript, READY))
    if later_client:
        fake.at(later_client[0], lambda: append(cscript, *later_client[1]))


def vanilla_baseline(proj: Path, *lines: str) -> None:
    """An older server session without @MyMod, plus its script log."""
    append(server_dir(proj) / "DayZDiag_x64_2026-10-19_09-00-00.RPT", "CLI params: server filePatching mod P:\\Mods\\@CF", *lines)
    append(server_dir(proj) / "script_2026-10-19_09-00-02.log", "SCRIPT : vanilla start")


def ingame(fake: FakeRuntime, capsys, *extra: str) -> tuple[int, str, dict]:
    return run_main(["ingame", "MyMod", "--json", "--settle", "6", *extra], fake, capsys)


def test_ingame_pass_stops_session_and_reports_ready(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()}, running=[7])
    session(fake, project)
    rc, first, data = ingame(fake, capsys)
    assert (rc, first) == (0, "PASS")
    assert data["ready"]["text"] == READY
    assert fake.stops() == 2  # the leftover session before, ours after
    assert fake.running == []
    launch_cmd = next(c for c in fake.calls if "launch.py" in " ".join(c))
    assert launch_cmd[2:] == ["MyMod", "--server", "chernarus", "--port", "2302"]


def test_ingame_result_is_the_last_test_on_the_health_page(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project)
    ingame(fake, capsys)
    data = gate.health.health(project, "MyMod")
    assert (data["last_test"]["kind"], data["last_test"]["verdict"]) == ("ingame", "PASS")


def test_ingame_reads_only_lines_written_after_start(project, capsys):
    old = client_dir(project) / "script_2026-10-20_12-00-31.log"
    append(old, "NULL pointer to instance", "Stack trace:", "MyMod/scripts/4_World/vest.c:3")
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project)
    rc, _, data = ingame(fake, capsys)
    assert rc == 0, data["failures"]


def test_ingame_null_pointer_in_mod_fails_with_stack_and_known_triage(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, later_client=(6, (
        "SCRIPT    (E): NULL pointer to instance",
        "Class:      'MyModVestHelper'",
        "Function: 'Init'",
        "Stack trace:",
        "MyMod/scripts/4_World/vest.c:2",
        "scripts/3_Game/dayzgame.c:327",
    )))
    rc, first, data = ingame(fake, capsys)
    assert (rc, first) == (1, "FAIL")
    [f] = data["failures"]
    assert f["category"] == "null_pointer"
    assert f["file"].endswith("script_2026-10-20_12-00-31.log")
    assert "MyMod/scripts/4_World/vest.c" in f["points_to"]
    assert len(f["context"]) == 5
    assert (f["triage"]["status"], f["triage"]["id"]) == ("known", "null-pointer")


def test_ingame_null_pointer_outside_mod_is_only_a_warning(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, client_lines=(
        "NULL pointer to instance", "Class:      'LoginTimeStatic'", "Stack trace:", "scripts/3_Game/dayzgame.c:327",
    ))
    rc, _, data = ingame(fake, capsys)
    assert rc == 0
    assert data["warnings"][0]["category"] == "null_pointer"


def test_ingame_mod_class_name_counts_as_naming_the_mod(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, server_lines=("Warning Message: No entry 'bin\\config.bin/CfgVehicles/MyMod_Vest.weight'.",))
    rc, _, data = ingame(fake, capsys)
    assert rc == 1
    assert data["failures"][0]["triage"]["id"] == "missing-config-entry"


def test_ingame_modded_vanilla_class_does_not_count_as_the_mods(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, client_lines=("NULL pointer to instance", "Class:      'PlayerBase'"))
    rc, _, _ = ingame(fake, capsys)
    assert rc == 0


def test_ingame_vanilla_noise_in_baseline_is_skipped(project, capsys):
    texture = "Warning Message: Cannot load texture 'dz\\gear\\camping\\data\\tent_medium_packed_co.paa'."
    vanilla_baseline(project, "10:00:00.000 " + texture)
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, server_lines=("12:00:01.500 " + texture,))
    rc, _, data = ingame(fake, capsys)
    assert rc == 0
    assert [n["text"] for n in data["noise"]] == ["12:00:01.500 " + texture]
    assert any(b.endswith("DayZDiag_x64_2026-10-19_09-00-00.RPT") for b in data["baseline"])
    assert any(b.endswith("script_2026-10-19_09-00-02.log") for b in data["baseline"])


def test_ingame_unnamed_error_is_a_warning_without_baseline(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, server_lines=("Warning Message: Cannot open object dz\\x\\y.p3d",))
    rc, _, data = ingame(fake, capsys)
    assert rc == 0
    assert data["baseline"] == []
    assert data["warnings"][0]["category"] == "missing_model"


def test_ingame_unnamed_error_missing_from_baseline_fails(project, capsys):
    vanilla_baseline(project, "Warning Message: Cannot open object dz\\other.p3d")
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, server_lines=("Warning Message: Cannot open object dz\\x\\y.p3d",))
    rc, _, data = ingame(fake, capsys)
    assert rc == 1
    assert data["failures"][0]["triage"]["id"] == "missing-model"


def test_ingame_session_with_the_mod_is_not_a_baseline(project, capsys):
    append(server_dir(project) / "DayZDiag_x64_2026-10-19_09-00-00.RPT",
           "CLI params: server mod P:\\Mods\\@MyMod", "Warning Message: Cannot open object dz\\x\\y.p3d")
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, server_lines=("Warning Message: Cannot open object dz\\x\\y.p3d",))
    _, _, data = ingame(fake, capsys)
    assert data["baseline"] == []
    assert data["noise"] == []


def test_ingame_timeout_without_ready_fails_and_still_stops(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, ready_at=None)
    rc, _, data = ingame(fake, capsys, "--timeout", "20")
    assert rc == 1
    assert data["failures"][0]["category"] == "no_ready"
    assert fake.now >= 20
    assert fake.stops() == 1 and fake.running == []


def test_ingame_process_exit_is_a_crash_and_stops_early(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, ready_at=None)
    fake.at(4, lambda: fake.dead.add(111))
    rc, _, data = ingame(fake, capsys)
    assert rc == 1
    assert data["failures"][0]["category"] == "crash"
    assert "PID 111" in data["failures"][0]["text"]
    assert fake.now < 10


def test_ingame_crash_log_fails(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, ready_at=None)
    fake.at(4, lambda: append(client_dir(project) / "crash_2026-10-20_12-01-00.log",
                              "NULL pointer to instance", "Stack trace:", "MyMod/scripts/4_World/vest.c:2"))
    rc, _, data = ingame(fake, capsys)
    assert rc == 1
    cats = [f["category"] for f in data["failures"]]
    assert cats[0] == "crash" and "null_pointer" in cats
    assert fake.now < 10


def test_ingame_compile_error_stops_early(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, ready_at=None, server_lines=(
        'SCRIPT    (E): @"MyMod/scripts/4_World/vest.c,3": Unknown type \'Foo\'',
        'SCRIPT    (E): Can\'t compile "World" script module!',
    ))
    rc, _, data = ingame(fake, capsys)
    assert rc == 1
    assert [f["triage"]["id"] for f in data["failures"]] == ["script-unknown-type"]
    # The module line names nothing of the mod and there is no vanilla run: a warning.
    assert [w["category"] for w in data["warnings"]] == ["compile"]
    assert fake.now <= gate.POLL_S  # only the stop step waited


def test_ingame_launch_failure_fails_with_known_fix(project, capsys):
    fake = FakeRuntime({"launch.py": (1, "[FAIL] Instance 'chernarus' is not set up. Missing:\n          - server cfg\n")})
    rc, _, data = ingame(fake, capsys)
    assert rc == 1
    f = data["failures"][0]
    assert f["triage"]["id"] == "instance-not-set-up"
    assert f["triage"]["fix"] == "Run /dayz-add-server chernarus."
    assert data.get("ready") is None


def test_ingame_deps_go_first_without_at_sign(project, capsys):
    cfg = project / "workspace" / "MyMod" / "config.cpp"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace('{"DZ_Data"}', '{"DZ_Data", "JM_CF_Scripts"}'), encoding="utf-8")
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project)
    rc, _, _ = ingame(fake, capsys, "--deps", "@CF", "Dabs", "--server", "livonia")
    launch_cmd = next(c for c in fake.calls if "launch.py" in " ".join(c))
    assert launch_cmd[2:] == ["CF", "Dabs", "MyMod", "--server", "livonia", "--port", "2302"]


def test_ingame_non_vanilla_required_addons_need_deps(project, capsys):
    cfg = project / "workspace" / "MyMod" / "config.cpp"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace('{"DZ_Data"}', '{"DZ_Data", "JM_CF_Scripts"}'), encoding="utf-8")
    fake = FakeRuntime({"launch.py": launch_ok()})
    rc, first, data = ingame(fake, capsys)
    assert (rc, first) == (2, "ERROR")
    assert "JM_CF_Scripts" in data["error"]
    assert not fake.ran("launch.py")


def test_ingame_stop_failure_after_session_exits_2(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project)
    fake.stop_rc = 1
    rc, first, _ = ingame(fake, capsys)
    assert (rc, first) == (2, "ERROR")


def test_ingame_custom_ready_pattern(project, capsys):
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, ready_at=None, later_client=(4, ("SCRIPT : [MyMod] ready",)))
    rc, _, data = ingame(fake, capsys, "--ready-pattern", r"\[MyMod\] ready")
    assert rc == 0
    assert data["ready"]["text"] == "SCRIPT : [MyMod] ready"


def test_ingame_repeated_lines_are_deduped_with_count(project, capsys):
    line = "Warning Message: Cannot load texture 'mymod\\data\\vest_co.paa'."
    fake = FakeRuntime({"launch.py": launch_ok()})
    session(fake, project, server_lines=(line, line, line))
    _, _, data = ingame(fake, capsys)
    [f] = data["failures"]
    assert f["count"] == 3 and f["triage"]["owner_agent"] == "dayz-asset-specialist"


# --- pieces ------------------------------------------------------------------------

def test_log_tail_holds_back_partial_line(tmp_path):
    log = tmp_path / "script_x.log"
    log.write_text("old line\n", encoding="utf-8")
    tail = gate.LogTail([tmp_path], gate.snapshot([tmp_path]))
    with log.open("a", encoding="utf-8") as f:
        f.write("first\nsec")
    assert [t for _, _, t in tail.poll()] == ["first"]
    with log.open("a", encoding="utf-8") as f:
        f.write("ond\n")
    assert [(n, t) for _, n, t in tail.poll()] == [(3, "second")]
    with log.open("a", encoding="utf-8") as f:
        f.write("no newline")
    assert [t for _, _, t in tail.poll(final=True)] == ["no newline"]


def test_config_classes_takes_only_top_level_definitions():
    text = (
        "// class Commented: X {}\nclass CfgPatches { class MyMod_Patch { requiredAddons[] = {}; }; };\n"
        "class CfgVehicles { class Vest_Base; class MyVest: Vest_Base { class DamageSystem { class GlobalHealth {}; }; }; };"
    )
    assert gate.config_classes(text) == {"MyMod_Patch", "MyVest"}


def test_mod_identity_uses_prefix_and_declared_classes(project):
    mod_dir = project / "workspace" / "MyMod"
    (mod_dir / "$PBOPREFIX$").write_text("MyMod\\data", encoding="utf-8")
    ident = gate.mod_identity("MyMod", mod_dir)
    assert ident.names("mymod\\data\\vest_co.paa")
    assert ident.names("Class: 'MyModVestHelper'")
    assert ident.names("P:\\Mods\\@MyMod")
    assert not ident.names("Class: 'PlayerBase'")
    assert not ident.names("dz\\gear\\vest_co.paa")
    assert not ident.names("MyModder thing")
    assert ident.required_addons == ["DZ_Data"]


def test_group_entries_attaches_stack_and_stops_at_next_message(tmp_path):
    p = tmp_path / "script.log"
    lines = [(p, 1, "NULL pointer to instance"), (p, 2, "Function: 'Init'"), (p, 3, "Stack trace:"),
             (p, 4, "MyMod/scripts/4_World/vest.c:2"), (p, 5, "SCRIPT       : next message"),
             (p, 6, "scripts/3_Game/x.c:1")]
    [entry] = gate.group_entries(lines)
    assert entry["context"] == ["Function: 'Init'", "Stack trace:", "MyMod/scripts/4_World/vest.c:2"]
