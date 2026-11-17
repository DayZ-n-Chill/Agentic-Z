# Rigging a custom humanoid mesh to the DayZ character skeleton

Covers the Blender workflow that gives a custom mesh per-vertex weights on the exact vanilla bone names, in the canonical bind pose, and the py3d export that carries them into the `.p3d` as named selections.

This is the expensive, character-specific step. In DayZ there is no shipped armature: `model.cfg` defines the skeleton, the `.p3d` carries named selections with weights, and the engine pairs them. A "bone" in `model.cfg` is a named vertex selection.

How to read the marks in this file: a `P:\` path with a line number was opened and checked in vanilla. "LFInfectedBig" marks a result measured on that custom infected project, in Blender or in game, on the date given; none of those can be checked on `P:\`. Blender and py3d behaviour is tool behaviour, also not checkable on `P:\`.

The Blender side was exercised end to end against the official Bohemia rig (LFInfectedBig, 2026-06-24). The export in section 6 was verified with py3d (LFInfectedBig, 2026-06-25) and corrected for handedness on 2026-10-01.

## 0. Get the official rig (one download)

`animation_rig_character.fbx` from the public repository `BohemiaInteractive/DayZ-Misc`, folder "Rig and Animations" (<https://github.com/BohemiaInteractive/DayZ-Misc>). It is a Blender-native FBX:

- An armature `Armature` with 114 bones whose names are the vanilla character bone names (the skeleton the community calls `OFP2_ManSkeleton`).
- A weighted reference body `Male_body` (7,499 vertices) in the canonical bind A-pose. It is a free proportion and bind reference.
- Units are centimetres (height about 172.5).
- Helpers (`*_Dummy`, `Weapon_*`, `EntityPosition`) import as empties, not bones. Ignore them for body deformation.

```powershell
$dir = "<work-folder>\_rig"; New-Item -ItemType Directory -Force $dir | Out-Null
$enc = "Rig%20and%20Animations/animation_rig_character.fbx"
Invoke-WebRequest "https://raw.githubusercontent.com/BohemiaInteractive/DayZ-Misc/master/$enc" `
  -OutFile "$dir\animation_rig_character.fbx" -Headers @{ "User-Agent" = "x" }
```

Inspect it once: import, list `bpy.data.objects` (armature, `Male_body`, empties), the `armature.data.bones` names, the world Z span (height in cm), and which target bones exist. Confirm the names against the bone catalog (`references/player-skeleton.md` of the dayz-animation-pipeline skill) and against the vanilla bone list in `P:\DZ\anims\cfg\skeletons.anim.xml`, never from memory.

Other tools the community uses for this step (reported by the user Strykar on the DayZ Modders Discord, 2026; not checked here): build the infected armature from the player rig, parent with automatic weights or rename the vertex groups to the DayZ bone names, then import into Object Builder with weights and selections. Arma 3 Object Builder shares the skeleton and imports RTM. DayZATool (by DTZxPorter) handles `.anm` only.

The vanilla character models are binarized (ODOL; the header of `P:\DZ\characters\zombies\hermit_above0.p3d` reads version 56 in 1.30), so they cannot be edited directly; author a new mesh and rig it. The bones a vanilla infected config names for its attachment proxies show which bones matter most: `Spine1`, `Spine2`, `Spine3`, `Head`, `Pelvis`, `LeftHand`, `RightHand_Dummy`, shoulders and legs (`BoneNames[]` at `P:\DZ\characters\zombies\config.cpp:48`).

## 1. Fit the armature to your mesh: the scale trap

Keep the mesh at its final size and scale the armature to it. The armature's absolute size does not reach the game (the engine uses its own skeleton); it only generates weights.

Bake the scale into the armature before bone-heat weighting. Scaling only the object, or a parent, leaves the bone data at native centimetre scale. Bone-heat then runs a 172-unit armature against a mesh about 2 units tall, the whole mesh is a dot near `Pelvis`, and every weight collapses onto `Pelvis` with zero vertices on every other bone. The tell: after binding, posing any limb moves nothing. (LFInfectedBig hit this first: the mesh was 2.277 m against the 172-unit rig.)

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

On LFInfectedBig the arms were 28 and 34 degrees narrower than canonical; this opened them onto the bones cleanly.

The angle is not enough: the joint positions must match too (LFInfectedBig, in game, 2026-06-24). The rotation above conforms each limb's direction, but the engine binds against the canonical bone positions (`references/canonical-bind.md`). When the mesh's anatomical joints (elbow, knee, shoulder, wrist) sit at other positions, which a generated mesh always has because its proportions are its own, the limbs overextend and stretch under animation even though scale, orientation and winding are right and the rest pose looks fine. LFInfectedBig shipped with this unfixed (arms about 0.12 m shorter than the armature: length, not angle) and showed visible arm overextension in game.

