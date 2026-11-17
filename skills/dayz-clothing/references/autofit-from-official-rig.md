# Auto-fit a garment on the official DayZ rig (joint landmarks and weight donor)

Covers fitting a garment mesh onto the official rig in headless Blender and taking its weights from the rig's body mesh: what works, what four test rounds refuted, and the gate to run before trusting a fit.

The logic comes from reading the Blender 3.6 add-on "DayZ Model Tools CZ" 1.16.4 (a third-party tool; line numbers below are those of its `addon.py`) and from runs in Blender 5.1.1. Scope: headless Blender 5.1 driven by script; no panels and no operators of that add-on. None of this is vanilla game data, so nothing here is checked on `P:\` except where a `P:\` path is given.

Labels: **[EXACT]** measured in Blender 5.1.1 / Python 3.13.9, headless, 2026-09-01; **[DESIGN]** logic read from the add-on or written here, not yet run end to end on a real garment; **[ASSUMPTION]** stated, unverified; **[RUN 2026-09-01]** executed on a real jacket (a Hunyuan3D shell, 1.35 M triangles decimated to 100 k) in Blender 5.1.1 headless, in two worker rounds. The renders, metrics and worker scripts of those runs were not brought into this repo.

**Read this first (result of the run).** Sections 3, 4, 5 and the corridor mask of 6 work as written, and the mechanical gate (7) passes on the exported p3d. What the run refuted is the idea that a garment modelled with hanging sleeves can be put on the A-pose body by fitting alone: neither the uniform fit (the sleeves stay on the torso) nor a rigid rotation per sleeve (it aligns the sleeve axis to 7 degrees but stretches fabric membranes between sleeve and flank, because on such garments the inner sleeve is fused to the torso) gives an acceptable mesh, and the gate sees neither failure. Two ways out, in order: (a) author or obtain the garment already in A-pose (sleeves about 50 degrees from vertical, matching the rig's arm axis); (b) for a hanging-sleeve garment, do the pose-match skinning of section 6b instead of any rotation. A render review of the fit is mandatory before the weight transfer; the gate alone is not enough.

**Round 3 (same day): the A-pose route is not reachable with SDXL then Hunyuan.** Nine SDXL ghost-mannequin concepts (two prompt variants, A-pose stated first, CLIP-safe length) gave sleeves 15 to 30 degrees from vertical at best; the one spread garment was a short batwing. Run through the unchanged round-1 pipeline (no rotation, 16 s in Blender): gate a to g and (i) pass (sleeve weight 92 % on arm bones, 0 unweighted, 0 bleed, no membranes), (h) fails at 28.8 / 27.2 degrees with cuffs 0.23 m short of the hand. That is a true positive of the garment's geometry, so the pipeline is validated end to end and (h) discriminates. For a real A-pose garment use a downloaded or authored one, or use section 6b, which handles any sleeve angle. The 12 degree and 0.08 m thresholds of (h) are a choice, not an in-game measurement [ASSUMPTION].

**Round 4 (2026-09-02): section 6b run on the hanging-sleeve jacket, and it also fails on this mesh.** Posing the rig onto the sleeve axis works (0.02 degrees), the bind sequence that avoids the double transform works, (h) passes (7.4 / 8.2 degrees, cuffs 7 cm), but (i) fails (61 / 59 % of sleeve weight on arm bones) and the new edge-stretch criterion (j) fails (max edge 6.5x): the same membranes as round 2, now at the mask boundary. Mechanism, measured by the worker: with the rig posed arms-down, the donor's arm occupies the same volume as the flank, so a proximity transfer paints arm weights on the flank too; restricting the posed weights to the sleeve mask moves the tear to the mask edge. On a closed AI shell where sleeve and flank are one continuous surface, no partition by proximity or by mask avoids the tear. Conclusion: a garment whose sleeves are fused to the torso needs topological separation (a seam, a cut at the armpit, or separate sleeve parts) before any pose-match; that is authoring, not fitting. What the four rounds did validate: sections 3 to 5 and 7 as a pipeline, and (j) as a membrane detector.

## 0. What replaces what

| Add-on piece (`addon.py`) | Why not | Replacement |
|---|---|---|
| `_load_local_dayz_player_rig` 3880-3924 and `_real_dayz_rig_landmarks` 3853-3876 | Needs the external `DayzAnimationTools.import_xob` and a hard-coded `P:\DZ\characters\bodies\player_testing.xob`; that XOB is a test skeleton with `To Be removed` bones (see the player skeleton reference of the `dayz-animation-pipeline` skill) | Bone heads of `animation_rig_character.fbx` (sections 1 and 3) |
| Donor `resources\DayzSkeleton.p3d` (`_ensure_builtin_reference` 1649-1673) | One visual LOD, 44 lowercase groups, 1,517 of 10,153 vertices with zero weight, sums not normalised; it embeds vanilla `m_adam` textures and rvmats (a licence question); the add-on decodes weights with its own table (`weight_decode` 225-231), not the py3d codec | `Male_body` of the same FBX: 0 unweighted vertices, at most 4 influences (sections 1 and 5) |
| `to_bl` / `from_bl` = `(x, z, y)` plus `rev()` 219-221 | The swap is right (it is the Blender to DayZ axis rule); `rev()` belongs to the add-on's own p3d writer (not checked here): with py3d, the axis rule keeps the Blender face order | Section 2 |
| `_apply_autofit_armature(..., apply=True)` 3213-3287, run by default in `clothing_prepare` 4454-4457 | Destructive bone-heat sleeve warp; the panel says it does not run (4828) and the code runs it | Do not port; sleeve detection as a mask only (section 6) |

## 1. The reference rig [EXACT]

- File: `animation_rig_character.fbx`, the official rig from the `BohemiaInteractive/DayZ-Misc` repository ("Rig and Animations"). The download steps are in section 0 of `character-rigging.md` in the `dayz-characters` skill.
- Import: `bpy.ops.wm.fbx_import(filepath=FBX)` (the native importer of 5.x; `import_scene.fbx` also still exists). Result: object `Armature` (114 bones, object scale 1.0, **bone heads already in metres**), object `Male_body` (object scale 0.01, parented to `Armature` with an Armature modifier, world dimensions 1.406 x 0.390 x 1.799 m, feet at z = 0), and 38 empties (`*_Dummy`, `Weapon_*`, `EntityPosition`: ignore them).
- Because the heads come in metres, the "bake the armature scale" step of `character-rigging.md` section 1 (written for the legacy importer, armature at 172 units) is not needed for landmarks. It is still needed if you bone-heat your own mesh against this armature at another size.
- **Bone tails are garbage after import** (the Pelvis tail is 11 m away, arm tails 10 m and more). Use `bone.head_local` only; never `tail`, `length` or `vector`.
- Frame: Z up; anatomical left = +X (`LeftArm` head x = +0.160, `LeftHand` x = +0.586); front = -Y (the `LeftToeBase` / `RightToeBase` heads sit 0.135 m in -Y from the `*Foot` heads).
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
- Name mapping: the 44 lowercase group names that vanilla worn p3ds and the add-on use (`leftarm`, `leftforearmroll`, `lefthipextra`, ...) map one to one onto bones by `bone.name.lower()` (44 of 44).
- `Male_body`: 7,499 vertices, 14,936 faces, 111 vertex groups named like the bones (PascalCase: `RightArm`, `Spine3`, `Pelvis`), at most 4 influences per vertex, 0 zero-weight vertices.

## 2. Axes: one swap between the rig frame and DayZ [EXACT plus rule; corrected 2026-10-01 for the axis rule]

- The official rig faces -Y with left at +X (section 1; measured again on 2026-10-01 with both FBX importers). The DayZ worn frame is -Z chest, +X left, +Y up (`skills/_shared/wearables/references/worn-models.md`, "Canonical worn frame"). [EXACT] cross-check on a body in the DayZ frame (the add-on's `DayzSkeleton.p3d`, read with py3d 1.5.0): the `lefttoebase` centroid sits 0.147 m in -Z from `leftfoot`, `head` 0.030 m in -Z from `neck`, `leftfoot` at x = +0.167: front -Z, left +X. The swap `(x, y, z)` in Blender to `(x, z, y)` in DayZ (determinant -1, its own inverse) puts those toes at -Y, onto the rig.
- Consequence: a garment fitted on `Male_body` returns to DayZ with that swap, faces in their Blender order and normals negated (Rule 12 of the dayz-model-pipeline skill, in-game test 2026-10-01). For a mesh with Blender's own winding (faces counter-clockwise seen from outside, outward normals) that is `py3d.blender_to_dayz()` (py3d 1.8.0 or newer). Until 2026-10-01 this item also asked for the face order to be reversed in every LOD, citing the add-on's `from_bl` plus `rev()`; under the axis rule that reversal turns a py3d export of such a mesh inside-out. [UNVERIFIED] `rev()` is right only for a mesh whose faces already point inward in Blender, such as one that came in through the add-on's own `to_bl` plus `rev()`. Do not apply the determinant +1 map `(x, z, -y)` (`py3d.ROT_X_NEG90`, formerly `py3d.BLENDER_TO_DAYZ`, now deprecated): it mirrors. The `dayz-characters` skill hit this on the same rig: `(x, z, -y)` shipped the LFInfectedBig infected walking backwards, and `(-x, z, y)` mirrored it (`character-rigging.md` section 6).
- Until 2026-10-01 the worn tooling imported DayZ to Blender with `(x, -z, y)` (`export_clothing_fbx.py`). That frame faced +Y with left at +X, a mirror image of the rig frame (the two differed by `y -> -y`). The script now uses the same swap, so the two frames are one. The alternative that used to stand here (mirror the rig into that frame, fit, export with `BLENDER_TO_DAYZ`) is withdrawn: it fits in a mirrored frame and exports with a determinant +1 map, so anything with a side modelled in that frame (text, a pocket, a buckle) ships reversed. Only geometry that entered through the old determinant +1 import comes back unmirrored, because the two maps cancel, as in the legacy return trip described in the artist handoff section of the skill.
- Before packing, run the anatomical facing test ("Canonical worn frame" in `worn-models.md`) and the per-component winding check of the dayz-model-pipeline skill (Rule 18; expected: cross product inward) on the exported p3d (the flipped-frame failure). With weights transferred from `Male_body` the facing test catches a determinant +1 export, since the selections then come from the true side. No winding check sees a mirror, and the facing test cannot see one once the left and right selections have been swapped by hand (the chiral check in `worn-models.md`).

## 3. Landmarks: replacing `_real_dayz_rig_landmarks` [RUN 2026-09-01: works; mirrors addon.py:3853-3876]

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

This drops the add-on's `scene.dayz.clothing_armature` lookup and its `dayz_real_player_rig` flag; the centroid fallback `_reference_arm_landmarks` (1844-1875) becomes unnecessary. `_reference_arm_radius_profile` (1875) samples the reference mesh around that axis: feed it `Male_body` and its `matrix_world` (the 0.01 object scale lives inside the matrix).

[RUN 2026-09-01] Works as written; the heads matched the rig probe to 1 mm; arm length shoulder to elbow to wrist = 0.565 m per side. `WristExtra` and `Hand` differ by 7 mm: irrelevant. Blender 5.1 has no `Mesh.calc_normals_split`: read `vertex.normal` and recompute the face normals after the axis swap.

## 4. Region bbox and uniform fit [RUN 2026-09-01: works for the torso, cannot move sleeves; addon.py:21-31, 1629-1638, 1700-1748]

- Region groups per garment type: `CLOTHING_REGION_GROUPS` (JACKET, SHIRT, VEST, PANTS, BOOTS, GLOVES, BACKPACK, HEADGEAR, MASK), lowercase names; match the `Male_body` groups by `.lower()`.
- `_reference_region_bbox`: world bbox of the `Male_body` vertices weighted above 0.02 in any group of the region.
- `_fit_objects_to_reference`: one uniform factor for all parts of the garment (multi-part OBJ or FBX files are measured together): `0.82 * height_ratio + 0.18 * secondary`, where `secondary` is whichever of the X or Y ratio is closest to 1 (`argmin |log r|`, addon.py:1721-1722), for JACKET, SHIRT, VEST, BACKPACK and PANTS (the median of the three ratios otherwise), times `margin` (the add-on's UI default is 1.06; the function default is 1.02). Then translate so the garment's top edge sits on the region's top edge (the bottom edge for BOOTS). No vertex warping at all.
  [RUN 2026-09-01] Works as written. JACKET region bbox of `Male_body`: lo (-0.603, -0.134, 0.945), hi (0.603, 0.143, 1.611); factor 0.424 with margin 1.04 on the Hunyuan jacket; collar at the neck, hem mid-thigh, front offset 0.035 m towards -Y. What it cannot do: a garment with hanging sleeves stays 0.69 m wide against a 1.21 m A-pose region, so the sleeves end up beside the torso, not on the arms.
- Rest forward offset (`_set_clothing_rest_forward_offset` 1608-1621): translate along the body's front vector by `offset` (add-on default 0.035 m), stored on the object so repeated fits do not accumulate. On the official rig the front vector is world `(0, -1, 0)`, and since 2026-10-01 in the worn tooling too (its retired +Y frame had `(0, +1, 0)`).

## 5. Weight transfer from `Male_body` [RUN 2026-09-01: works in Blender 5.1.1 with the three corrections of item 7]

1. Remove foreign deform groups from the garment (`_remove_foreign_deform_groups` 4036-4065): anything that is neither a bone name nor a named selection (`camo*`, `zbytek`, `hiddenSelection*` stay).
2. Create the destination groups by name (`_copy_reference_vgroup_names` 3781), then add a `DATA_TRANSFER` modifier on the garment: `object = Male_body`, `use_vert_data = True`, `data_types_verts = {'VGROUP_WEIGHTS'}`, `vert_mapping = 'POLYINTERP_NEAREST'`, `layers_vgroup_select_src = 'ALL'`, `layers_vgroup_select_dst = 'NAME'` (addon.py:4110-4118). Apply it with `bpy.ops.object.modifier_apply(modifier=name)` inside `bpy.context.temp_override(object=g, active_object=g, selected_objects=[g])`; headless there is no active object otherwise.
3. Cleanup (`_cleanup_weights` 4127-4155): per vertex keep the top 4 or fewer bone groups with weight 0.005 or more, drop the rest, renormalise to 1.0; touch only bone-named groups so named selections survive. That is why it is better than Blender's global Clean or Limit Total.
4. Add what the add-on lacks: cross-midline cleanup (`left*` weight on the right half and the reverse; `character-rigging.md` section 4) and the two counts of section 7.
5. Export with py3d: group names to lowercase; the byte encoding is py3d's `round((1-w)*255)+1` (both in `character-rigging.md` section 6), never the add-on's `weight_encode` table (addon.py:233-238).
6. The in-game skeleton is still `DayzTemporarySkeleton` with the 159-pair template (`worn-models.md`, "Skeleton"); the rig only generates weights. The 44-name set is what vanilla worn items actually weight: more bones is fine, fewer works but articulates coarsely.
7. [RUN 2026-09-01] Steps 2 to 5 work in Blender 5.1.1 (`modifier_apply` under `temp_override` applied first time; 111 groups transferred). Three corrections found by the run:
   - Restrict the "bone-named groups" of step 3 to the deform set of `character-rigging.md` section 2 (no `Face_*`, eyes, tongue, fingers): otherwise a collar ends up weighted to `face_jawbone`.
   - py3d's byte encoding quantises weights: sums come back as 0.996 to 1.004 after the p3d round trip, so the gate tolerance is plus or minus 0.01, not exactly 1.0.
   - The empty Geometry LOD (1e13, `autocenter=0`) makes `python -m py3d validate` raise `ERR_COMPONENT_NAMING` unless it carries an empty `Component01` selection (0 points). Adding it satisfies the validator; whether vanilla worn p3ds carry it is [ASSUMPTION]. That is py3d up to 1.8.0; from 1.9.0 on, a collision LOD without faces raises no component-naming or component-coverage finding, so the validator no longer asks for the empty selection.

   Result on the test jacket: 49,994 vertices, 0 unweighted, at most 4 influences, 0 midline bleed, 34 of the 44 selections populated.

## 6. Sleeve detection: mask only [RUN 2026-09-01: the corridor mask works; rigid rotation refuted]

`_find_disconnected_sleeve_component` 2245, `_find_sleeve_by_reference_corridor` 2294, `_auto_source_sleeve` 2358 and `_auto_assign_both_sleeves` 2480 are reusable to tag `DAYZ_SLEEVE_L` and `DAYZ_SLEEVE_R` vertex groups (corridor = 0.19 x arm length around the section 3 axis) for the alignment viewer. Do not port the heuristic warp that follows (`_apply_autofit_armature` 3213-3287) as it is: the add-on's own README admits wrong-sleeve detection (README_AUTOFIT_1_9.md, the section on what to do when the automation marks the wrong sleeve) and `_filter_plausible_arm_fields` (2927-2955) silently continues with one arm.

[RUN 2026-09-01] On a closed AI shell the wrist-seed flood found 0 of 2 sleeves (no open cuffs); labelling the whole corridor found 2 of 2 (4,582 / 4,468 vertices with the A-pose axis; 12,659 / 12,346 with a corridor around the garment's own axis from hanging cuff to shoulder, which also captures flank vertices). A rigid rotation of the masked sleeve about the `*Arm` head onto the rig axis (the add-on's v4 logic, addon.py:2720-2809, blend `smoothstep(0.05, 0.22)` of the arm length at the root, axial scale 0.75) reached 7.2 / 7.6 degrees and cuffs 4.7 / 4.6 cm from the hand, but tore the mesh: flank vertices inside the corridor rotated with the sleeve and stretched into fan-shaped membranes between sleeve and torso. Verdict: rigid rotation is unusable on garments whose sleeves are fused to the torso, and the gate cannot detect the membranes. Do not ship a fit without looking at the render.

## 6b. Hanging-sleeve garments: pose-match skinning instead of rotation [RUN 2026-09-02: the mechanics work, it still tears on a fused AI shell]

This is the add-on's v5 idea (`_apply_autofit_armature`: bind in the garment's pose, then move the rig to rest) made deterministic with the measured axes. It is the only route that moves the sleeve with a proper skinning falloff instead of a cut:

1. Measure the garment's sleeve axes from the corridor mask (shoulder root, PCA axis, cuff).
2. Pose the official `Armature` in Pose Mode so that the `LeftArm` and `RightArm` chains follow those axes (rotate the arm bones about the shoulder; keep the rest of the rig untouched). `Male_body` follows through its Armature modifier, so the donor body is now arms-down too.
3. Transfer weights from the posed `Male_body` (section 5, evaluated mesh) and clean them.
4. Bind the garment to the armature in that pose (Armature modifier, parent inverse), then return the armature to its rest pose: the skinning carries the sleeves to the A-pose with weight falloff at the shoulder instead of a rigid seam.
5. Apply the Armature modifier (bake), run the gate (7) including (h) and (i), review renders, export via section 2.

Expected failure to watch for: flank vertices weighted to arm bones (the corridor problem in a different form). The cross-midline and per-bone-share checks of the gate catch part of it, the render catches the rest. Cheaper alternative: regenerate the garment in A-pose upstream.

[RUN 2026-09-02, worker notes] Rotate the `*Arm` pose bone about its world head with `pose_bone.matrix` (never `bone.vector` or `tail`: tails are garbage after import); one rotation of `*Arm` was enough (ForeArm untouched), residual 0.02 degrees. Bind sequence that avoids the double transform: record the rest world matrices of the 18 arm-chain bones before posing; `bpy.ops.pose.armature_apply`; add the Armature modifier and parent inverse; set the chain back to the recorded matrices parent-first with `view_layer.update()` between bones; apply the modifier. The posed donor paints arm weights on the flank (hanging arm = flank volume), so the worker blended posed weights inside `DAYZ_SLEEVE_*` with rest-pose weights outside; the tear then appears at that boundary (see the round-4 note at the top). On this mesh the route is refuted, not the mechanics.

## 7. Gate before trusting a fit [DESIGN]

- 0 zero-weight vertices; every vertex weight sum = 1.0 plus or minus 0.01; at most 4 influences; `left*` / `right*` bleed across the midline = 0.
- Facing: the anatomical test ("Canonical worn frame" in `worn-models.md`) on the exported p3d (front detail at -Z, `left*` centroids at +X). Measured on the test jacket: `left*` centroid x = +0.16 (fit only) / +0.25 (sleeves on arms); spine and pelvis weighted z = -0.040 / -0.059 (vanilla -0.04 to -0.08); garment y in [0.77, 1.61].
- Sleeves on arms (added after the run): (h) the angle between each sleeve's principal axis and the rig's `Arm -> Hand` axis is 12 degrees or less, and the cuff centroid (the 10 % of sleeve vertices farthest from the shoulder) is 0.08 m or less from the `Hand` head, both in the DayZ frame; (i) 70 % or more of the weight of the sleeve vertices sits on arm bones (`*arm*`, `*forearm*`, `*hand`, their roll and extra bones), not on `spine*` or `*shoulder`. The gate script of the run was not brought into this repo.
- Membranes or torn fabric (added 2026-09-02, criterion j): on the exported visual LOD, edge lengths after the fit against the fitted but unposed garment: p99 ratio 1.3 or less and max ratio 2.0 or less. Calibrated on the round-2 p3d (membranes): p99 1.31 and max 6.15, a fail; the pose-match round: max 6.53, a fail. It is the only mechanical check that sees the tears.
- (h) to (j) still do not see a sleeve sitting beside the torso without stretching: look at an orthographic front render with `Male_body` overlaid before trusting any of them.
- Then the in-game gate of the skill's build steps (spawn, equip, move). A worn item cannot be validated offline only.
