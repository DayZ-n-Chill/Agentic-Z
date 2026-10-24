"""Tests for health.py: storing results, open findings, history and both page formats. No DayZ needed."""
import importlib.util
import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("dayz_health_under_test", HERE / "health.py")
health = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(health)

T0 = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def project(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    (proj / "workspace" / "MyVest").mkdir(parents=True)
    monkeypatch.setattr(health.h, "resolve_project_dir", lambda: proj)
    return proj


def gate_report(mode, verdict, failures=(), warnings=(), lint=None, checks=None):
    report = {"verdict": verdict, "mode": mode, "mod": "MyVest", "steps": [], "failures": list(failures),
              "warnings": list(warnings), "noise": [], "warnings_not_listed": 0}
    if lint:
        report["lint"] = lint
    if checks is not None:
        report["checks"] = checks
    return report


def failure(text, file="workspace/MyVest/config.cpp", line=5, category="build_error", triage=None):
    return {"category": category, "file": file, "line": line, "text": text, "context": [], "points_to": [],
            "count": 1, "triage": triage or {"status": "new"}}


KNOWN = {"status": "known", "id": "missing-texture", "owner_agent": "dayz-asset-specialist", "fix": "Pack the .paa."}

REVIEW_TEXT = """FAIL
CRITICAL workspace/MyVest/config.cpp:12: hiddenSelectionsTextures points at a missing file, pack it -> dayz-asset-specialist
WARN workspace/MyVest/scripts/4_World/vest.c:3: global state in a modded class, move it to a member -> dayz-script-specialist
NIT workspace/MyVest/config.cpp:30: displayName is not localized -> dayz-config-specialist
Checked config.cpp, scripts and textures.
"""


def fixture_history(proj):
    """An old failing build, a later passing build with lint, an in-game FAIL and a behavior run."""
    health.record_gate(proj, gate_report("build", "FAIL", [failure("Cannot open file vest_co.paa", triage=KNOWN)],
                                         lint={"verdict": "PASS", "errors": 0, "warnings": 0}), T0)
    health.record_gate(proj, gate_report("build", "PASS", lint={"verdict": "PASS", "errors": 0, "warnings": 1},
                                         warnings=[failure("[lint:suffix] vest.paa has no suffix", category="lint",
                                                           triage=None)]),
                       T0 + timedelta(hours=1))
    health.record_gate(proj, gate_report("ingame", "FAIL", [failure("SCRIPT (E): NULL pointer in MyVest_Carrier",
                                                                    file="!ClientDiagLogs/script.log", line=40,
                                                                    category="null_pointer")]),
                       T0 + timedelta(hours=2))
    checks = [{"id": "vest-spawns", "status": "PASS", "reason": "", "file": None, "line": None, "text": ""},
              {"id": "vest-wear", "status": "FAIL", "reason": "no slot", "file": None, "line": None, "text": ""}]
    health.record_gate(proj, gate_report("behavior", "FAIL", [failure("[behavior] FAIL vest-wear no slot", file="log",
                                                                      line=9, category="behavior")], checks=checks),
                       T0 + timedelta(hours=3))


def test_gate_report_stores_one_file_per_result_and_lint_separately(project):
    fixture_history(project)
    files = sorted((project / ".server" / "!Health" / "MyVest" / "results").glob("*.json"))
    kinds = [json.loads(f.read_text(encoding="utf-8"))["kind"] for f in files]
    # Oldest first: each build's lint step ran before the build, so it is listed before it.
    assert kinds == ["lint", "build", "lint", "build", "ingame", "behavior"]
    first = json.loads(files[0].read_text(encoding="utf-8"))
    assert first["schema"] == 1 and first["mod"] == "MyVest" and first["time"] == "2026-10-20T12:00:00Z"
    assert json.loads(files[1].read_text(encoding="utf-8"))["time"] == first["time"]


def test_history_lists_a_builds_lint_step_before_the_build(project, capsys):
    report = gate_report("build", "PASS", lint={"verdict": "PASS", "errors": 0, "warnings": 0})
    assert health.main(["record", "MyVest", "build"], stdin=io.StringIO(json.dumps(report))) == 0
    assert [r["kind"] for r in health.health(project, "MyVest")["history"]] == ["build", "lint"]  # newest first


def test_health_has_last_build_last_test_open_findings_and_history(project):
    fixture_history(project)
    data = health.health(project, "MyVest")
    assert data["last_build"]["verdict"] == "PASS"
    assert data["last_test"]["kind"] == "behavior"
    assert len(data["history"]) == 6
    assert data["history"][0]["kind"] == "behavior"
    texts = [f["text"] for f in data["open_findings"]]
    # The old build failure is fixed by the newer passing build, so it is not open.
    assert "Cannot open file vest_co.paa" not in texts
    assert "SCRIPT (E): NULL pointer in MyVest_Carrier" in texts
    assert "[behavior] FAIL vest-wear no slot" in texts
    assert "[lint:suffix] vest.paa has no suffix" in texts
    # Failures come before warnings.
    assert data["open_findings"][-1]["severity"] == "warn"


def test_known_failure_keeps_owner_and_fix_new_goes_to_debugger(project):
    health.record_gate(project, gate_report("build", "FAIL", [failure("Cannot open file vest_co.paa", triage=KNOWN),
                                                              failure("odd line", line=9)]), T0)
    found = {f["text"]: f for f in health.health(project, "MyVest")["open_findings"]}
    assert found["Cannot open file vest_co.paa"]["owner"] == "dayz-asset-specialist"
    assert found["Cannot open file vest_co.paa"]["fix"] == "Pack the .paa."
    assert found["odd line"]["owner"] == "dayz-mod-debugger"


def test_lint_stop_is_summarized_on_the_build(project):
    lint_fail = failure("[lint:cfgpatches-field] no units[]", category="lint")
    health.record_gate(project, gate_report("build", "FAIL", [lint_fail],
                                            lint={"verdict": "FAIL", "errors": 1, "warnings": 0}), T0)
    data = health.health(project, "MyVest")
    assert data["last_build"]["summary"] == "stopped at lint, nothing was packed"
    assert data["latest"]["lint"]["verdict"] == "FAIL"
    # Same finding in the lint and the build result is listed once.
    assert [f["text"] for f in data["open_findings"]] == ["[lint:cfgpatches-field] no units[]"]


def test_markdown_page_from_fixture_history(project):
    fixture_history(project)
    _, md, page = health.render(project, "MyVest")
    text = md.read_text(encoding="utf-8")
    assert text.startswith("# MyVest health")
    assert "* Last build: PASS (Build, 2026-10-20 13:00:00 UTC)" in text
    assert "* Last test: FAIL (Behavior test, 2026-10-20 15:00:00 UTC, 1 of 2 checks passed)" in text
    assert "## Open findings" in text and "NULL pointer in MyVest_Carrier" in text
    assert "| vest-wear | FAIL | no slot |" in text
    assert "| Review | never run | | | |" in text
    history = text.split("## History", 1)[1]
    assert history.index("Behavior test") < history.index("In-game test") < history.index("Build")


def test_html_page_is_escaped_and_accessible(project):
    health.record_gate(project, gate_report("ingame", "FAIL", [failure("<script>alert(1)</script> & co")]), T0)
    _, _, page = health.render(project, "MyVest")
    text = page.read_text(encoding="utf-8")
    assert text.startswith("<!doctype html>")
    assert '<html lang="en">' in text and "<title>MyVest health</title>" in text
    assert "<script>alert" not in text and "&lt;script&gt;alert(1)&lt;/script&gt; &amp; co" in text
    assert '<th scope="col">' in text and "prefers-color-scheme: dark" in text
    # Results are written as words, not shown by color alone.
    assert '<span class="FAIL">FAIL</span>' in text


def test_page_without_results_says_so(project):
    _, md, page = health.render(project, "Empty")
    assert "No gate results yet" in md.read_text(encoding="utf-8")
    assert "No gate results yet" in page.read_text(encoding="utf-8")


def test_markdown_cells_escape_pipes(project):
    health.record_gate(project, gate_report("build", "FAIL", [failure("a | b")]), T0)
    _, md, _ = health.render(project, "MyVest")
    assert "a \\| b" in md.read_text(encoding="utf-8")


def test_old_results_are_pruned(project, monkeypatch):
    monkeypatch.setattr(health, "KEEP", 3)
    for i in range(5):
        health.store(project, "MyVest", {"kind": "build", "verdict": "PASS", "findings": [], "warnings": 0},
                     T0 + timedelta(minutes=i))
    files = sorted((project / ".server" / "!Health" / "MyVest" / "results").glob("*.json"))
    assert len(files) == 3
    assert json.loads(files[0].read_text(encoding="utf-8"))["time"] == "2026-10-20T12:02:00Z"


def test_unreadable_result_files_are_skipped(project):
    health.store(project, "MyVest", {"kind": "build", "verdict": "PASS", "findings": [], "warnings": 0}, T0)
    (project / ".server" / "!Health" / "MyVest" / "results" / "zzz-build.json").write_text("{not json", encoding="utf-8")
    assert len(health.load_results(project, "MyVest")) == 1


@pytest.mark.parametrize("name", ["..", "../x", "a/b", "a\\b", "", "My Vest"])
def test_bad_mod_names_are_refused(project, name):
    with pytest.raises(health.HealthError):
        health.mod_dir(project, name)


# --- parsing what `record` is given -------------------------------------------------

def test_review_text_is_parsed():
    result = health.parse_report("review", REVIEW_TEXT)
    assert result["verdict"] == "FAIL"
    sev = [(f["severity"], f["file"], f["line"], f["owner"]) for f in result["findings"]]
    assert sev == [("fail", "workspace/MyVest/config.cpp", 12, "dayz-asset-specialist"),
                   ("warn", "workspace/MyVest/scripts/4_World/vest.c", 3, "dayz-script-specialist"),
                   ("nit", "workspace/MyVest/config.cpp", 30, "dayz-config-specialist")]
    assert result["findings"][0]["text"] == "hiddenSelectionsTextures points at a missing file, pack it"
    assert result["warnings"] == 2


def test_review_without_verdict_line_is_refused():
    with pytest.raises(health.HealthError):
        health.parse_report("review", "WARN a.c:1: x -> dayz-script-specialist\n")


def test_lint_json_is_parsed():
    lint = {"verdict": "FAIL", "mod": "MyVest", "errors": 1, "warnings": 1, "findings": [
        {"rule": "cfgpatches-field", "severity": "error", "file": "workspace/MyVest/config.cpp", "line": 5,
         "message": "no units[]", "text": "[lint:cfgpatches-field] no units[]",
         "triage": {"status": "known", "owner_agent": "dayz-config-specialist", "fix": "Add units[]."}},
        {"rule": "suffix", "severity": "warning", "file": "a.paa", "line": None, "message": "no suffix",
         "text": "[lint:suffix] no suffix", "triage": {"status": "known", "owner_agent": "dayz-asset-specialist", "fix": "x"}},
    ]}
    result = health.parse_report("lint", "FAIL\n" + json.dumps(lint))
    assert [(f["severity"], f["owner"]) for f in result["findings"]] == [("fail", "dayz-config-specialist"),
                                                                          ("warn", "dayz-asset-specialist")]


def test_gate_json_must_match_the_kind():
    text = "PASS\n" + json.dumps(gate_report("build", "PASS"))
    assert health.parse_report("build", text)["kind"] == "build"
    with pytest.raises(health.HealthError):
        health.parse_report("ingame", text)


def test_error_verdict_is_not_stored():
    with pytest.raises(health.HealthError):
        health.parse_report("build", 'ERROR\n{"verdict": "ERROR", "error": "no project"}')


# --- cli ----------------------------------------------------------------------------

def test_cli_record_review_from_stdin_then_show(project, capsys):
    assert health.main(["record", "MyVest", "review"], stdin=io.StringIO(REVIEW_TEXT)) == 0
    out = capsys.readouterr().out
    assert out.startswith("OK\n") and "recorded" in out
    assert health.main(["MyVest", "--json"]) == 0
    first, _, rest = capsys.readouterr().out.partition("\n")
    data = json.loads(rest)
    assert first == "OK"
    summary = data["mods"][0]
    assert summary["mod"] == "MyVest" and summary["results"] == 1 and len(summary["open_findings"]) == 3
    assert (project / summary["markdown"]).is_file() and (project / summary["html"]).is_file()


def test_cli_record_from_file(project, tmp_path, capsys):
    report = tmp_path / "gate.json"
    report.write_text("PASS\n" + json.dumps(gate_report("ingame", "PASS")), encoding="utf-8")
    assert health.main(["record", "MyVest", "ingame", str(report)]) == 0
    assert health.health(project, "MyVest")["last_test"]["verdict"] == "PASS"


def test_cli_all_lists_every_mod_with_results(project, capsys):
    health.store(project, "ModA", {"kind": "build", "verdict": "PASS", "findings": [], "warnings": 0}, T0)
    health.store(project, "ModB", {"kind": "lint", "verdict": "FAIL", "findings": [], "warnings": 0}, T0)
    assert health.main(["show", "--all", "--json"]) == 0
    data = json.loads(capsys.readouterr().out.partition("\n")[2])
    assert [m["mod"] for m in data["mods"]] == ["ModA", "ModB"]


def test_cli_all_with_nothing_stored(project, capsys):
    assert health.main(["--all"]) == 0
    assert "no gate results stored yet" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["show"], ["show", "MyVest", "--all"], ["record", "MyVest", "frobnicate"],
                                  ["record", "../x", "build"]])
