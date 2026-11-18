# Auto-fitting a garment on the official rig

Covers fitting a garment mesh onto the official DayZ rig by script in headless Blender and taking its weights from the rig's body: what works, where it fails, and the checks to run before trusting a fit. The worn model the result must become is in `worn-models.md`; fitting by hand or by an artist is in `fitting-worn-models.md`.

None of this is vanilla game data. It is Blender 5.1 behaviour driven by script, with no add-on panels, measured on the official rig and on a generated jacket shell decimated to 100 k triangles; nothing is checked on `P:\` except where a `P:\` path is given. The check thresholds below are a choice, not an in-game measurement.

## What works and what does not

The landmarks, the uniform fit of the torso, the weight transfer and the corridor sleeve mask work as written, and the mechanical checks pass on the exported `.p3d`. What fails is putting a garment modelled with hanging sleeves onto the A-pose body by fitting alone:

- The uniform fit leaves the sleeves beside the torso.
- A rigid rotation per sleeve aligns the sleeve axis to about 7 degrees, but stretches fabric membranes between sleeve and flank, because the inner sleeve is fused to the torso.
- Pose-match skinning moves the sleeves onto the arms, but on a closed shell the weights still tear at the flank (section "Hanging sleeves: pose-match skinning").

The checks catch the last case but not the first two, so look at a render of every fit before the weight transfer. Two ways out, in order:

1. Author or obtain the garment already in A-pose, sleeves about 50 degrees from vertical to match the rig's arm. Image generator concepts asked for an A-pose came back with sleeves 15 to 30 degrees from vertical at best; one run through the fit with no rotation passed every check but the sleeve angle (28.8 and 27.2 degrees, cuffs 0.23 m short of the hand), so that check does tell a sleeve that is off the arm.
2. Give a garment with fused sleeves real separation first: a seam, a cut at the armpit or separate sleeve parts. That is authoring, not fitting.

## What this route uses

| Use | Not | Why |
|---|---|---|
| Bone heads of `animation_rig_character.fbx` as landmarks | The survivor skeleton `player_testing.xob` (named at `P:\DZ\characters\data\config.cpp:158`) | Blender has no native XOB import; the FBX imports with the built-in importer |
| `Male_body` of the same FBX as the weight source: no unweighted vertices, at most 4 influences | A one-LOD body `.p3d` with lowercase groups | The one measured had 44 groups, 1,517 of 10,153 vertices with no weight, and sums not normalised |
| The export map `(x, z, y)` with the Blender face order kept | The map plus a reversed face order | With py3d the export keeps the Blender face order; reversing it turns the mesh inside out |
| Sleeve detection as a mask only | A bone heat sleeve warp applied to the mesh | The warp is destructive |

## The official rig in Blender

- File: `animation_rig_character.fbx` from Bohemia's `DayZ-Misc` repository; the download is in `body-rigging.md`, section "Get the official rig".
- Import with `bpy.ops.wm.fbx_import(filepath=FBX)`, the native importer of Blender 5.x (`import_scene.fbx` still exists). The result is an object `Armature` (114 bones, object scale 1.0, bone heads already in metres), an object `Male_body` (object scale 0.01, parented to `Armature` with an Armature modifier, world size 1.406 by 0.390 by 1.799 m, feet at z = 0) and 38 empties (`*_Dummy`, `Weapon_*`, `EntityPosition`) to ignore.
- Because the heads come in metres, the armature scale step of `body-rigging.md` is not needed for landmarks. It is still needed to bone heat your own mesh against this armature at another size.
- Bone tails are meaningless after import (the `Pelvis` tail is 11 m away, the arm tails 10 m and more). Use `bone.head_local` only, never `tail`, `length` or `vector`.
- Frame: Z up, anatomical left on +X (`LeftArm` head x = +0.160, `LeftHand` x = +0.586), front on -Y (the `LeftToeBase` and `RightToeBase` heads sit 0.135 m in -Y from the `*Foot` heads).
- `Male_body` has 7,499 vertices, 14,936 faces and 111 vertex groups named like the bones, at most 4 influences per vertex and no vertex without a weight.
- The 44 lowercase group names vanilla worn models use (`leftarm`, `leftforearmroll`, `lefthipextra` and the rest) map one to one onto bones by `bone.name.lower()`.

Left arm heads in world metres; the right side is the same with x negated:

| Bone | Head (x, y, z) |
|---|---|
| `LeftShoulder` | (0.010, -0.020, 1.390) |
| `LeftArm` | (0.160, 0.010, 1.430) |
| `LeftArmRoll` | (0.309, 0.057, 1.305) |
| `LeftForeArm` | (0.376, 0.078, 1.249) |
| `LeftElbowExtra` | (0.380, 0.079, 1.246) |
| `LeftForeArmRoll` | (0.532, 0.074, 1.117) |
| `LeftWristExtra` | (0.579, 0.073, 1.078) |
| `LeftHand` | (0.586, 0.073, 1.072) |

Spine head heights (z): `Pelvis` 1.000, `Spine` 1.030, `Spine1` 1.060, `Spine2` 1.137, `Spine3` 1.235, `Neck` 1.490, `Neck1` 1.565, `Head` 1.620. In the A-pose the upper arm drops about 40 degrees (shoulder to elbow: dx 0.216, dz -0.181).

## One map between the rig and DayZ

- The rig faces -Y with left on +X. The DayZ worn frame is chest on -Z, left on +X, up on +Y (`worn-models.md`, section "Canonical worn frame"). A body `.p3d` in the DayZ frame read with py3d agrees: the `lefttoebase` centroid sits 0.147 m in -Z from `leftfoot`, `head` 0.030 m in -Z from `neck`, `leftfoot` at x = +0.167. The map `(x, y, z)` in Blender to `(x, z, y)` in DayZ (determinant -1, its own inverse) puts the toes on the rig's.
- A garment fitted on `Male_body` returns to DayZ with that map, faces in their Blender order and normals negated: `py3d.blender_to_dayz()` (py3d 1.8.0 or newer), the export rule in `body-export.md`. Reversing the face order as well is right only for a mesh whose faces already point inward in Blender (unverified). Never apply the determinant +1 map `(x, z, -y)` (`py3d.ROT_X_NEG90`, the deprecated `py3d.BLENDER_TO_DAYZ`): it mirrors, and anything with a side (text, a pocket, a buckle) ships reversed.
- The FBX export of the worn model tools uses the same map (`fitting-worn-models.md`, section "Artist handoff").
- Before packing, run the anatomical facing test (`worn-models.md`) and the winding gate (`body-export.md`) on the exported `.p3d`. A worn model's only collision LOD is the empty Geometry LOD, so collision checks per component do not apply. With weights from `Male_body` the facing test catches a determinant +1 export. No winding check sees a mirror, and the facing test cannot see one once the left and right selections were swapped by hand (the chiral check in `worn-models.md`).

## Landmarks from the bone heads

```python
def arm_landmarks(arm, side):
    """Shoulder joint, elbow, wrist of the official rig; world space, metres."""
    p = "Left" if side == "L" else "Right"
    b = arm.data.bones
    upper = b[p + "Arm"]
    elbow = b.get(p + "ForeArm") or b[p + "ElbowExtra"]
    wrist = b.get(p + "WristExtra") or b[p + "Hand"]
    W = arm.matrix_world
    return W @ upper.head_local, W @ elbow.head_local, W @ wrist.head_local
