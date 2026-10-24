"""Answer tests for evals/questions/dayz-script-specialist.json: each check accepts correct phrasings and rejects wrong ones.

Run with: py -m pytest scripts/dev/test_script_specialist_evals.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("run_evals", Path(__file__).with_name("run_evals.py"))
run_evals = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_evals)


def _question(qid):
    data, problems = run_evals.validate(run_evals.QUESTIONS_DIR / "dayz-script-specialist.json")
    assert problems == []
    return next(q for q in data["questions"] if q["id"] == qid)


CITE = " See 4_World/entities/manbase/playerbase.c."
FIXED = "\n```c\nmodded class PlayerBase\n{\n}\n```"


@pytest.mark.parametrize("answer", [
    "Remove the `extends PlayerBase`." + FIXED,
    "A modded class never uses extends." + FIXED,
    "Modded classes must not use extends." + FIXED,
    "The `extends PlayerBase` part must be removed." + FIXED,
    "Write it without extends." + FIXED,
    "The header `modded class PlayerBase extends PlayerBase` is wrong: leave the extends out." + FIXED,
    "Writing extends on a modded class is redundant; delete it." + FIXED,
    "The `extends PlayerBase` is wrong here." + FIXED,
    "The extends clause is the problem, drop it." + FIXED,
])
def test_modded_class_extends_accepts_correct_answers(answer):
    assert run_evals.score(answer + CITE, _question("modded-class-extends"))["passed"]


@pytest.mark.parametrize("answer", [
    "Keep extends; do not remove anything. modded class PlayerBase {",
    "There is no problem with extends here, it is fine. modded class PlayerBase {",
    "Leave the extends as it is. modded class PlayerBase {",
    "The extends is not wrong; the bug is elsewhere. modded class PlayerBase {",
    "The extends PlayerBase is fine. modded class PlayerBase {",
])
def test_modded_class_extends_rejects_wrong_answers(answer):
    assert not run_evals.score(answer + CITE, _question("modded-class-extends"))["passed"]


@pytest.mark.parametrize("answer", [
    "It goes in 4_World. It never goes in 3_Game.",
    "4_World. It does not belong in 3_Game, because ActionContinuousBase is defined in 4_World.",
    "Put it in 4_World; you can't put it in 5_Mission.",
    "4_World. ActionContinuousBase is defined in 4_World, and nothing that references PlayerBase belongs in 3_Game.",
    "4_World. Only engine-level helpers go in 3_Game; UI code goes in 5_Mission.",
    "Not 3_Game or 5_Mission: it goes in 4_World.",
    "3_Game cannot see PlayerBase, so it goes in 4_World.",
])
def test_action_layer_accepts_correct_answers(answer):
    assert run_evals.score(answer, _question("action-layer"))["passed"]


@pytest.mark.parametrize("answer", [
    "It goes in 3_Game, next to 4_World helpers.",
    "5_Mission. Actions are registered there, not in 4_World.",
    "**3_Game**\n\nActions are core gameplay; 4_World would also compile.",
])
def test_action_layer_rejects_wrong_layer(answer):
    assert not run_evals.score(answer, _question("action-layer"))["passed"]


@pytest.mark.parametrize("answer", [
    "RegisterNetSyncVariableInt and SetSynchDirty. Both are declared on EntityAI, in EntityAI.c.",
    "RegisterNetSyncVariableBool, then SetSynchDirty(); see P:\\scripts\\3_game\\entities\\entityai.c.",
])
def test_net_sync_calls_accepts_file_name_or_full_path(answer):
    assert run_evals.score(answer, _question("net-sync-calls"))["passed"]


def test_net_sync_calls_rejects_wrong_file():
    answer = "RegisterNetSyncVariableInt and SetSynchDirty, both in ItemBase.c."
    assert not run_evals.score(answer, _question("net-sync-calls"))["passed"]


@pytest.mark.parametrize("answer", [
    "No. PlayerBase lives in 4_World.",
    "**No.** PlayerBase lives in 4_World.",
    "Short answer: no. PlayerBase lives in 4_World.",
    "**Short answer: no.** PlayerBase lives in 4_World.",
])
def test_layer_visibility_accepts_no_with_or_without_label(answer):
    assert run_evals.score(answer, _question("layer-visibility"))["passed"]


@pytest.mark.parametrize("answer", [
    "Yes. No problem, 4_World types are visible.",
    "Short answer: yes. No problem, 4_World types are visible.",
])
def test_layer_visibility_rejects_yes(answer):
    assert not run_evals.score(answer, _question("layer-visibility"))["passed"]


@pytest.mark.parametrize("answer", [
    "if (GetGame().IsDedicatedServer())\n{\n    DoServerThing();\n}",
    "if ( g_Game.IsDedicatedServer() ) { DoServerThing(); }",
    "if (GetGame() && GetGame().IsDedicatedServer()) { DoServerThing(); }",
    "if (!GetGame().IsDedicatedServer())\n    return;\nDoServerThing();",
])
def test_server_only_gate_accepts_server_checks(answer):
    assert run_evals.score(answer, _question("server-only-gate"))["passed"]


def test_server_only_gate_rejects_inverted_check():
    answer = "if (!GetGame().IsDedicatedServer()) { /* client */ DoServerThing(); }"
    assert not run_evals.score(answer, _question("server-only-gate"))["passed"]
