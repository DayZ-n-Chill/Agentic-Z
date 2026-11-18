# UV unwrap and normal and AO bake for a rigged body

Covers unwrapping the low-poly body and baking the high-poly detail into a tangent-space `_nohq` normal map and an ambient occlusion map in the new UV, with the traps a rigged mesh adds, and how to weight internal decorative geometry.

How to read the marks: this file is Blender and texture tool behaviour, measured on a custom giant infected test build (the "giant infected build") in Blender headless (2026-06-25). None of it can be checked on `P:\`. The one vanilla fact, the texture suffixes, is cited.

After the mesh is rigged (`body-rigging.md`) you unwrap the low-poly and bake the high-poly surface into two maps. The suffixes the result ships under are the vanilla ones: a vanilla infected material names its normal map `hermit_nohq.paa` in `Stage1` (`P:\DZ\characters\zombies\data\hermit.rvmat:11`) and its specular map `hermit_smdi.paa` in `Stage5` (`P:\DZ\characters\zombies\data\hermit.rvmat:59`). Suffix rules are in `skills/_shared/textures/suffixes-and-sizes.md`.

The deciding gate is not "the map looks purple". It is a lit preview of the low-poly with the normal map applied, compared with the high-poly, plus numeric checks: UV stretch spread, the share of black pixels (zero), and the AO mean on the surface (about 200 of 255). Render and look; the raw map is not the test.

## 1. Unwrap: Smart UV on quads, then triangulate

Unwrap on the quad mesh (cleaner islands), pack to fill the square, then triangulate. Triangulation adds no vertices, so the rig weights are untouched, and it makes the bake tangents equal the shipped tangents (no shading seams in game). Ship the triangulated mesh.

```python
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=radians(66), island_margin=0.003)   # small margin
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.008)           # fill the 0..1 square
bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
```

`island_margin=0.02` packs row by row and wastes about 40 % of the square. A small smart-project margin plus an explicit rotating `pack_islands` fills about 97 % of the bounding box.

Verify with numbers. Per triangle, `uv_area / world_area` normalized to its median should sit in a tight band (10th to 90th percentile about 0.8 to 1.15 times, which is uniform texel density), with no zero-area UV faces. Render a `COLOR_GRID` flat lit (Workbench render engine, `light='FLAT'`, `color_type='TEXTURE'`): checker squares stay square and nothing smears. Rasterize the UV layout (dump loop UVs and draw them with Pillow) to confirm there is no clumping or overlap.

## 2. The alignment trap: bake from a proxy in the pose before the conform

The rig step conforms the low-poly's limbs to the canonical bind (`body-rigging.md`, section 3; on the giant infected build the arms opened about 8 cm). The high-poly was never conformed, so after rigging the low and high no longer occupy the same space in the conformed regions. The tell: `low.dims.x` differs from `high.dims.x`. Baking high to low directly there gives rainbow noise (rays hit the wrong surface) and flat misses.

A tangent-space normal map does not depend on the pose when topology and UV are identical. So bake in a pose where low and high do align (the retopology pose from before the conform), using the shipped low's topology and new UV, then apply the result to the conformed shipped low.

```python
# co3 = world positions of the retopo low from BEFORE the conform (it matches the high; check the dims)
proxy = duplicate(shipped_low); proxy.matrix_world = Identity
for i, v in enumerate(proxy.data.vertices): v.co = co3[i]    # topology and UV of the shipped low, aligned positions
# check the index correspondence first: median |co3[i] - shipped[i]| is about 0 in the regions that were not
# conformed (torso, legs) and large only in the conformed limbs. Confirm proxy.dims == high.dims before baking.
```

The same misalignment corrupts a colour bake: on the giant infected build the in-game "camo" or black and grey facet noise was in the baked `_co` texture, not the normal map, and stayed after `_nohq` was removed. Open the baked `_co` image and look at it.

## 3. Do not recalculate normals on a generated high-poly that is not watertight

Recalculating normals "outside" (`normals_make_consistent`) on a non-manifold generated mesh can flip whole shells inward, which shows as large coherent black blotches in the lit preview. Mesh generators output normals that are already consistent for rendering. Use them as they are and only call `shade_smooth()`. Recalculating is safe on the clean retopology target (section 5).

## 4. Bake misses stay neutral, never black

Cycles with `use_clear=True` clears the target to black `(0, 0, 0)`. A Normal Map node decodes that as a normal pointing inward, and the texel renders black under light. Where the low has no high counterpart within the ray distance (thin fingers, the rim of a cavity, a conformed limb the proxy did not fully cover) you get black holes.

Fill the image with the neutral value first and switch the clear off:

```python
nrm = bpy.data.images.new("normal_ogl", 2048, 2048, float_buffer=True)
nrm.colorspace_settings.name = 'Non-Color'
nrm.pixels.foreach_set(np.tile(np.float32([0.5, 0.5, 1.0, 1.0]), 2048 * 2048))   # neutral tangent normal
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_selected_to_active=True,
                    cage_extrusion=0.025, max_ray_distance=0.05,            # generous; a body is thick
                    margin=16, margin_type='EXTEND', use_clear=False)       # keep the neutral fill