def test_cli_usage_errors_exit_2(project, capsys, argv):
    assert health.main(argv, stdin=io.StringIO("PASS\n{}")) == 2
    assert not list(project.glob(".server/!Health/*/results/*.json"))


@pytest.mark.parametrize("argv", [["--bogus"], ["record"], ["record", "MyVest"], ["MyVest", "--bogus"],
                                  ["record", "MyVest", "frobnicate"]])
def test_cli_bad_arguments_print_error_first(project, capsys, argv):
    assert health.main(argv, stdin=io.StringIO("PASS\n{}")) == 2
    out = capsys.readouterr().out
    assert out.startswith("ERROR\n") and "usage:" in out


def test_cli_bad_arguments_with_json_print_error_json(project, capsys):
    assert health.main(["record", "--json"]) == 2
    first, _, rest = capsys.readouterr().out.partition("\n")
    assert first == "ERROR" and json.loads(rest)["verdict"] == "ERROR"


def test_cli_help_exits_0(project, capsys):
    assert health.main(["--help"]) == 0


def test_cli_show_unknown_mod_is_refused_and_creates_nothing(project, capsys):
    health.store(project, "ModA", {"kind": "build", "verdict": "PASS", "findings": [], "warnings": 0}, T0)
    assert health.main(["MyVst"]) == 2
    out = capsys.readouterr().out
    assert out.startswith("ERROR\n") and "workspace/MyVst/" in out and "ModA" in out
    assert not (project / ".server" / "!Health" / "MyVst").exists()