The fix is a proportion conform: move the mesh's joint regions onto the canonical bone positions, weight-masked like the angle conform, so every bone sits on the anatomy it drives, then bind and weight again. Check it offline with the distance from each bone head to the weighted centroid of its vertices; a large distance means that limb will deform. (The project's helper for this was `diag_bind_mismatch.py`; it is not part of this repo. The position conform had not shipped on LFInfectedBig when this was written.)

## 4. Cleanup

```python
bpy.ops.object.vertex_group_limit_total(limit=4)     # DayZ skinning: at most 4 influences per vertex
bpy.ops.object.vertex_group_normalize_all()
```

Target: at most 4 influences per vertex and zero vertices without a weight. A vertex with no weight shows as a pinched or spiky vertex in game.

Remove automatic-weight bleed across the midline. This is the "totally deformed in game" bug. Blender bone-heat on a narrow torso bleeds weight across the body centre: vertices near the spine, neck, chest and shoulders end up weighted to both a `left*` and a `right*` bone (a chest vertex on `leftarm` and `rightarm`). It looks fine at rest and passes a pose test that never moves the two arms in opposite directions. In game, opposing limb animations tear those vertices apart: a grossly deformed mesh, and smeared UVs that read as wrong colours. It logs no script error.

- The binarize tell is `Error: vertices of bone X are shared with bone Y` for a left and right pair. Treat it as blocking, never cosmetic.
- Fix per vertex: keep only the dominant side plus the centre bones (spine, pelvis, neck, head), zero the minority side, normalize again.
- Verify: zero vertices with both a `left*` and a `right*` weight, and binarize reports no "shared with bone".
- LFInfectedBig: 1,847 vertices bled, and the mesh was totally deformed in game. The project's fix function was `clean_cross_side()` in its export script (not part of this repo).
- Limit of that fix (LFInfectedBig, 2026-06-24): on weights that are already asymmetric it makes things worse. Keeping the dominant side per vertex reassigned whole regions to the opposite limb and raised the measured stretch to 21 to 34 times. See the envelope weighting note in `references/case-log.md`.

## 5. Deform sanity check (gross motion only, not the deform gate)

This Blender pose test is a false gate for real deformation: the engine skins against its own skeleton, not the rig FBX armature. The deform gate is in game or in Buldozer (`references/canonical-bind.md`, "The Blender deform test is a false gate").

Pose spine, arms and legs and render several views. Bends must be smooth, with no exploded vertices, joints holding, and any internal or cavity geometry following its parent bone. Pose the left and right limbs in opposite directions in the same pose (left arm up and right arm down, left leg forward and right leg back). It is the only pose test that shows cross-midline bleed (section 4); posing one side at a time hides it and ships a model that explodes in game.

Headless pitfalls, all hit on LFInfectedBig:

- The FBX may carry an Action. If posing does nothing, call `arm.animation_data_clear()` first; f-curves override a manual `rotation_euler`. Set `arm.data.pose_position = 'POSE'`.
- FBX bone tails are generated by the importer, so `tail - head` does not follow the limb. Never detect A-pose against T-pose from bone vectors; use a render or the skinned result.
- Track deformation by original vertex index. `evaluated_get(dg).to_mesh().vertices[i].index` is invalid after `to_mesh_clear()`. Take the index from `low.data.vertices`, then read evaluated positions at that same `i` across poses, and compare the largest delta over all vertices (a single foot vertex may be on the side that was not posed).
- Set the pose through `pose.bones[n].rotation_euler` (mode `'XYZ'`) and `view_layer.update()`; no mode switch is needed in background mode.

```python
arm.data.pose_position = 'POSE'
pb = arm.pose.bones['LeftUpLeg']; pb.rotation_mode = 'XYZ'; pb.rotation_euler = (radians(45), 0, 0)
bpy.context.view_layer.update()
# largest vertex delta against rest > 0, with thousands of vertices moving, means skinning works
```

## 6. Export to `.p3d`: vertex groups become named selections

The Blender vertex groups become named selections that carry per-vertex bone weights in the `.p3d`, with the mesh in the canonical bind pose. The route that works headless is a direct py3d write (the fork in `scripts/tools/py3d/`); no Object Builder or DayZATool window is needed. The Object Builder import and the DayZATool bridge need a GUI and were not needed. py3d carries the per-vertex weights faithfully: the cross-side fix and the later scale and facing fixes all showed in game.

