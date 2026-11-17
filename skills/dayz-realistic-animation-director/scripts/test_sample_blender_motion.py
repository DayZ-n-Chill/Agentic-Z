import copy
import json
import math
import os
import sys
import tempfile
import traceback
from pathlib import Path

try:
    import bpy
except ImportError:
    # Outside Blender the module skips itself, as pytest.importorskip("bpy")
    # would. pytest is imported on this branch only: Blender's bundled Python
    # has none, and run_regression_tests.py runs this file inside Blender.
    import pytest

    pytest.skip(
        "needs Blender's bpy: blender --background --factory-startup --python <this file>",
        allow_module_level=True,
    )


SCRIPTS_DIR = Path(__file__).resolve().parent  # this test sits next to the scripts
sys.path.insert(0, str(SCRIPTS_DIR))


def assert_close(actual, expected, tolerance=1e-6):
    if len(actual) != len(expected):
        raise AssertionError(f"length mismatch: {actual!r} vs {expected!r}")
    for index, (left, right) in enumerate(zip(actual, expected)):
        if abs(float(left) - float(right)) > tolerance:
            raise AssertionError(f"component {index}: {left!r} vs {right!r}")


def build_fixture():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    armature_data = bpy.data.armatures.new("RigData")
    rig = bpy.data.objects.new("Rig", armature_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    hand = armature_data.edit_bones.new("Hand")
    hand.head = (0.0, 0.0, 0.0)
    hand.tail = (0.0, 1.0, 0.0)
    finger = armature_data.edit_bones.new("Finger")
    finger.head = (0.0, 1.0, 0.0)
    finger.tail = (0.0, 2.0, 0.0)
    finger.parent = hand
    finger.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")

    handle = bpy.data.objects.new("Handle", None)
    bpy.context.collection.objects.link(handle)
    handle.location = (2.0, 0.0, 0.0)

    rig.location = (0.0, 0.0, 0.0)
    rig.keyframe_insert("location", frame=0)
    rig.location = (1.0, 0.0, 0.0)
    rig.keyframe_insert("location", frame=10)
    handle.location = (2.0, 0.0, 0.0)
    handle.keyframe_insert("location", frame=0)
    handle.location = (3.0, 0.0, 0.0)
    handle.keyframe_insert("location", frame=10)
    return rig, handle


def run_test():
    rig, handle = build_fixture()
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.frame_start = 0
    scene.frame_end = 10
    scene.frame_set(5)
    rig_action = rig.animation_data.action
    handle_action = handle.animation_data.action
    contract = {
        "schema_version": 1,
        "contract_mode": "diagnostic",
        "sample_frames": [0, 10],
        "action_bindings": [
            {"object": "Rig", "action": rig_action.name},
            {"object": "Handle", "action": handle_action.name},
        ],
        "landmarks": {
            "finger_base": {"type": "bone_head", "object": "Rig", "bone": "Finger"},
            "finger_tip": {"type": "bone_tail", "object": "Rig", "bone": "Finger"},
            "finger_mid": {"type": "bone_point", "object": "Rig", "bone": "Finger", "factor": 0.5},
            "handle_point": {"type": "object_origin", "object": "Handle"},
            "average_point": {"type": "average", "sources": ["finger_tip", "handle_point"]},
        },
        "transforms": {
            "hand": {"type": "pose_bone_world", "object": "Rig", "bone": "Hand"},
            "hand_local": {"type": "pose_bone_local", "object": "Rig", "bone": "Hand"},
            "handle": {"type": "object_world", "object": "Handle"},
        },
        "segments": {
            "finger": {"point_a": "finger_base", "point_b": "finger_tip", "radius_m": 0.01}
        },
    }
    with tempfile.TemporaryDirectory() as temporary:
        contract_path = os.path.join(temporary, "contract.json")
        output_path = os.path.join(temporary, "report.json")
        with open(contract_path, "w", encoding="utf-8") as handle_file:
            json.dump(contract, handle_file)
        from sample_blender_motion import SamplingError, main as sampler_main, sample_scene, write_json

        report = sample_scene(contract)
        ranged_contract = copy.deepcopy(contract)
        del ranged_contract["sample_frames"]
        ranged_contract["sample_ranges"] = [{"start": 0, "end": 10, "step": 10}]
        ranged_report = sample_scene(ranged_contract)
        if list(ranged_report["frames"].keys()) != ["0", "10"]:
            raise AssertionError("sample_ranges did not expand inclusively")
        write_json(output_path, report)
        with open(output_path, "r", encoding="utf-8") as handle_file:
            round_tripped = json.load(handle_file)

        fractional_frames = copy.deepcopy(contract)
        fractional_frames["sample_frames"] = [0.5]
        try:
            sample_scene(fractional_frames)
        except SamplingError:
            pass
        else:
            raise AssertionError("fractional sample frame was accepted")

        duplicate_binding = copy.deepcopy(contract)
        duplicate_binding["action_bindings"].append({"object": "Rig", "action": rig_action.name})
        try:
            sample_scene(duplicate_binding)
        except SamplingError:
            pass
        else:
            raise AssertionError("duplicate action binding was accepted")

        outside_timeline = copy.deepcopy(contract)
        outside_timeline["sample_frames"] = [999]
        try:
            sample_scene(outside_timeline)
        except SamplingError:
            pass
        else:
            raise AssertionError("sample frame outside scene timeline was accepted")

        missing_radius = copy.deepcopy(contract)
        del missing_radius["segments"]["finger"]["radius_m"]
        try:
            sample_scene(missing_radius)
        except SamplingError:
            pass
        else:
            raise AssertionError("segment without radius was accepted")
        invalid_contract_path = os.path.join(temporary, "invalid-contract.json")
        invalid_output_path = os.path.join(temporary, "invalid-report.json")
        with open(invalid_contract_path, "w", encoding="utf-8") as invalid_handle:
            json.dump(missing_radius, invalid_handle)
        if sampler_main(["--contract", invalid_contract_path, "--output", invalid_output_path]) != 2:
            raise AssertionError("sampler CLI did not return exit 2 for invalid input")
        if os.path.exists(invalid_output_path):
            raise AssertionError("sampler CLI wrote a report for invalid input")

        production_without_radius_provenance = copy.deepcopy(contract)
        production_without_radius_provenance["contract_mode"] = "production"
        try:
            sample_scene(production_without_radius_provenance)
        except SamplingError:
            pass
        else:
            raise AssertionError("production segment radii without provenance were accepted")

        for bad_mode in (None, "productions"):
            invalid_mode = copy.deepcopy(contract)
            if bad_mode is None:
                del invalid_mode["contract_mode"]
            else:
                invalid_mode["contract_mode"] = bad_mode
            try:
                sample_scene(invalid_mode)
            except SamplingError:
                pass
            else:
                raise AssertionError(f"invalid contract_mode {bad_mode!r} was accepted")

    assert scene.frame_current == 5
    assert rig.animation_data.action == rig_action
    assert handle.animation_data.action == handle_action
    assert {
        key: round_tripped["metadata"][key]
        for key in ("fps", "frame_start", "frame_end")
    } == {"fps": 30.0, "frame_start": 0, "frame_end": 10}
    assert list(round_tripped["frames"].keys()) == ["0", "10"]
    assert_close(round_tripped["frames"]["0"]["points"]["finger_tip"], [0.0, 2.0, 0.0])
    assert_close(round_tripped["frames"]["10"]["points"]["finger_tip"], [1.0, 2.0, 0.0])
    assert_close(round_tripped["frames"]["0"]["points"]["finger_mid"], [0.0, 1.5, 0.0])
    assert_close(round_tripped["frames"]["10"]["points"]["handle_point"], [3.0, 0.0, 0.0])
    assert_close(round_tripped["frames"]["0"]["points"]["average_point"], [1.0, 1.0, 0.0])
    assert_close(round_tripped["frames"]["0"]["transforms"]["handle"]["q"], [0.0, 0.0, 0.0, 1.0])
    assert_close(round_tripped["frames"]["10"]["transforms"]["hand"]["p"], [1.0, 0.0, 0.0])
    assert_close(round_tripped["frames"]["10"]["transforms"]["hand_local"]["p"], [0.0, 0.0, 0.0])
    assert round_tripped["metadata"]["action_bindings"] == [
        {"object": "Rig", "action": rig_action.name, "frame_start": 0.0, "frame_end": 10.0},
        {"object": "Handle", "action": handle_action.name, "frame_start": 0.0, "frame_end": 10.0},
    ]
    assert_close(round_tripped["frames"]["0"]["segments"]["finger"]["a"], [0.0, 1.0, 0.0])
    assert math.isclose(round_tripped["frames"]["0"]["segments"]["finger"]["radius_m"], 0.01)


def test_sample_blender_motion():
    # The pytest entry, where bpy imports (Blender's Python, or the bpy module).
    run_test()


if __name__ == "__main__":
    try:
        run_test()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
    print("SAMPLE_BLENDER_MOTION_TEST=PASS")
