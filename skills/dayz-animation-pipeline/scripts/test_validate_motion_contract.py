import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent  # this test sits next to the scripts
sys.path.insert(0, str(SCRIPTS_DIR))

from validate_motion_contract import ContractError, evaluate_report, main as validator_main


IDENTITY = [0.0, 0.0, 0.0, 1.0]


def frame(points=None, segments=None, transforms=None):
    return {
        "points": points or {},
        "segments": segments or {},
        "transforms": transforms or {},
    }


def evaluate(frames, checks, metadata=None):
    if metadata is None:
        metadata = {
            "fps": 30.0,
            "frame_start": min(frames),
            "frame_end": max(frames),
        }
    report = {
        "schema_version": 1,
        "metadata": metadata,
        "frames": {str(key): value for key, value in frames.items()},
    }
    contract = {"schema_version": 1, "contract_mode": "diagnostic", "checks": checks}
    return evaluate_report(report, contract)


class MotionContractTests(unittest.TestCase):
    def test_contact_band_rejects_two_centimeter_surface_gap(self):
        result = evaluate(
            {52: frame(points={"fist": [0.0, 0.0, 0.0], "handle": [0.035, 0.0, 0.0]})},
            [{
                "id": "contact",
                "type": "point_distance_band",
                "frames": [52],
                "point_a": "fist",
                "point_b": "handle",
                "radius_a_m": 0.015,
                "radius_b_m": 0.0,
                "min_m": 0.0,
                "max_m": 0.003,
            }],
        )
        check = result["checks"]["contact"]
        self.assertFalse(check["pass"])
        self.assertAlmostEqual(check["measured"], 0.020, places=6)

    def test_contact_band_accepts_surface_contact(self):
        result = evaluate(
            {52: frame(points={"fist": [0.0, 0.0, 0.0], "handle": [0.016, 0.0, 0.0]})},
            [{
                "id": "contact",
                "type": "point_distance_band",
                "frames": [52],
                "point_a": "fist",
                "point_b": "handle",
                "radius_a_m": 0.015,
                "max_m": 0.003,
            }],
        )
        self.assertTrue(result["overall_pass"])

    def test_relative_lock_rejects_target_moving_alone(self):
        result = evaluate(
            {
                52: frame(transforms={
                    "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                }),
                76: frame(transforms={
                    "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    "handle": {"p": [0.010, 0.0, 0.0], "q": IDENTITY},
                }),
            },
            [{
                "id": "lock",
                "type": "relative_transform_lock",
                "frames": [52, 76],
                "actor": "hand",
                "target": "handle",
                "max_translation_drift_m": 0.003,
                "max_rotation_drift_deg": 3.0,
            }],
        )
        self.assertFalse(result["checks"]["lock"]["pass"])
        self.assertAlmostEqual(result["checks"]["lock"]["measured"]["translation_drift_m"], 0.010)

    def test_relative_lock_rejects_single_frame_window(self):
        with self.assertRaises(ContractError):
            evaluate(
                {0: frame(transforms={
                    "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                })},
                [{
                    "id": "lock",
                    "type": "relative_transform_lock",
                    "frames": [0],
                    "actor": "hand",
                    "target": "handle",
                    "max_translation_drift_m": 0.001,
                    "max_rotation_drift_deg": 1.0,
                }],
            )

    def test_frame_range_fails_closed_when_an_intermediate_frame_is_missing(self):
        with self.assertRaises(ContractError):
            evaluate(
                {
                    0: frame(transforms={
                        "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                        "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    }),
                    2: frame(transforms={
                        "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                        "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    }),
                },
                [{
                    "id": "lock",
                    "type": "relative_transform_lock",
                    "frame_range": {"start": 0, "end": 2, "step": 1},
                    "actor": "hand",
                    "target": "handle",
                    "max_translation_drift_m": 0.001,
                    "max_rotation_drift_deg": 1.0,
                }],
            )

    def test_relative_lock_accepts_shared_motion_in_rotated_actor_space(self):
        quarter_turn_z = [0.0, 0.0, math.sin(math.pi / 4.0), math.cos(math.pi / 4.0)]
        result = evaluate(
            {
                0: frame(transforms={
                    "hand": {"p": [0.0, 0.0, 0.0], "q": quarter_turn_z},
                    "handle": {"p": [0.0, 1.0, 0.0], "q": quarter_turn_z},
                }),
                1: frame(transforms={
                    "hand": {"p": [2.0, 0.0, 0.0], "q": quarter_turn_z},
                    "handle": {"p": [2.0, 1.0, 0.0], "q": quarter_turn_z},
                }),
            },
            [{
                "id": "lock",
                "type": "relative_transform_lock",
                "frames": [0, 1],
                "actor": "hand",
                "target": "handle",
                "max_translation_drift_m": 0.0001,
                "max_rotation_drift_deg": 0.01,
            }],
        )
        self.assertTrue(result["overall_pass"])

    def test_segment_clearance_rejects_crossing_fingers(self):
        result = evaluate(
            {52: frame(segments={
                "middle2": {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": 0.004},
                "ring2": {"a": [0.5, -0.010, 0.0], "b": [0.5, 0.010, 0.0], "radius_m": 0.004},
            })},
            [{
                "id": "no_overlap",
                "type": "segment_clearance",
                "frames": [52],
                "segments_a": ["middle2"],
                "segments_b": ["ring2"],
                "minimum_surface_gap_m": 0.0,
            }],
        )
        check = result["checks"]["no_overlap"]
        self.assertFalse(check["pass"])
        self.assertLess(check["measured"], 0.0)

    def test_segment_clearance_rejects_missing_or_negative_radius(self):
        for bad_segment in (
            {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0]},
            {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": -1.0},
        ):
            with self.subTest(bad_segment=bad_segment), self.assertRaises(ContractError):
                evaluate(
                    {0: frame(segments={
                        "a": bad_segment,
                        "b": {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": 0.1},
                    })},
                    [{
                        "id": "clear",
                        "type": "segment_clearance",
                        "frames": [0],
                        "segment_pairs": [["a", "b"]],
                    }],
                )

    def test_segment_clearance_rejects_malformed_segment_object(self):
        with self.assertRaises(ContractError):
            evaluate(
                {0: frame(segments={
                    "a": "not-an-object",
                    "b": {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": 0.1},
                })},
                [{
                    "id": "clear",
                    "type": "segment_clearance",
                    "frames": [0],
                    "segment_pairs": [["a", "b"]],
                }],
            )

    def test_segment_clearance_accepts_separated_segments(self):
        result = evaluate(
            {52: frame(segments={
                "middle2": {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": 0.004},
                "ring2": {"a": [0.0, 0.020, 0.0], "b": [1.0, 0.020, 0.0], "radius_m": 0.004},
            })},
            [{
                "id": "no_overlap",
                "type": "segment_clearance",
                "frames": [52],
                "segments_a": ["middle2"],
                "segments_b": ["ring2"],
                "minimum_surface_gap_m": 0.001,
            }],
        )
        self.assertTrue(result["overall_pass"])

    def test_segment_clearance_accepts_explicit_adjacent_pairs(self):
        result = evaluate(
            {52: frame(segments={
                "middle2": {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": 0.004},
                "ring2": {"a": [0.0, 0.020, 0.0], "b": [1.0, 0.020, 0.0], "radius_m": 0.004},
                "pinky2": {"a": [0.0, 0.040, 0.0], "b": [1.0, 0.040, 0.0], "radius_m": 0.004},
            })},
            [{
                "id": "adjacent",
                "type": "segment_clearance",
                "frames": [52],
                "segment_pairs": [["middle2", "ring2"], ["ring2", "pinky2"]],
                "minimum_surface_gap_m": 0.001,
            }],
        )
        self.assertTrue(result["overall_pass"])

    def test_ordered_projection_checks_intermediate_joints(self):
        result = evaluate(
            {52: frame(points={
                "middle_pip": [0.0, 0.0, 0.0],
                "ring_pip": [0.0, -0.001, 0.0],
            })},
            [{
                "id": "ordered",
                "type": "ordered_projection",
                "frames": [52],
                "point_groups": [["middle_pip", "ring_pip"]],
                "axis": [0.0, 1.0, 0.0],
                "minimum_gap_m": 0.0,
            }],
        )
        self.assertFalse(result["checks"]["ordered"]["pass"])

    def test_ordered_projection_can_follow_a_per_frame_hand_axis(self):
        result = evaluate(
            {52: frame(points={
                "index_root": [0.0, 0.0, 0.0],
                "pinky_root": [1.0, 1.0, 0.0],
                "middle_pip": [0.4, 0.4, 0.0],
                "ring_pip": [0.3, 0.3, 0.0],
            })},
            [{
                "id": "ordered_dynamic",
                "type": "ordered_projection",
                "frames": [52],
                "point_groups": [["middle_pip", "ring_pip"]],
                "axis_from_points": ["index_root", "pinky_root"],
                "minimum_gap_m": 0.0,
            }],
        )
        self.assertFalse(result["checks"]["ordered_dynamic"]["pass"])

    def test_joint_angle_range_rejects_overextension(self):
        angle = math.radians(45.0)
        result = evaluate(
            {10: frame(transforms={
                "wrist": {"p": [0.0, 0.0, 0.0], "q": [math.sin(angle / 2.0), 0.0, 0.0, math.cos(angle / 2.0)]},
            })},
            [{
                "id": "wrist_range",
                "type": "joint_angle_range",
                "frames": [10],
                "transform": "wrist",
                "reference_q": IDENTITY,
                "min_deg": 0.0,
                "max_deg": 30.0,
            }],
        )
        self.assertFalse(result["checks"]["wrist_range"]["pass"])

    def test_joint_angle_range_rejects_impossible_contract_bounds(self):
        with self.assertRaises(ContractError):
            evaluate(
                {10: frame(transforms={
                    "wrist": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                })},
                [{
                    "id": "wrist_range",
                    "type": "joint_angle_range",
                    "frames": [10],
                    "transform": "wrist",
                    "reference_q": IDENTITY,
                    "min_deg": -1.0,
                    "max_deg": 30.0,
                }],
            )

    def test_joint_swing_twist_range_rejects_excess_twist(self):
        angle = math.radians(60.0)
        result = evaluate(
            {10: frame(transforms={
                "wrist_local": {"p": [0.0, 0.0, 0.0], "q": [math.sin(angle / 2.0), 0.0, 0.0, math.cos(angle / 2.0)]},
            })},
            [{
                "id": "wrist_swing_twist",
                "type": "joint_swing_twist_range",
                "frames": [10],
                "transform": "wrist_local",
                "reference_q": IDENTITY,
                "twist_axis": [1.0, 0.0, 0.0],
                "min_twist_deg": -30.0,
                "max_twist_deg": 30.0,
                "max_swing_deg": 45.0,
            }],
        )
        self.assertFalse(result["checks"]["wrist_swing_twist"]["pass"])

    def test_continuity_limit_rejects_position_stutter(self):
        result = evaluate(
            {
                0: frame(points={"shoulder": [0.0, 0.0, 0.0]}),
                1: frame(points={"shoulder": [0.001, 0.0, 0.0]}),
                2: frame(points={"shoulder": [0.030, 0.0, 0.0]}),
            },
            [{
                "id": "shoulder_stutter",
                "type": "continuity_limit",
                "frames": [0, 1, 2],
                "point": "shoulder",
                "fps": 30.0,
                "max_acceleration_m_s2": 5.0,
            }],
        )
        self.assertFalse(result["checks"]["shoulder_stutter"]["pass"])

    def test_continuity_limit_reports_worst_normalized_violation(self):
        result = evaluate(
            {
                0: frame(points={"shoulder": [0.0, 0.0, 0.0]}),
                1: frame(points={"shoulder": [0.0, 0.0, 0.0]}),
                2: frame(points={"shoulder": [10.0, 0.0, 0.0]}),
                3: frame(points={"shoulder": [22.0, 0.0, 0.0]}),
            },
            [{
                "id": "shoulder_stutter",
                "type": "continuity_limit",
                "frames": [0, 1, 2, 3],
                "point": "shoulder",
                "fps": 1.0,
                "max_acceleration_m_s2": 100.0,
                "max_jerk_m_s3": 1.0,
            }],
        )
        self.assertEqual(result["checks"]["shoulder_stutter"]["worst_frame"], 3)

    def test_continuity_limit_rejects_negative_limit(self):
        with self.assertRaises(ContractError):
            evaluate(
                {
                    0: frame(points={"shoulder": [0.0, 0.0, 0.0]}),
                    1: frame(points={"shoulder": [0.0, 0.0, 0.0]}),
                },
                [{
                    "id": "shoulder_stutter",
                    "type": "continuity_limit",
                    "frames": [0, 1],
                    "point": "shoulder",
                    "fps": 30.0,
                    "max_speed_m_s": -1.0,
                }],
            )

    def test_continuity_limits_reject_too_few_frames_to_measure(self):
        two_frames = {
            0: frame(
                points={"shoulder": [0.0, 0.0, 0.0]},
                transforms={"wrist_local": {"p": [0.0, 0.0, 0.0], "q": IDENTITY}},
            ),
            1: frame(
                points={"shoulder": [0.0, 0.0, 0.0]},
                transforms={"wrist_local": {"p": [0.0, 0.0, 0.0], "q": IDENTITY}},
            ),
        }
        cases = [
            {"type": "continuity_limit", "point": "shoulder", "max_acceleration_m_s2": 0.0},
            {"type": "continuity_limit", "point": "shoulder", "max_jerk_m_s3": 0.0},
            {"type": "rotation_continuity_limit", "transform": "wrist_local", "max_angular_acceleration_deg_s2": 0.0},
            {"type": "rotation_continuity_limit", "transform": "wrist_local", "max_angular_jerk_deg_s3": 0.0},
        ]
        for case in cases:
            check = {"id": "short_window", "frames": [0, 1], "fps": 30.0, **case}
            with self.subTest(check=case), self.assertRaises(ContractError):
                evaluate(two_frames, [check])

    def test_rotation_continuity_limit_rejects_angular_stutter(self):
        quarter_turn = [0.0, 0.0, math.sin(math.pi / 4.0), math.cos(math.pi / 4.0)]
        result = evaluate(
            {
                0: frame(transforms={"wrist_local": {"p": [0.0, 0.0, 0.0], "q": IDENTITY}}),
                1: frame(transforms={"wrist_local": {"p": [0.0, 0.0, 0.0], "q": IDENTITY}}),
                2: frame(transforms={"wrist_local": {"p": [0.0, 0.0, 0.0], "q": quarter_turn}}),
            },
            [{
                "id": "wrist_stutter",
                "type": "rotation_continuity_limit",
                "frames": [0, 1, 2],
                "transform": "wrist_local",
                "fps": 30.0,
                "max_angular_acceleration_deg_s2": 1000.0,
            }],
        )
        self.assertFalse(result["checks"]["wrist_stutter"]["pass"])

    def test_endpoint_match_rejects_non_looping_pose(self):
        result = evaluate(
            {
                0: frame(points={"hand": [0.0, 0.0, 0.0]}),
                290: frame(points={"hand": [0.010, 0.0, 0.0]}),
            },
            [{
                "id": "loop",
                "type": "endpoint_match",
                "frame_a": 0,
                "frame_b": 290,
                "points": ["hand"],
                "max_translation_delta_m": 0.001,
            }],
        )
        self.assertFalse(result["checks"]["loop"]["pass"])

    def test_endpoint_match_rejects_negative_tolerance(self):
        with self.assertRaises(ContractError):
            evaluate(
                {0: frame(points={"hand": [0.0, 0.0, 0.0]})},
                [{
                    "id": "loop",
                    "type": "endpoint_match",
                    "frame_a": 0,
                    "frame_b": 0,
                    "points": ["hand"],
                    "max_translation_delta_m": -0.001,
                }],
            )

    def test_endpoint_match_rejects_fractional_frames(self):
        with self.assertRaises(ContractError):
            evaluate(
                {
                    0: frame(points={"hand": [0.0, 0.0, 0.0]}),
                    1: frame(points={"hand": [0.0, 0.0, 0.0]}),
                },
                [{
                    "id": "loop",
                    "type": "endpoint_match",
                    "frame_a": 0.9,
                    "frame_b": 1.9,
                    "points": ["hand"],
                }],
            )

    def test_seam_derivative_match_rejects_velocity_reversal(self):
        result = evaluate(
            {
                0: frame(points={"root": [0.0, 0.0, 0.0]}),
                1: frame(points={"root": [1.0, 0.0, 0.0]}),
                9: frame(points={"root": [1.0, 0.0, 0.0]}),
                10: frame(points={"root": [0.0, 0.0, 0.0]}),
            },
            [{
                "id": "seam_velocity",
                "type": "seam_derivative_match",
                "frame_start": 0,
                "frame_start_next": 1,
                "frame_end_prev": 9,
                "frame_end": 10,
                "point": "root",
                "fps": 1.0,
                "max_linear_velocity_delta_m_s": 0.1,
            }],
            metadata={"fps": 1.0, "frame_start": 0, "frame_end": 10},
        )
        self.assertFalse(result["checks"]["seam_velocity"]["pass"])

    def test_timeline_rejects_wrong_fixed_duration(self):
        with self.assertRaises(ContractError):
            evaluate(
                {0: frame(), 290: frame()},
                [{
                    "id": "timeline",
                    "type": "timeline",
                    "fps": 30.0,
                    "frame_start": 0,
                    "frame_end": 290,
                    "frame_count": 291,
                }],
                metadata={"fps": 30.0, "frame_start": 0, "frame_end": 289},
            )

    def test_timeline_missing_required_field_is_contract_error(self):
        with self.assertRaises(ContractError):
            evaluate(
                {0: frame()},
                [{"id": "timeline", "type": "timeline", "fps": 30.0, "frame_start": 0}],
            )

    def test_report_frame_outside_declared_timeline_is_contract_error(self):
        with self.assertRaises(ContractError):
            evaluate(
                {999: frame()},
                [{
                    "id": "timeline",
                    "type": "timeline",
                    "fps": 30.0,
                    "frame_start": 0,
                    "frame_end": 10,
                }],
                metadata={"fps": 30.0, "frame_start": 0, "frame_end": 10},
            )

    def test_timeline_can_require_each_bound_action_range(self):
        result = evaluate(
            {0: frame(), 10: frame()},
            [{
                "id": "timeline",
                "type": "timeline",
                "fps": 30.0,
                "frame_start": 0,
                "frame_end": 10,
                "require_action_range": True,
            }],
            metadata={
                "fps": 30.0,
                "frame_start": 0,
                "frame_end": 10,
                "action_bindings": [{"object": "Rig", "action": "Short", "frame_start": 0.0, "frame_end": 9.0}],
            },
        )
        self.assertFalse(result["checks"]["timeline"]["pass"])

    def test_production_contract_requires_check_provenance(self):
        report = {
            "schema_version": 1,
            "metadata": {"fps": 30.0, "frame_start": 0, "frame_end": 0},
            "frames": {"0": frame()},
        }
        contract = {
            "schema_version": 1,
            "contract_mode": "production",
            "checks": [{
                "id": "timeline",
                "type": "timeline",
                "fps": 30.0,
                "frame_start": 0,
                "frame_end": 0,
            }],
        }
        with self.assertRaises(ContractError):
            evaluate_report(report, contract)

    def test_production_contract_requires_segment_radius_provenance(self):
        provenance = {
            "source_kind": "explicit_user_decision",
            "source": "unit fixture",
            "verified_date": "2026-07-19",
            "method": "declared test threshold",
        }
        report = {
            "schema_version": 1,
            "metadata": {"fps": 30.0, "frame_start": 0, "frame_end": 0},
            "frames": {"0": frame(segments={
                "a": {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": 0.1},
                "b": {"a": [0.0, 1.0, 0.0], "b": [1.0, 1.0, 0.0], "radius_m": 0.1},
            })},
        }
        contract = {
            "schema_version": 1,
            "contract_mode": "production",
            "checks": [{
                "id": "clear",
                "type": "segment_clearance",
                "frames": [0],
                "segment_pairs": [["a", "b"]],
                "provenance": provenance,
            }],
        }
        with self.assertRaises(ContractError):
            evaluate_report(report, contract)

    def test_contract_mode_is_required_and_rejects_unknown_values(self):
        report = {
            "schema_version": 1,
            "metadata": {"fps": 30.0, "frame_start": 0, "frame_end": 0},
            "frames": {"0": frame()},
        }
        for bad_mode in (None, "productions"):
            contract = {
                "schema_version": 1,
                "checks": [{
                    "id": "timeline",
                    "type": "timeline",
                    "fps": 30.0,
                    "frame_start": 0,
                    "frame_end": 0,
                }],
            }
            if bad_mode is not None:
                contract["contract_mode"] = bad_mode
            with self.subTest(contract_mode=bad_mode), self.assertRaises(ContractError):
                evaluate_report(report, contract)

    def test_diagnostic_result_is_not_eligible_for_offline_pass(self):
        result = evaluate(
            {0: frame()},
            [{
                "id": "timeline",
                "type": "timeline",
                "fps": 30.0,
                "frame_start": 0,
                "frame_end": 0,
            }],
        )
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["contract_mode"], "diagnostic")
        self.assertFalse(result["eligible_for_offline_pass"])

    def test_passing_production_result_is_eligible_for_offline_pass(self):
        provenance = {
            "source_kind": "explicit_user_decision",
            "source": "unit fixture",
            "verified_date": "2026-07-19",
            "method": "declared test threshold",
        }
        report = {
            "schema_version": 1,
            "metadata": {"fps": 30.0, "frame_start": 0, "frame_end": 0},
            "frames": {"0": frame()},
        }
        contract = {
            "schema_version": 1,
            "contract_mode": "production",
            "checks": [{
                "id": "timeline",
                "type": "timeline",
                "fps": 30.0,
                "frame_start": 0,
                "frame_end": 0,
                "provenance": provenance,
            }],
        }
        result = evaluate_report(report, contract)
        self.assertTrue(result["overall_pass"])
        self.assertTrue(result["eligible_for_offline_pass"])

    def test_production_continuous_lock_requires_step_one(self):
        provenance = {
            "source_kind": "explicit_user_decision",
            "source": "unit fixture",
            "verified_date": "2026-07-19",
            "method": "declared test threshold",
        }
        report = {
            "schema_version": 1,
            "metadata": {"fps": 30.0, "frame_start": 0, "frame_end": 2},
            "frames": {
                "0": frame(transforms={
                    "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                }),
                "2": frame(transforms={
                    "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                }),
            },
        }
        contract = {
            "schema_version": 1,
            "contract_mode": "production",
            "checks": [{
                "id": "lock",
                "type": "relative_transform_lock",
                "frame_range": {"start": 0, "end": 2, "step": 2},
                "actor": "hand",
                "target": "handle",
                "max_translation_drift_m": 0.001,
                "max_rotation_drift_deg": 1.0,
                "provenance": provenance,
            }],
        }
        with self.assertRaises(ContractError):
            evaluate_report(report, contract)

    def test_relative_lock_rejects_negative_tolerance(self):
        with self.assertRaises(ContractError):
            evaluate(
                {0: frame(transforms={
                    "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                    "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
                })},
                [{
                    "id": "lock",
                    "type": "relative_transform_lock",
                    "frames": [0],
                    "actor": "hand",
                    "target": "handle",
                    "max_translation_drift_m": -0.001,
                    "max_rotation_drift_deg": 3.0,
                }],
            )

    def test_relative_lock_rejects_duplicate_or_unsorted_frames(self):
        transforms = {
            "hand": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
            "handle": {"p": [0.0, 0.0, 0.0], "q": IDENTITY},
        }
        for bad_frames in ([0, 0], [1, 0]):
            with self.subTest(frames=bad_frames), self.assertRaises(ContractError):
                evaluate(
                    {0: frame(transforms=transforms), 1: frame(transforms=transforms)},
                    [{
                        "id": "lock",
                        "type": "relative_transform_lock",
                        "frames": bad_frames,
                        "actor": "hand",
                        "target": "handle",
                        "max_translation_drift_m": 0.001,
                        "max_rotation_drift_deg": 1.0,
                    }],
                )

    def test_frames_reject_fractional_values(self):
        for bad_frame in (0.5, "0"):
            with self.subTest(bad_frame=bad_frame), self.assertRaises(ContractError):
                evaluate(
                    {0: frame(points={"a": [0.0, 0.0, 0.0], "b": [0.0, 0.0, 0.0]})},
                    [{
                        "id": "contact",
                        "type": "point_distance_band",
                        "frames": [bad_frame],
                        "point_a": "a",
                        "point_b": "b",
                        "max_m": 0.001,
                    }],
                )

    def test_unknown_check_type_fails_closed(self):
        with self.assertRaises(ContractError):
            evaluate({0: frame()}, [{"id": "mystery", "type": "imaginary"}])

    def test_cli_returns_exit_two_for_malformed_nested_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report_path = base / "report.json"
            contract_path = base / "contract.json"
            output_path = base / "audit.json"
            report_path.write_text(json.dumps({
                "schema_version": 1,
                "metadata": {"fps": 30.0, "frame_start": 0, "frame_end": 0},
                "frames": {"0": frame(segments={
                    "a": "malformed",
                    "b": {"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0], "radius_m": 0.1},
                })},
            }), encoding="utf-8")
            contract_path.write_text(json.dumps({
                "schema_version": 1,
                "contract_mode": "diagnostic",
                "checks": [{
                    "id": "clear",
                    "type": "segment_clearance",
                    "frames": [0],
                    "segment_pairs": [["a", "b"]],
                }],
            }), encoding="utf-8")
            exit_code = validator_main([
                "--report", str(report_path),
                "--contract", str(contract_path),
                "--output", str(output_path),
            ])
            self.assertEqual(exit_code, 2)
            self.assertFalse(output_path.exists())

    def test_optional_failure_does_not_flip_overall_pass(self):
        result = evaluate(
            {0: frame(points={"a": [0.0, 0.0, 0.0], "b": [1.0, 0.0, 0.0]})},
            [{
                "id": "optional",
                "type": "point_distance_band",
                "required": False,
                "frames": [0],
                "point_a": "a",
                "point_b": "b",
                "max_m": 0.001,
            }],
        )
        self.assertFalse(result["checks"]["optional"]["pass"])
        self.assertTrue(result["overall_pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
