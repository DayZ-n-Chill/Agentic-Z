# Rigging a custom body to the DayZ character skeleton

Covers giving a custom humanoid mesh (a survivor body, a human NPC or an infected) per-vertex weights on the exact vanilla bone names, in the canonical bind pose, in Blender, and exporting it with py3d so the weights become named selections in the `.p3d`. It ends with a symptom table for a body that deforms, explodes or renders wrong.

This is the expensive step of any new body. In DayZ there is no shipped armature: `model.cfg` defines the skeleton, the `.p3d` carries named selections with weights, and the engine pairs them. A "bone" in `model.cfg` is a named vertex selection. Why a rig that looks fine at rest still deforms in game, and the mirrored-mesh fault, are in `canonical-bind.md`. The infected side (class, size, LODs, AI) is in `skills/_shared/ai/custom-infected.md`.

How to read the marks: a `P:\` path with a line number was opened and checked in vanilla. "Giant infected build" marks a result measured on a custom giant infected test build, in Blender or in game, on the date given; none of those can be checked on `P:\`. Blender and py3d behaviour is tool behaviour, also not checkable on `P:\`. The Blender side was run end to end against the official rig (2026-06-24); the export was verified with py3d (2026-06-25) and corrected for handedness on 2026-10-01.

## Rules that decide the outcome

1. **The engine binds against its own canonical bind, not your mesh.** Match it in scale (about 1.8 m), orientation and handedness, and joint positions (`canonical-bind.md`).
2. **Export from Blender with `(x, y, z)` to `(x, z, y)`, faces in Blender order, normals negated** (section 6). Every determinant +1 map mirrors the mesh.
3. **Bake the armature scale before automatic weights** (section 1), then at most 4 influences per vertex, no vertex without a weight, and no vertex weighted to both a left and a right bone (section 4).
4. **A Blender pose test is not a deform gate.** Only an in-game spawn or Buldozer validates deformation (`canonical-bind.md`).
5. **Size is baked into the mesh, and it fights the bind.** A mesh far from vanilla size deforms under animation; about 1.27 times was already too much, and only up to about 1.1 times may pass (giant infected build, in game).
6. **Inheriting the vanilla animation block is free; shipping new character animations is not.** Only one mod that changes the player or creature animation graphs can be loaded at a time (`skills/_shared/animation/anim-graphs.md`). Warn the user before a plan ships custom character animations.
7. **Check bone names on `P:\`, never from memory**: the vanilla bone lists are in `P:\DZ\anims\cfg\skeletons.anim.xml` (the player's `player_testing.xob` list starts at `:110`).

## 0. Get the official rig (one download)

`animation_rig_character.fbx` from Bohemia's public repository `BohemiaInteractive/DayZ-Misc`, folder "Rig and Animations" (<https://github.com/BohemiaInteractive/DayZ-Misc>). It is a Blender-native FBX:

- An armature `Armature` with 114 bones whose names are the vanilla character bone names (the skeleton often called `OFP2_ManSkeleton`).
- A weighted reference body `Male_body` (7,499 vertices) in the canonical bind A-pose. It is a free proportion and bind reference.
- Units are centimetres (height about 172.5) with the legacy importer; the native importer of Blender 5.x gives bone heads in metres (`autofit-on-official-rig.md`, section 1).
- Helpers (`*_Dummy`, `Weapon_*`, `EntityPosition`) import as empties, not bones. Ignore them for body deformation.

```powershell
$dir = "<work-folder>\_rig"; New-Item -ItemType Directory -Force $dir | Out-Null
$enc = "Rig%20and%20Animations/animation_rig_character.fbx"
Invoke-WebRequest "https://raw.githubusercontent.com/BohemiaInteractive/DayZ-Misc/master/$enc" `
  -OutFile "$dir\animation_rig_character.fbx" -Headers @{ "User-Agent" = "x" }
```

Inspect it once: import, list `bpy.data.objects` (armature, `Male_body`, empties), the `armature.data.bones` names, the world Z span (height), and which target bones exist. Confirm the names against the vanilla bone list in `P:\DZ\anims\cfg\skeletons.anim.xml`.

