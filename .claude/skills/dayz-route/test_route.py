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
        ("conflict check MyVest", "dayz-conflict-check", {"mod": "MyVest"}),
        ("check my mod for conflicts with CF and Expansion", "dayz-conflict-check", None),
        ("do my classes collide with COT?", "dayz-conflict-check", None),
        ("run the linter on my mod", "dayz-lint", None),
        ("balance MyVest", "dayz-balance", {"mod": "MyVest"}),
        ("is my vest balanced against vanilla?", "dayz-balance", None),
        ("is my new rifle overpowered", "dayz-balance", None),
        ("compare my backpack stats with vanilla", "dayz-balance", None),
        ("launch the test server", "dayz-launch-test", None),
        ("test it in-game", "dayz-launch-test", None),
        ("stop", "dayz-stop-test", None),
        ("watch the logs while I test MyVest", "dayz-logwatch", None),
        ("tail the server script.log for errors", "dayz-logwatch", None),
        ("start logwatch", "dayz-logwatch", None),
        ("kill the dayz session", "dayz-stop-test", None),
        ("add my jacket to types.xml", "dayz-server-admin", None),
        ("make the AK spawn less often", "dayz-server-admin", None),
        ("fix the CfgPatches in config.cpp", "dayz-config-specialist", None),
        # Pasted log lines go to triage first; a crash described in words goes to the debugger.
        ("here's my log: 12:01 SCRIPT (E): NULL pointer to instance", "dayz-gate", {"mode": "triage"}),
        ("my server crashes on startup", "dayz-mod-debugger", None),
        ("run preflight", "dayz-preflight", None),
        ("run the behavior tests for MyVest", "dayz-gate", {"mod": "MyVest"}),
        ("behaviour check", "dayz-gate", None),
        ("run the visual test for MyVest", "dayz-gate", {"mod": "MyVest"}),
        ("compare the screenshots with the baseline", "dayz-gate", None),
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
        ("add a CfgWeapons class", "dayz-weapon-specialist", None),
        # A rule that names a file, a log or a tool keeps winning when the request also names an object.
        ("My car crashes the server, here is the RPT.", "dayz-mod-debugger", None),
        ("Make my rifle spawn rarely in military zones.", "dayz-server-admin", None),
        ("zombies spawn too much in types.xml", "dayz-server-admin", None),
        ("launch a test with my car", "dayz-launch-test", None),
        ("write a modded class for my rifle", "dayz-script-specialist", None),
        # Saved data and AI belong to their own specialists even when the request says modded class.
        ("write a modded class so my safe keeps its code after a restart", "dayz-persistence-specialist", None),
        ("write a modded class so my zombies patrol the town", "dayz-ai-specialist", None),
        ("review my vehicle mod", "dayz-mod-reviewer", None),
        ("preview gui/layouts/compass.layout at 4k", "dayz-layout-preview", None),
        ("show me a layout preview of my HUD", "dayz-layout-preview", None),
        ("render trader_menu.layout at different screen sizes", "dayz-layout-preview", None),
        ("show the health page for MyVest", "dayz-health", {"mod": "MyVest"}),
        ("what are the open review findings", "dayz-health", None),
        ("show me the last build results and the test history", "dayz-health", None),
        # Player health in a mod is not the health page.
        ("add a health bar to my HUD", "dayz-ui-specialist", None),
        ("run the upgrade guard on MyVest", "dayz-upgrade-guard", None),
        ("DayZ just updated, which of my classes broke?", "dayz-upgrade-guard", None),
        ("after the DayZ update, check my modded classes", "dayz-upgrade-guard", None),
        # Real preview widgets in a HUD or menu are UI work, not a layout preview.
        ("make a player preview panel in the hud", "dayz-ui-specialist", None),
        ("add an item preview widget to my inventory menu", "dayz-ui-specialist", None),
        # UI icons and the Dabs Framework MVC layer go to the UI specialist.
        ("pack my menu icons into an imageset", "dayz-ui-specialist", None),
        ("make a Dabs ScriptView for my trader panel", "dayz-ui-specialist", None),
        # Release texts and the server kit beat the docs writer and server admin rules they overlap.
        ("make the release pack for MyVest", "dayz-release-pack", {"mod": "MyVest"}),
        ("write the workshop description and changelog for my vest", "dayz-release-pack", None),
        ("build the server kit for MyVest", "dayz-server-kit", {"mod": "MyVest"}),
        ("zip the types.xml entries and cfgeconomycore lines for server owners", "dayz-server-kit", None),
        ("start MyRifle from the new weapon recipe", "dayz-recipe", {"recipe": "weapon"}),
        ("use the vest recipe for my plate carrier mod", "dayz-recipe", {"recipe": "vest"}),
        ("run /dayz-recipe craftable MyKit", "dayz-recipe", None),
        ("build me a weapon mod from a recipe for a new weapon", "dayz-recipe", {"recipe": "weapon"}),
        # Questions about how vanilla works get a cited answer, whatever they are about.
        ("how does vanilla handle food spoilage?", "dayz-ask", None),
        ("Where is bleeding started in vanilla?", "dayz-ask", None),
        ("what does vanilla use for the AKM recoil?", "dayz-ask", None),
        ("How does DayZ decide when food goes bad?", "dayz-ask", None),
        # Tool and setup skills: opening Workbench is not plugin work, packing files is not texture design.
        ("open Workbench on MyVest", "dayz-launch-workbench", {"mod": "MyVest"}),
        ("start workbench with vanilla dayz", "dayz-launch-workbench", None),
        ("add a test server for chernarus-hardcore", "dayz-add-server", None),
        ("create a test server for my mod", "dayz-add-server", None),
        ("refresh the mission after the update", "dayz-add-server", None),
        ("pack this texture", "dayz-pack-texture", None),
        ("run ImageToPAA on vest_co.png", "dayz-pack-texture", None),
        ("build an imageset for my HUD icons", "dayz-build-imageset", None),
        ("rebuild the imageset from .gui-sources", "dayz-build-imageset", None),
        ("set up COT admin on my test server", "dayz-cot-bootstrap", None),
        ("give me admin in Community Online Tools", "dayz-cot-bootstrap", None),
        ("init", "dayz-init", None),
        ("set up DayZ modding", "dayz-init", None),
        ("what's my next step?", "dayz-init", None),
    ],
)
def test_rules_route_confidently(text, expected, args):
    _assert_confident(text, expected, args)


