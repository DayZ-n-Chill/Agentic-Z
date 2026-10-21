"""Tests for route.py: rule matching, fall-through, target existence. No network (Jev unkeyed or mocked)."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
_SPEC = importlib.util.spec_from_file_location("dayz_route_under_test", HERE / "route.py")
route = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(route)

CFG = route.load_rules()
NO_KEY: dict = {}


def decide(text, env=NO_KEY):
    return route.decide(text, CFG, env)


@pytest.mark.parametrize(
    "text, expected, args",
    [
        ("build MyVest", "dayz-build-pbo", {"mod": "MyVest"}),
        ("rebuild the pbo for Tactical_Gear", "dayz-build-pbo", {"mod": "Tactical_Gear"}),
        ("lint MyVest", "dayz-lint", {"mod": "MyVest"}),
        ("run the linter on my mod", "dayz-lint", None),
        ("launch the test server", "dayz-launch-test", None),
        ("test it in-game", "dayz-launch-test", None),
        ("stop", "dayz-stop-test", None),
        ("kill the dayz session", "dayz-stop-test", None),
        ("add my jacket to types.xml", "dayz-server-admin", None),
        ("make the AK spawn less often", "dayz-server-admin", None),
        ("fix the CfgPatches in config.cpp", "dayz-config-specialist", None),
        ("here's my log: 12:01 SCRIPT (E): NULL pointer to instance", "dayz-mod-debugger", None),
        ("run preflight", "dayz-preflight", None),
        ("build me a tactical vest mod with three retextures that spawns in military zones", "orchestrator", None),
        ("create a new backpack mod", "orchestrator", None),
        ("convert vest_camo_co.png to .paa and write an rvmat", "dayz-asset-specialist", None),
        ("the texture on my jacket looks washed out", "dayz-asset-specialist", None),
        ("import my DayZ Editor base into Terrain Builder", "dayz-map-specialist", None),
        ("add clutter to the forest surface in layers.cfg", "dayz-map-specialist", None),
        ("write a Workbench plugin that lists textures missing a suffix", "dayz-workbench-specialist", None),
        ("make a playable test build of MyVest and start a session", "dayz-build-engineer", None),
        ("update the README and changelog for MyVest", "dayz-docs-writer", None),
        ("turn https://www.figma.com/design/abc123/Trader?node-id=10-42 into a .layout", "figma-node-normalizer", None),
        ("build this Figma frame as my HUD", "figma-node-normalizer", None),
    ],
)
def test_rules_route_confidently(text, expected, args):
    d = decide(text)
    assert d["route"] == expected
    assert d["source"] == "rules"
    assert d["confidence"] >= CFG["threshold"]
    assert d["kind"] == CFG["targets"][expected]["kind"]
    assert d.get("args") == args


def test_orchestrator_is_a_team():
    assert decide("build me a vest mod")["kind"] == "team"


@pytest.mark.parametrize("text", ["build me a mod", "build a pbo", "build the config", "build it"])
def test_build_me_is_not_a_pbo_build(text):
    assert decide(text)["route"] != "dayz-build-pbo"


@pytest.mark.parametrize("text", ["build MyVest and then launch the test server", "what should I do next?"])
def test_multi_step_or_unknown_falls_through(text):
    d = decide(text)
    assert d == {"route": None, "next": "dayz-router", "note": d["note"]}
    assert "TYPESAFE_API_KEY not set" in d["note"]


def test_conflict_note_names_best_guess():
    d = decide("build MyVest and then launch the test server")
    assert "best guess" in d["note"]


def test_confident_rule_never_calls_jev(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("jev called")
    monkeypatch.setattr(route.jev, "route", boom)
    assert decide("stop", {"TYPESAFE_API_KEY": "k"})["route"] == "dayz-stop-test"


def test_confident_jev_result_is_used(monkeypatch):
    jev_decision = {"route": "dayz-ui-specialist", "kind": "agent", "confidence": 0.91, "source": "jev"}
    monkeypatch.setattr(route.jev, "route", lambda *a: (jev_decision, "jev: ok"))
    assert decide("make the inventory screen look nicer", {"TYPESAFE_API_KEY": "k"}) == jev_decision


def test_weak_jev_result_falls_through(monkeypatch):
    weak = {"route": "dayz-ui-specialist", "kind": "agent", "confidence": 0.4, "source": "jev"}
    monkeypatch.setattr(route.jev, "route", lambda *a: (weak, "jev: dayz-ui-specialist at 0.40"))
    d = decide("make it nicer", {"TYPESAFE_API_KEY": "k"})
    assert d["route"] is None and "below" in d["note"]


def test_every_rule_route_is_a_target():
    for rule in CFG["rules"]:
        assert rule["route"] in CFG["targets"]
        for pattern in rule["patterns"]:
            re.compile(pattern)


def test_every_target_is_a_real_skill_or_agent():
    for name, target in CFG["targets"].items():
        kind = target["kind"]
        if kind == "skill":
            assert (REPO / ".claude" / "skills" / name / "SKILL.md").is_file(), name
        elif kind == "agent":
            assert (REPO / ".claude" / "agents" / f"{name}.md").is_file(), name
        else:
            assert kind == "team", name
            assert (REPO / ".claude" / "agents" / f"{target['agent']}.md").is_file(), name


def test_router_agent_lists_exactly_the_targets():
    text = (REPO / ".claude" / "agents" / "dayz-router.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^- `([\w-]+)` \((?:skill|agent|team)\)", text, re.MULTILINE))
    assert listed == set(CFG["targets"])
    for name, target in CFG["targets"].items():
        assert f"- `{name}` ({target['kind']})" in text


def test_cli_json_and_text(monkeypatch):
    env = {k: v for k, v in __import__("os").environ.items() if k != "TYPESAFE_API_KEY"}
    out = subprocess.run([sys.executable, str(HERE / "route.py"), "build MyVest", "--json"],
                         capture_output=True, text=True, env=env, check=True).stdout
    assert json.loads(out)["args"] == {"mod": "MyVest"}
    out = subprocess.run([sys.executable, str(HERE / "route.py"), "what now?"],
                         capture_output=True, text=True, env=env, check=True).stdout
    assert "dayz-router" in out


def test_cli_rejects_empty_request():
    r = subprocess.run([sys.executable, str(HERE / "route.py"), "  "], capture_output=True, text=True)
    assert r.returncode == 2
