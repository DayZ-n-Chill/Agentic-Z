# Rigging a body to the character skeleton

Covers giving a custom humanoid mesh (a survivor body, a human NPC or an infected) weights on the vanilla bone names in the canonical bind pose, in Blender, and why a body explodes or does not move. Writing the result to `.p3d` and checking it is in `body-export.md`.

This is the expensive step of any new body. DayZ ships no armature: `model.cfg` defines the skeleton, the `.p3d` carries named selections with weights, and the engine pairs them, so a bone in `model.cfg` is a named vertex selection. Why a rig that looks fine at rest still deforms in game, and the mirrored mesh fault, are in `canonical-bind.md`. The infected side (class, size, AI) is in `_shared/ai/custom-infected.md`, and the LODs in `body-lods.md`. Blender and py3d behaviour is tool knowledge and not checked on `P:\`; results from a test infected body about 1.27 times vanilla size were measured in Blender or in game.

## Rules that decide the outcome

- The engine binds against its own canonical bind, not your mesh. Match it in scale (about 1.8 m), facing and handedness, and joint positions (`canonical-bind.md`).
- Export from Blender with `(x, y, z)` to `(x, z, y)`, faces in Blender order and normals negated (`body-export.md`). Every determinant +1 map mirrors the mesh.
- Bake the armature scale before automatic weights. Then keep at most 4 influences per vertex, no vertex without a weight, and no vertex weighted to both a left and a right bone.
- A Blender pose test is not a deform gate. Only a spawn in game or Buldozer proves deformation (`canonical-bind.md`).
- Size is baked into the mesh, and it fights the bind. About 1.27 times vanilla deforms visibly under animation; only up to about 1.1 times may pass (measured in game).
- Inheriting the vanilla animation block is free; shipping new character animations is not. Only one mod that changes the player or creature graphs can load at a time (`_shared/animation/anim-graphs.md`), so warn the user before a plan ships custom character animations.
- Check bone names on `P:\`, never from memory. The vanilla lists are in `P:\DZ\anims\cfg\skeletons.anim.xml`; the player's `player_testing.xob` list starts at `:110`.

## Get the official rig

Download `animation_rig_character.fbx` from Bohemia's public repository `BohemiaInteractive/DayZ-Misc`, folder "Rig and Animations" (<https://github.com/BohemiaInteractive/DayZ-Misc>). It is a Blender native FBX holding:

- An armature `Armature` with 114 bones named like the vanilla character bones (the skeleton often called `OFP2_ManSkeleton`).
- A weighted reference body `Male_body` (7,499 vertices) in the canonical bind A-pose, a free reference for proportions and bind.
- Units in centimetres (about 172.5 tall) with the legacy importer; the native importer of Blender 5.x gives bone heads in metres (`autofit-on-official-rig.md`).
- Helpers (`*_Dummy`, `Weapon_*`, `EntityPosition`) that import as empties, not bones. Ignore them for deformation.

```powershell
$dir = "<work-folder>\_rig"; New-Item -ItemType Directory -Force $dir | Out-Null
$enc = "Rig%20and%20Animations/animation_rig_character.fbx"
Invoke-WebRequest "https://raw.githubusercontent.com/BohemiaInteractive/DayZ-Misc/master/$enc" `
  -OutFile "$dir\animation_rig_character.fbx" -Headers @{ "User-Agent" = "x" }
```

Inspect it once: import it, list `bpy.data.objects` and the `armature.data.bones` names, read the world Z span, and confirm the names against `P:\DZ\anims\cfg\skeletons.anim.xml`.

Another route, not checked here: build the armature from the player rig, parent with automatic weights or rename the vertex groups to the DayZ bone names, then import into Object Builder with weights and selections.

The vanilla character models are binarized (the header of `P:\DZ\characters\zombies\hermit_above0.p3d` reads ODOL version 56 in 1.30), so they cannot be edited; author a new mesh and rig it. The bones a vanilla infected config names for its attachment proxies show which bones matter most: `Spine1`, `Spine2`, `Spine3`, `Head`, `Pelvis`, `LeftHand`, `RightHand_Dummy`, the shoulders and the legs (`BoneNames[]` at `P:\DZ\characters\zombies\config.cpp:48`).