# Tool skills that a nearby agent or skill cannot do: the object-builder agent cannot open
# Object Builder, and dayz-build-pbo runs AddonBuilder instead of copying prebuilt PBOs.
@pytest.mark.parametrize(
    "text, expected, args",
    [
        ("Open my vest.p3d in Object Builder", "dayz-launch-objectbuilder", None),
        ("launch Object Builder", "dayz-launch-objectbuilder", None),
        ("Copy these prebuilt PBOs to P:", "dayz-deploy-pbo", None),
        ("deploy the pbos for UmbrellaPack", "dayz-deploy-pbo", {"mod": "UmbrellaPack"}),
        ("audit my vest.p3d for collision problems", "dayz-p3d-audit", None),
        ("check the p3d and its model.cfg", "dayz-p3d-audit", None),
        ("split my types.xml into categories", "dayz-split-types", None),
        ("scope the session to MyVest", "dayz-scope-mod", {"mod": "MyVest"}),
        ("lift the scope", "dayz-scope-mod", None),
        # These used to fall through, or worse, "rebuild the search index" was a PBO build of a mod named "search".
        ("mount my P drive", "dayz-workdrive", None),
        ("unmount the work drive", "dayz-workdrive", None),
        ("P: is not mounted", "dayz-workdrive", None),
        ("rebuild the search index", "dayz-search-index", None),
        ("build the vanilla search index", "dayz-search-index", None),
        ("add the missing scaffold to MyVest", "dayz-add-scaffold", None),
        ("add a gproj to MyVest", "dayz-add-scaffold", None),
        ("create the P: link for MyVest", "dayz-add-scaffold", None),
        ("set up Object Builder", "dayz-setup-objectbuilder", None),
        ("Object Builder opens with broken panels", "dayz-setup-objectbuilder", None),
        ("show me the vanilla particle catalog", "dayz-particles", None),
        ("mount P:", "dayz-workdrive", None),
        ("mount the P: drive", "dayz-workdrive", None),
        ("download the search index", "dayz-search-download", None),
        ("get the prebuilt index", "dayz-search-download", None),
        ("install the statusline", "dayz-statusline", None),
        ("remove the dayz status line", "dayz-statusline", None),
    ],
)
def test_tool_skills_beat_their_neighbours(text, expected, args):
    _assert_confident(text, expected, args)


@pytest.mark.parametrize("text", ["is P: drive mounted", "check my environment"])
def test_checking_the_drive_is_still_preflight(text):
    assert decide(text)["route"] == "dayz-preflight"


@pytest.mark.parametrize("text", ["add smoke particles to my generator", "make a spark particle effect"])
def test_making_a_particle_effect_is_still_the_specialists(text):
    assert decide(text)["route"] == "dayz-audio-fx-specialist"