Another route for this step (not checked here): build the armature from the player rig, parent with automatic weights or rename the vertex groups to the DayZ bone names, then import into Object Builder with weights and selections.

The vanilla character models are binarized (ODOL; the header of `P:\DZ\characters\zombies\hermit_above0.p3d` reads version 56 in 1.30), so they cannot be edited directly; author a new mesh and rig it. The bones a vanilla infected config names for its attachment proxies show which bones matter most: `Spine1`, `Spine2`, `Spine3`, `Head`, `Pelvis`, `LeftHand`, `RightHand_Dummy`, shoulders and legs (`BoneNames[]` at `P:\DZ\characters\zombies\config.cpp:48`).

## 1. Fit the armature to your mesh: the scale trap

Keep the mesh at its final size and scale the armature to it. The armature's absolute size does not reach the game (the engine uses its own skeleton); it only generates weights.

Bake the scale into the armature before bone-heat weighting. Scaling only the object, or a parent, leaves the bone data at native centimetre scale. Bone-heat then runs a 172-unit armature against a mesh about 2 units tall, the whole mesh is a dot near `Pelvis`, and every weight collapses onto `Pelvis` with zero vertices on every other bone. The tell: after binding, posing any limb moves nothing. (The giant infected build hit this first: the mesh was 2.277 m against the 172-unit rig.)

```python
# arm = the imported Armature, low = your mesh (feet at z=0, centred)
arm.parent = None; arm.animation_data_clear()
s = mesh_height / armature_world_height
arm.scale = (s, s, s); bpy.context.view_layer.update()
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # bake into bone data
# then translate the armature so its bone bounding box has its feet at z=0, centred on the mesh, and apply location
```

## 2. Bind with automatic weights

Disable deform on bones you do not want as selections (face, fingers, eyes, tongue) to keep the vertex group set clean, then parent with automatic weights.

```python
for b in arm.data.bones:
    if b.name.startswith("Face_") or b.name in ("EyeLeft", "EyeRight") \
       or any(f in b.name for f in ("Index", "Middle", "Ring", "Pinky", "Thumb")) or "Tongue" in b.name:
        b.use_deform = False
bpy.ops.object.select_all(action='DESELECT')
low.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
```

Check the distribution, not just that the operator succeeded. Count weighted vertices per major bone: when `LeftUpLeg`, `Spine1`, `LeftArm` and the rest are non-zero and `Pelvis` is not holding everything, the fit was right. A body rig ends with about 44 deform bones. Confirm zero vertices without a weight.

**Envelope weighting** is the robust alternative for a body with a see-through cavity: weight by distance to the bone segment, with a fade by side and a column from pelvis to crotch. On the giant infected build a data transfer from the solid `Male_body` weighted the tunnel interior wrong and gave 100 times spikes; envelope weighting did not.

## 3. Bind pose: conform the mesh to the canonical pose

The mesh must ship in the rig's canonical A-pose, because the animations are relative to that rest pose. Measure each limb's direction against its bone. Where it is off, rotate that limb's vertices around the joint, masked by each vertex's automatic weight in the limb groups, so the shoulder or hip blends smoothly with no crease. Bind again afterwards for clean weights on the conformed mesh.

```python
# per side: pivot = armb.head (world); target = bone chain direction; R aligns mesh_arm_dir -> target
from mathutils import Quaternion
for v in low.data.vertices:
    w = sum(g.weight for g in v.groups if vgname(g) in arm_groups)   # 0..1
    if w <= 1e-4: continue
    Rw = Quaternion().slerp(R, min(w, 1.0))                           # partial rotation = smooth falloff
    v.co = MWi @ (pivot + Rw @ (MW @ v.co - pivot))
```

On the giant infected build the arms were 28 and 34 degrees narrower than canonical; this opened them onto the bones cleanly.

The angle is not enough: the joint positions must match too (giant infected build, in game, 2026-06-25). The engine binds against the canonical bone positions (`canonical-bind.md`). When the mesh's anatomical joints (elbow, knee, shoulder, wrist) sit elsewhere, which a generated mesh always has because its proportions are its own, the limbs overextend and stretch under animation even though scale, orientation and winding are right. The giant infected build shipped with arms about 0.12 m shorter than the armature (length, not angle) and showed visible arm overextension in game.