## Fit the armature to the mesh

Keep the mesh at its final size and scale the armature to it. The armature's size never reaches the game (the engine uses its own skeleton); it only makes weights.

Bake the scale into the armature before bone heat weighting. Scaling only the object, or a parent, leaves the bone data at centimetre scale. Bone heat then runs a 172 unit armature against a mesh about 2 units tall, the whole mesh is a dot near `Pelvis`, and every weight lands on `Pelvis`. The tell: after binding, posing any limb moves nothing.

```python
# arm = the imported Armature, low = your mesh (feet at z=0, centred)
arm.parent = None; arm.animation_data_clear()
s = mesh_height / armature_world_height
arm.scale = (s, s, s); bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # bake into bone data
# then move the armature so its bones stand with feet at z=0, centred on the mesh, and apply location
```

## Bind with automatic weights

Turn off deform on bones you do not want as selections (face, fingers, eyes, tongue) so the vertex groups stay clean, then parent with automatic weights.

```python
for b in arm.data.bones:
    if b.name.startswith("Face_") or b.name in ("EyeLeft", "EyeRight") \
       or any(f in b.name for f in ("Index", "Middle", "Ring", "Pinky", "Thumb")) or "Tongue" in b.name:
        b.use_deform = False
bpy.ops.object.select_all(action='DESELECT')
low.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
```

Check the spread, not just that the operator ran. Count weighted vertices per major bone: when `LeftUpLeg`, `Spine1`, `LeftArm` and the rest have vertices and `Pelvis` is not holding everything, the fit was right. A body ends with about 44 deform bones and no vertex without a weight.

For a body with a see-through cavity, envelope weighting is the robust choice: weight by distance to the bone segment, with a fade by side and a column from pelvis to crotch. On the test infected a data transfer from the solid `Male_body` weighted the tunnel inside wrong and gave spikes of 100 times; envelope weighting did not.

## Conform the mesh to the bind pose

The mesh must ship in the rig's canonical A-pose, because the animations are relative to that rest pose. Measure each limb's direction against its bone. Where it is off, rotate that limb's vertices around the joint, masked by each vertex's automatic weight in the limb groups, so the shoulder or hip blends with no crease. Bind again afterwards for clean weights on the conformed mesh.

```python
# per side: pivot = armb.head (world); target = bone chain direction; R turns mesh_arm_dir onto target
from mathutils import Quaternion
for v in low.data.vertices:
    w = sum(g.weight for g in v.groups if vgname(g) in arm_groups)   # 0..1
    if w <= 1e-4: continue
    Rw = Quaternion().slerp(R, min(w, 1.0))                           # partial rotation = smooth falloff
    v.co = MWi @ (pivot + Rw @ (MW @ v.co - pivot))
```

On the test infected the arms sat 28 and 34 degrees narrower than canonical, and this opened them onto the bones cleanly.

The angle is not enough: the joints must sit on the canonical bone positions too. A generated mesh has its own proportions, so its elbows, knees, shoulders and wrists sit elsewhere, and the limbs overextend and stretch under animation even when scale, facing and winding are right. The test infected had arms about 0.12 m shorter than the armature and showed it in game.

The fix is a proportion conform: move the joint regions of the mesh onto the canonical bone positions, masked by weight like the angle conform, then bind again. Check it offline with the distance from each bone head to the weighted centroid of its vertices; a large distance means that limb will deform.

- Conform in X and Z only and keep the depth (Y in Blender). A thin plate spline conform to bone midpoints that lie almost in one plane flattens the body to paper, and it renders flat in game. Always look at a side render of the rest pose.
- Conform and new weights have a ceiling of about 30 to 45 % less deformation. Past it, rebuild on the vanilla body (`canonical-bind.md`, section "When conform and new weights stall").

## Clean up the weights

