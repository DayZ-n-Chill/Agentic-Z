"""Tests for bone_matching.py, the pure-Python matching engine (no bpy needed)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bone_matching import (  # noqa: E402
    calculate_similarity,
    find_best_match,
    fuzzy_match_bones,
    get_match_quality_report,
    normalize_bone_name,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Left_Arm", "left_arm"),
        ("left-arm", "left_arm"),
        ("LeftArm", "leftarm"),
        ("Left Arm", "left_arm"),
        ("left.arm", "left.arm"),  # dots are kept, so the .l and .r suffix bonus can work
        ("__Spine__1__", "spine_1"),
    ],
)
def test_normalize_bone_name(raw, expected):
    assert normalize_bone_name(raw) == expected


def test_similarity_scores_quoted_in_the_guide():
    # references/bone-mapping-guide.md quotes these as measured values.
    assert calculate_similarity("LeftArm", "left_arm") == 1.0
    assert calculate_similarity("LeftArm", "L_Arm") == pytest.approx(0.717, abs=0.001)
    assert calculate_similarity("LeftArm", "LeftLeg") == pytest.approx(0.671, abs=0.001)
    assert calculate_similarity("LeftArm", "RightArm") == pytest.approx(0.583, abs=0.001)
    assert calculate_similarity("LeftArm", "Head") == pytest.approx(0.364, abs=0.001)


def test_same_side_leg_beats_the_threshold_but_other_side_arm_does_not():
    # The trap SKILL.md warns about: a shared side prefix outweighs a shared limb keyword.
    assert find_best_match("LeftArm", ["LeftLeg"]) == "LeftLeg"
    assert find_best_match("LeftArm", ["RightArm"]) is None


def test_find_best_match_returns_the_score_on_request():
    assert find_best_match("Head", ["Neck", "head"], return_score=True) == ("head", 1.0)
    assert find_best_match("Head", ["Pelvis"], return_score=True) == (None, 0.0)


def test_exact_aliases_win_and_a_target_is_used_once():
    aliases = {"Hips": ["pelvis"], "Spine": ["spine"]}
    bone_map = fuzzy_match_bones(["Hips", "Spine", "Spine1"], ["Pelvis", "Spine"], known_aliases=aliases)
    assert bone_map == {"Hips": "Pelvis", "Spine": "Spine"}  # Spine1 has no free target left


def test_quality_report_counts_critical_bones():
    assert get_match_quality_report({})["quality"] == "none"
    critical = ["Hips", "Spine", "Head", "LeftArm", "RightArm", "LeftLeg", "RightLeg", "LeftHand", "RightHand"]
    report = get_match_quality_report({name: name.lower() for name in critical[:6]})
    assert report["quality"] == "good"
    assert report["critical_bones_mapped"] == "6/9"
    assert get_match_quality_report({name: name for name in critical})["quality"] == "excellent"