def test_debugging_a_particle_effect_is_the_specialists():
    # The router used to call dayz-particles lookup-only while the skill said "writing or debugging".
    assert decide("debug my smoke particle")["route"] == "dayz-audio-fx-specialist"


# Corrections used to have no route, so the router sent them to an unrelated handler at 0.6 or less.
@pytest.mark.parametrize("text", ["record a correction: never put scripts in 5_Mission",
                                  "remember this: always use the CfgPatches name from config.cpp",
                                  "never use hiddenSelections without a texture",
                                  "from now on, review every mod before you build it"])
def test_corrections_go_to_record_correction(text):
    _assert_confident(text, "dayz-record-correction", None)


@pytest.mark.parametrize("text", ["make the safe remember this code after a restart",
                                  "make the zombies never use doors"])
def test_remember_or_never_inside_a_request_is_not_a_correction(text):
    assert decide(text)["route"] != "dayz-record-correction"


def test_router_report_template_has_no_copyable_confidence():
    # A literal "confidence": 0.0 in the template can be copied by Haiku and drops every answer below 0.8.
    text = (REPO / ".claude" / "agents" / "dayz-router.md").read_text(encoding="utf-8")
    report = text.split("## Report", 1)[1]
    assert not re.search(r'"confidence"\s*:\s*\d', report)
    assert '"confidence": <score>' in report


@pytest.mark.parametrize("text", ["add named selections to my vest.p3d", "add a view LOD in Object Builder"])
def test_model_changes_still_go_to_object_builder(text):
    assert decide(text)["route"] == "dayz-object-builder"


def _assert_confident(text, expected, args):
    d = decide(text)
    assert d["route"] == expected
    assert d["source"] == "rules"
    assert d["confidence"] >= CFG["threshold"]
    assert d["kind"] == CFG["targets"][expected]["kind"]
    assert d.get("args") == args


# The sample requests the Agentic-Z guide gives for each specialist, short and long forms.
GUIDE_SAMPLES = [
    ("Make my safe keep its code and contents after a restart.", "dayz-persistence-specialist"),
    ("Make my safe keep its code and contents after a restart, and do not break saves from the last version.",
     "dayz-persistence-specialist"),
    ("Add guards that patrol my base and react to gunfire.", "dayz-ai-specialist"),
    ("Add a patrol of guards that walk a route around my military base and react to gunfire.", "dayz-ai-specialist"),
    ("Add a four door pickup with a bigger fuel tank.", "dayz-vehicle-specialist"),
    ("Add a four door pickup with its own doors and a bigger fuel tank.", "dayz-vehicle-specialist"),
    ("Add a hunting rifle that takes a five round magazine.", "dayz-weapon-specialist"),
    ("Add a scoped hunting rifle that takes a five round magazine and the vanilla long range optics.",
     "dayz-weapon-specialist"),
    ("Make a plate carrier in three colors.", "dayz-wearables-specialist"),
    ("Make a plate carrier with three colors that fits the vest slot and holds six items.", "dayz-wearables-specialist"),
    ("Make my bunker doors open and close.", "dayz-animation-specialist"),
    ("Make the doors on my bunker open and close when a player uses them.", "dayz-animation-specialist"),
    ("Give my generator a running sound and exhaust smoke.", "dayz-audio-fx-specialist"),
    ("Give my generator a running sound that fades with distance and a puff of exhaust smoke.",
     "dayz-audio-fx-specialist"),
    ("My crate falls through the floor. Fix it.", "dayz-physics-specialist"),
    ("My crate falls through the floor when I drop it. Fix it.", "dayz-physics-specialist"),
]


@pytest.mark.parametrize("text, expected", GUIDE_SAMPLES)
def test_guide_samples_reach_their_specialist(text, expected):
    d = decide(text)
    assert d["route"] == expected
    assert d["kind"] == "agent"
    assert d["confidence"] >= CFG["threshold"]


@pytest.mark.parametrize("text", ["add guards that spawn at my base and patrol it",
                                  "add a helicopter that spawns at the airfield"])
def test_spawn_alone_is_not_server_admin(text):
    d = decide(text)
    assert d["route"] != "dayz-server-admin"
    assert d["route"] in {"dayz-ai-specialist", "dayz-vehicle-specialist", None}