The fix is a proportion conform: move the mesh's joint regions onto the canonical bone positions, weight-masked like the angle conform, then bind and weight again. Check it offline with the distance from each bone head to the weighted centroid of its vertices; a large distance means that limb will deform.

- Conform in X and Z only and keep the depth (Y in Blender). A thin-plate-spline conform to near-coplanar bone midpoint targets flattened the giant infected build to paper, and it rendered 2D in game. Always look at the side render of the rest pose.
- Conform and new weights have a ceiling (30 to 45 % less deformation on the giant infected build). Past it, rebuild on the vanilla body (`canonical-bind.md`, "When conform and new weights stall").

## 4. Cleanup

```python
bpy.ops.object.vertex_group_limit_total(limit=4)     # DayZ skinning: at most 4 influences per vertex
bpy.ops.object.vertex_group_normalize_all()
```

Target: at most 4 influences per vertex and zero vertices without a weight. A vertex with no weight shows as a pinched or spiky vertex in game.

Remove automatic-weight bleed across the midline. This is the "totally deformed in game" bug. Blender bone-heat on a narrow torso bleeds weight across the body centre: vertices near the spine, neck, chest and shoulders end up weighted to both a `left*` and a `right*` bone. It looks fine at rest and passes a pose test that never moves the two arms in opposite directions. In game, opposing limb animations tear those vertices apart: a grossly deformed mesh, and smeared UVs that read as wrong colours. It logs no script error.

- The binarize tell is `Error: vertices of bone X are shared with bone Y` for a left and right pair. Treat it as blocking, never cosmetic.
- Fix per vertex: keep only the dominant side plus the centre bones (spine, pelvis, neck, head), zero the minority side, normalize again.
- Verify: zero vertices with both a `left*` and a `right*` weight, and binarize reports no "shared with bone".
- Giant infected build: 1,847 vertices bled, and the mesh was totally deformed in game.
- Limit of that fix: on weights that are already asymmetric it makes things worse. On the giant infected build (`LeftUpLeg` 37 vertices against `RightUpLeg` 166, 19 % of weight across the midline) keeping the dominant side per vertex reassigned whole regions to the opposite limb and raised the measured stretch to 21 to 34 times. Use envelope weighting (section 2) there.

## 5. Deform sanity check (gross motion only, not the deform gate)

This Blender pose test only shows whether a limb moves at all; the deform gate is in game or in Buldozer (`canonical-bind.md`, "The Blender deform test is a false gate").

Pose spine, arms and legs and render several views. Bends must be smooth, with no exploded vertices, joints holding, and any internal or cavity geometry following its parent bone. Pose the left and right limbs in opposite directions in the same pose (left arm up and right arm down, left leg forward and right leg back). It is the only pose test that shows cross-midline bleed (section 4).

Headless pitfalls, all hit on the giant infected build:

- The FBX may carry an Action. If posing does nothing, call `arm.animation_data_clear()` first; f-curves override a manual `rotation_euler`. Set `arm.data.pose_position = 'POSE'`.
- FBX bone tails are generated by the importer, so `tail - head` does not follow the limb. Never detect A-pose against T-pose from bone vectors; use a render or the skinned result.
- Track deformation by original vertex index. `evaluated_get(dg).to_mesh().vertices[i].index` is invalid after `to_mesh_clear()`. Take the index from `low.data.vertices`, then read evaluated positions at that same `i` across poses, and compare the largest delta over all vertices.
- Set the pose through `pose.bones[n].rotation_euler` (mode `'XYZ'`) and `view_layer.update()`; no mode switch is needed in background mode.

```python
arm.data.pose_position = 'POSE'
pb = arm.pose.bones['LeftUpLeg']; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (radians(45), 0, 0)
bpy.context.view_layer.update()
# largest vertex delta against rest > 0, with thousands of vertices moving, means skinning works
```

## 6. Export to `.p3d`: vertex groups become named selections

