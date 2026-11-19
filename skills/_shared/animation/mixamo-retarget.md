# Mixamo retarget

How to move a Mixamo or other FBX clip onto a Blender armature with the two retarget modules, and where the result enters the DayZ pipeline. The bone name matching itself is in `mixamo-bone-mapping.md`.

Experimental: the modules `retargeting.py` and `bone_matching.py` in `skills/dayz-animation-pipeline/scripts/` have unit tests outside Blender (`test_bone_matching.py`, and `test_retargeting.py` against a stand-in `bpy`), but nothing here has run inside Blender yet. Treat every step as untested until the two checks in "Before the first real use" pass. Nothing here runs against `P:\`, DayZ Tools or the game.

## The functions

Both modules are plain Blender Python. They run through the Blender MCP server already connected (`execute_blender_code`) and need no add-on.

| Function | Module | Use |
|---|---|---|
| `auto_map_bones(source, target)` | `retargeting.py` | Fuzzy bone matching with a Mixamo alias table. Returns `{source_bone: target_bone}`. |
| `get_preset_bone_mapping("mixamo_to_rigify")` | `retargeting.py` | A preset map of ten bones, hips to left hand. Extend it before you rely on it. |
| `store_bone_mapping`, `load_bone_mapping` | `retargeting.py` | Keep a reviewed map per armature pair on the scene. They need scene properties no module registers; see "Known gaps". |
| `retarget_animation(source, target, bone_map, preserve_rotation=True, preserve_location=False)` | `retargeting.py` | Adds Copy Rotation constraints from source to target bones (and Copy Location on `Hips` when `preserve_location` is true), then bakes them to keys on the target over the scene frame range. |
| `import_fbx`, `import_dae`, `list_armatures`, `get_bones`, `list_animations`, `play_animation`, `stop_animation`, `add_to_nla` | `retargeting.py` | Import, inspect, play and stack. `list_animations` returns every object level action in the file, not only that armature's. |
| `normalize_bone_name`, `calculate_similarity`, `find_best_match`, `fuzzy_match_bones`, `get_match_quality_report` | `bone_matching.py` | The matching engine, pure Python with no `bpy`. |

## Running it

1. Load both modules once per Blender session. `retargeting.py` imports from `bone_matching`, so the scripts folder must be on the path:

   ```python
   import sys
   sys.path.insert(0, r"<repo>\skills\dayz-animation-pipeline\scripts")
   from retargeting import *
   ```

   When Blender cannot read that folder, send the source of both files instead, `bone_matching.py` first, and drop the `from bone_matching import ...` line from `retargeting.py`.

2. Import the clip, strip the `mixamorig:` prefix and get a first map:

   ```python
   import_fbx(r"<path-to>\Walking.fbx")
   print(list_armatures())                          # for example ['Armature', 'MyMod_Rig']
   for b in list(bpy.data.objects["Armature"].data.bones):
       b.name = b.name.split(":", 1)[-1]
   bm = auto_map_bones("Armature", "MyMod_Rig")
   print(bm)
   ```

3. Review the map before you bake. Print it, correct it by hand or with a reasoned pass over both bone lists, keep the corrected copy, then bake:

   ```python
   scene = bpy.context.scene
   scene.frame_start, scene.frame_end = (int(f) for f in bpy.data.objects["Armature"].animation_data.action.frame_range)
   retarget_animation("Armature", "MyMod_Rig", bone_map=bm)
   baked = bpy.data.objects["MyMod_Rig"].animation_data.action
   baked.name = "Walking_retarget"
   play_animation("MyMod_Rig", "Walking_retarget")
   ```

   `retarget_animation` has no parameter for the action name and bakes the scene frame range, so set the range from the source action first and rename the baked action after.

## Match the rest poses first

Mixamo rigs rest in a T pose; most game rigs rest in an A pose or their own pose. A retarget across different rest poses bakes a fixed offset into every frame, and the arms float about 45 degrees off. Line the rest poses up first: apply the rotation on the Mixamo armature, or pose the target's rest to match the source.

## Known gaps

Read from the code, not yet run in Blender. Check each one when the first real run happens.

- Prefixed names. `auto_map_bones` only takes source bones whose names are keys of its alias table (`Hips`, `LeftArm` and so on). A Mixamo FBX imports as `mixamorig:Hips`, which matches nothing, and the call stops with `KeyError: 'critical_bones_mapped'` because the quality report of an empty map lacks that key (`test_retargeting.py` pins this). Any pair of armatures with no match at all gives the same error. Strip the prefix (step 2 above) or build the map by hand.
- Stored maps. `store_bone_mapping` and `load_bone_mapping` use `scene.bone_mapping_items`, `scene.bone_mapping_source_armature` and `scene.bone_mapping_target_armature`, which neither module registers, so both calls fail. Keep the reviewed map as a Python dict or as JSON next to the `.blend`.
- DAE import. `import_dae` calls `bpy.ops.wm.collada_import`, which Blender 5.0 removed. Convert the clip to FBX, or import the DAE in Blender 4.x.
- Empty map. `retarget_animation` accepts an empty `bone_map`, adds no constraints and still bakes a frozen action.
- Near misses. With the default threshold 0.6, `LeftArm` against `LeftLeg` scores 0.671 in `bone_matching.py`, so an arm can land on a leg bone when the target has no better name. This is why the map is reviewed before baking.

## Where the result goes in DayZ

A retarget onto the survivor skeleton (the `player_testing.xob` block at `P:\DZ\anims\cfg\skeletons.anim.xml:110`; zones in `player-skeleton.md`) gives source keys, not a game ready clip. It enters the clip route in `tooling-and-walls.md`: Blender keys, then SEAnim, then DayZATool, then `.anm`. The graph limits still apply when the clip ships in a replacement player or creature graph: two mods that replace the same graph collide, and loading both is reported to crash client and server (not measured on 1.30). Use it to source mocap for creatures, poses and reference motion. When the motion has to look physically right in game, set the acceptance first with `realistic-motion.md`.

## Before the first real use

Run one good case and one bad case, and record both results before you drop the experimental label:

- Good: import any Mixamo FBX and retarget it onto a copy of its own armature with the identity map. The result must match the original; render three frames with the capture helper in `_shared/models/blender-visual-review.md`.
- Bad: a retarget with an empty bone map must raise or return an error, not bake a frozen action.

This repo ships no Mixamo or Adobe clips, FBX files or characters, only the workflow. Download Mixamo clips yourself; they stay on your machine.
