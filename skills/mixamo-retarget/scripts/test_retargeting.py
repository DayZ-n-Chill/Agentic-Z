"""Tests for retargeting.py, run against a small stand-in for Blender's bpy module.

retargeting.py imports bpy at the top, so it cannot be imported under plain pytest.
The fixture below puts a stand-in bpy in sys.modules for one test and takes it out
again, so tests elsewhere that skip on a missing bpy still skip. These tests cover the
module's own logic and pin the gaps SKILL.md lists; they do not prove the Blender
calls behave the same way inside Blender.
"""

import importlib
import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = str(Path(__file__).resolve().parent)


def _armature(name, bone_names, action=None):
    bones = [SimpleNamespace(name=b, parent=None, children=[]) for b in bone_names]
    return SimpleNamespace(
        name=name,
        type="ARMATURE",
        data=SimpleNamespace(bones=bones),
        pose=SimpleNamespace(
            bones={b: SimpleNamespace(constraints=_Constraints()) for b in bone_names}
        ),
        animation_data=SimpleNamespace(action=action) if action else None,
        select_set=lambda state: None,
    )


class _Constraints(list):
    def new(self, kind):
        constraint = SimpleNamespace(type=kind, target=None, subtarget=None)
        self.append(constraint)
        return constraint


class _Objects(dict):
    def __iter__(self):
        return iter(self.values())


@pytest.fixture
def blender(monkeypatch):
    calls = []
    objects = _Objects()
    fake_bpy = SimpleNamespace(
        data=SimpleNamespace(objects=objects, actions={}),
        context=SimpleNamespace(
            scene=SimpleNamespace(frame_start=1, frame_end=10),
            view_layer=SimpleNamespace(objects=SimpleNamespace(active=None)),
        ),
        ops=SimpleNamespace(
            object=SimpleNamespace(mode_set=lambda mode: calls.append(("mode_set", mode))),
            nla=SimpleNamespace(bake=lambda **kwargs: calls.append(("bake", kwargs))),
        ),
    )
    monkeypatch.setitem(sys.modules, "bpy", fake_bpy)
    monkeypatch.syspath_prepend(SCRIPTS)
    monkeypatch.delitem(sys.modules, "retargeting", raising=False)
    module = importlib.import_module("retargeting")
    yield SimpleNamespace(module=module, objects=objects, calls=calls, bpy=fake_bpy)
    sys.modules.pop("retargeting", None)


def test_list_armatures_and_get_bones(blender):
    blender.objects["Rig"] = _armature("Rig", ["Hips", "Spine"])
    blender.objects["Cube"] = SimpleNamespace(name="Cube", type="MESH")
    assert blender.module.list_armatures() == ["Rig"]
    assert blender.module.get_bones("Rig")[0] == {"name": "Hips", "parent": None, "children": []}
    with pytest.raises(ValueError):
        blender.module.get_bones("Cube")


def test_auto_map_bones_maps_bare_mixamo_names(blender):
    blender.objects["Src"] = _armature("Src", ["Hips", "Head", "LeftArm"])
    blender.objects["Dst"] = _armature("Dst", ["pelvis", "head", "upper_arm.L"])
    assert blender.module.auto_map_bones("Src", "Dst") == {
        "Hips": "pelvis",
        "Head": "head",
        "LeftArm": "upper_arm.L",
    }


def test_auto_map_bones_fails_on_prefixed_names(blender):
    # Known gap in SKILL.md: mixamorig:-prefixed bones match no key of the alias table,
    # and the empty map then has no 'critical_bones_mapped' entry in its quality report.
    blender.objects["Src"] = _armature("Src", ["mixamorig:Hips", "mixamorig:Head"])
    blender.objects["Dst"] = _armature("Dst", ["pelvis", "head"])
    with pytest.raises(KeyError, match="critical_bones_mapped"):
        blender.module.auto_map_bones("Src", "Dst")


def test_auto_map_bones_rejects_a_missing_armature(blender):
    with pytest.raises(ValueError):
        blender.module.auto_map_bones("Nope", "AlsoNope")