```

To sample the arm's radius around that axis, use `Male_body` with its `matrix_world` (the 0.01 object scale lives inside the matrix). The heads match the rig to 1 mm; shoulder to elbow to wrist is 0.565 m per side. Blender 5.1 has no `Mesh.calc_normals_split`: read `vertex.normal` and recompute the face normals after the axis map.

## Region box and uniform fit

This fits the torso and cannot move sleeves.

- Region groups: each garment type (jacket, shirt, vest, pants, boots, gloves, backpack, headgear, mask) has a list of lowercase bone group names, matched to the `Male_body` groups by `.lower()`.
- Region box: the world bounding box of the `Male_body` vertices weighted above 0.02 in any group of the region.
- Uniform fit: one factor for every part of the garment, multi-part files measured together. For jacket, shirt, vest, backpack and pants it is `0.82 * height_ratio + 0.18 * secondary`, where `secondary` is whichever of the X or Y ratio is closest to 1 (`argmin |log r|`); other types take the median of the three ratios. Multiply by a `margin` of 1.02 to 1.06, then move the garment so its top edge sits on the region's top edge (the bottom edge for boots). No vertex is warped.
- Rest offset: move along the body's front vector, world `(0, -1, 0)` on this rig, by `offset` (0.035 m by default), stored on the object so repeated fits do not add up.
- On the test jacket the region box is lo (-0.603, -0.134, 0.945), hi (0.603, 0.143, 1.611), the factor 0.424 with margin 1.04: collar at the neck, hem mid-thigh. Its hanging sleeves stay 0.69 m wide against a 1.21 m A-pose region, so they end up beside the torso.

## Weight transfer from `Male_body`

1. Remove foreign deform groups from the garment: anything that is neither a bone name nor a named selection (`camo*`, `zbytek` and `hiddenSelection*` stay).
2. Create the destination groups by name, then add a `DATA_TRANSFER` modifier on the garment: `object = Male_body`, `use_vert_data = True`, `data_types_verts = {'VGROUP_WEIGHTS'}`, `vert_mapping = 'POLYINTERP_NEAREST'`, `layers_vgroup_select_src = 'ALL'`, `layers_vgroup_select_dst = 'NAME'`. Apply it with `bpy.ops.object.modifier_apply(modifier=name)` inside `bpy.context.temp_override(object=g, active_object=g, selected_objects=[g])`; headless there is no active object otherwise.
3. Clean up per vertex: keep the top 4 or fewer bone groups at weight 0.005 or more, drop the rest and normalise to 1.0. Count as bone groups only the deform set of `body-rigging.md`, section "Bind with automatic weights" (no `Face_*`, eyes, tongue or fingers), or a collar ends up weighted to `face_jawbone`. Touch only bone groups, so named selections survive; that is why this beats Blender's global Clean or Limit Total.
4. Remove weight that crosses the midline (`body-rigging.md`, section "Clean up the weights").
5. Export with py3d, group names in lowercase. py3d stores a weight as the byte `round((1-w)*255)+1` (`body-export.md`, section "Building the model with py3d"), so sums come back as 0.996 to 1.004; check sums to plus or minus 0.01, not exactly 1.0.
6. The in-game skeleton is still `DayzTemporarySkeleton` with the 159 pair template (`worn-models.md`); the rig only makes weights. The 44 name set is what vanilla worn items weight: more bones is fine, fewer works but articulates coarsely.

With py3d up to 1.8.0, `python -m py3d validate` raises `ERR_COMPONENT_NAMING` on the empty Geometry LOD (`autocenter=0`) unless it carries an empty `Component01` selection; from 1.9.0 a collision LOD with no faces raises nothing. Whether vanilla worn models carry that empty selection is unverified.

On the test jacket this gives 49,994 vertices, none without a weight, at most 4 influences, no weight across the midline and 34 of the 44 selections used; all 111 groups transfer.

## Sleeve detection as a mask

Sleeves can be tagged as `DAYZ_SLEEVE_L` and `DAYZ_SLEEVE_R` vertex groups for the alignment viewer three ways: as a separate mesh part, by a flood from a wrist seed, or as a corridor of 0.19 times the arm length around the arm axis. Never follow the tag with an automatic warp of the sleeve: detection can mark the wrong sleeve or only one arm, and the warp then moves the wrong vertices without any error.

On a closed shell the wrist flood finds no sleeve (there are no open cuffs), and the corridor finds both (about 4,500 vertices each around the A-pose axis; about 12,500 around the garment's own axis, which also takes in flank vertices). Rotating the masked sleeve about the `*Arm` head onto the rig axis (blend `smoothstep(0.05, 0.22)` of the arm length at the root, axial scale 0.75) reaches 7.2 and 7.6 degrees with the cuffs under 5 cm from the hand, but flank vertices inside the corridor turn with the sleeve and stretch into fan shaped membranes. Rigid rotation is unusable on a garment with fused sleeves, and the checks cannot see the membranes.

## Hanging sleeves: pose-match skinning

Bind in the garment's pose, then move the rig to rest, with the axes measured:

1. Measure each sleeve's axis from the corridor mask: shoulder root, main axis, cuff.
2. Pose the `Armature` so the `LeftArm` and `RightArm` chains follow those axes. Rotate the `*Arm` pose bone about its world head with `pose_bone.matrix`, never `bone.vector` or `tail`; one rotation is enough (about 0.02 degrees left over). `Male_body` follows through its Armature modifier.
3. Transfer weights from the posed `Male_body` (the evaluated mesh) and clean them as above.
4. Bind the garment in that pose, then return the armature to rest so the skinning carries the sleeves to the A-pose. To avoid a double transform: record the rest world matrices of the 18 arm chain bones before posing, run `bpy.ops.pose.armature_apply`, add the Armature modifier and parent inverse, set the chain back to the recorded matrices parent first with `view_layer.update()` between bones, then apply the modifier.
5. Run all the checks below, look at the renders, and export with the map above.

On the test jacket the sleeves land on the arms (7.4 and 8.2 degrees, cuffs 7 cm from the hand), but only 61 and 59 % of the sleeve weight sits on arm bones and the longest edge stretches 6.5 times. With the rig posed arms down, its arm fills the same space as the flank, so a transfer by distance paints arm weights onto the flank. Blending posed weights inside the sleeve mask with rest weights outside it only moves the tear to the mask edge.

## Checks before trusting a fit

| Check | Pass |
|---|---|
| Weights | No vertex without a weight; every sum 1.0 plus or minus 0.01; at most 4 influences; no `left*` or `right*` weight across the midline |
| Facing | The anatomical test of `worn-models.md` on the exported `.p3d`. On the test jacket the `left*` centroid sits at x = +0.16 (fit only) or +0.25 (sleeves on arms); spine and pelvis weight at z = -0.040 and -0.059, against vanilla -0.04 to -0.08 |
| Sleeve angle | The angle between each sleeve's main axis and the rig's `Arm` to `Hand` axis is 12 degrees or less, and the cuff centroid (the 10 % of sleeve vertices farthest from the shoulder) is 0.08 m or less from the `Hand` head, in the DayZ frame |
| Sleeve weight | 70 % or more of the sleeve vertices' weight sits on arm bones (`*arm*`, `*forearm*`, `*hand` and their roll and extra bones), not on `spine*` or `*shoulder` |
| Stretch | On the exported visual LOD, edge length after the fit against the fitted but unposed garment: 99th percentile 1.3 times or less, maximum 2.0 times or less. The rigid rotation gives 1.31 and 6.15 and pose-matching a maximum of 6.53, both a fail; it is the only check that sees the tears |

None of these sees a sleeve sitting beside the torso without stretching. Look at an orthographic front render with `Male_body` overlaid first, then run the in-game gate of `worn-models.md`: spawn, equip, move. A worn item cannot be validated offline only.
