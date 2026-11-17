#!/usr/bin/env python3
"""Run unit, synthetic, and optional real-Blender animation regression gates."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
TEST_DIR = SCRIPT_DIR  # the tests sit next to the scripts they cover
FIXTURE_DIR = SCRIPT_DIR / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))

from validate_motion_contract import (
    evaluate_report,
    point_distance,
    quaternion_conjugate,
    quaternion_multiply,
    quaternion_rotate,
    relative_transform,
)


EXPECTED_V44_FAILURES = {
    "left_fingers_no_overlap",
    "fist_contacts_handle",
    "hand_tracks_handle",
}
REQUIRED_NEGATIVE_CASES = {
    "contact_gap",
    "segment_penetration",
    "ordered_inversion",
    "target_moves_alone",
    "relative_rotation_drift",
    "joint_range",
    "continuity_translation",
    "continuity_rotation",
    "endpoint_mismatch",
    "timeline_mismatch",
    "seam_derivative_mismatch",
}


class RegressionFailure(RuntimeError):
    """Raised when a regression fixture does not produce its expected verdict."""


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def run_unit_tests() -> dict[str, Any]:
    suite = unittest.defaultTestLoader.discover(str(TEST_DIR), pattern="test_validate_motion_contract.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise RegressionFailure("neutral validator unit tests failed")
    return {"status": "PASS", "tests_run": result.testsRun}


def find_blender() -> Path | None:
    """Blender from BLENDER_EXE, else the one on PATH; None when neither is set."""
    raw = os.environ.get("BLENDER_EXE") or shutil.which("blender")
    return Path(raw) if raw else None


def run_blender_sampler_test(blender_exe: Path | None) -> dict[str, Any]:
    if blender_exe is None:
        # A skip is not a PASS: the sampler was not exercised on this machine.
        return {"status": "SKIP_NO_BLENDER", "reason": "BLENDER_EXE is unset and blender is not on PATH"}
    if not blender_exe.is_file():
        raise RegressionFailure(f"Blender executable is missing: {blender_exe}")
    command = [
        str(blender_exe),
        "--background",
        "--factory-startup",
        "--python",
        str(TEST_DIR / "test_sample_blender_motion.py"),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
    output = completed.stdout + "\n" + completed.stderr
    if completed.returncode != 0 or "SAMPLE_BLENDER_MOTION_TEST=PASS" not in output:
        raise RegressionFailure(
            f"Blender sampler test failed with {completed.returncode}: {output}"
        )
    return {"status": "PASS", "executable": str(blender_exe)}


def run_synthetic_fixtures() -> dict[str, Any]:
    positive_report = read_json(FIXTURE_DIR / "positive-generic.json")
    positive_contract = read_json(FIXTURE_DIR / "positive-generic.contract.json")
    positive_result = evaluate_report(positive_report, positive_contract)
    if not positive_result["overall_pass"]:
        raise RegressionFailure(f"positive fixture failed: {positive_result['failed_required_checks']}")
    negative_payload = read_json(FIXTURE_DIR / "negative-checks.json")
    cases = negative_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise RegressionFailure("negative fixture manifest must contain cases")
    identifiers = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(identifiers) != len(cases) or any(not isinstance(identifier, str) or not identifier for identifier in identifiers):
        raise RegressionFailure("every negative fixture requires a non-empty id")
    if len(identifiers) != len(set(identifiers)):
        raise RegressionFailure("negative fixture ids must be unique")
    missing = REQUIRED_NEGATIVE_CASES - set(identifiers)
    if missing:
        raise RegressionFailure(f"negative fixture manifest is missing {sorted(missing)}")
    case_results = {}
    for case in cases:
        identifier = case["id"]
        expected_raw = case.get("expected_failed_checks")
        if not isinstance(expected_raw, list) or not expected_raw:
            raise RegressionFailure(f"negative fixture {identifier} must expect at least one failure")
        result = evaluate_report(case["report"], case["contract"])
        actual = set(result["failed_required_checks"])
        expected = set(expected_raw)
        if actual != expected:
            raise RegressionFailure(f"negative fixture {identifier}: expected {sorted(expected)}, got {sorted(actual)}")
        case_results[identifier] = {"status": "PASS", "observed_failures": sorted(actual)}
    return {"status": "PASS", "positive": "PASS", "negative_cases": case_results}


def _normalized(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(component * component for component in vector))
    if length <= 1e-12:
        raise RegressionFailure("cannot normalize zero-length correction vector")
    return [component / length for component in vector]


def _declared_frames(check: dict[str, Any]) -> list[int]:
    if "frames" in check:
        return [int(frame) for frame in check["frames"]]
    frame_range = check.get("frame_range")
    if not isinstance(frame_range, dict):
        raise RegressionFailure(f"check {check.get('id')} has no declared frames")
    start = int(frame_range["start"])
    end = int(frame_range["end"])
    step = int(frame_range["step"])
    return list(range(start, end + 1, step))


def _correct_contact(report: dict[str, Any], contract: dict[str, Any]) -> None:
    check = next(item for item in contract["checks"] if item["id"] == "fist_contacts_handle")
    frame = str(check["frames"][0])
    points = report["frames"][frame]["points"]
    actor = list(points[check["point_a"]])
    target = list(points[check["point_b"]])
    direction = _normalized([target[index] - actor[index] for index in range(3)])
    target_center_distance = float(check.get("radius_a_m", 0.0)) + float(check.get("radius_b_m", 0.0)) + 0.001
    current_distance = point_distance(actor, target)
    move = current_distance - target_center_distance
    points[check["point_a"]] = [actor[index] + direction[index] * move for index in range(3)]


def _correct_finger_segments(report: dict[str, Any]) -> None:
    digits = ["thumb", "index", "middle", "ring", "pinky"]
    lateral_spacing = 0.025
    segment_length = 0.030
    for frame_data in report["frames"].values():
        for digit_index, digit in enumerate(digits):
            lateral = digit_index * lateral_spacing
            for segment_index in range(1, 4):
                name = f"{digit}{segment_index}"
                segment = frame_data["segments"][name]
                start = (segment_index - 1) * segment_length
                end = segment_index * segment_length
                segment["a"] = [start, lateral, 0.0]
                segment["b"] = [end, lateral, 0.0]


def _correct_relative_lock(report: dict[str, Any], contract: dict[str, Any]) -> None:
    check = next(item for item in contract["checks"] if item["id"] == "hand_tracks_handle")
    frames = _declared_frames(check)
    first_frame = str(frames[0])
    baseline_frame = report["frames"][first_frame]
    baseline_relative = relative_transform(
        baseline_frame["transforms"][check["actor"]],
        baseline_frame["transforms"][check["target"]],
    )
    relative_inverse_q = quaternion_conjugate(baseline_relative["q"])
    for frame in frames:
        transforms = report["frames"][str(frame)]["transforms"]
        target = transforms[check["target"]]
        actor_q = quaternion_multiply(target["q"], relative_inverse_q)
        actor_q_length = math.sqrt(sum(component * component for component in actor_q))
        actor_q = [component / actor_q_length for component in actor_q]
        offset_world = quaternion_rotate(actor_q, baseline_relative["p"])
        actor_p = [float(target["p"][index]) - offset_world[index] for index in range(3)]
        transforms[check["actor"]] = {"p": actor_p, "q": actor_q}


def corrected_v44_result(report: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    corrected = copy.deepcopy(report)
    _correct_contact(corrected, contract)
    _correct_finger_segments(corrected)
    _correct_relative_lock(corrected, contract)
    return evaluate_report(corrected, contract)


def run_real_v44(blend_path: Path, blender_exe: Path) -> dict[str, Any]:
    contract_path = FIXTURE_DIR / "sr2m-v44.contract.json"
    contract = read_json(contract_path)
    with tempfile.TemporaryDirectory(prefix="dayz_anim_v44_") as temporary:
        report_path = Path(temporary) / "report.json"
        command = [
            str(blender_exe),
            "--background",
            str(blend_path),
            "--python",
            str(SCRIPT_DIR / "sample_blender_motion.py"),
            "--",
            "--contract",
            str(contract_path),
            "--output",
            str(report_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, timeout=120, check=False)
        if completed.returncode != 0:
            raise RegressionFailure(
                f"Blender sampling failed with {completed.returncode}: {completed.stdout}\n{completed.stderr}"
            )
        report = read_json(report_path)
    result = evaluate_report(report, contract)
    actual_failures = set(result["failed_required_checks"])
    if actual_failures != EXPECTED_V44_FAILURES:
        raise RegressionFailure(
            f"v44 expected {sorted(EXPECTED_V44_FAILURES)}, got {sorted(actual_failures)}"
        )
    corrected = corrected_v44_result(report, contract)
    corrected_failures = EXPECTED_V44_FAILURES.intersection(corrected["failed_required_checks"])
    if corrected_failures:
        raise RegressionFailure(f"anti-tautology correction still fails {sorted(corrected_failures)}")
    return {
        "status": "PASS",
        "fixture_verdict": "EXPECTED_FAIL",
        "observed_failures": sorted(actual_failures),
        "measurements": {identifier: result["checks"][identifier]["measured"] for identifier in sorted(actual_failures)},
        "anti_tautology": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-fixtures", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    blender_exe = find_blender()
    summary: dict[str, Any] = {
        "unit": run_unit_tests(),
        "blender_sampler": run_blender_sampler_test(blender_exe),
        "synthetic": run_synthetic_fixtures(),
    }
    if args.real_fixtures:
        raw_blend = os.environ.get("SR2M_V44_BLEND")
        if not raw_blend:
            summary["sr2m_v44"] = {"status": "SKIP_REAL_FIXTURE", "reason": "SR2M_V44_BLEND is unset"}
        else:
            blend_path = Path(raw_blend)
            if not blend_path.is_file() or blender_exe is None or not blender_exe.is_file():
                raise RegressionFailure("real fixture blend or Blender executable is missing")
            summary["sr2m_v44"] = run_real_v44(blend_path, blender_exe)
    else:
        summary["sr2m_v44"] = {"status": "NOT_REQUESTED"}
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("DAYZ_ANIMATION_REGRESSION=" + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RegressionFailure as exc:
        print(f"DAYZ_ANIMATION_REGRESSION_ERROR={exc}", file=sys.stderr)
        raise SystemExit(1)