def test_cli_record_unknown_mod_is_refused_and_creates_nothing(project, capsys):
    text = "PASS\n" + json.dumps(gate_report("ingame", "PASS") | {"mod": "MyVst"})
    assert health.main(["record", "MyVst", "ingame"], stdin=io.StringIO(text)) == 2
    assert capsys.readouterr().out.startswith("ERROR")
    assert not (project / ".server" / "!Health" / "MyVst").exists()


def test_cli_show_mod_with_workspace_but_no_results(project, capsys):
    assert health.main(["MyVest"]) == 0
    assert "No gate results yet" in (project / ".server" / "!Health" / "MyVest" / "health.md").read_text(encoding="utf-8")


def test_cli_show_mod_with_results_but_no_workspace(project, capsys):
    health.store(project, "OldMod", {"kind": "build", "verdict": "PASS", "findings": [], "warnings": 0}, T0)
    assert health.main(["OldMod"]) == 0


def test_cli_bad_report_exits_2(project, capsys):
    assert health.main(["record", "MyVest", "build"], stdin=io.StringIO("not a report")) == 2
    assert capsys.readouterr().out.startswith("ERROR")


def test_cli_report_for_another_mod_exits_2(project, capsys):
    report = gate_report("ingame", "FAIL", [failure("SCRIPT (E): NULL pointer")])
    report["mod"] = "ModA"
    assert health.main(["record", "ModB", "ingame"], stdin=io.StringIO("FAIL\n" + json.dumps(report))) == 2
    out = capsys.readouterr().out
    assert out.startswith("ERROR") and "'ModA'" in out and "'ModB'" in out
    assert not list(project.glob(".server/!Health/*/results/*.json"))