The Blender vertex groups become named selections that carry per-vertex bone weights in the `.p3d`, with the mesh in the canonical bind pose. The route that works headless is a direct write with the py3d DayZ fork in `scripts/tools/py3d/`; no Object Builder window is needed. py3d carries the per-vertex weights faithfully: the cross-side fix and the later scale and facing fixes all showed in game.

**Stage A, Blender headless dump.** `mesh.calc_loop_triangles()` handles quads and n-gons. Per mesh, dump world-space vertices (`matrix_world @ v.co`), triangles (loop-triangle vertex indices), per-loop UV, per-corner normals (`mesh.corner_normals[loop].vector`, transformed by `matrix_world.to_3x3()`), and a dense vertices by bones weight matrix from `v.groups`. Save it as `.npz`. Confirm that weights sum to 1.0 and no vertex is without a weight before going on.

**Stage B, py3d builder.** Each point was verified on the giant infected build unless it says otherwise.

- **The export rule: `(x, y, z)` to `(x, z, y)`, determinant -1,** applied to every point and normal of every LOD and to the bone and memory points. Why this map:
  - The rig in Blender is a body that is not mirrored: front -Y, anatomical left +X, Z up. Measured offline 2026-10-01 in Blender 5.1.1 with both FBX importers: `LeftArm` head x = +0.16; `LeftToeBase` head 0.135 m in -Y from `LeftFoot`; `Male_body` vertices weighted to `LeftArm` at x = +0.22, toe vertices at y = -0.10.
  - The armature's `matrix_world` is a rotation of +90 degrees about X, and its inverse `(x, z, -y)` returns to the FBX file's own frame: Y up, front +Z, left +X. That frame is right-handed. Read as DayZ numbers, which are left-handed, it is a mirrored body that faces backwards.
  - The DayZ bind is a body that is not mirrored, in a left-handed frame: front -Z, left +X (the worn frame in `worn-models.md`, verified in game).
  - So Blender to DayZ is `(x, z, -y)` followed by `z -> -z`: `(x, z, y)`. It sends front -Y to -Z and keeps left on +X. Every determinant +1 map lands the body mirrored.
  - The build history matches (in game): `(x, z, -y)` shipped the giant infected build facing and walking backward; `(-x, z, y)` turned it round but left it mirrored, and the limbs flung back and up until the left and right selections were swapped.
- **Winding and normals: do not reverse the faces.** Under `(x, z, y)` the Blender face order lands in the MLOD convention by itself (cross product inward), and the shading normals are negated because MLOD stores them inward. The older "reverse every visual face" was right only under the determinant +1 map, where it hid the mirror. With py3d 1.8.0 or newer, build the model from the Blender-space dump and call `py3d.blender_to_dayz(model)` once, before adding anything built in DayZ space: it maps every LOD, memory points included, keeps the face order and negates the normals. By hand: `P3D.transform(((1, 0, 0), (0, 0, 1), (0, 1, 0)))` maps points and normals and reverses every face because the determinant is negative; reverse them back and negate the normal pool. `py3d.BLENDER_TO_DAYZ` is the old `(x, z, -y)`, deprecated in 1.8.0 and kept as `py3d.ROT_X_NEG90`; it is not for this export.
- **Gate the winding and normals** with the offline winding gate `check_dayz_winding.py` (it ships with the model tools; find it with Glob) or the absolute winding check of `/dayz-p3d-audit`. A double-sided Blender preview never shows DayZ's single-sided culling. Do not compare against a debinarized vanilla model for winding: the converter's winding handling inverts the comparison.
- **Selection names lowercase.** Vanilla `.p3d` selections are lowercase (`leftarm`, `pelvis`, `spine3`); Blender vertex groups are mixed case, so call `.lower()` on them.
- **Identity binding (py3d).** Alias `points = lod.points` before creating any `Face(lod.points, ...)` or `Vertex(...)`, and use `lod.new_selection(name)`. Selection point and face keys must be the same objects that sit in `lod.points` and `lod.faces`, or their weight is silently dropped, or `write()` raises "foreign key".
- **Fractional weight byte range.** py3d encodes a weight `w` between 0 and 1 as `round((1 - w) * 255) + 1` (reading back: byte 1 is 1.0, bytes 2 to 255 are `1 - (b - 1) / 255`). For `w` below about 0.002 this overflows to 256 and raises `ValueError: bytes must be in range`. Clamp: `w >= 0.995` becomes the integer 1, `0.005 <= w < 0.995` stays a float, and `w < 0.005` is dropped.
- **Drop empty selections.** A twist or helper bone whose every weight fell below the cutoff gives an empty selection, an orphan. Skip any bone selection with no members.
- **`point.mass = None`** on the visual LOD. Mass belongs only on the Geometry LOD.
- **Internal decorative geometry** (a ribcage) is merged into the same visual LOD point and face pool; its spine selections merge by name with the body's. How to weight it is in `body-uv-bake.md`, section 7.
- **Hidden selections.** Add a `camo` selection holding all body points and faces for `hiddenSelectionsTextures[]`; vanilla infected declare exactly that selection (`hiddenSelections[]` at `P:\DZ\characters\zombies\config.cpp:96`). An internal mesh with its own texture gets a second one. Selections that are not bones (`camo`, proxies) are ignored by the skeleton matcher.
- **Reading weights back.** To read selection weights from an MLOD use the constructor, `py3d.P3D(open(path, 'rb'))`, not `m = P3D(); m.read(f)`: only the constructor fills `selection.points = {Point: weight}`. An old debinarized MLOD may keep the selection names with empty `.points`.