Two stages.

**Stage A, Blender headless dump.** `mesh.calc_loop_triangles()` handles quads and n-gons. Per mesh, dump world-space vertices (`matrix_world @ v.co`), triangles (loop-triangle vertex indices), per-loop UV, per-corner normals (`mesh.corner_normals[loop].vector`, transformed by `matrix_world.to_3x3()`), and a dense vertices by bones weight matrix from `v.groups`. Save it as `.npz`. Confirm that weights sum to 1.0 and no vertex is without a weight before going on (Blender already ran the limit and normalize of section 4).

**Stage B, py3d builder.** Each point below was verified on LFInfectedBig unless it says otherwise.

- **Coordinate map `(x, y, z)` to `(x, z, y)`, determinant -1** (Rule 12 of the dayz-model-pipeline skill), applied to every point and normal of every LOD and to the bone and memory points. Corrected 2026-10-01: this step used to prescribe `(x, z, -y)`, determinant +1, as "the inverse of the armature matrix, the exact space of the bind". That derivation dropped a handedness change. What the frames measure:
  - The rig in Blender is a body that is not mirrored: front -Y, anatomical left +X, Z up. Measured offline 2026-10-01 in Blender 5.1.1 with both FBX importers: `LeftArm` head x = +0.16; `LeftToeBase` head 0.135 m in -Y from `LeftFoot`; `Male_body` vertices weighted to `LeftArm` at x = +0.22, toe vertices at y = -0.10.
  - The armature's `matrix_world` is a rotation of +90 degrees about X (same run), and its inverse `(x, z, -y)` returns to the FBX file's own frame: Y up, front +Z, left +X. That frame is right-handed. Read as DayZ numbers, which are left-handed, it is a mirrored body that faces backwards.
  - The DayZ bind is a body that is not mirrored, in a left-handed frame: front -Z, left +X. A debinarized vanilla male has its `left*` bones on +X, and the worn-clothing frame is -Z front and +X left (`references/worn-clothing-skeleton.md`, verified in game).
  - So the FBX frame differs from DayZ by `z -> -z`, and Blender to DayZ is `(x, z, -y)` followed by `z -> -z`: `(x, z, y)`. It sends front -Y to -Z and keeps left on +X. Every determinant +1 map lands the body mirrored: left and right swapped relative to where it faces.
  - The project history matches (in game): `(x, z, -y)` shipped LFInfectedBig facing and walking backward; `(-x, z, y)` turned it round but left it mirrored, and the limbs flung back and up until the left and right selections were swapped. That shipped build (`(-x, z, y)`, reversed faces, left and right swap) is the mirror image of the authored mesh.
  - In game on 2026-10-02 the chiral check at the end of this section ran: the `(x, z, y)` build reads its marker correctly and is lit like a vanilla infected; the shipped recipe reads it mirrored.