def test_lint_report_for_another_mod_is_refused():
    lint = {"verdict": "PASS", "mod": "ModA", "errors": 0, "warnings": 0, "findings": []}
    assert health.parse_report("lint", json.dumps(lint), "ModA")["verdict"] == "PASS"
    with pytest.raises(health.HealthError, match="ModA"):
        health.parse_report("lint", json.dumps(lint), "ModB")


@pytest.mark.parametrize("line", ["ERROR workspace/MyVest/config.cpp:12: missing texture -> dayz-asset-specialist",
                                  "CRITICAL workspace/MyVest/config.cpp:12 missing texture",
                                  "critical workspace/MyVest/config.cpp:12: missing texture"])
def test_fail_review_with_no_parsed_finding_is_refused(project, capsys, line):
    text = f"FAIL\n{line}\nChecked config.cpp.\n"
    assert health.main(["record", "MyVest", "review"], stdin=io.StringIO(text)) == 2
    assert capsys.readouterr().out.startswith("ERROR")
    assert not list(project.glob(".server/!Health/*/results/*.json"))


def test_review_lines_that_do_not_parse_are_counted_and_warned(project, capsys):
    bad = "ERROR workspace/MyVest/config.cpp:40: requiredAddons misspelled -> dayz-config-specialist"
    text = REVIEW_TEXT + bad + "\n"
    result = health.parse_report("review", text)
    assert len(result["findings"]) == 3 and result["unparsed"] == [bad]
    assert "unparsed" not in health.parse_report("review", REVIEW_TEXT)  # the closing prose line is not a finding
    assert health.main(["record", "MyVest", "review"], stdin=io.StringIO(text)) == 0
    out = capsys.readouterr().out
    assert out.startswith("OK\n") and "warning: 1 review line(s)" in out and bad in out
    assert health.main(["record", "MyVest", "review", "--json"], stdin=io.StringIO(text)) == 0
    assert json.loads(capsys.readouterr().out.partition("\n")[2])["unparsed"] == [bad]