# Paste-in: what the user pastes decides the route, whatever else the message says.
PASTES = [
    ("My car crashes the server, here is the RPT:\n10:01:02 Unhandled exception\n10:01:02 Access violation",
     "dayz-gate", {"mode": "triage"}),
    ('SCRIPT    (E): @"MyMod/scripts/4_World/Vest.c,12": Unknown type \'Foo\'', "dayz-gate", {"mode": "triage"}),
    ('add these to types.xml:\n<type name="MyMod_Vest"><nominal>5</nominal></type>', "dayz-edit-types",
     {"mode": "merge"}),
    ("import https://github.com/Owner/MyVest please", "dayz-import-mod",
     {"source": "https://github.com/Owner/MyVest"}),
    ("work on github.com/Owner/MyVest/tree/dev.", "dayz-import-mod", {"source": "github.com/Owner/MyVest/tree/dev"}),
    ("build me a mod from https://steamcommunity.com/sharedfiles/filedetails/?id=1559212036", "dayz-import-mod",
     {"source": "https://steamcommunity.com/sharedfiles/filedetails/?id=1559212036"}),
    ("https://www.figma.com/design/abc123/Trader?node-id=10-42", "figma-node-normalizer", None),
]


@pytest.mark.parametrize("text, expected, args", PASTES)
def test_pastes_route_to_their_workflow(text, expected, args):
    d = decide(text)
    assert d["route"] == expected
    assert d["confidence"] >= CFG["threshold"]
    assert d.get("args") == args


@pytest.mark.parametrize("text", ["build PBOs for everything", "repack PBOs", "build pbo for everything",
                                  "rebuild the pbos"])
def test_plural_pbos_and_for_are_never_a_mod_name(text):
    d = decide(text)
    assert d.get("args", {}).get("mod", "").lower() not in {"pbos", "pbo", "for"}


def test_plural_pbos_for_a_mod_still_names_the_mod():
    assert decide("build the pbos for MyVest").get("args") == {"mod": "MyVest"}


# Without a mod name only the "and launch" rule used to match, so these went straight to
# dayz-launch-test at 0.85 and the build step was dropped.
@pytest.mark.parametrize("text", ["build MyVest and launch it", "build MyVest then test it", "rebuild and launch",
                                  "build it and test", "rebuild and launch the test server", "pack it then run it"])
def test_build_and_launch_is_two_steps(text):
    d = decide(text)
    assert d["route"] is None or d["confidence"] < CFG["threshold"]


# An absorbing rule used to keep full confidence over any other match, so a second step
# (a build, a lint, a types.xml edit) was silently dropped. A separate step is absorbed
# only by a rule whose own work includes it.
@pytest.mark.parametrize("text", ["build MyVest then show me the health page",
                                  "lint MyVest and check conflicts with CF",
                                  "here is my crash log and also add a types entry",
                                  "my server crashes, build MyVest again",
                                  "open Workbench on MyVest and build MyVest",
                                  "how does vanilla handle food? then lint MyVest"])
def test_an_absorbing_rule_never_drops_a_separate_step(text):
    d = decide(text)
    assert d == {"route": None, "next": "dayz-router", "note": d["note"]}
    assert "best guess" in d["note"]


# A step that is part of the winner's own work, or pasted content, still keeps full confidence.
@pytest.mark.parametrize(
    "text, expected, args",
    [
        ("make a playable test build of MyVest and launch it", "dayz-build-engineer", None),
        ("build me a vest mod and test it", "orchestrator", None),
        ("add a types.xml entry for my jacket", "dayz-server-admin", None),
        ("run the behavior tests for MyVest", "dayz-gate", {"mod": "MyVest"}),
        ("here's my log: 12:01 SCRIPT (E): NULL pointer to instance, then build MyVest", "dayz-gate",
         {"mode": "triage"}),
        ("remove the types entry for MyVest_Vest", "dayz-edit-types", None),
    ],
)
def test_steps_inside_the_winners_own_work_are_absorbed(text, expected, args):
    _assert_confident(text, expected, args)


def test_absorbs_lists_name_step_targets():
    for rule in CFG["rules"]:
        absorbs = rule.get("absorbs", False)
        assert isinstance(absorbs, bool) or absorbs == "all" or isinstance(absorbs, list), rule["route"]
        if isinstance(absorbs, list):
            for other in absorbs:
                assert CFG["targets"][other].get("step"), (rule["route"], other)