- **Winding and normals follow Rule 12; do not reverse the faces.** Under `(x, z, y)` the Blender face order lands in the MLOD convention by itself (cross product inward, collision LODs included, as Rule 18 of that skill wants), and the shading normals are negated because MLOD stores them inward. The older "reverse every visual face" was right only under the determinant +1 map, where it hid the mirror (that map without the reversal rendered inside-out on LFInfectedBig). With py3d 1.8.0 or newer, build the model from the Blender-space dump and call `py3d.blender_to_dayz(model)` once, before adding anything built in DayZ space: it maps every LOD, memory points included, keeps the face order and negates the normals. By hand: `P3D.transform(((1, 0, 0), (0, 0, 1), (0, 1, 0)))` maps points and normals and reverses every face because the determinant is negative; reverse them back and negate the normal pool. `py3d.BLENDER_TO_DAYZ` is the old `(x, z, -y)`, deprecated in 1.8.0 and kept as `py3d.ROT_X_NEG90`; it is not for this export.
- **Gate: `check_dayz_winding.py`** next to this skill's `SKILL.md`, rewritten 2026-10-02 for Rule 12. Per visual LOD it reads the winding from the signed volume of each closed shell and the normals corner by corner. Usage, exit codes, limits and the measurements behind it are in `references/winding-gate.md`. A double-sided Blender or Three.js preview never shows DayZ's single-sided culling, so a gate is needed. Do not compare against a debinarized vanilla model for winding: the converter's winding handling inverts the comparison.
- **Selection names lowercase.** Vanilla `.p3d` selections are lowercase (`leftarm`, `pelvis`, `spine3`); Blender vertex groups are mixed case, so call `.lower()` on them. Matching is case-insensitive, but match vanilla.
- **Identity binding (py3d).** Alias `points = lod.points` before creating any `Face(lod.points, ...)` or `Vertex(...)`, and use `lod.new_selection(name)`. Selection point and face keys must be the same objects that sit in `lod.points` and `lod.faces`, or their weight is silently dropped, or `write()` raises "foreign key".
- **Fractional weight byte range.** py3d encodes a weight `w` between 0 and 1 as `round((1 - w) * 255) + 1` (reading back: byte 1 is 1.0, bytes 2 to 255 are `1 - (b - 1) / 255`). For `w` below about 0.002 this overflows to 256 and raises `ValueError: bytes must be in range`. Clamp: `w >= 0.995` becomes the integer 1, `0.005 <= w < 0.995` stays a float, and `w < 0.005` is dropped (negligible with at most 4 influences).
- **Drop empty selections.** A twist or helper bone whose every weight fell below the cutoff (for example `leftwristextra`) gives an empty selection, an orphan. Skip any bone selection with no members.
- **`point.mass = None`** on the visual LOD. Mass belongs only on the Geometry LOD.
- **Internal decorative geometry** (a ribcage) is merged into the same visual LOD point and face pool; its spine selections merge by name with the body's.
- **Hidden selections.** Add a `camo` selection holding all body points and faces for `hiddenSelectionsTextures[]`; vanilla infected declare exactly that selection (`hiddenSelections[]` at `P:\DZ\characters\zombies\config.cpp:96`). An internal mesh with its own texture gets a second one (LFInfectedBig used `camo_bone`). Selections that are not bones (`camo`, proxies) are ignored by the skeleton matcher and do not explode the mesh.
- **Reading weights back.** To read selection weights from an MLOD use the constructor, `py3d.P3D(open(path, 'rb'))`, not `m = P3D(); m.read(f)`: only the constructor fills `selection.points = {Point: weight}`. An old debinarized MLOD may keep the selection names with empty `.points` (weights lost).