def test_cli_no_project_exits_2(monkeypatch, capsys):
    def refuse():
        raise SystemExit(2)
    monkeypatch.setattr(health.h, "resolve_project_dir", refuse)
    assert health.main(["MyVest"]) == 2
    assert capsys.readouterr().out.startswith("ERROR")


# --- visual runs from /dayz-gate visual -----------------------------------------

def visual_report(verdict="FAIL"):
    fails = [failure("[visual:diff] hud: 4.10% of pixels differ", file="output/x/hud.png", line=None,
                     category="visual")] if verdict == "FAIL" else []
    report = gate_report("visual", verdict, fails)
    report["shots"] = [
        {"id": "inventory", "status": "PASS", "reason": "", "ratio": 0.001, "capture": "c", "baseline": "b", "diff": None},
        {"id": "hud", "status": verdict, "reason": "", "ratio": 0.041, "capture": "c", "baseline": "b", "diff": "d"},
    ]
    return report


def test_record_gate_visual_is_stored_and_loaded(project):
    paths = health.record_gate(project, visual_report(), T0)
    assert len(paths) == 1 and paths[0].name.endswith("-visual.json")
    results = health.load_results(project, "MyVest")
    assert [r["kind"] for r in results] == ["visual"]
    assert results[0]["summary"] == "1 of 2 shots passed"
    assert [s["id"] for s in results[0]["shots"]] == ["inventory", "hud"]