```

Confirm that the share of pixels equal to `(0, 0, 0)` is about zero after the bake. Save 16-bit raw (`view_transform='Raw'`, depth `'16'`, `img.save_render`).

## 5. AO: the target is the only occluder, and its normals are clean

Two separate causes of an AO bake that is too dark:

- **The high-poly occludes.** AO uses all scene geometry as occluders; the high-poly sits on the same space and shadows the low. Hide every mesh except the target (`hide_render=True`) before the AO bake.
- **The target's own normals are inconsistent.** Voxel remesh, decimate and conform leave custom split normals or flipped faces, AO rays go into the surface, and the result is dark and noisy. Clean them first:

```python
bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.shade_smooth()
```

Bake AO on the conformed shipped low, low only: `bake(type='AO', use_selected_to_active=False, samples=256, margin=16, use_clear=True)`. Sanity: the AO mean on surface pixels (mask out the black gaps) should be about 180 to 210. Keep the cleaned normals on the shipped mesh; the normal map was baked against the same convention.

## 6. `_nohq` orientation: invert green for DayZ

Tool knowledge, not a vanilla file: DayZ reads `_nohq` in the DirectX convention (Y down). Blender bakes the OpenGL convention (Y up). Invert the green channel of the Blender result for the DayZ source. Keep the 16-bit OpenGL map as the master and derive `_nohq` from it, not from an 8-bit intermediate. `skills/_shared/textures/checking-the-look.md` gives the in-game symptom of a flipped green channel.

```python
r, g, b = Image.open("normal_ogl.png").convert("RGB").split()
Image.merge("RGB", (r, ImageOps.invert(g), b)).save("nohq.png")
```

## 7. Internal decorative geometry (ribcage, organs): bone-heat fails

Thin, self-intersecting internal meshes such as a ribcage break Blender bone-heat (`ARMATURE_AUTO`) entirely, leaving every vertex without a weight. Two alternatives, in order:

- **Weight by height along the spine chain.** For each vertex take the two nearest of `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck`, `Neck1` by world Z and blend by inverse distance. Ribs hang from the spine, not the arms.
- **`DATA_TRANSFER` weights from the body mesh** (`POLYINTERP_NEAREST`, `layers_vgroup_select_src='ALL'`). A wide ribcage picks up shoulder and arm weights from the chest skin near it, and the ribs swing with the arms. Use it only when you then strip the groups that are not spine and normalize again.

Decimate first (`DECIMATE` collapse to about 15,000 faces; the giant infected build's ribcage went from 95,000 to 15,800), parent with `type='ARMATURE'` (a modifier, no automatic weights), assign weights, then `vertex_group_limit_total(4)` and `normalize_all`. Pose test: pose the spine and confirm the ribs follow the torso (the dot product of the displacement direction with the chest skin's is about 1; the giant infected build measured 0.823) and stay inside the cavity. Set `arm.data.pose_position = 'POSE'` for the test (the mesh ships at rest, which is the bind).

## Symptoms

| Symptom | Cause | Fix |
|---|---|---|
| Rainbow or garbage normal map | Low conformed after retopology, so low and high differ in the conformed regions | Bake from the proxy in the pose before the conform (section 2) |
| Large black blotches in the lit preview | Misses cleared to black, or high-poly shells flipped by a recalculation | Neutral fill and `use_clear=False` (section 4); do not recalculate the generated high (section 3) |
| AO dark and muddy everywhere | The high-poly occludes, or the target's normals are inconsistent | Section 5 |
| `_nohq` lights inverted in game | OpenGL green shipped as DayZ green | Invert green (section 6) |
| Shading seams along UV islands in game | Baked on quads, shipped triangulated | Triangulate before the bake (section 1) |
| Internal mesh has no weights | Bone-heat failed on thin self-intersecting geometry | Weights by height along the spine (section 7) |
| Wasted UV resolution | `island_margin` too big, no rotating pack | Section 1 |