```python
bpy.ops.object.vertex_group_limit_total(limit=4)     # DayZ skinning: at most 4 influences per vertex
bpy.ops.object.vertex_group_normalize_all()
```

Aim for at most 4 influences per vertex and no vertex without a weight; an unweighted vertex shows as a pinched or spiky point in game.

Then remove weight that crosses the midline, the usual cause of a body "totally deformed in game". Bone heat on a narrow torso bleeds across the centre, so vertices near the spine, neck, chest and shoulders get both a `left*` and a `right*` bone. It looks fine at rest and passes any pose test that never moves the two arms apart. In game, opposing limb animations tear those vertices apart: a badly deformed mesh and smeared UVs that read as wrong colours, with no script error.

- Binarize warns `Error: vertices of bone X are shared with bone Y` for a left and right pair. Treat it as blocking, never cosmetic.
- Fix per vertex: keep only the dominant side plus the centre bones (spine, pelvis, neck, head), zero the other side and normalize again. The test infected had 1,847 such vertices.
- Verify: no vertex with both a `left*` and a `right*` weight, and no "shared with bone" from binarize.
- On weights that are already lopsided this fix makes things worse. On the test infected (`LeftUpLeg` 37 vertices against `RightUpLeg` 166, 19 % of weight across the midline) it moved whole regions to the opposite limb and raised the stretch to 21 to 34 times. Use envelope weighting there.

## Check that limbs move

This Blender pose test shows only whether a limb moves at all; the deform gate is in game or in Buldozer (`canonical-bind.md`, section "The Blender deform test is a false gate").

Pose spine, arms and legs and render several views. Bends must be smooth, with no exploded vertices, joints holding, and any internal geometry following its parent bone. Pose the left and right limbs in opposite directions in the same pose (left arm up and right arm down, left leg forward and right leg back); it is the only pose test that shows weight across the midline.

Headless pitfalls:

- The FBX may carry an Action whose curves override a manual `rotation_euler`. If posing does nothing, call `arm.animation_data_clear()` first, and set `arm.data.pose_position = 'POSE'`.
- FBX bone tails are made up by the importer, so `tail - head` does not follow the limb. Never tell A-pose from T-pose by bone vectors; use a render or the skinned result.
- Track deformation by original vertex index. `evaluated_get(dg).to_mesh().vertices[i].index` is invalid after `to_mesh_clear()`, so take the index from `low.data.vertices` and read evaluated positions at that same `i` in each pose.
- Set the pose through `pose.bones[n].rotation_euler` (mode `'XYZ'`) and `view_layer.update()`; background mode needs no mode switch.

```python
arm.data.pose_position = 'POSE'
pb = arm.pose.bones['LeftUpLeg']; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (radians(45), 0, 0)
bpy.context.view_layer.update()
# a largest vertex delta against rest above 0, with thousands of vertices moving, means skinning works
```

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| Posing the rig moves nothing; all weights on `Pelvis` | Armature scale not baked before bone heat, or a live Action | "Fit the armature to the mesh"; "Check that limbs move" |
| Spiky or pinched vertices | Vertices without a weight | "Clean up the weights" |
| Badly deformed in game, Blender pose looked fine; binarize says "shared with bone" | Weight across the midline | "Clean up the weights" |
| Limbs lag or float during animations | Mesh not in the canonical A-pose, or baked scale drift | "Conform the mesh to the bind pose"; `canonical-bind.md` |
| Limbs overextend or stretch under animation, fine at rest | Scale or proportions differ from the canonical bind | The proportion conform above; `canonical-bind.md` |
| The whole mesh renders flat, like paper | A conform collapsed the depth | "Conform the mesh to the bind pose" |
| Deforms wrong in game although the Blender pose test was clean | The Blender armature is not the engine skeleton | `canonical-bind.md`; gate in game or in Buldozer |
| Explodes, faces backward, renders inside out or lit wrong | The export | `body-export.md`, section "Symptom to cause" |
| Worn item floats above the player as a rigid block, or breaks into rigid pieces | Clothing skeleton name, or a worn mesh facing +Z | `worn-models.md` |
