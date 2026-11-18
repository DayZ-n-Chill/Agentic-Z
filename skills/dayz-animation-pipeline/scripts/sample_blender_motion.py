#!/usr/bin/env python3
"""Sample Blender scene landmarks and transforms into a neutral motion report."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from typing import Any

import bpy
from mathutils import Matrix, Vector


SCHEMA_VERSION = 1


class SamplingError(ValueError):
    """Raised when a sampling contract cannot be evaluated safely."""


def _validate_provenance(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise SamplingError(f"{label} must be an object")
    required = ("source_kind", "source", "verified_date", "method")
    if any(not isinstance(value.get(field), str) or not value[field].strip() for field in required):
        raise SamplingError(f"{label} is incomplete")
    if value["source_kind"] not in {
        "approved_reference", "measured_geometry", "verified_vanilla", "explicit_user_decision"
    }:
        raise SamplingError(f"{label}.source_kind is invalid")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value["verified_date"]) is None:
        raise SamplingError(f"{label}.verified_date is invalid")


def _finite(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SamplingError(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise SamplingError(f"{label} must be finite")
    return result


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SamplingError(f"{label} must be an integer")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise SamplingError(f"{label} must be an integer") from exc
    if isinstance(value, float) and not value.is_integer():
        raise SamplingError(f"{label} must be an integer")
    return result


def _vector3(value: Any, label: str) -> Vector:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise SamplingError(f"{label} must contain three numbers")
    return Vector(tuple(_finite(component, f"{label}[{index}]") for index, component in enumerate(value)))


def _object(name: Any) -> bpy.types.Object:
    if not isinstance(name, str) or not name:
        raise SamplingError("object name must be a non-empty string")
    value = bpy.data.objects.get(name)
    if value is None:
        raise SamplingError(f"missing object {name}")
    return value


def _pose_bone(object_value: bpy.types.Object, bone_name: Any) -> bpy.types.PoseBone:
    if object_value.type != "ARMATURE" or object_value.pose is None:
        raise SamplingError(f"object {object_value.name} is not an armature")
    if not isinstance(bone_name, str) or not bone_name:
        raise SamplingError("bone name must be a non-empty string")
    value = object_value.pose.bones.get(bone_name)
    if value is None:
        raise SamplingError(f"missing pose bone {object_value.name}.{bone_name}")
    return value


def _point_list(value: Vector) -> list[float]:
    result = [float(value.x), float(value.y), float(value.z)]
    if not all(math.isfinite(component) for component in result):
        raise SamplingError("sampled point contains a non-finite component")
    return result


def _matrix_transform(value: Matrix) -> dict[str, list[float]]:
    translation, rotation, _scale = value.decompose()
    quaternion = rotation.normalized()
    result = {
        "p": _point_list(translation),
        "q": [float(quaternion.x), float(quaternion.y), float(quaternion.z), float(quaternion.w)],
    }
    if not all(math.isfinite(component) for component in result["q"]):
        raise SamplingError("sampled quaternion contains a non-finite component")
    return result


def _primitive_landmark(spec: dict[str, Any], depsgraph: bpy.types.Depsgraph) -> Vector:
    landmark_type = spec.get("type")
    if landmark_type in {"bone_head", "bone_tail", "bone_point"}:
        object_value = _object(spec.get("object"))
        bone = _pose_bone(object_value, spec.get("bone"))
        if landmark_type == "bone_head":
            local = bone.head.copy()
        elif landmark_type == "bone_tail":
            local = bone.tail.copy()
        else:
            factor = _finite(spec.get("factor"), "bone_point.factor")
            if factor < 0.0 or factor > 1.0:
                raise SamplingError("bone_point.factor must be in 0..1")
            local = bone.head.lerp(bone.tail, factor)
        return object_value.matrix_world @ local
    if landmark_type == "object_origin":
        return _object(spec.get("object")).matrix_world.translation.copy()
    if landmark_type == "mesh_vertex_centroid":
        object_value = _object(spec.get("object"))
        if object_value.type != "MESH":
            raise SamplingError(f"object {object_value.name} is not a mesh")
        indices = spec.get("indices")
        if not isinstance(indices, list) or not indices:
            raise SamplingError("mesh_vertex_centroid.indices must be a non-empty list")
        evaluated = object_value.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            points = []
            for raw_index in indices:
                index = _integer(raw_index, f"{object_value.name} vertex index")
                if index < 0 or index >= len(mesh.vertices):
                    raise SamplingError(f"vertex index {index} is outside {object_value.name}")
                points.append(evaluated.matrix_world @ mesh.vertices[index].co)
            return sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
        finally:
            evaluated.to_mesh_clear()
    raise SamplingError(f"unsupported primitive landmark type {landmark_type!r}")


def _resolve_landmark(
    name: str,
    specs: dict[str, dict[str, Any]],
    resolved: dict[str, Vector],
    resolving: set[str],
    depsgraph: bpy.types.Depsgraph,
) -> Vector:
    if name in resolved:
        return resolved[name]
    if name in resolving:
        raise SamplingError(f"cyclic average landmark dependency at {name}")
    spec = specs.get(name)
    if not isinstance(spec, dict):
        raise SamplingError(f"missing landmark specification {name}")
    resolving.add(name)
    if spec.get("type") == "average":
        sources = spec.get("sources")
        if not isinstance(sources, list) or not sources:
            raise SamplingError(f"average landmark {name} requires sources")
        points = [
            _resolve_landmark(str(source), specs, resolved, resolving, depsgraph)
            for source in sources
        ]
        value = sum(points, Vector((0.0, 0.0, 0.0))) / len(points)
    else:
        value = _primitive_landmark(spec, depsgraph)
    if "offset_world" in spec:
        value += _vector3(spec["offset_world"], f"landmark {name}.offset_world")
    resolving.remove(name)
    resolved[name] = value
    return value


def _sample_transform(spec: dict[str, Any]) -> dict[str, list[float]]:
    transform_type = spec.get("type")
    object_value = _object(spec.get("object"))
    if transform_type == "object_world":
        return _matrix_transform(object_value.matrix_world)
    if transform_type == "pose_bone_world":
        bone = _pose_bone(object_value, spec.get("bone"))
        return _matrix_transform(object_value.matrix_world @ bone.matrix)
    if transform_type == "pose_bone_local":
        bone = _pose_bone(object_value, spec.get("bone"))
        return _matrix_transform(bone.matrix_basis)
    raise SamplingError(f"unsupported transform type {transform_type!r}")


def _bind_actions(bindings: Any) -> list[tuple[bpy.types.Object, bool, Any]]:
    if bindings is None:
        return []
    if not isinstance(bindings, list):
        raise SamplingError("action_bindings must be a list")
    states = []
    bound_objects: set[str] = set()
    try:
        for binding in bindings:
            if not isinstance(binding, dict):
                raise SamplingError("each action binding must be an object")
            object_value = _object(binding.get("object"))
            if object_value.name in bound_objects:
                raise SamplingError(f"duplicate action binding for object {object_value.name}")
            bound_objects.add(object_value.name)
            action_name = binding.get("action")
            if not isinstance(action_name, str) or not action_name:
                raise SamplingError("action binding requires a non-empty action name")
            action = bpy.data.actions.get(action_name)
            if action is None:
                raise SamplingError(f"missing action {action_name}")
            had_animation_data = object_value.animation_data is not None
            old_action = object_value.animation_data.action if had_animation_data else None
            states.append((object_value, had_animation_data, old_action))
            object_value.animation_data_create()
            object_value.animation_data.action = action
    except Exception:
        _restore_actions(states)
        raise
    return states


def _restore_actions(states: list[tuple[bpy.types.Object, bool, Any]]) -> None:
    for object_value, had_animation_data, old_action in reversed(states):
        if had_animation_data:
            object_value.animation_data_create()
            object_value.animation_data.action = old_action
        elif object_value.animation_data is not None:
            object_value.animation_data_clear()


def sample_scene(contract: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(contract, dict) or contract.get("schema_version") != SCHEMA_VERSION:
        raise SamplingError(f"contract schema_version must be {SCHEMA_VERSION}")
    contract_mode = contract.get("contract_mode")
    if contract_mode not in {"diagnostic", "production"}:
        raise SamplingError("contract_mode must be exactly 'diagnostic' or 'production'")
    raw_frames = contract.get("sample_frames", [])
    raw_ranges = contract.get("sample_ranges", [])
    if not isinstance(raw_frames, list) or not isinstance(raw_ranges, list):
        raise SamplingError("sample_frames and sample_ranges must be lists")
    frames = []
    for raw_frame in raw_frames:
        frames.append(_integer(raw_frame, "sample frame"))
    for range_index, raw_range in enumerate(raw_ranges):
        if not isinstance(raw_range, dict):
            raise SamplingError(f"sample_ranges[{range_index}] must be an object")
        start = _integer(raw_range.get("start"), f"sample_ranges[{range_index}].start")
        end = _integer(raw_range.get("end"), f"sample_ranges[{range_index}].end")
        step = _integer(raw_range.get("step"), f"sample_ranges[{range_index}].step")
        if step <= 0 or start > end or (end - start) % step != 0:
            raise SamplingError(f"sample_ranges[{range_index}] is invalid")
        frames.extend(range(start, end + 1, step))
    if not frames:
        raise SamplingError("sample_frames or sample_ranges must provide at least one frame")
    frames = sorted(set(frames))
    if raw_frames != sorted(set(raw_frames)):
        raise SamplingError("sample_frames must be increasing and unique")
    landmark_specs = contract.get("landmarks", {})
    transform_specs = contract.get("transforms", {})
    segment_specs = contract.get("segments", {})
    if not isinstance(landmark_specs, dict) or not isinstance(transform_specs, dict) or not isinstance(segment_specs, dict):
        raise SamplingError("landmarks, transforms and segments must be objects")
    if contract_mode == "production" and segment_specs:
        _validate_provenance(contract.get("segment_radius_provenance"), "segment_radius_provenance")
    scene = bpy.context.scene
    scene_start = int(scene.frame_start)
    scene_end = int(scene.frame_end)
    for frame in frames:
        if frame < scene_start or frame > scene_end:
            raise SamplingError(f"sample frame {frame} is outside scene timeline {scene_start}..{scene_end}")
    original_frame = int(scene.frame_current)
    action_states = _bind_actions(contract.get("action_bindings"))
    report_frames: dict[str, Any] = {}
    action_metadata = []
    try:
        for binding in contract.get("action_bindings") or []:
            action = bpy.data.actions.get(binding["action"])
            frame_start, frame_end = action.frame_range
            action_metadata.append({
                "object": binding["object"],
                "action": binding["action"],
                "frame_start": _finite(frame_start, "action frame_start"),
                "frame_end": _finite(frame_end, "action frame_end"),
            })
        for frame in frames:
            scene.frame_set(frame)
            bpy.context.view_layer.update()
            depsgraph = bpy.context.evaluated_depsgraph_get()
            resolved: dict[str, Vector] = {}
            points = {
                name: _point_list(_resolve_landmark(name, landmark_specs, resolved, set(), depsgraph))
                for name in landmark_specs
            }
            transforms = {
                name: _sample_transform(spec)
                for name, spec in transform_specs.items()
            }
            segments = {}
            for name, spec in segment_specs.items():
                if not isinstance(spec, dict):
                    raise SamplingError(f"segment {name} must be an object")
                point_a = str(spec.get("point_a"))
                point_b = str(spec.get("point_b"))
                if point_a not in points or point_b not in points:
                    raise SamplingError(f"segment {name} references a missing point")
                if "radius_m" not in spec:
                    raise SamplingError(f"segment {name}.radius_m is required")
                radius = _finite(spec.get("radius_m"), f"segment {name}.radius_m")
                if radius < 0.0:
                    raise SamplingError(f"segment {name}.radius_m cannot be negative")
                segments[name] = {"a": points[point_a], "b": points[point_b], "radius_m": radius}
            report_frames[str(frame)] = {
                "points": points,
                "segments": segments,
                "transforms": transforms,
            }
    finally:
        scene.frame_set(original_frame)
        bpy.context.view_layer.update()
        _restore_actions(action_states)
        bpy.context.view_layer.update()
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata": {
            "fps": float(scene.render.fps) / float(scene.render.fps_base),
            "frame_start": scene_start,
            "frame_end": scene_end,
            "action_bindings": action_metadata,
        },
        "frames": report_frames,
    }


def read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise SamplingError(f"cannot read JSON {path}: {exc}") from exc


def write_json(path: str, payload: Any) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _script_arguments() -> list[str]:
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(_script_arguments() if argv is None else argv)
    try:
        report = sample_scene(read_json(args.contract))
        write_json(args.output, report)
    except Exception as exc:
        print(f"BLENDER_MOTION_SAMPLING_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "output": os.path.abspath(args.output),
        "sampled_frames": len(report["frames"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
