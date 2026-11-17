---
name: mixamo-retarget
description: "Experimental (unit-tested outside Blender; a run inside Blender is still pending): retargets Mixamo or any FBX or DAE animation onto a custom Blender rig, including the DayZ skeleton, with fuzzy bone matching, a Mixamo to Rigify preset, a reviewed bone map per armature pair, NLA stacking and playback, all run through the Blender MCP server. Use when the user wants to apply Mixamo mocap to a character, retarget an animation between skeletons, auto-map bones between two armatures, import an animation FBX onto an existing rig, or source motion-capture keyframes for the DayZ animation pipeline. Triggers: retarget, Mixamo, mocap onto my rig, move an animation between skeletons, bone mapping, apply an FBX animation (Spanish: \"mocap a mi rig\", \"pasar animación entre esqueletos\", \"aplicar animación FBX\")."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# Mixamo retarget (through the Blender MCP)

Retargets skeletal animation between armatures inside Blender, driven through the Blender MCP server that is already connected (`execute_blender_code`). It needs no extra add-on and no WebSocket server: the two modules in `<skill-dir>\scripts\` are plain Blender Python.

**Status: experimental.** The modules are unit-tested outside Blender (`scripts\test_bone_matching.py` and `scripts\test_retargeting.py`, the second against a stand-in `bpy`), not yet validated on a fixture inside Blender. Before the first production use, run the fixture at the end of this file and record the result.

This skill runs nothing against `P:\`, DayZ Tools or the game, so there is no preflight gate.

## What it does

| Function | Module | Purpose |
|---|---|---|
| `auto_map_bones(source, target)` | `retargeting.py` | Fuzzy bone matching with a Mixamo alias table. Returns `{source_bone: target_bone}`. |
| `get_preset_bone_mapping("mixamo_to_rigify")` | `retargeting.py` | A preset map. The shipped preset holds ten bones (hips to left hand); extend it before relying on it. |
| `store_bone_mapping`, `load_bone_mapping` | `retargeting.py` | Keep a reviewed map per armature pair on the scene, so the fuzzy pass runs once and the corrected map is reused. See "Known gaps". |
| `retarget_animation(source, target, bone_map, preserve_rotation=True, preserve_location=False)` | `retargeting.py` | Adds Copy Rotation constraints from source to target bones (and Copy Location on `Hips` when `preserve_location` is true), then bakes them to keyframes on the target rig over the scene frame range. |
| `import_fbx`, `import_dae`, `list_armatures`, `get_bones`, `list_animations`, `play_animation`, `stop_animation`, `add_to_nla` | `retargeting.py` | Import, inspect, play and stack. |
| `normalize_bone_name`, `calculate_similarity`, `find_best_match`, `fuzzy_match_bones`, `get_match_quality_report` | `bone_matching.py` | The matching engine: pure Python, no `bpy`. |

## How to run it (through the Blender MCP)

1. Load both modules once per Blender session. `retargeting.py` imports `fuzzy_match_bones` from `bone_matching`, so the scripts folder has to be importable. Send this through `execute_blender_code`:

   ```python
   import sys
   sys.path.insert(0, r"<skill-dir>\scripts")
   from retargeting import *
   ```

   When Blender cannot read that folder, read the two files and send their source instead, `bone_matching.py` first, with the `from bone_matching import ...` line removed from the `retargeting.py` source so the names already defined are used.

2. Import the clip and get a first map:

   ```python
   import_fbx(r"<path-to>\Walking.fbx")            # brings in the Mixamo armature and its action
   print(list_armatures())                          # for example ['Armature', 'MyDayZRig']
   bm = auto_map_bones("Armature", "MyDayZRig")    # fuzzy pass: review this dict
   print(bm)
   ```

3. **Two phases, always.** Never retarget straight off the fuzzy map. Print it, review and correct it (the user, or a reasoned pass over both bone lists), keep the corrected version, and only then bake:

   ```python
   scene = bpy.context.scene
   scene.frame_start, scene.frame_end = (int(f) for f in bpy.data.objects["Armature"].animation_data.action.frame_range)
   retarget_animation("Armature", "MyDayZRig", bone_map=bm)
   baked = bpy.data.objects["MyDayZRig"].animation_data.action
   baked.name = "Walking_retarget"
   play_animation("MyDayZRig", "Walking_retarget")
   ```

   `retarget_animation` has no parameter for the action name and bakes the scene frame range, which is why the example sets the range from the source action first and renames the baked action afterwards.

## References

| File | Question it answers |
|---|---|
| `references/bone-mapping-guide.md` | How does the matching algorithm score names, what do the quality ratings mean, which bone names does each rig family (Rigify, Unreal, Unity) use, and how do I fix a bad match? Read it when the fuzzy map comes back with gaps. |

## Rest-pose caveat (the classic failure)

Mixamo rigs are in T-pose; many targets, game rigs included, are in A-pose or a custom pose. A retarget across mismatched rest poses bakes a permanent offset into every frame. Align the rest poses first (apply the rotation on the Mixamo armature, or pose-match the target's rest to the source) before judging the result. Symptom: arms floating about 45 degrees off on every frame.

## Known gaps in the shipped modules

Read from the code, not yet run in Blender. Check each one when the fixture below is run.

- **`mixamorig:` prefix.** `auto_map_bones` only takes source bones whose names are keys of its alias table (`Hips`, `LeftArm`, ...). A Mixamo FBX normally imports with prefixed names (`mixamorig:Hips`), and those match no key, so nothing is mapped. The call then stops with `KeyError: 'critical_bones_mapped'`, because the quality report for an empty map has no such entry (`test_retargeting.py` pins this against a stand-in `bpy`). The same error appears for any pair of armatures with no match at all. Rename the source bones to drop the prefix first, or build the map by hand.
- **Stored maps.** `store_bone_mapping` and `load_bone_mapping` use `scene.bone_mapping_items`, `scene.bone_mapping_source_armature` and `scene.bone_mapping_target_armature`. Neither module registers those scene properties, so without that registration both calls fail. Until they are registered, keep the reviewed map as a Python dict, or save it as JSON next to the `.blend`.
- **Empty map.** `retarget_animation` does not reject an empty `bone_map`: it adds no constraints and still bakes. That is the negative case of the fixture below.
- **Near misses above the threshold.** With the default threshold 0.6, `LeftArm` against `LeftLeg` scores 0.671 (measured with `bone_matching.py`), so a left arm can land on a leg bone when the target has no better name. This is why the map is reviewed before baking.

## DayZ integration note

A retarget onto the DayZ skeleton gives **source keyframes**, not a game-ready animation. It feeds Layer 2 of `dayz-animation-pipeline` (Blender keyframes, then SEAnim, then DayZATool, then `.anm`), and the wall that skill flags still applies when the result ships in a replacement player or creature animation graph: a server can load only one mod that replaces a given graph. Use it to source mocap for creatures, poses and reference motion, not as a shortcut around the pipeline. For motion that has to look physically right in game, `dayz-realistic-animation-director` sets the acceptance contract first.

## Fixture before first real use

A new skill is not trusted until one positive and one negative fixture have run.

- **Positive:** import any Mixamo FBX and retarget it onto a copy of its own armature with the identity map. The result must visually match the original (render three frames with `blender-visual-review`).
- **Negative:** a retarget with an empty bone map must raise or return an error, not silently produce a frozen action.

Record both outcomes; only then drop the experimental label.

## Assets

This skill ships no Mixamo or Adobe mocap, FBX or character assets, only the retargeting workflow. Download Mixamo clips yourself; they stay on your machine and are not part of this repo.
