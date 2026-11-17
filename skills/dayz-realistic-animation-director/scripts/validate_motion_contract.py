#!/usr/bin/env python3
"""Validate sampled animation motion against a declarative quality contract."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from typing import Any, Callable


SCHEMA_VERSION = 1
EPSILON = 1e-12


class ContractError(ValueError):
    """Raised when a report or contract is incomplete, inconsistent, or unsafe."""


def _validate_provenance(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    required_fields = ("source_kind", "source", "verified_date", "method")
    if any(not isinstance(value.get(field), str) or not value[field].strip() for field in required_fields):
        raise ContractError(f"{label} is incomplete")
    if value["source_kind"] not in {
        "approved_reference", "measured_geometry", "verified_vanilla", "explicit_user_decision"
    }:
        raise ContractError(f"{label}.source_kind is invalid")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value["verified_date"]) is None:
        raise ContractError(f"{label}.verified_date is invalid")


def _finite_number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise ContractError(f"{label} must be finite")
    return result


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{label} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label} must be an integer") from exc
    if isinstance(value, float) and not value.is_integer():
        raise ContractError(f"{label} must be an integer")
    return result


def _required_int(mapping: dict[str, Any], key: str, label: str) -> int:
    return _integer(mapping.get(key), label)


def _vector(value: Any, size: int, label: str) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ContractError(f"{label} must contain {size} numbers")
    return [_finite_number(component, f"{label}[{index}]") for index, component in enumerate(value)]


def _sub(a: list[float], b: list[float]) -> list[float]:
    return [a[index] - b[index] for index in range(3)]


def _length(vector: list[float]) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _dot(a: list[float], b: list[float]) -> float:
    return sum(a[index] * b[index] for index in range(len(a)))


def _normalize(vector: list[float], label: str) -> list[float]:
    magnitude = math.sqrt(_dot(vector, vector))
    if magnitude <= EPSILON:
        raise ContractError(f"{label} cannot be zero length")
    return [component / magnitude for component in vector]


def point_distance(a: Any, b: Any) -> float:
    first = _vector(a, 3, "point a")
    second = _vector(b, 3, "point b")
    return _length(_sub(first, second))


def closest_segment_distance(a0: Any, a1: Any, b0: Any, b1: Any) -> float:
    first_start = _vector(a0, 3, "segment a start")
    first_end = _vector(a1, 3, "segment a end")
    second_start = _vector(b0, 3, "segment b start")
    second_end = _vector(b1, 3, "segment b end")
    u = _sub(first_end, first_start)
    v = _sub(second_end, second_start)
    w = _sub(first_start, second_start)
    clamp01 = lambda value: max(0.0, min(1.0, value))
    a = _dot(u, u)
    e = _dot(v, v)
    f = _dot(v, w)
    if a <= EPSILON and e <= EPSILON:
        return point_distance(first_start, second_start)
    if a <= EPSILON:
        s = 0.0
        t = clamp01(f / e)
    else:
        c = _dot(u, w)
        if e <= EPSILON:
            s = clamp01(-c / a)
            t = 0.0
        else:
            b = _dot(u, v)
            denominator = a * e - b * b
            s = clamp01((b * f - c * e) / denominator) if denominator > EPSILON else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                s = clamp01(-c / a)
                t = 0.0
            elif t > 1.0:
                s = clamp01((b - c) / a)
                t = 1.0
    delta = [w[index] + s * u[index] - t * v[index] for index in range(3)]
    return _length(delta)


def _normalized_quaternion(value: Any, label: str) -> list[float]:
    quaternion = _vector(value, 4, label)
    magnitude = math.sqrt(_dot(quaternion, quaternion))
    if magnitude <= EPSILON:
        raise ContractError(f"{label} cannot be zero length")
    return [component / magnitude for component in quaternion]


def quaternion_angle_deg(a_xyzw: Any, b_xyzw: Any) -> float:
    first = _normalized_quaternion(a_xyzw, "quaternion a")
    second = _normalized_quaternion(b_xyzw, "quaternion b")
    cosine = max(-1.0, min(1.0, abs(_dot(first, second))))
    return math.degrees(2.0 * math.acos(cosine))


def quaternion_conjugate(value: Any) -> list[float]:
    x, y, z, w = _normalized_quaternion(value, "quaternion")
    return [-x, -y, -z, w]


def quaternion_multiply(a: Any, b: Any) -> list[float]:
    ax, ay, az, aw = _vector(a, 4, "quaternion a")
    bx, by, bz, bw = _vector(b, 4, "quaternion b")
    return [
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ]


def quaternion_rotate(value: Any, vector: Any) -> list[float]:
    quaternion = _normalized_quaternion(value, "rotation quaternion")
    point = _vector(vector, 3, "rotation vector")
    rotated = quaternion_multiply(
        quaternion_multiply(quaternion, [point[0], point[1], point[2], 0.0]),
        quaternion_conjugate(quaternion),
    )
    return rotated[:3]


def relative_transform(actor: Any, target: Any) -> dict[str, list[float]]:
    actor_transform = _transform(actor, "actor transform")
    target_transform = _transform(target, "target transform")
    actor_inverse = quaternion_conjugate(actor_transform["q"])
    world_delta = _sub(target_transform["p"], actor_transform["p"])
    return {
        "p": quaternion_rotate(actor_inverse, world_delta),
        "q": _normalized_quaternion(
            quaternion_multiply(actor_inverse, target_transform["q"]),
            "relative quaternion",
        ),
    }


def _transform(value: Any, label: str) -> dict[str, list[float]]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    return {
        "p": _vector(value.get("p"), 3, f"{label}.p"),
        "q": _normalized_quaternion(value.get("q"), f"{label}.q"),
    }


def _check_id(check: dict[str, Any]) -> str:
    identifier = check.get("id")
    if not isinstance(identifier, str) or not identifier.strip():
        raise ContractError("each check requires a non-empty string id")
    return identifier


def _frames(check: dict[str, Any], report: dict[str, Any]) -> list[int]:
    values = check.get("frames")
    frame_range = check.get("frame_range")
    if values is not None and frame_range is not None:
        raise ContractError(f"check {_check_id(check)} cannot combine frames and frame_range")
    if frame_range is not None:
        if not isinstance(frame_range, dict):
            raise ContractError(f"check {_check_id(check)} frame_range must be an object")
        start = _required_int(frame_range, "start", f"check {_check_id(check)} frame_range.start")
        end = _required_int(frame_range, "end", f"check {_check_id(check)} frame_range.end")
        step = _required_int(frame_range, "step", f"check {_check_id(check)} frame_range.step")
        if step <= 0 or start > end or (end - start) % step != 0:
            raise ContractError(f"check {_check_id(check)} has an invalid frame_range")
        values = list(range(start, end + 1, step))
    if not isinstance(values, list) or not values:
        raise ContractError(f"check {_check_id(check)} requires frames or frame_range")
    result = []
    for value in values:
        frame = _integer(value, f"check {_check_id(check)} frame")
        if str(frame) not in report["frames"]:
            raise ContractError(f"check {_check_id(check)} references missing frame {frame}")
        result.append(frame)
    if result != sorted(set(result)):
        raise ContractError(f"check {_check_id(check)} frames must be strictly increasing and unique")
    return result


def _frame(report: dict[str, Any], frame: int) -> dict[str, Any]:
    value = report["frames"].get(str(frame))
    if not isinstance(value, dict):
        raise ContractError(f"frame {frame} must be an object")
    return value


def _named(frame_data: dict[str, Any], group: str, name: str, frame: int) -> Any:
    values = frame_data.get(group)
    if not isinstance(values, dict) or name not in values:
        raise ContractError(f"frame {frame} is missing {group}.{name}")
    return values[name]


def _segment(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{label} must be an object")
    if "radius_m" not in value:
        raise ContractError(f"{label}.radius_m is required")
    radius = _finite_number(value.get("radius_m"), f"{label}.radius_m")
    if radius < 0.0:
        raise ContractError(f"{label}.radius_m cannot be negative")
    return {
        "a": _vector(value.get("a"), 3, f"{label}.a"),
        "b": _vector(value.get("b"), 3, f"{label}.b"),
        "radius_m": radius,
    }


def _result(
    check: dict[str, Any],
    passed: bool,
    worst_frame: int | None,
    measured: Any,
    limit: Any,
    message: str,
) -> dict[str, Any]:
    return {
        "pass": bool(passed),
        "required": bool(check.get("required", True)),
        "worst_frame": worst_frame,
        "measured": measured,
        "limit": limit,
        "message": message,
    }


def evaluate_point_distance_band(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    minimum = _finite_number(check.get("min_m", 0.0), "min_m")
    maximum = _finite_number(check.get("max_m"), "max_m")
    radius_a = _finite_number(check.get("radius_a_m", 0.0), "radius_a_m")
    radius_b = _finite_number(check.get("radius_b_m", 0.0), "radius_b_m")
    if minimum > maximum or radius_a < 0.0 or radius_b < 0.0:
        raise ContractError(f"check {_check_id(check)} has an invalid distance band")
    rows = []
    for frame in _frames(check, report):
        frame_data = _frame(report, frame)
        first = _named(frame_data, "points", str(check.get("point_a")), frame)
        second = _named(frame_data, "points", str(check.get("point_b")), frame)
        gap = point_distance(first, second) - radius_a - radius_b
        violation = max(minimum - gap, gap - maximum, 0.0)
        rows.append((violation, frame, gap))
    violation, worst_frame, gap = max(rows, key=lambda row: row[0])
    return _result(
        check,
        violation <= EPSILON,
        worst_frame,
        gap,
        {"min_m": minimum, "max_m": maximum},
        f"surface gap {gap:.6f} m at frame {worst_frame}",
    )


def evaluate_segment_clearance(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    names_a = check.get("segments_a")
    names_b = check.get("segments_b")
    explicit_pairs = check.get("segment_pairs")
    if explicit_pairs is not None:
        if not isinstance(explicit_pairs, list) or not explicit_pairs:
            raise ContractError(f"check {_check_id(check)} segment_pairs must be a non-empty list")
        pair_names = []
        for pair in explicit_pairs:
            if not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1]:
                raise ContractError(f"check {_check_id(check)} contains an invalid segment pair")
            pair_names.append((str(pair[0]), str(pair[1])))
    else:
        if not isinstance(names_a, list) or not names_a or not isinstance(names_b, list) or not names_b:
            raise ContractError(f"check {_check_id(check)} requires segment lists or segment_pairs")
        pair_names = [
            (str(name_a), str(name_b))
            for name_a in names_a
            for name_b in names_b
            if name_a != name_b
        ]
    minimum = _finite_number(check.get("minimum_surface_gap_m", 0.0), "minimum_surface_gap_m")
    rows = []
    for frame in _frames(check, report):
        frame_data = _frame(report, frame)
        for name_a, name_b in pair_names:
            first = _segment(_named(frame_data, "segments", str(name_a), frame), f"segment {name_a}")
            second = _segment(_named(frame_data, "segments", str(name_b), frame), f"segment {name_b}")
            distance = closest_segment_distance(first["a"], first["b"], second["a"], second["b"])
            surface_gap = distance - first["radius_m"] - second["radius_m"]
            rows.append((surface_gap, frame, str(name_a), str(name_b)))
    if not rows:
        raise ContractError(f"check {_check_id(check)} produced no segment pairs")
    gap, worst_frame, first_name, second_name = min(rows, key=lambda row: row[0])
    return _result(
        check,
        gap + EPSILON >= minimum,
        worst_frame,
        gap,
        {"minimum_surface_gap_m": minimum},
        f"minimum surface gap {gap:.6f} m between {first_name} and {second_name}",
    )


def evaluate_ordered_projection(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    groups = check.get("point_groups")
    if not isinstance(groups, list) or not groups:
        raise ContractError(f"check {_check_id(check)} requires point_groups")
    dynamic_axis = check.get("axis_from_points")
    fixed_axis = None
    if dynamic_axis is not None:
        if not isinstance(dynamic_axis, list) or len(dynamic_axis) != 2:
            raise ContractError(f"check {_check_id(check)} axis_from_points requires two point names")
    else:
        fixed_axis = _normalize(_vector(check.get("axis"), 3, "projection axis"), "projection axis")
    minimum = _finite_number(check.get("minimum_gap_m", 0.0), "minimum_gap_m")
    rows = []
    for frame in _frames(check, report):
        frame_data = _frame(report, frame)
        if dynamic_axis is not None:
            axis_start = _vector(
                _named(frame_data, "points", str(dynamic_axis[0]), frame),
                3,
                f"point {dynamic_axis[0]}",
            )
            axis_end = _vector(
                _named(frame_data, "points", str(dynamic_axis[1]), frame),
                3,
                f"point {dynamic_axis[1]}",
            )
            axis = _normalize(_sub(axis_end, axis_start), "dynamic projection axis")
        else:
            axis = fixed_axis
        for group_index, group in enumerate(groups):
            if not isinstance(group, list) or len(group) < 2:
                raise ContractError(f"check {_check_id(check)} has an invalid point group")
            projections = [
                _dot(_vector(_named(frame_data, "points", str(name), frame), 3, f"point {name}"), axis)
                for name in group
            ]
            for pair_index, (first, second) in enumerate(zip(projections, projections[1:])):
                rows.append((second - first, frame, group_index, pair_index))
    gap, worst_frame, group_index, pair_index = min(rows, key=lambda row: row[0])
    return _result(
        check,
        gap + EPSILON >= minimum,
        worst_frame,
        gap,
        {"minimum_gap_m": minimum},
        f"minimum ordered gap {gap:.6f} m in group {group_index} pair {pair_index}",
    )


def evaluate_relative_transform_lock(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    frames = _frames(check, report)
    if len(frames) < 2:
        raise ContractError(f"check {_check_id(check)} requires at least two frames")
    actor_name = str(check.get("actor"))
    target_name = str(check.get("target"))
    max_translation = _finite_number(check.get("max_translation_drift_m"), "max_translation_drift_m")
    max_rotation = _finite_number(check.get("max_rotation_drift_deg"), "max_rotation_drift_deg")
    if max_translation < 0.0 or max_rotation < 0.0:
        raise ContractError(f"check {_check_id(check)} requires non-negative drift tolerances")
    first_data = _frame(report, frames[0])
    baseline = relative_transform(
        _named(first_data, "transforms", actor_name, frames[0]),
        _named(first_data, "transforms", target_name, frames[0]),
    )
    rows = []
    for frame in frames:
        frame_data = _frame(report, frame)
        current = relative_transform(
            _named(frame_data, "transforms", actor_name, frame),
            _named(frame_data, "transforms", target_name, frame),
        )
        translation = point_distance(baseline["p"], current["p"])
        rotation = quaternion_angle_deg(baseline["q"], current["q"])
        score = max(
            translation / max(max_translation, EPSILON),
            rotation / max(max_rotation, EPSILON),
        )
        rows.append((score, frame, translation, rotation))
    _, worst_frame, _, _ = max(rows, key=lambda row: row[0])
    max_translation_value = max(row[2] for row in rows)
    max_rotation_value = max(row[3] for row in rows)
    passed = max_translation_value <= max_translation + EPSILON and max_rotation_value <= max_rotation + EPSILON
    return _result(
        check,
        passed,
        worst_frame,
        {"translation_drift_m": max_translation_value, "rotation_drift_deg": max_rotation_value},
        {"max_translation_drift_m": max_translation, "max_rotation_drift_deg": max_rotation},
        f"relative drift {max_translation_value:.6f} m / {max_rotation_value:.3f} deg",
    )


def evaluate_joint_angle_range(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    name = str(check.get("transform"))
    reference = _normalized_quaternion(check.get("reference_q"), "reference_q")
    minimum = _finite_number(check.get("min_deg", 0.0), "min_deg")
    maximum = _finite_number(check.get("max_deg"), "max_deg")
    if minimum < 0.0 or maximum > 180.0 or minimum > maximum:
        raise ContractError(f"check {_check_id(check)} requires 0 <= min_deg <= max_deg <= 180")
    rows = []
    for frame in _frames(check, report):
        transform = _transform(_named(_frame(report, frame), "transforms", name, frame), f"transform {name}")
        angle = quaternion_angle_deg(reference, transform["q"])
        violation = max(minimum - angle, angle - maximum, 0.0)
        rows.append((violation, frame, angle))
    violation, worst_frame, angle = max(rows, key=lambda row: row[0])
    return _result(
        check,
        violation <= EPSILON,
        worst_frame,
        angle,
        {"min_deg": minimum, "max_deg": maximum},
        f"joint delta {angle:.3f} deg at frame {worst_frame}",
    )


def evaluate_joint_swing_twist_range(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    name = str(check.get("transform"))
    reference = _normalized_quaternion(check.get("reference_q"), "reference_q")
    twist_axis = _normalize(_vector(check.get("twist_axis"), 3, "twist_axis"), "twist_axis")
    minimum_twist = _finite_number(check.get("min_twist_deg"), "min_twist_deg")
    maximum_twist = _finite_number(check.get("max_twist_deg"), "max_twist_deg")
    maximum_swing = _finite_number(check.get("max_swing_deg"), "max_swing_deg")
    if not (-180.0 <= minimum_twist <= maximum_twist <= 180.0) or not (0.0 <= maximum_swing <= 180.0):
        raise ContractError(f"check {_check_id(check)} has invalid swing/twist bounds")
    rows = []
    for frame in _frames(check, report):
        current = _transform(
            _named(_frame(report, frame), "transforms", name, frame),
            f"transform {name}",
        )["q"]
        delta = _normalized_quaternion(
            quaternion_multiply(quaternion_conjugate(reference), current),
            "joint delta quaternion",
        )
        if delta[3] < 0.0:
            delta = [-component for component in delta]
        projection = _dot(delta[:3], twist_axis)
        raw_twist = [twist_axis[index] * projection for index in range(3)] + [delta[3]]
        twist_length = math.sqrt(_dot(raw_twist, raw_twist))
        twist = [0.0, 0.0, 0.0, 1.0] if twist_length <= EPSILON else [component / twist_length for component in raw_twist]
        swing = _normalized_quaternion(
            quaternion_multiply(delta, quaternion_conjugate(twist)),
            "joint swing quaternion",
        )
        twist_angle = math.degrees(2.0 * math.atan2(_dot(twist[:3], twist_axis), twist[3]))
        while twist_angle > 180.0:
            twist_angle -= 360.0
        while twist_angle < -180.0:
            twist_angle += 360.0
        swing_angle = quaternion_angle_deg([0.0, 0.0, 0.0, 1.0], swing)
        violation = max(
            minimum_twist - twist_angle,
            twist_angle - maximum_twist,
            swing_angle - maximum_swing,
            0.0,
        )
        rows.append((violation, frame, twist_angle, swing_angle))
    violation, worst_frame, twist_angle, swing_angle = max(rows, key=lambda row: row[0])
    return _result(
        check,
        violation <= EPSILON,
        worst_frame,
        {"twist_deg": twist_angle, "swing_deg": swing_angle},
        {"min_twist_deg": minimum_twist, "max_twist_deg": maximum_twist, "max_swing_deg": maximum_swing},
        f"joint twist {twist_angle:.3f} deg / swing {swing_angle:.3f} deg at frame {worst_frame}",
    )


def _scaled_delta(a: list[float], b: list[float], seconds: float) -> list[float]:
    if seconds <= EPSILON:
        raise ContractError("continuity frames must increase")
    return [(b[index] - a[index]) / seconds for index in range(3)]


def _quaternion_delta_vector_deg(first: Any, second: Any) -> list[float]:
    delta = _normalized_quaternion(
        quaternion_multiply(quaternion_conjugate(first), second),
        "rotation delta quaternion",
    )
    if delta[3] < 0.0:
        delta = [-component for component in delta]
    cosine = max(-1.0, min(1.0, delta[3]))
    angle = 2.0 * math.acos(cosine)
    sine = math.sqrt(max(0.0, 1.0 - cosine * cosine))
    if sine <= EPSILON or angle <= EPSILON:
        return [0.0, 0.0, 0.0]
    scale = math.degrees(angle) / sine
    return [delta[index] * scale for index in range(3)]


def evaluate_continuity_limit(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    frames = _frames(check, report)
    if len(frames) < 2 or frames != sorted(frames) or len(set(frames)) != len(frames):
        raise ContractError(f"check {_check_id(check)} requires increasing unique frames")
    fps = _finite_number(check.get("fps", report.get("metadata", {}).get("fps")), "fps")
    if fps <= 0.0:
        raise ContractError("fps must be positive")
    name = str(check.get("point"))
    positions = [
        _vector(_named(_frame(report, frame), "points", name, frame), 3, f"point {name}")
        for frame in frames
    ]
    velocity_rows = []
    for index in range(1, len(frames)):
        seconds = (frames[index] - frames[index - 1]) / fps
        velocity_rows.append((frames[index], seconds, _scaled_delta(positions[index - 1], positions[index], seconds)))
    acceleration_rows = []
    for index in range(1, len(velocity_rows)):
        seconds = (velocity_rows[index - 1][1] + velocity_rows[index][1]) * 0.5
        acceleration_rows.append((velocity_rows[index][0], seconds, _scaled_delta(velocity_rows[index - 1][2], velocity_rows[index][2], seconds)))
    jerk_rows = []
    for index in range(1, len(acceleration_rows)):
        seconds = (acceleration_rows[index - 1][1] + acceleration_rows[index][1]) * 0.5
        jerk_rows.append((acceleration_rows[index][0], _scaled_delta(acceleration_rows[index - 1][2], acceleration_rows[index][2], seconds)))
    metric_rows = {
        "speed_m_s": [(row[0], _length(row[2])) for row in velocity_rows],
        "acceleration_m_s2": [(row[0], _length(row[2])) for row in acceleration_rows],
        "jerk_m_s3": [(row[0], _length(row[1])) for row in jerk_rows],
    }
    measured = {
        name: max((row[1] for row in rows), default=0.0)
        for name, rows in metric_rows.items()
    }
    limits = {}
    comparisons = []
    mapping = {
        "max_speed_m_s": "speed_m_s",
        "max_acceleration_m_s2": "acceleration_m_s2",
        "max_jerk_m_s3": "jerk_m_s3",
    }
    for limit_name, measured_name in mapping.items():
        if limit_name in check:
            limit = _finite_number(check[limit_name], limit_name)
            if limit < 0.0:
                raise ContractError(f"check {_check_id(check)} requires non-negative continuity limits")
            limits[limit_name] = limit
            value = measured[measured_name]
            score = value / max(limit, EPSILON) if value > EPSILON else 0.0
            comparisons.append((score, value <= limit + EPSILON, measured_name))
    if not comparisons:
        raise ContractError(f"check {_check_id(check)} requires at least one continuity limit")
    passed = all(item[1] for item in comparisons)
    _, _, worst_metric = max(comparisons, key=lambda item: item[0])
    worst_rows = metric_rows[worst_metric]
    worst_frame = max(worst_rows, key=lambda row: row[1])[0] if worst_rows else frames[0]
    return _result(check, passed, worst_frame, measured, limits, f"continuity maxima {measured}")


def evaluate_rotation_continuity_limit(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    frames = _frames(check, report)
    if len(frames) < 2 or frames != sorted(frames) or len(set(frames)) != len(frames):
        raise ContractError(f"check {_check_id(check)} requires increasing unique frames")
    fps = _finite_number(check.get("fps", report.get("metadata", {}).get("fps")), "fps")
    if fps <= 0.0:
        raise ContractError("fps must be positive")
    name = str(check.get("transform"))
    rotations = [
        _transform(_named(_frame(report, frame), "transforms", name, frame), f"transform {name}")["q"]
        for frame in frames
    ]
    velocity_rows = []
    for index in range(1, len(frames)):
        seconds = (frames[index] - frames[index - 1]) / fps
        delta = _quaternion_delta_vector_deg(rotations[index - 1], rotations[index])
        velocity_rows.append((frames[index], seconds, [component / seconds for component in delta]))
    acceleration_rows = []
    for index in range(1, len(velocity_rows)):
        seconds = (velocity_rows[index - 1][1] + velocity_rows[index][1]) * 0.5
        acceleration_rows.append((velocity_rows[index][0], seconds, _scaled_delta(velocity_rows[index - 1][2], velocity_rows[index][2], seconds)))
    jerk_rows = []
    for index in range(1, len(acceleration_rows)):
        seconds = (acceleration_rows[index - 1][1] + acceleration_rows[index][1]) * 0.5
        jerk_rows.append((acceleration_rows[index][0], _scaled_delta(acceleration_rows[index - 1][2], acceleration_rows[index][2], seconds)))
    metric_rows = {
        "angular_speed_deg_s": [(row[0], _length(row[2])) for row in velocity_rows],
        "angular_acceleration_deg_s2": [(row[0], _length(row[2])) for row in acceleration_rows],
        "angular_jerk_deg_s3": [(row[0], _length(row[1])) for row in jerk_rows],
    }
    measured = {name: max((row[1] for row in rows), default=0.0) for name, rows in metric_rows.items()}
    mapping = {
        "max_angular_speed_deg_s": "angular_speed_deg_s",
        "max_angular_acceleration_deg_s2": "angular_acceleration_deg_s2",
        "max_angular_jerk_deg_s3": "angular_jerk_deg_s3",
    }
    limits = {}
    comparisons = []
    for limit_name, measured_name in mapping.items():
        if limit_name in check:
            limit = _finite_number(check[limit_name], limit_name)
            if limit < 0.0:
                raise ContractError(f"check {_check_id(check)} requires non-negative rotation continuity limits")
            value = measured[measured_name]
            limits[limit_name] = limit
            score = value / max(limit, EPSILON) if value > EPSILON else 0.0
            comparisons.append((score, value <= limit + EPSILON, measured_name))
    if not comparisons:
        raise ContractError(f"check {_check_id(check)} requires at least one rotation continuity limit")
    passed = all(item[1] for item in comparisons)
    _, _, worst_metric = max(comparisons, key=lambda item: item[0])
    worst_rows = metric_rows[worst_metric]
    worst_frame = max(worst_rows, key=lambda row: row[1])[0] if worst_rows else frames[0]
    return _result(check, passed, worst_frame, measured, limits, f"rotation continuity maxima {measured}")


def evaluate_seam_derivative_match(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    frame_start = _required_int(check, "frame_start", f"check {_check_id(check)} frame_start")
    frame_start_next = _required_int(check, "frame_start_next", f"check {_check_id(check)} frame_start_next")
    frame_end_prev = _required_int(check, "frame_end_prev", f"check {_check_id(check)} frame_end_prev")
    frame_end = _required_int(check, "frame_end", f"check {_check_id(check)} frame_end")
    if frame_start_next <= frame_start or frame_end <= frame_end_prev:
        raise ContractError(f"check {_check_id(check)} requires increasing seam frame pairs")
    fps = _finite_number(check.get("fps", report.get("metadata", {}).get("fps")), "fps")
    if fps <= 0.0:
        raise ContractError("fps must be positive")
    first = _frame(report, frame_start)
    first_next = _frame(report, frame_start_next)
    last_prev = _frame(report, frame_end_prev)
    last = _frame(report, frame_end)
    start_seconds = (frame_start_next - frame_start) / fps
    end_seconds = (frame_end - frame_end_prev) / fps
    measured = {}
    limits = {}
    comparisons = []
    point_name = check.get("point")
    transform_name = check.get("transform")
    if point_name is not None and transform_name is not None:
        raise ContractError(f"check {_check_id(check)} cannot combine point and transform")
    if point_name is not None:
        name = str(point_name)
        start_velocity = _scaled_delta(
            _vector(_named(first, "points", name, frame_start), 3, f"point {name}"),
            _vector(_named(first_next, "points", name, frame_start_next), 3, f"point {name}"),
            start_seconds,
        )
        end_velocity = _scaled_delta(
            _vector(_named(last_prev, "points", name, frame_end_prev), 3, f"point {name}"),
            _vector(_named(last, "points", name, frame_end), 3, f"point {name}"),
            end_seconds,
        )
        delta = _length(_sub(start_velocity, end_velocity))
        limit = _finite_number(check.get("max_linear_velocity_delta_m_s"), "max_linear_velocity_delta_m_s")
        if limit < 0.0:
            raise ContractError(f"check {_check_id(check)} requires a non-negative seam tolerance")
        measured["linear_velocity_delta_m_s"] = delta
        limits["max_linear_velocity_delta_m_s"] = limit
        comparisons.append(delta <= limit + EPSILON)
    elif transform_name is not None:
        name = str(transform_name)
        transforms = [
            _transform(_named(frame_data, "transforms", name, frame), f"transform {name}")
            for frame_data, frame in (
                (first, frame_start), (first_next, frame_start_next),
                (last_prev, frame_end_prev), (last, frame_end),
            )
        ]
        if "max_linear_velocity_delta_m_s" in check:
            start_velocity = _scaled_delta(transforms[0]["p"], transforms[1]["p"], start_seconds)
            end_velocity = _scaled_delta(transforms[2]["p"], transforms[3]["p"], end_seconds)
            delta = _length(_sub(start_velocity, end_velocity))
            limit = _finite_number(check["max_linear_velocity_delta_m_s"], "max_linear_velocity_delta_m_s")
            if limit < 0.0:
                raise ContractError(f"check {_check_id(check)} requires non-negative seam tolerances")
            measured["linear_velocity_delta_m_s"] = delta
            limits["max_linear_velocity_delta_m_s"] = limit
            comparisons.append(delta <= limit + EPSILON)
        if "max_angular_velocity_delta_deg_s" in check:
            start_velocity = [component / start_seconds for component in _quaternion_delta_vector_deg(transforms[0]["q"], transforms[1]["q"])]
            end_velocity = [component / end_seconds for component in _quaternion_delta_vector_deg(transforms[2]["q"], transforms[3]["q"])]
            delta = _length(_sub(start_velocity, end_velocity))
            limit = _finite_number(check["max_angular_velocity_delta_deg_s"], "max_angular_velocity_delta_deg_s")
            if limit < 0.0:
                raise ContractError(f"check {_check_id(check)} requires non-negative seam tolerances")
            measured["angular_velocity_delta_deg_s"] = delta
            limits["max_angular_velocity_delta_deg_s"] = limit
            comparisons.append(delta <= limit + EPSILON)
    else:
        raise ContractError(f"check {_check_id(check)} requires point or transform")
    if not comparisons:
        raise ContractError(f"check {_check_id(check)} requires at least one seam tolerance")
    passed = all(comparisons)
    return _result(check, passed, frame_end, measured, limits, f"seam derivative deltas {measured}")


def evaluate_endpoint_match(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    frame_a = _required_int(check, "frame_a", f"check {_check_id(check)} frame_a")
    frame_b = _required_int(check, "frame_b", f"check {_check_id(check)} frame_b")
    first = _frame(report, frame_a)
    second = _frame(report, frame_b)
    max_translation = _finite_number(check.get("max_translation_delta_m", 0.0), "max_translation_delta_m")
    max_rotation = _finite_number(check.get("max_rotation_delta_deg", 0.0), "max_rotation_delta_deg")
    if max_translation < 0.0 or max_rotation < 0.0:
        raise ContractError(f"check {_check_id(check)} requires non-negative endpoint tolerances")
    translation_values = []
    rotation_values = []
    for name in check.get("points", []):
        translation_values.append(point_distance(
            _named(first, "points", str(name), frame_a),
            _named(second, "points", str(name), frame_b),
        ))
    for name in check.get("transforms", []):
        first_transform = _transform(_named(first, "transforms", str(name), frame_a), f"transform {name}")
        second_transform = _transform(_named(second, "transforms", str(name), frame_b), f"transform {name}")
        translation_values.append(point_distance(first_transform["p"], second_transform["p"]))
        rotation_values.append(quaternion_angle_deg(first_transform["q"], second_transform["q"]))
    if not translation_values and not rotation_values:
        raise ContractError(f"check {_check_id(check)} requires points or transforms")
    translation = max(translation_values, default=0.0)
    rotation = max(rotation_values, default=0.0)
    passed = translation <= max_translation + EPSILON and rotation <= max_rotation + EPSILON
    return _result(
        check,
        passed,
        frame_b,
        {"translation_delta_m": translation, "rotation_delta_deg": rotation},
        {"max_translation_delta_m": max_translation, "max_rotation_delta_deg": max_rotation},
        f"endpoint delta {translation:.6f} m / {rotation:.3f} deg",
    )


def evaluate_timeline(report: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        raise ContractError("report metadata must be an object")
    expected_fps = _finite_number(check.get("fps"), "timeline fps")
    actual_fps = _finite_number(metadata.get("fps"), "report fps")
    expected_start = _required_int(check, "frame_start", "timeline frame_start")
    expected_end = _required_int(check, "frame_end", "timeline frame_end")
    expected_count = (
        _required_int(check, "frame_count", "timeline frame_count")
        if "frame_count" in check
        else expected_end - expected_start + 1
    )
    actual_start = _required_int(metadata, "frame_start", "report frame_start")
    actual_end = _required_int(metadata, "frame_end", "report frame_end")
    if expected_start > expected_end or expected_count <= 0:
        raise ContractError(f"check {_check_id(check)} has an invalid timeline range")
    if expected_count != expected_end - expected_start + 1:
        raise ContractError(f"check {_check_id(check)} has an inconsistent frame_count")
    actual_count = actual_end - actual_start + 1
    action_ranges = metadata.get("action_bindings", [])
    if not isinstance(action_ranges, list):
        raise ContractError("report action_bindings must be a list")
    action_range_pass = True
    action_measurements = []
    if bool(check.get("require_action_range", False)):
        if not action_ranges:
            raise ContractError(f"check {_check_id(check)} requires sampled action ranges")
        for binding in action_ranges:
            if not isinstance(binding, dict):
                raise ContractError("each report action binding must be an object")
            action_start = _finite_number(binding.get("frame_start"), "action frame_start")
            action_end = _finite_number(binding.get("frame_end"), "action frame_end")
            action_measurements.append({
                "object": binding.get("object"),
                "action": binding.get("action"),
                "frame_start": action_start,
                "frame_end": action_end,
            })
            action_range_pass = action_range_pass and abs(action_start - expected_start) <= 1e-6 and abs(action_end - expected_end) <= 1e-6
    passed = (
        abs(actual_fps - expected_fps) <= 1e-6
        and actual_start == expected_start
        and actual_end == expected_end
        and actual_count == expected_count
        and action_range_pass
    )
    return _result(
        check,
        passed,
        None,
        {"fps": actual_fps, "frame_start": actual_start, "frame_end": actual_end, "frame_count": actual_count, "action_bindings": action_measurements},
        {"fps": expected_fps, "frame_start": expected_start, "frame_end": expected_end, "frame_count": expected_count},
        f"timeline {actual_start}..{actual_end} at {actual_fps:g} fps ({actual_count} frames)",
    )


CHECK_EVALUATORS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "point_distance_band": evaluate_point_distance_band,
    "segment_clearance": evaluate_segment_clearance,
    "ordered_projection": evaluate_ordered_projection,
    "relative_transform_lock": evaluate_relative_transform_lock,
    "joint_angle_range": evaluate_joint_angle_range,
    "joint_swing_twist_range": evaluate_joint_swing_twist_range,
    "continuity_limit": evaluate_continuity_limit,
    "rotation_continuity_limit": evaluate_rotation_continuity_limit,
    "endpoint_match": evaluate_endpoint_match,
    "seam_derivative_match": evaluate_seam_derivative_match,
    "timeline": evaluate_timeline,
}


def _validate_root(report: Any, contract: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(report, dict) or report.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"report schema_version must be {SCHEMA_VERSION}")
    if not isinstance(contract, dict) or contract.get("schema_version") != SCHEMA_VERSION:
        raise ContractError(f"contract schema_version must be {SCHEMA_VERSION}")
    if not isinstance(report.get("frames"), dict):
        raise ContractError("report frames must be an object")
    metadata = report.get("metadata")
    if not isinstance(metadata, dict):
        raise ContractError("report metadata must be an object")
    report_start = _required_int(metadata, "frame_start", "report frame_start")
    report_end = _required_int(metadata, "frame_end", "report frame_end")
    if report_start > report_end:
        raise ContractError("report timeline range is invalid")
    for raw_frame, frame_data in report["frames"].items():
        if not isinstance(raw_frame, str) or re.fullmatch(r"-?(0|[1-9]\d*)", raw_frame) is None:
            raise ContractError(f"report frame key {raw_frame!r} is not canonical")
        frame = int(raw_frame)
        if frame < report_start or frame > report_end:
            raise ContractError(f"report frame {frame} is outside declared timeline")
        if not isinstance(frame_data, dict):
            raise ContractError(f"frame {frame} must be an object")
    checks = contract.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ContractError("contract checks must be a non-empty list")
    contract_mode = contract.get("contract_mode")
    if contract_mode not in {"diagnostic", "production"}:
        raise ContractError("contract_mode must be exactly 'diagnostic' or 'production'")
    if contract_mode == "production":
        dense_check_types = {
            "point_distance_band",
            "segment_clearance",
            "ordered_projection",
            "relative_transform_lock",
            "joint_angle_range",
            "joint_swing_twist_range",
            "continuity_limit",
            "rotation_continuity_limit",
        }
        if any(isinstance(check, dict) and check.get("type") == "segment_clearance" for check in checks):
            _validate_provenance(
                contract.get("segment_radius_provenance"),
                "production segment_radius_provenance",
            )
        for check in checks:
            if not isinstance(check, dict):
                raise ContractError("each check must be an object")
            _validate_provenance(check.get("provenance"), f"production check {_check_id(check)} provenance")
            if check.get("type") in dense_check_types:
                frame_range = check.get("frame_range")
                if not isinstance(frame_range, dict) or frame_range.get("step") != 1:
                    raise ContractError(
                        f"production continuous check {_check_id(check)} requires frame_range.step == 1"
                    )
    return report, contract


def evaluate_report(report: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    report, contract = _validate_root(report, contract)
    results: dict[str, dict[str, Any]] = {}
    for check in contract["checks"]:
        if not isinstance(check, dict):
            raise ContractError("each check must be an object")
        identifier = _check_id(check)
        if identifier in results:
            raise ContractError(f"duplicate check id {identifier}")
        check_type = check.get("type")
        evaluator = CHECK_EVALUATORS.get(str(check_type))
        if evaluator is None:
            raise ContractError(f"unknown check type {check_type!r} for {identifier}")
        results[identifier] = evaluator(report, check)
    failed_required = sorted(
        identifier
        for identifier, result in results.items()
        if result["required"] and not result["pass"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_mode": contract["contract_mode"],
        "overall_pass": not failed_required,
        "eligible_for_offline_pass": contract["contract_mode"] == "production" and not failed_required,
        "failed_required_checks": failed_required,
        "checks": results,
    }


def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot read JSON {path}: {exc}") from exc


def _write_json(path: str, payload: Any) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        result = evaluate_report(_read_json(args.report), _read_json(args.contract))
        _write_json(args.output, result)
    except Exception as exc:
        print(f"MOTION_CONTRACT_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "output": os.path.abspath(args.output),
        "overall_pass": result["overall_pass"],
        "failed_required_checks": result["failed_required_checks"],
    }, sort_keys=True))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