**Verify offline** by comparing with a debinarized vanilla character (the models under `P:\DZ\characters\zombies\` are ODOL, so this needs an external ODOL to MLOD converter, which this repo does not ship; the selection names come back even though the visual LOD's bone membership does not). Assert:

- the file reads back;
- every bone selection name is in the vanilla bone name set, with no orphan selections;
- no point is without a bone weight, and no vertex has more than 4 influences;
- the bounding box is Y-up with vanilla-like proportions;
- winding about 0 % flipped, fractional weights present and reading back;
- `left*` centroids on +X and the front on -Z (toe and face vertices in -Z from the foot and neck). "Left and right on opposite X" alone also passes a mirrored export. Facing plus side rule out a determinant +1 map only while the left and right selections were never swapped by hand.

The selections present in the `.p3d` must be a subset of the `skeletonBones[]` list in `model.cfg`, or the mesh explodes. A misnamed bone logs `Bone X doesn't exist in skeleton ...` in the RPT and that bone does not animate. LFInfectedBig named its skeleton `OFP2_ManSkeleton` in `model.cfg`; see `references/worn-clothing-skeleton.md` for the name vanilla models carry.

The project's reference scripts for these stages (`bl_export_rig.py`, `build_p3d.py`, `verify_p3d.py` and the vanilla extractor `debin_vanilla.py`) are not part of this repo.

### Chiral in-game check for this route (run 2026-10-02, DayZDiag 1.29.163709)

Winding gates, the bounding box and the facing test cannot see a mirror once the left and right selections have been swapped, which is how LFInfectedBig shipped.

1. Export the character again with `(x, z, y)`, faces in Blender order, negated normals and no left and right swap. Add one marker: an "F" in relief on the chest, weighted 100 % to `spine3`. Build the old recipe once more with the same marker as the negative control.
2. Spawn both and a vanilla `ZombieMaleBase` child with the same yaw, and put the camera in front of them.
3. Pass on the new build: it faces the camera like the vanilla one; no limb flings back or up over 30 s of idle and one attack; the "F" reads correctly; an off-centre detail sits on the anatomical side it has in the rig frame in Blender (the character's left is screen right when it faces you). Expected on the control: "F" mirrored, detail on the other side.
4. Lighting: the lit side of the body is bright. (At design time the normal sign rested on Rule 12, measured on static models only; the result below covers a character.)

Result. LFInfectedBig was rebuilt three ways from one dump, each with the "F": Rule 12 through `py3d.blender_to_dayz()`; the same with the normals negated back outward; and the shipped recipe as control, equal to the shipped `.p3d` in every point, normal, face and selection apart from the marker. References: a vanilla `ZmbM_SoldierNormal` and the player, sun from the east.

- Rule 12 build: solid, the "F" reads correctly, lit like the vanilla infected and the player. The gate as it was that day failed it ("inside-out"); the absolute check of dayz-p3d-audit passes it, and so does the gate rewritten afterwards.
- Rule 12 with outward normals: solid, the "F" reads correctly, lit inverted.
- Shipped recipe: solid, the "F" mirrored, lit inverted.
- The state the old gate passed, winding in the MLOD order with the normals stored outward, renders solid but lit inverted (dark on the sunlit side; base shading on a client without textures), and so does the shipped LFInfectedBig. Binarize gives all three builds vanilla's winding; only the inward-normal build keeps vanilla's relation between stored normals and winding in the ODOL (agreement 0.2 %, vanilla infected 0.3 to 0.4 %, the outward-normal builds 99.8 %). So store the normals inward. (claim id CLAIM-CHAR-NORMALS-INWARD-INGAME)
- An AI-enabled Rule 12 build walked about 18 m with its limbs in place; the attack was not seen in that run (it never engaged the player). The chest hole is centred (x about 0), so the off-centre criterion of step 3 cannot show chirality on this model. The client ran without textures: this covers the base shading of these builds, not colour, `_nohq` normal maps or tangents.
- Second run the same day, same PBO, client with textures, sun from the east: an AI-enabled Rule 12 build spawned 2.4 m in front of the player and attacked once the player moved (a wind-up with one arm raised behind, then swings at the shoulder) with its limbs in place, the same moves a vanilla `ZmbM_SoldierNormal` made on that player. A static Rule 12 build kept its limbs in place over about 80 s of idle with the "F" reading correctly; the shipped recipe looked dark, as in the first run. The ribcage mesh seen through the hole spans x -0.165 to +0.134 m in the Blender dump (centre -0.016 m), consistent with a centred hole. (claim id CLAIM-CHAR-ATTACK-INGAME)

## Failure to cause quick map

| Symptom | Cause |
|---|---|
| Posing moves nothing | Armature scale not applied before bone-heat, so all weights sit on `Pelvis`; or a live Action |
| All vertices on `Pelvis` | The same scale trap |
| Spiky or pinched vertices in game | Vertices without a weight, or a selection with no weight |
| Mesh explodes | A selection not in `skeletonBones[]`, or the wrong skeleton name in `model.cfg` |
| `Bone X doesn't exist` in the RPT | Bone name casing or underscore mismatch |
| Limbs drift during animations | Mesh not in the canonical bind, or baked-scale drift (accepted for about 1.2 times) |
| Faces and walks backward, proportions fine | Determinant +1 export `(x, z, -y)` sends the rig front (-Y) to +Z. Export again with `(x, z, y)` (Rule 12), not `(-x, z, y)` |
| Limbs fling back or up at idle, sane rest pose; an off-centre detail on the wrong side | Mirrored export (any determinant +1 map, for example `(-x, z, y)`). Export again with `(x, z, y)`; a left and right selection swap only relabels the mirror |

## DayZ 1.30: bone indices and infected graphs

Up to 1.29, `skeletons.anim.xml` listed a numeric `index` per bone, and community practice treated 250 as a hard global cap. Bohemia's 1.30 experimental modding changelog says the 250 global bone limit is removed, the global bone index is derived from the bone name and not from a value in `skeletons.anim.xml`, and most of that XML is unused: only the `lod` attribute is used, plus adding bones that were missing inside the `.xob`. (Changelog statements; the engine behaviour cannot be checked on `P:\`.)

What `P:\` shows:

- The `hermit_newbindpose.xob` block still contains leftover `index` attributes, for example `Pelvis` with `index = "10"` at `P:\DZ\anims\cfg\skeletons.anim.xml:8`. Do not copy those numbers into a custom skeleton.
- The skeletons added later name bones only. The one `index` left in them is `EntityPosition` with `index = "0"`, for example in `ovis_gmelini_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:988`) and `canis_familiaris_dobermann_skeleton.xob` (`P:\DZ\anims\cfg\skeletons.anim.xml:1049`). Those animal skeletons are not the infected bind: a custom infected still weights to the 95-bone `hermit_newbindpose.xob` list.

Infected graph files: `infected.agr` is now an index over `.agf` subgraphs. See `references/dayz-1-30-characters.md`. For a custom infected workspace, open the 1.29 `.aw` in Workbench 1.30 and save it again (the changelog notes the converter was not tested).