def test_visual_run_counts_as_last_test_and_shows_its_shots(project):
    fixture_history(project)
    health.record_gate(project, visual_report(), T0 + timedelta(hours=4))
    data, md, page = health.render(project, "MyVest")
    assert data["last_test"]["kind"] == "visual"
    text = md.read_text(encoding="utf-8")
    assert "* Last test: FAIL (Visual test, 2026-10-20 16:00:00 UTC, 1 of 2 shots passed)" in text
    assert "## Visual shots (latest run)" in text
    assert "| hud | FAIL | 4.10% of pixels differ |" in text
    assert "| Visual test | FAIL |" in text
    assert "Visual shots (latest run)" in page.read_text(encoding="utf-8")


def test_cli_record_visual(project, tmp_path, capsys):
    report = tmp_path / "visual.json"
    report.write_text("PASS\n" + json.dumps(visual_report("PASS")), encoding="utf-8")
    assert health.main(["record", "MyVest", "visual", str(report)]) == 0
    assert health.load_results(project, "MyVest")[0]["kind"] == "visual"


# --- malformed and hand-recorded reports -----------------------------------------------

def _results_dir(proj):
    return proj / ".server" / "!Health" / "MyVest" / "results"


@pytest.mark.parametrize("kind, report, field", [
    ("review", {"verdict": "FAIL", "mod": "MyVest", "findings": [{"severity": "WARN", "message": "x"}]}, "text"),
    ("build", {"verdict": "FAIL", "mode": "build", "mod": "MyVest", "failures": [{"category": "build_error"}]}, "text"),
    ("lint", {"verdict": "FAIL", "mod": "MyVest", "findings": [{"severity": "error", "file": "a.c"}]}, "text"),
    ("behavior", {"verdict": "FAIL", "mode": "behavior", "mod": "MyVest", "checks": [{"status": "FAIL"}]}, "id"),
    ("build", {"verdict": "PASS", "mode": "build", "mod": "MyVest", "lint": {"verdict": "PASS"}}, "warnings"),
])
def test_cli_report_missing_a_field_exits_2_and_names_it(project, capsys, kind, report, field):
    # These used to raise an uncaught KeyError: a traceback with exit 1 instead of ERROR and exit 2.
    assert health.main(["record", "MyVest", kind], stdin=io.StringIO(json.dumps(report))) == 2
    out = capsys.readouterr().out
    assert out.startswith("ERROR\n") and repr(field) in out
    assert not _results_dir(project).exists()


def test_cli_report_with_a_wrong_type_exits_2(project, capsys):
    report = gate_report("build", "FAIL", [dict(failure("x"), count="many")])
    assert health.main(["record", "MyVest", "build"], stdin=io.StringIO(json.dumps(report))) == 2
    assert capsys.readouterr().out.startswith("ERROR\n")
    assert not _results_dir(project).exists()