@pytest.mark.parametrize(
    "content, reason",
    [
        ("{not json", "not valid JSON"),
        ('{"threshold": 0.8, "conflict_factor": 0.5, "targets": {"a": {"kind": "skill"}},'
         ' "rules": [{"route": "a", "confidence": 0.9, "patterns": ["(unclosed"]}]}', "bad regex"),
        ('{"threshold": 0.8, "conflict_factor": 0.5, "targets": {},'
         ' "rules": [{"route": "a", "confidence": 0.9, "patterns": ["x"]}]}', "route is not in targets"),
        ('{"threshold": 0.8, "conflict_factor": 0.5, "targets": {"a": {"kind": "skill"}},'
         ' "rules": [{"route": "a", "confidence": 0.9, "absorbs": "yes", "patterns": ["x"]}]}', "absorbs must be"),
        ('{"targets": {}, "rules": []}', "missing or malformed field"),
    ],
)
def test_broken_rules_json_exits_1_with_one_line(tmp_path, monkeypatch, capsys, content, reason):
    bad = tmp_path / "rules.json"
    bad.write_text(content, encoding="utf-8")
    with pytest.raises(route.RulesError, match=reason):
        route.load_rules(bad)
    monkeypatch.setattr(route, "RULES", bad)
    assert route.main(["build MyVest"]) == 1
    err = capsys.readouterr().err.strip()
    assert err.startswith("dayz-route: rules.json:") and reason in err
    assert "\n" not in err and "Traceback" not in err


def test_missing_rules_json_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(route, "RULES", tmp_path / "rules.json")
    assert route.main(["build MyVest"]) == 1
    assert capsys.readouterr().err.startswith("dayz-route: rules.json: cannot read")


def test_a_crash_after_an_update_is_still_the_debuggers():
    assert decide("my server crashes after the DayZ update")["route"] == "dayz-mod-debugger"


@pytest.mark.parametrize("text", ["add a crafting recipe for a new vest", "write a craft recipe that makes a new weapon",
                                  "add a recipe so players can craft rope"])
def test_crafting_recipes_are_not_mod_recipes(text):
    assert decide(text)["route"] != "dayz-recipe"


def test_orchestrator_is_a_team():
    assert decide("build me a vest mod")["kind"] == "team"


@pytest.mark.parametrize("text", ["make my vest work like the vanilla one", "add a vanilla style rifle"])
def test_vanilla_in_a_change_request_is_not_a_question(text):
    assert decide(text)["route"] != "dayz-ask"


@pytest.mark.parametrize("text", ["build me a mod", "build a pbo", "build the config", "build it"])
def test_build_me_is_not_a_pbo_build(text):
    assert decide(text)["route"] != "dayz-build-pbo"


# A debugging noun after "build" used to be taken as the mod name: "build errors in MyVest"
# went to dayz-build-pbo at 0.9 with mod=errors and never reached Jev or the router.
@pytest.mark.parametrize("text", ["build errors in MyVest", "build fails for MyVest", "build log for MyVest",
                                  "build issues with MyVest", "pack crashes on MyVest", "build is broken for MyVest",
                                  "rebuild keeps failing on MyVest", "build results for MyVest"])
def test_build_debugging_nouns_are_not_a_mod_name(text):
    d = decide(text)
    assert d["route"] != "dayz-build-pbo"
    assert "mod" not in d.get("args", {})


# These used to match no rule and cost a router turn.
@pytest.mark.parametrize("text", ["rebuild the pbo", "build the pbo", "pack my pbos", "rebuild the pbos"])
def test_rebuild_the_pbo_without_a_name_is_a_pbo_build(text):
    _assert_confident(text, "dayz-build-pbo", None)


def test_the_pbo_for_everything_is_still_not_a_mod_name():
    assert decide("build the pbo for everything")["route"] is None


@pytest.mark.parametrize("text", ["scaffold a whole new mod with a car", "start a new vest mod",
                                  "start a mod that adds a car and a garage", "scaffold me a weapons mod"])
def test_scaffold_or_start_a_mod_with_content_is_the_team(text):
    _assert_confident(text, "orchestrator", None)


# An empty scaffold stays with dayz-new-mod; the new orchestrator verbs must not take it.
@pytest.mark.parametrize("text", ["scaffold a new mod", "scaffold an empty mod", "scaffold a whole new mod"])
def test_scaffold_an_empty_mod_is_still_new_mod(text):
    _assert_confident(text, "dayz-new-mod", None)


@pytest.mark.parametrize("text", ["build MyVest and then launch the test server", "what should I do next?",
                                  "fix the throw action script"])
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


def test_every_user_facing_dayz_skill_is_a_target():
    # A skill with no target is unreachable, so the router forces it onto a wrong route.
    not_targets = {
        "dayz-route",  # the router itself
    }
    skills = {p.parent.name for p in (REPO / ".claude" / "skills").glob("dayz-*/SKILL.md")}
    assert sorted(skills - not_targets - set(CFG["targets"])) == []


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
