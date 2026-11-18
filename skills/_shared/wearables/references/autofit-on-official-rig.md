# Auto-fitting a garment on the official rig

Covers fitting a garment mesh onto the official DayZ rig in headless Blender and taking its weights from the rig's body mesh: what works, what four test rounds refuted, and the gate to run before trusting a fit. The worn model the result must become is described in `worn-models.md`; fitting by hand or by an artist is in `fitting-worn-models.md`.

Scope: headless Blender 5.1 driven by script, with no add-on panels or operators. None of this is vanilla game data, so nothing here is checked on `P:\` except where a `P:\` path is given.

How to read the marks: **Measured** was measured in Blender 5.1.1 with Python 3.13.9, headless, on 2026-09-01 (rig facts) or in the round named; **Run** marks a step executed on a real AI-generated jacket shell (1.35 M triangles decimated to 100 k) in two rounds on 2026-09-01; **Design** marks logic written here and not yet run end to end; **Assumption** marks something stated and not verified. The renders, metrics and scripts of those runs are not in this repo.

## Result first

Sections 3, 4, 5 and the corridor mask of 6 work as written, and the mechanical gate (7) passes on the exported `.p3d`. What the runs refuted is that a garment modelled with hanging sleeves can be put on the A-pose body by fitting alone: neither the uniform fit (the sleeves stay on the torso) nor a rigid rotation per sleeve (it aligns the sleeve axis to 7 degrees but stretches fabric membranes between sleeve and flank, because the inner sleeve is fused to the torso) gives an acceptable mesh, and the gate sees neither failure. Two ways out, in order: (a) author or obtain the garment already in A-pose (sleeves about 50 degrees from vertical, matching the rig's arm axis); (b) for a hanging-sleeve garment, do the pose-match skinning of section 6b. A render review of the fit is mandatory before the weight transfer.

- **Round 3 (same day): an A-pose garment could not be generated.** Nine image-generator concepts with A-pose in the prompt gave sleeves 15 to 30 degrees from vertical at best. Through the unchanged pipeline (no rotation, 16 s in Blender) the gate passed a to g and (i) (sleeve weight 92 % on arm bones, 0 unweighted, 0 bleed, no membranes) and failed (h) at 28.8 and 27.2 degrees with cuffs 0.23 m short of the hand. That is a true positive, so the pipeline is validated end to end and (h) discriminates. The 12 degree and 0.08 m thresholds of (h) are a choice, not an in-game measurement (assumption).
- **Round 4 (2026-09-02): section 6b on the hanging-sleeve jacket also fails on this mesh.** Posing the rig onto the sleeve axis works (0.02 degrees), the bind sequence works, (h) passes (7.4 and 8.2 degrees, cuffs 7 cm), but (i) fails (61 and 59 % of sleeve weight on arm bones) and (j) fails (max edge 6.5 times). With the rig posed arms-down, the donor's arm occupies the same volume as the flank, so a proximity transfer paints arm weights on the flank too. On a closed shell where sleeve and flank are one continuous surface, no partition by proximity or by mask avoids the tear. A garment whose sleeves are fused to the torso needs topological separation (a seam, a cut at the armpit, or separate sleeve parts) before any pose-match; that is authoring, not fitting.

## 0. What this route uses, and what it avoids

| Use | Not | Why |
|---|---|---|
| Bone heads of `animation_rig_character.fbx` as landmarks (sections 1 and 3) | The survivor skeleton `player_testing.xob` (named at `P:\DZ\characters\data\config.cpp:158`) | Blender has no native XOB import; the FBX imports with the built-in importer |
| `Male_body` of the same FBX as the weight donor: 0 unweighted vertices, at most 4 influences (sections 1 and 5) | A one-LOD body `.p3d` with lowercase groups | The one measured had 44 groups, 1,517 of 10,153 vertices with zero weight, and sums not normalised |
| The export map `(x, z, y)` with the Blender face order kept (section 2) | The map plus a reversed face order | With py3d, the export rule keeps the Blender face order; reversing it turns the mesh inside-out |
| Sleeve detection as a mask only (section 6) | A bone-heat sleeve warp applied to the mesh | The warp is destructive |

## 1. The reference rig (measured)

- File: `animation_rig_character.fbx` from the official `DayZ-Misc` repository; the download is in `body-rigging.md`, section 0.
- Import: `bpy.ops.wm.fbx_import(filepath=FBX)` (the native importer of 5.x; `import_scene.fbx` also still exists). Result: object `Armature` (114 bones, object scale 1.0, **bone heads already in metres**), object `Male_body` (object scale 0.01, parented to `Armature` with an Armature modifier, world dimensions 1.406 x 0.390 x 1.799 m, feet at z = 0), and 38 empties (`*_Dummy`, `Weapon_*`, `EntityPosition`: ignore them).
- Because the heads come in metres, the "bake the armature scale" step of `body-rigging.md` section 1 (written for the legacy importer, armature at 172 units) is not needed for landmarks. It is still needed if you bone-heat your own mesh against this armature at another size.
- **Bone tails are garbage after import** (the Pelvis tail is 11 m away, arm tails 10 m and more). Use `bone.head_local` only; never `tail`, `length` or `vector`.
- Frame: Z up; anatomical left = +X (`LeftArm` head x = +0.160, `LeftHand` x = +0.586); front = -Y (the `LeftToeBase` and `RightToeBase` heads sit 0.135 m in -Y from the `*Foot` heads).
- Arm chain heads, world, metres (the right side is the same with x negated):

  | Bone | Head (x, y, z) |
  |---|---|
  | LeftShoulder | (0.010, -0.020, 1.390) |
  | LeftArm | (0.160, 0.010, 1.430) |
  | LeftArmRoll | (0.309, 0.057, 1.305) |
  | LeftForeArm | (0.376, 0.078, 1.249) |
  | LeftElbowExtra | (0.380, 0.079, 1.246) |
  | LeftForeArmRoll | (0.532, 0.074, 1.117) |
  | LeftWristExtra | (0.579, 0.073, 1.078) |
  | LeftHand | (0.586, 0.073, 1.072) |

  Spine head heights (z): Pelvis 1.000, Spine 1.030, Spine1 1.060, Spine2 1.137, Spine3 1.235, Neck 1.490, Neck1 1.565, Head 1.620. A-pose: the upper arm drops about 40 degrees (shoulder to elbow: dx 0.216, dz -0.181).
- Name mapping: the 44 lowercase group names that vanilla worn models use (`leftarm`, `leftforearmroll`, `lefthipextra`, ...) map one to one onto bones by `bone.name.lower()` (44 of 44).
- `Male_body`: 7,499 vertices, 14,936 faces, 111 vertex groups named like the bones (`RightArm`, `Spine3`, `Pelvis`), at most 4 influences per vertex, 0 zero-weight vertices.

## 2. Axes: one map between the rig frame and DayZ

- The official rig faces -Y with left at +X (section 1; measured again on 2026-10-01 with both FBX importers). The DayZ worn frame is -Z chest, +X left, +Y up (`worn-models.md`, "Canonical worn frame"). Cross-check on a body in the DayZ frame (a body `.p3d` with lowercase bone selections, read with py3d 1.5.0): the `lefttoebase` centroid sits 0.147 m in -Z from `leftfoot`, `head` 0.030 m in -Z from `neck`, `leftfoot` at x = +0.167: front -Z, left +X. The map `(x, y, z)` in Blender to `(x, z, y)` in DayZ (determinant -1, its own inverse) puts those toes at -Y, onto the rig.
- A garment fitted on `Male_body` returns to DayZ with that map, faces in their Blender order and normals negated: `py3d.blender_to_dayz()` (py3d 1.8.0 or newer), the export rule of `body-rigging.md` section 6. Reversing the face order as well is right only for a mesh whose faces already point inward in Blender (assumption). Do not apply the determinant +1 map `(x, z, -y)` (`py3d.ROT_X_NEG90`, formerly `py3d.BLENDER_TO_DAYZ`, now deprecated): it mirrors.
- The FBX export of the worn-model tools now uses the same map (`fitting-worn-models.md`, "Artist handoff"). An older mirrored frame, fitted and exported with a determinant +1 map, is withdrawn: anything with a side (text, a pocket, a buckle) ships reversed.
- Before packing, run the anatomical facing test (`worn-models.md`) and the winding gate (`body-rigging.md`, section 6) on the exported `.p3d`. A worn model's only collision LOD is the empty Geometry LOD, so per-component collision checks do not apply. With weights transferred from `Male_body` the facing test catches a determinant +1 export. No winding check sees a mirror, and the facing test cannot see one once the left and right selections have been swapped by hand (the chiral check in `worn-models.md`).

## 3. Landmarks from the rig's bone heads (run: works)

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

To sample the arm's radius profile around that axis, use `Male_body` with its `matrix_world` (the 0.01 object scale lives inside the matrix). In the run the heads matched the rig probe to 1 mm; arm length shoulder to elbow to wrist = 0.565 m per side. Blender 5.1 has no `Mesh.calc_normals_split`: read `vertex.normal` and recompute the face normals after the axis map.

## 4. Region box and uniform fit (run: works for the torso, cannot move sleeves)

- Region groups: each garment type (jacket, shirt, vest, pants, boots, gloves, backpack, headgear, mask) has a list of lowercase bone group names; match the `Male_body` groups by `.lower()`.
- Region box: the world bounding box of the `Male_body` vertices weighted above 0.02 in any group of the region.
- Uniform fit: one uniform factor for all parts of the garment (multi-part files are measured together): `0.82 * height_ratio + 0.18 * secondary`, where `secondary` is whichever of the X or Y ratio is closest to 1 (`argmin |log r|`), for jacket, shirt, vest, backpack and pants (the median of the three ratios otherwise), times a `margin` of 1.02 to 1.06. Then translate so the garment's top edge sits on the region's top edge (the bottom edge for boots). No vertex warping at all.
- Run: jacket region box of `Male_body` lo (-0.603, -0.134, 0.945), hi (0.603, 0.143, 1.611); factor 0.424 with margin 1.04; collar at the neck, hem mid-thigh, front offset 0.035 m towards -Y. A garment with hanging sleeves stays 0.69 m wide against a 1.21 m A-pose region, so the sleeves end up beside the torso, not on the arms.
- Rest forward offset: translate along the body's front vector by `offset` (0.035 m by default), stored on the object so repeated fits do not accumulate. On the official rig the front vector is world `(0, -1, 0)`.

## 5. Weight transfer from `Male_body` (run: works with the three corrections of step 7)

1. Remove foreign deform groups from the garment: anything that is neither a bone name nor a named selection (`camo*`, `zbytek`, `hiddenSelection*` stay).
2. Create the destination groups by name, then add a `DATA_TRANSFER` modifier on the garment: `object = Male_body`, `use_vert_data = True`, `data_types_verts = {'VGROUP_WEIGHTS'}`, `vert_mapping = 'POLYINTERP_NEAREST'`, `layers_vgroup_select_src = 'ALL'`, `layers_vgroup_select_dst = 'NAME'`. Apply it with `bpy.ops.object.modifier_apply(modifier=name)` inside `bpy.context.temp_override(object=g, active_object=g, selected_objects=[g])`; headless there is no active object otherwise.
3. Cleanup: per vertex keep the top 4 or fewer bone groups with weight 0.005 or more, drop the rest, renormalise to 1.0; touch only bone-named groups so named selections survive. That is why it is better than Blender's global Clean or Limit Total.
4. Add cross-midline cleanup (`body-rigging.md`, section 4) and the counts of section 7.
5. Export with py3d: group names to lowercase; the byte encoding is py3d's `round((1-w)*255)+1` (`body-rigging.md`, section 6), never another weight table.
6. The in-game skeleton is still `DayzTemporarySkeleton` with the 159-pair template (`worn-models.md`, "Skeleton"); the rig only generates weights. The 44-name set is what vanilla worn items weight: more bones is fine, fewer works but articulates coarsely.
7. Run: steps 2 to 5 work in Blender 5.1.1 (`modifier_apply` under `temp_override` applied first time; 111 groups transferred). Three corrections found:
   - Restrict the "bone-named groups" of step 3 to the deform set of `body-rigging.md` section 2 (no `Face_*`, eyes, tongue, fingers): otherwise a collar ends up weighted to `face_jawbone`.
   - py3d's byte encoding quantises weights: sums come back as 0.996 to 1.004 after the round trip, so the gate tolerance is plus or minus 0.01, not exactly 1.0.
   - The empty Geometry LOD (`autocenter=0`) makes `python -m py3d validate` raise `ERR_COMPONENT_NAMING` unless it carries an empty `Component01` selection (0 points), with py3d up to 1.8.0. From 1.9.0 on, a collision LOD without faces raises no such finding. Whether vanilla worn models carry the empty selection is an assumption.

   Result on the test jacket: 49,994 vertices, 0 unweighted, at most 4 influences, 0 midline bleed, 34 of the 44 selections populated.

## 6. Sleeve detection: mask only (run: the corridor mask works; rigid rotation refuted)

Sleeves can be tagged as `DAYZ_SLEEVE_L` and `DAYZ_SLEEVE_R` vertex groups for the alignment viewer in three ways: as a disconnected mesh component, by a flood from a wrist seed, or as a corridor of 0.19 x arm length around the section 3 axis. Do not follow the tagging with a heuristic warp of the sleeve: automatic detection can mark the wrong sleeve or find only one arm, and the warp then deforms the wrong vertices without any error.

Run: on a closed shell the wrist-seed flood found 0 of 2 sleeves (no open cuffs); labelling the whole corridor found 2 of 2 (4,582 and 4,468 vertices with the A-pose axis; 12,659 and 12,346 with a corridor around the garment's own axis, which also captures flank vertices). A rigid rotation of the masked sleeve about the `*Arm` head onto the rig axis (blend `smoothstep(0.05, 0.22)` of the arm length at the root, axial scale 0.75) reached 7.2 and 7.6 degrees and cuffs 4.7 and 4.6 cm from the hand, but tore the mesh: flank vertices inside the corridor rotated with the sleeve and stretched into fan-shaped membranes. Rigid rotation is unusable on garments whose sleeves are fused to the torso, and the gate cannot detect the membranes. Do not ship a fit without looking at the render.

## 6b. Hanging-sleeve garments: pose-match skinning instead of rotation (run 2026-09-02: the mechanics work, it still tears on a fused shell)

Bind in the garment's pose, then move the rig to rest, with the axes measured instead of guessed:

1. Measure the garment's sleeve axes from the corridor mask (shoulder root, principal axis, cuff).
2. Pose the official `Armature` so that the `LeftArm` and `RightArm` chains follow those axes (rotate the arm bones about the shoulder; keep the rest of the rig untouched). `Male_body` follows through its Armature modifier.
3. Transfer weights from the posed `Male_body` (section 5, evaluated mesh) and clean them.
4. Bind the garment to the armature in that pose (Armature modifier, parent inverse), then return the armature to its rest pose: the skinning carries the sleeves to the A-pose with weight falloff at the shoulder.
5. Apply the Armature modifier (bake), run the gate (7) including (h) and (i), review renders, export via section 2.

Run: rotate the `*Arm` pose bone about its world head with `pose_bone.matrix` (never `bone.vector` or `tail`); one rotation of `*Arm` was enough, residual 0.02 degrees. Bind sequence that avoids the double transform: record the rest world matrices of the 18 arm-chain bones before posing; `bpy.ops.pose.armature_apply`; add the Armature modifier and parent inverse; set the chain back to the recorded matrices parent-first with `view_layer.update()` between bones; apply the modifier. The posed donor paints arm weights on the flank, so the run blended posed weights inside `DAYZ_SLEEVE_*` with rest-pose weights outside; the tear then appears at that boundary.

## 7. Gate before trusting a fit (design)

- 0 zero-weight vertices; every vertex weight sum = 1.0 plus or minus 0.01; at most 4 influences; `left*` and `right*` bleed across the midline = 0.
- Facing: the anatomical test (`worn-models.md`) on the exported `.p3d`. Measured on the test jacket: `left*` centroid x = +0.16 (fit only) and +0.25 (sleeves on arms); spine and pelvis weighted z = -0.040 and -0.059 (vanilla -0.04 to -0.08); garment y in [0.77, 1.61].
- Sleeves on arms: (h) the angle between each sleeve's principal axis and the rig's `Arm` to `Hand` axis is 12 degrees or less, and the cuff centroid (the 10 % of sleeve vertices farthest from the shoulder) is 0.08 m or less from the `Hand` head, both in the DayZ frame; (i) 70 % or more of the weight of the sleeve vertices sits on arm bones (`*arm*`, `*forearm*`, `*hand`, their roll and extra bones), not on `spine*` or `*shoulder`.
- Membranes or torn fabric (j): on the exported visual LOD, edge lengths after the fit against the fitted but unposed garment: 99th percentile ratio 1.3 or less and max ratio 2.0 or less. Calibrated on the round-2 model (membranes): 1.31 and 6.15, a fail; the pose-match round: max 6.53, a fail. It is the only mechanical check that sees the tears.
- (h) to (j) still do not see a sleeve sitting beside the torso without stretching: look at an orthographic front render with `Male_body` overlaid before trusting any of them.
- Then the in-game gate (`worn-models.md`): spawn, equip, move. A worn item cannot be validated offline only.