def test_json_review_critical_is_a_failure_counted_once(project):
    report = {"verdict": "FAIL", "mod": "MyVest",
              "findings": [{"severity": "CRITICAL", "text": "missing texture", "file": "config.cpp", "line": 12}]}
    result = health.parse_report("review", json.dumps(report))
    assert result["findings"][0]["severity"] == "fail" and result["warnings"] == 0
    assert health.main(["record", "MyVest", "review"], stdin=io.StringIO(json.dumps(report))) == 0
    md = (project / ".server" / "!Health" / "MyVest" / "health.md").read_text(encoding="utf-8")
    assert "| Review | FAIL | 1 | 0 |" in md  # history row: one failure, no warning


@pytest.mark.parametrize("sev, stored", [("WARN", "warn"), ("warning", "warn"), ("NIT", "nit"), ("error", "fail")])
def test_json_review_severities_map_like_the_text_form(sev, stored):
    report = {"verdict": "FAIL", "findings": [{"severity": sev, "text": "x"}]}
    result = health.parse_report("review", json.dumps(report))
    assert result["findings"][0]["severity"] == stored
    assert result["warnings"] == (0 if stored == "fail" else 1)


def test_json_review_unknown_severity_is_refused():
    with pytest.raises(health.HealthError, match="severity"):
        health.parse_report("review", json.dumps({"verdict": "FAIL", "findings": [{"severity": "BAD", "text": "x"}]}))


def test_cli_hand_recorded_build_stores_its_lint_step(project, capsys):
    lint_warn = failure("[lint:suffix] vest.paa has no suffix", category="lint", triage=None)
    report = gate_report("build", "PASS", warnings=[lint_warn], lint={"verdict": "PASS", "errors": 0, "warnings": 1})
    assert health.main(["record", "MyVest", "build", "--json"], stdin=io.StringIO("PASS\n" + json.dumps(report))) == 0
    out = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert out["recorded"].endswith("-build.json") and out["also_recorded"][0].endswith("-lint.json")
    latest = health.health(project, "MyVest")["latest"]
    assert latest["lint"]["verdict"] == "PASS" and latest["lint"]["warnings"] == 1
    assert latest["lint"]["findings"][0]["text"] == "[lint:suffix] vest.paa has no suffix"
    assert latest["build"]["verdict"] == "PASS"


def test_hand_recorded_build_without_lint_stores_one_result():
    assert [r["kind"] for r in health.parse_reports("build", json.dumps(gate_report("build", "PASS")))] == ["build"]


def test_cli_stdin_with_byte_order_mark_is_read(project, capsys):
    assert health.main(["record", "MyVest", "review"], stdin=io.StringIO("\ufeff" + REVIEW_TEXT)) == 0
    assert capsys.readouterr().out.startswith("OK\n")
    assert health.load_results(project, "MyVest")[0]["verdict"] == "FAIL"


def test_json_report_followed_by_trailing_text_is_parsed():
    text = "PASS\n" + json.dumps(gate_report("build", "PASS")) + "\nBuild finished in 12s.\n"
    assert health.parse_report("build", text)["verdict"] == "PASS"


@pytest.mark.parametrize("quote", ["has an empty body {}", 'quotes {"a": 1} from the config'])
def test_text_review_whose_finding_quotes_braces_is_parsed_as_text(project, capsys, quote):
    text = f"FAIL\nCRITICAL workspace/MyVest/a.c:12: modded class Foo {quote}, add the override -> dayz-script-specialist\n"
    result = health.parse_report("review", text)
    assert result["verdict"] == "FAIL" and result["findings"][0]["line"] == 12 and quote in result["findings"][0]["text"]
    assert health.main(["record", "MyVest", "review"], stdin=io.StringIO(text)) == 0
    assert health.load_results(project, "MyVest")[0]["verdict"] == "FAIL"


def test_json_review_with_leading_whitespace_is_still_json():
    report = {"verdict": "PASS", "findings": [{"severity": "NIT", "text": "x"}]}
    assert health.parse_report("review", "\n  " + json.dumps(report))["findings"][0]["severity"] == "nit"
