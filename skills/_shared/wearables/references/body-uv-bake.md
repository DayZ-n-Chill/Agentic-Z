# UV unwrap and bake for a rigged body

Covers unwrapping the low poly body and baking the high poly detail into a tangent space `_nohq` normal map and an ambient occlusion map, the traps a rigged mesh adds, and how to weight internal decorative geometry such as a ribcage.

All of this is Blender and texture tool knowledge, measured headless on a custom test infected body, and none of it can be checked on `P:\`. The suffixes the result ships under are the vanilla ones: a vanilla infected material names its normal map `hermit_nohq.paa` in `Stage1` (`P:\DZ\characters\zombies\data\hermit.rvmat:11`) and its specular map `hermit_smdi.paa` in `Stage5` (`:59`). Suffix rules are in `_shared/textures/suffixes-and-sizes.md`.

The test of a bake is not "the map looks purple". It is a lit preview of the low poly with the normal map on, compared with the high poly, plus numbers: the spread of UV stretch, no black pixels, and an AO mean of about 200 of 255 on the surface. Render and look; the raw map is not the test.

## Unwrap on quads, then triangulate

Unwrap the quad mesh (cleaner islands), pack to fill the square, then triangulate. Triangulating adds no vertices, so the rig weights are untouched, and it makes the bake tangents equal the shipped ones, so there are no shading seams in game. Ship the triangulated mesh.

```python
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=radians(66), island_margin=0.003)   # small margin
bpy.ops.uv.select_all(action='SELECT')
bpy.ops.uv.pack_islands(rotate=True, scale=True, margin=0.008)           # fill the 0..1 square
bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
```

`island_margin=0.02` packs row by row and wastes about 40 % of the square. A small margin plus a rotating `pack_islands` fills about 97 % of it.

Check it with numbers. Per triangle, `uv_area / world_area` divided by its median should sit in a tight band, about 0.8 to 1.15 times from the 10th to the 90th percentile, with no zero area UV faces. Render a `COLOR_GRID` flat lit (Workbench engine, `light='FLAT'`, `color_type='TEXTURE'`): squares stay square and nothing smears. Draw the UV layout from the loop UVs with Pillow to see clumping or overlap.

## Bake from the pose before the conform

The rig step conforms the low poly's limbs to the canonical bind (`body-rigging.md`, section "Conform the mesh to the bind pose"); on the test body the arms opened about 8 cm. The high poly was never conformed, so low and high no longer share the same space in those regions. The tell: `low.dims.x` differs from `high.dims.x`. Baking straight across gives rainbow noise where rays hit the wrong surface, and flat misses.

A tangent space normal map does not depend on the pose when topology and UV are the same. So bake in the pose where low and high line up (the retopology pose from before the conform), with the shipped low's topology and new UV, then use the result on the conformed shipped low.

```python
# co3 = world positions of the retopo low from BEFORE the conform (it matches the high; check the dims)
proxy = duplicate(shipped_low); proxy.matrix_world = Identity
for i, v in enumerate(proxy.data.vertices): v.co = co3[i]    # shipped topology and UV, aligned positions
# check the index match first: median |co3[i] - shipped[i]| is about 0 where nothing was
# conformed (torso, legs) and large only in the conformed limbs. Confirm proxy.dims == high.dims.
```

The same mismatch spoils a colour bake. On the test body the "camo" or black and grey facet noise seen in game was in the baked `_co`, not the normal map, and stayed after `_nohq` was removed. Open the baked `_co` and look at it.

## Keep a generated high poly's normals

Recalculating normals outside (`normals_make_consistent`) on a generated mesh that is not watertight can flip whole shells inward, which shows as large black blotches in the lit preview. Generators output normals that are already consistent; use them and only call `shade_smooth()`. Recalculating is safe on the clean retopology target (next sections).

## Misses stay neutral, never black

Cycles with `use_clear=True` clears the target to black `(0, 0, 0)`. A Normal Map node reads that as a normal pointing inward, and the texel renders black under light. Wherever the low has no high within the ray distance (thin fingers, the rim of a cavity, a conformed limb the proxy did not cover) you get black holes.

Fill the image with the neutral value first and turn the clear off:

```python
nrm = bpy.data.images.new("normal_ogl", 2048, 2048, float_buffer=True)
nrm.colorspace_settings.name = 'Non-Color'
nrm.pixels.foreach_set(np.tile(np.float32([0.5, 0.5, 1.0, 1.0]), 2048 * 2048))   # neutral tangent normal
bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', use_selected_to_active=True,
                    cage_extrusion=0.025, max_ray_distance=0.05,            # generous; a body is thick
                    margin=16, margin_type='EXTEND', use_clear=False)       # keep the neutral fill