def test_rigify_preset_holds_ten_bones(blender):
    preset = blender.module.get_preset_bone_mapping("mixamo_to_rigify")
    assert len(preset) == 10
    assert preset["Hips"] == "torso"
    assert blender.module.get_preset_bone_mapping("unknown") == {}


def test_retarget_animation_signature_has_no_action_name(blender):
    assert list(inspect.signature(blender.module.retarget_animation).parameters) == [
        "source_armature",
        "target_armature",
        "bone_map",
        "preserve_rotation",
        "preserve_location",
    ]


def test_retarget_animation_needs_a_source_action(blender):
    blender.objects["Src"] = _armature("Src", ["Hips"])
    blender.objects["Dst"] = _armature("Dst", ["pelvis"])
    with pytest.raises(ValueError, match="no animation"):
        blender.module.retarget_animation("Src", "Dst", {"Hips": "pelvis"})


def test_retarget_animation_adds_constraints_and_bakes(blender):
    blender.objects["Src"] = _armature("Src", ["Hips", "Head"], action=object())
    target = _armature("Dst", ["pelvis", "head"])
    blender.objects["Dst"] = target
    result = blender.module.retarget_animation(
        "Src", "Dst", {"Hips": "pelvis", "Head": "head", "Tail": "tail"}, preserve_location=True
    )
    assert result == "Animation retargeted to Dst"
    assert [c.type for c in target.pose.bones["pelvis"].constraints] == ["COPY_ROTATION", "COPY_LOCATION"]
    assert [c.type for c in target.pose.bones["head"].constraints] == ["COPY_ROTATION"]
    bake = [kwargs for name, kwargs in blender.calls if name == "bake"]
    assert len(bake) == 1
    assert (bake[0]["frame_start"], bake[0]["frame_end"]) == (1, 10)
    assert bake[0]["clear_constraints"] is True


def test_retarget_animation_still_bakes_an_empty_map(blender):
    # Known gap in SKILL.md: an empty bone map is not rejected.
    blender.objects["Src"] = _armature("Src", ["Hips"], action=object())
    blender.objects["Dst"] = _armature("Dst", ["pelvis"])
    blender.module.retarget_animation("Src", "Dst", {})
    assert [name for name, _ in blender.calls].count("bake") == 1


def test_store_bone_mapping_fails_without_registered_scene_properties(blender):
    # Known gap in SKILL.md: neither module registers scene.bone_mapping_items.
    with pytest.raises(AttributeError):
        blender.module.store_bone_mapping("Src", "Dst", {"Hips": "pelvis"})


def test_list_animations_reads_slots_without_id_root(blender):
    # Blender 5.x actions have slots and no id_root attribute.
    actions = _Objects()
    actions["Walk"] = SimpleNamespace(name="Walk", slots=[SimpleNamespace(target_id_type="OBJECT")])
    actions["Mat"] = SimpleNamespace(name="Mat", slots=[SimpleNamespace(target_id_type="MATERIAL")])
    blender.bpy.data.actions = actions
    blender.objects["Rig"] = _armature("Rig", ["Hips"], action=actions["Walk"])
    assert blender.module.list_animations("Rig") == ["Walk"]


def test_list_animations_reads_id_root_on_actions_without_slots(blender):
    # Blender 4.3 and earlier: no slots, id_root on the action.
    actions = _Objects()
    actions["Walk"] = SimpleNamespace(name="Walk", id_root="OBJECT")
    actions["Key"] = SimpleNamespace(name="Key", id_root="KEY")
    blender.bpy.data.actions = actions
    blender.objects["Rig"] = _armature("Rig", ["Hips"], action=actions["Walk"])
    assert blender.module.list_animations("Rig") == ["Walk"]


def test_imports_reject_a_missing_file(blender, tmp_path):
    with pytest.raises(ValueError, match="File not found"):
        blender.module.import_fbx(str(tmp_path / "missing.fbx"))
    with pytest.raises(ValueError, match="File not found"):
        blender.module.import_dae(str(tmp_path / "missing.dae"))