**Verify offline** by comparing with a debinarized vanilla character (the models under `P:\DZ\characters\zombies\` are ODOL, so this needs an external ODOL to MLOD converter, which this repo does not ship). Assert:

- the file reads back;
- every bone selection name is in the vanilla bone name set, with no orphan selections;
- no point is without a bone weight, and no vertex has more than 4 influences;
- the bounding box is Y-up with vanilla-like proportions;
- winding about 0 % flipped, fractional weights present and reading back;
- `left*` centroids on +X and the front on -Z (toe and face vertices in -Z from the foot and neck). "Left and right on opposite X" alone also passes a mirrored export. Facing plus side rule out a determinant +1 map only while the left and right selections were never swapped by hand.

The selections in the `.p3d` must be a subset of the `skeletonBones[]` list in `model.cfg`, or the mesh explodes. A misnamed bone logs `Bone X doesn't exist in skeleton ...` in the RPT and that bone does not animate. Which skeleton name vanilla models carry is in `worn-models.md`, "Skeleton".

This repo ships no script for stage A, stage B or the offline verification; write them from the steps above.

### Chiral check in game

Winding gates, the bounding box and the facing test cannot see a mirror once the left and right selections have been swapped.

1. Export the character with `(x, z, y)`, faces in Blender order, negated normals and no left and right swap. Add one marker: an "F" in relief on the chest, weighted 100 % to `spine3`. Build the old recipe once more with the same marker as the negative control.
2. Spawn both and a vanilla character with the same yaw, and put the camera in front of them.
3. Pass on the new build: it faces the camera like the vanilla one; no limb flings back or up over 30 s of idle and one attack; the "F" reads correctly; an off-centre detail sits on the anatomical side it has in Blender (the character's left is screen right when it faces you). Expected on the control: "F" mirrored, detail on the other side.
4. Lighting: the lit side of the body is bright.

Result (run 2026-10-02, DayZDiag 1.29.163709). The giant infected build was rebuilt three ways from one dump, each with the "F": the export rule through `py3d.blender_to_dayz()`; the same with the normals negated back outward; and the shipped recipe as control.

- Export rule build: solid, the "F" reads correctly, lit like a vanilla infected and the player.
- Export rule with outward normals: solid, the "F" reads correctly, lit inverted.
- Shipped recipe: solid, the "F" mirrored, lit inverted.
- Binarize gives all three builds vanilla's winding; only the inward-normal build keeps vanilla's relation between stored normals and winding in the ODOL (agreement 0.2 %, vanilla infected 0.3 to 0.4 %, the outward-normal builds 99.8 %). So store the normals inward.
- An AI-enabled build with the export rule walked about 18 m and, in a second run with textures, attacked the player with its limbs in place, the same moves a vanilla `ZmbM_SoldierNormal` made. A static build kept its limbs in place over about 80 s of idle.

## DayZ 1.30: bone indices

Up to 1.29, `skeletons.anim.xml` listed a numeric `index` per bone, and 250 was treated as a hard global cap. Bohemia's 1.30 modding changelog says the 250 global bone limit is removed, the global bone index is derived from the bone name and not from a value in `skeletons.anim.xml`, and most of that XML is unused: only the `lod` attribute is used, plus adding bones missing inside the `.xob` (changelog statements; not checkable on `P:\`).

What `P:\` shows:

- The `hermit_newbindpose.xob` block still contains leftover `index` attributes, for example `Pelvis` with `index = "10"` at `P:\DZ\anims\cfg\skeletons.anim.xml:8`. Do not copy those numbers into a custom skeleton.
- The skeletons added later name bones only. The one `index` left in them is `EntityPosition` with `index = "0"`, for example in `ovis_gmelini_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:988`) and `canis_familiaris_dobermann_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:1049`).

## Symptoms

| Symptom | Likely cause | Where |
|---|---|---|
| Posing the rig moves nothing; all weights on `Pelvis` | Armature scale not applied before bone-heat, or a live Action | Sections 1 and 5 |
| The whole mesh explodes in game | A named selection that is not in `skeletonBones[]`, or the wrong skeleton name | Section 6; the `model.cfg` skeleton |
| Spiky or pinched vertices | Vertices without a weight, or a selection with no weight | Section 4 |
| `Bone X doesn't exist in skeleton ...` in the RPT | A bone name typo (casing, underscore) | `P:\DZ\anims\cfg\skeletons.anim.xml` |
| Limbs lag or float during animations | Mesh not in the canonical bind A-pose, or baked-scale drift | Section 3; `canonical-bind.md` |
| Limbs overextend or stretch under animation, fine at rest | Mesh scale or proportions differ from the canonical bind | `canonical-bind.md`; the proportion conform in section 3 |
| Faces and walks backward, proportions fine | Determinant +1 export `(x, z, -y)` sends the rig front (-Y) to +Z | Export again with `(x, z, y)`, not `(-x, z, y)` (section 6) |
| A limb flings back or up at idle; sane rest pose, skeleton matches vanilla | Mirrored export (any determinant +1 map) | `canonical-bind.md`, "The mesh can be left and right mirrored" |
| Deforms wrong in game although the Blender pose test looked clean | The Blender armature is not the engine skeleton | `canonical-bind.md`; gate in game or in Buldozer |
| Looks wrong at rest and idle, not only when walking | Bind or skeleton mismatch, not weights | `canonical-bind.md` |
| A corpse goes invisible from one angle | Single-sided faces of a reflected mesh | Undo the reflection (`canonical-bind.md`); a selection swap alone leaves it |
| The whole mesh renders flat, like paper | A conform collapsed the depth | Section 3 |
| Textures on the inside; see-through from outside | Faces not in the MLOD inward order: a determinant +1 map without a face reversal, or a determinant -1 map with one | Section 6 |
| Solid, but dark on the sunlit side and lit in the shade | Shading normals stored outward; rule out the material and `_nohq` too | Section 6; the winding gate or `/dayz-p3d-audit` (agreement near 0 % means normals against the winding) |
| In-game colour is "camo" or black and grey facet noise, and stays without `_nohq` | A corrupt bake of the colour map | `body-uv-bake.md`, section 2 |
| Green, grey or brown patches that survive replacing `_co` and removing `_nohq` | The `.rvmat`, a texture in the wrong stage for the shader. Vanilla infected materials sample the environment texture in `Stage7` (`P:\DZ\characters\zombies\data\hermit.rvmat:74`) | Compare stage by stage with a vanilla `.rvmat` of the same shader (`skills/_shared/textures/rvmat-stages.md`); prove the mesh with a clay render first |
| Worn item floats above the player as a rigid block, or breaks into rigid pieces | Clothing skeleton name, or a worn mesh built facing +Z | `worn-models.md` |