```

After the bake the share of pixels equal to `(0, 0, 0)` should be about zero. Save 16 bit raw (`view_transform='Raw'`, depth `'16'`, `img.save_render`).

## AO: only the target occludes, with clean normals

An AO bake comes out too dark for two separate reasons:

- **The high poly occludes.** AO uses every mesh in the scene, and the high poly sits in the same space as the low. Hide every mesh but the target (`hide_render=True`) before the AO bake.
- **The target's normals are inconsistent.** Voxel remesh, decimate and conform leave custom split normals or flipped faces, so AO rays go into the surface. Clean them first:

```python
bpy.ops.mesh.customdata_custom_splitnormals_clear()
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.shade_smooth()
```

Bake AO on the conformed shipped low alone: set `bpy.context.scene.cycles.samples = 256`, then `bake(type='AO', use_selected_to_active=False, margin=16, use_clear=True)` (the bake operator has no `samples` argument). The AO mean on surface pixels, with the black gaps masked out, should be about 180 to 210. Keep the cleaned normals on the shipped mesh; the normal map was baked against them.

## Invert green for `_nohq`

DayZ reads `_nohq` in the DirectX convention (Y down), while Blender bakes OpenGL (Y up); this is tool knowledge, not a vanilla file. Invert the green channel of the Blender result. Keep the 16 bit OpenGL map as the master and make `_nohq` from it, not from an 8 bit copy. `_shared/textures/checking-the-look.md` gives the symptom of a flipped green channel in game.

```python
r, g, b = Image.open("normal_ogl.png").convert("RGB").split()
Image.merge("RGB", (r, ImageOps.invert(g), b)).save("nohq.png")
```

## Weighting internal geometry

Thin, self intersecting inner meshes such as a ribcage break Blender bone heat (`ARMATURE_AUTO`) completely, leaving every vertex without a weight. Two routes, in order:

- **Weight by height along the spine.** For each vertex take the two nearest of `Pelvis`, `Spine`, `Spine1`, `Spine2`, `Spine3`, `Neck` and `Neck1` by world Z and blend by inverse distance. Ribs hang from the spine, not the arms.
- **`DATA_TRANSFER` from the body mesh** (`POLYINTERP_NEAREST`, `layers_vgroup_select_src='ALL'`). A wide ribcage picks up shoulder and arm weights from the chest skin near it, and the ribs then swing with the arms. Use it only if you then strip every group that is not spine and normalize again.

Decimate first (collapse to about 15,000 faces; the test ribcage went from 95,000 to 15,800), parent with `type='ARMATURE'` (a modifier, no automatic weights), assign the weights, then `vertex_group_limit_total(4)` and `normalize_all`. Pose the spine and confirm the ribs follow the torso and stay inside the cavity: the dot product of their movement with the chest skin's should be close to 1 (the test body gave 0.823). Set `arm.data.pose_position = 'POSE'` for the test; the mesh ships at rest, which is the bind.

## Symptom to cause

| Symptom | Cause | Fix |
|---|---|---|
| Rainbow or garbage normal map | Low conformed after retopology, so low and high differ in those regions | "Bake from the pose before the conform" |
| Large black blotches in the lit preview | Misses cleared to black, or high poly shells flipped by a recalculation | "Misses stay neutral, never black"; "Keep a generated high poly's normals" |
| AO dark and muddy everywhere | The high poly occludes, or the target's normals are inconsistent | "AO: only the target occludes, with clean normals" |
| `_nohq` lights inverted in game | OpenGL green shipped as DayZ green | "Invert green for `_nohq`" |
| Shading seams along UV islands in game | Baked on quads, shipped triangulated | Triangulate before the bake |
| Internal mesh has no weights | Bone heat failed on thin self intersecting geometry | "Weighting internal geometry" |
| Wasted UV space | `island_margin` too big, no rotating pack | "Unwrap on quads, then triangulate" |
