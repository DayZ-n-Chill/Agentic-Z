---
name: blender-assembly
description: "Rules and a helper library for building 3D models in Blender through Blender MCP tools (such as mcp__blender__execute_blender_code): furniture, vehicles, architecture, props, mechanical parts, scenes. Use whenever Blender Python code will create geometry with primitives, bmesh, curves, modifiers or booleans, including 'simple' objects, and load it before writing that code. It prevents the common geometry bugs (exploded models, silent scale errors, broken boolean meshes), adds a detail pass so models do not ship as bare boxes (bevels, panel recesses, hardware, cables, lofted grips and stocks, baked normal maps), and runs a mesh integrity gate after every boolean or modifier apply."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# Blender assembly

This skill prevents geometry errors when building 3D models in Blender over MCP, and adds a detail pass so models come out looking like objects, not boxes. It needs a Blender MCP server connected to the session; this repo configures none. The recurring failures it addresses:

1. **Cube size math.** `primitive_cube_add(size=1)` creates vertices at ±0.5, so `scale=0.4` gives a half-extent of 0.2, not 0.4. This silently halves every dimension and misplaces all connected parts.
2. **Euler rotation on cylinders.** Rotating a cylinder to point in a direction with Euler angles often points it along the wrong axis, because of the XYZ rotation order.
3. **Invisible gaps.** Parts placed near each other with no geometric overlap look exploded when rendered. Even a 5 mm gap is visible at model scale.
4. **Bare-box output.** Nothing in the workflow asked for detail, so none was built. Phase 1.5 and Rules 6 to 11 fix this.
5. **Broken meshes.** Booleans and joins leave non-manifold edges, duplicate vertices and degenerate faces that bounding-box checks never see. The integrity gate in Phase 3 catches them.

This is a Blender method, not a statement about the game. Where it touches DayZ (the `_nohq` convention, LOD budgets) it says who measured the fact; none of those can be checked against the vanilla files on `P:\`.

## What to read

| Question | Read |
|---|---|
| The helper functions themselves (run the file in Blender at session start) | `<skill-dir>\blender_helpers.py` |
| How to scan a reference zone by zone for the detail list, the texture-side detail kinds and where each lands in DayZ textures, and the three kinds of linework | `<skill-dir>\references\detail-scan.md` |
| Renders over MCP show the mesh from before an edit, or the wrong scene | `<skill-dir>\references\mcp-render-pitfalls.md` |

## Helper library

All helper functions live in `blender_helpers.py`, next to this file, with a version in its docstring. At session start, read that file and execute it whole through the Blender MCP instead of pasting individual functions again: this stops copies drifting apart. A new helper enters the library only after surviving its fixtures. The module docstring records the 2026-06-10 validation against Blender 5.1.1 (fixtures F1 to F3, F5 and F6, run by the library's author); the section banners of the v2 helpers still read PENDING FIXTURES from before that run.

## Routing: build it, or generate it?

This skill covers parametric hard-surface modeling: anything that can be defined by dimensions, joints and repeated features (furniture, machines, crates, frames, pipes, electrical devices, weapons). For organic or densely decorative geometry (statues, creatures, irregular props, sculpted surfaces), building by hand in Blender is the expensive path. Route those to AI generation instead: an AI base mesh, then optimize and remesh, then this skill for cleanup and export. The image to 3D ladder (local, then fal, then paid) is in the optional external skill `hunyuan3d-local`, which is not shipped in this repo; the DayZ side of that route is in `ai-3d-to-dayz`. Decide before writing any geometry code. A half-sculpted bmesh blob is the worst of both.

## Phase 1: connection planning (before any code)

Write a connection map listing every joint before writing any geometry. This forces correct thinking about where parts touch.

For each joint, write:

- the two parts that connect
- which face or edge of each meets the other
- the target overlap (at least 0.005 m, 5 mm)

```
Connection Map:
  tabletop_bottom (Z=0.73) <-> leg_top (Z=0.74)     overlap: 0.01m on Z
  leg_bottom (Z=0.01)      <-> floor (Z=0.00)        sits on floor
  drawer_back              <-> desk_body_front        overlap: 0.01m on Y
```

Write this as a comment block in your first code cell, before any `bpy` call.

## Phase 1.5: detail planning (before any code)

The connection map guarantees the model holds together. It does not stop the model shipping as a set of bare boxes. A model with zero detail features is unfinished by default: nothing in the real world has perfect 90 degree edges.

Next to the connection map, write a detail list: for each visible part, the features the real object has, the technique that produces each, and its approximate size. Think like the reference photo, not like the primitive.

```
Detail List:
  housing      edge chamfer        bevel 3mm/2seg      all exterior edges
  housing      side vent recess    inset+sink          0.12 x 0.06m, depth 5mm
  housing      corner bolts        place_copies        4 per corner plate
  front panel  panel line          inset+sink          2mm wide, 1mm deep
  frame        cable run           make_cable r=6mm    junction box to motor
  grip         compound shape      loft_profile        palm swell + taper
  grip         stippling           bake (Rule 11)      normal map, not geometry
```

Floors (a model below these is not done):

- Every exterior edge of every visible part gets a bevel (Rule 6), background parts included. Edges without a bevel read as computer graphics from any distance.
- A hero object carries at least 3 distinct detail feature types (for example bevel, recess and hardware). If the detail list has fewer, go back to the reference before coding.
- Budget by LOD: the full list on LOD0, then drop hardware and recesses step by step on lower LODs. The poly budgets are in `dayz-model-pipeline`.
- Fine surface detail (knurling, threads, stippling, stamped text) goes to the bake (Rule 11), never to LOD0 geometry.

If no reference image exists, get one first. `blender-visual-review` compares against it later, and a detail list invented from memory produces generic detail.

A detail list written from one glance at the reference misses the small marks that give the object its identity. Scan the reference zone by zone and keep the scan with the list: the method, the count floor by complexity, the per-detail record, the texture-side detail kinds and the three kinds of linework are in `references/detail-scan.md`.

## Phase 2: geometry rules

### Rule 1: always use size=2 for cube primitives

A cube with `size=S` has vertices at `±S/2`. After `scale=K`, the half-extent is `K * S/2`, not `K`.

Always use `size=2`. Then the vertices are at ±1, and after `scale=K` the half-extent equals `K` directly. The math is plain and the factor of 2 error disappears.

```python
# CORRECT: size=2, scale = desired half-extent
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.75))
obj.scale = (0.60, 0.30, 0.02)   # box is 1.2m wide, 0.6m deep, 0.04m tall

# WRONG: size=1, scale misread as full extent
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.75))
obj.scale = (0.60, 0.30, 0.02)   # box is only 0.6m wide, half of what was intended
```

Cylinders and spheres take `radius`, which is already the real radius. No conversion is needed.

### Rule 2: use bmesh for directional geometry, never rotate cylinders

Never create a cylinder and rotate it to point in a direction. The Euler rotation order (XYZ) makes this fail silently: the cylinder often ends up on the wrong axis.

For any geometry that must span from point A to point B (legs, beams, axles, supports, pipes, rails), build it with explicit vertex positions: `make_beam(name, start, end, hw, hh)` from the helper library.

- Use it for: chair and table legs, beams, axles, frame members, railings, any angled strut.
- Skip it for: vertical posts, wheels, hubs, anything aligned with a world axis where no rotation is needed.
- Round cross-sections (pipes, cables, trigger guards): `make_cable` (Rule 8). Varying cross-sections (grips, stocks): `loft_profile` (Rule 10).

### Rule 3: call transform_apply right after setting scale

When objects are created in a loop, `bpy.context.active_object` can silently point at the wrong object by the end of the loop, so a scale assignment fails or lands on the wrong mesh. Call `transform_apply` immediately after every scale assignment, inside the loop, before anything else:

```python
# CORRECT
bpy.ops.mesh.primitive_cube_add(size=2, location=(x, y, z))
obj = bpy.context.active_object
obj.name = name
obj.scale = (sx, sy, sz)
bpy.ops.object.transform_apply(scale=True)   # immediately, inside the loop

# WRONG: the scale may silently not apply
obj.scale = (sx, sy, sz)
# ... more operations ...
bpy.ops.object.transform_apply(scale=True)   # too late; active_object may have changed
```

### Rule 4: derive spanning dimensions from verified neighbour bounds

Never hardcode a dimension for a part that must reach between two existing parts. Hardcoded values drift from the real geometry. Call `verify_bounds()` on both neighbours and compute the size from their real extents:

```python
# CORRECT: measure first, then size the new part
b_a = verify_bounds("Part_A")
b_b = verify_bounds("Part_B")
half_span = (b_b['x'][1] - b_a['x'][0]) / 2   # the half-width needed to bridge A and B

# WRONG: dimension set independently of the neighbours' real positions
half_span = 0.28   # guessed; wrong if a neighbour shifted even slightly
```

Apply this rule whenever one part must cover, fill or connect two others on any axis. Measure the gap from real bounds; never guess.

### Rule 5: compensate for subsurf shrinkage

Subdivision surface modifiers pull geometry inward. A box spanning 0.0 to 0.30 m may only reach 0.26 m after level 2 subsurf.

Extend the geometry 10 to 15% past the target boundary before applying subsurf, then verify:

```python
target_reach = 0.28
build_to     = target_reach * 1.13   # 13% longer to compensate for shrinkage
```

Alternative: use a bevel modifier instead of subsurf for structural parts. It adds smooth edges without shrinking the shape.

### Rule 6: bevel every exterior edge (the box-to-object rule)

About 80% of the visual difference between a primitive and an object is edge bevels. Add an angle-limited bevel to every visible part as the last step of its construction, after all booleans: `add_bevel(obj, width=0.003, segments=2, angle_deg=40)`. The width is in meters; 2 to 4 mm reads right at prop scale.

Apply the bevel (do not leave it live) so LOD decimation and export see real geometry. Scale must already be applied (Rule 3): a live scale makes the bevel width uneven. Run `verify_mesh_integrity` after applying (Phase 3).

### Rule 7: panel recesses and insets through bmesh

Panel lines, vents, screens and recessed faces come from an inset plus a sink: `panel_recess(obj, near_point, inset, depth)`. The face is picked by its world-space center, never by index, which changes with any earlier edit. For a raised panel instead of a recess, translate along `+face.normal` (edit the helper call). Chain two insets (frame, then sink) for vent-style detail.

### Rule 8: repeated hardware and cables

**Hardware (bolts, rivets, handles).** Model one low-poly instance (a cylinder with 8 segments is plenty at bolt scale), then place copies in an explicit loop with `place_copies(src, positions)`. That matches this skill's explicit-math approach and is easier to verify than an Array modifier. Each copy must overlap its mount surface by at least 1 mm: the connection map applies to hardware too.

**Cables, pipes, hoses, trigger guards.** Never chain rotated cylinders. `make_cable(name, points, radius)` builds a Bezier curve through explicit points, bevels it and converts it to mesh. The endpoints come from `verify_bounds()` of the parts being connected (Rule 4), with at least 5 mm of penetration into each.

### Rule 9: boolean protocol

Booleans are the main source of broken meshes. Three rules, then cleanup:

1. Apply scale on both operands first (Rule 3). Booleans on a live scale produce garbage intersections.
2. Do not leave coplanar faces between the operands. The cutter overshoots every surface it cuts through by at least 1 mm. A flush cutter is a coplanar cutter, the first cause of boolean failure (degenerate slivers, open holes).
3. The solver is always `'EXACT'`.

`boolean_cut(target, cutter, op)` enforces all three plus the cleanup (`remove_doubles` and `dissolve_degenerate`). After every boolean, run `verify_mesh_integrity` before building anything on top. A broken mesh found three parts later costs the whole session.

Point 2 is a strong recommendation, not an absolute (adjusted 2026-06-10, fixture F3, LL-119). Blender 5.1 EXACT handled an exactly flush, axis-aligned cutter without breaking the mesh: the open pocket and the volume were identical to the overshoot cut and the hard counters were clean; only the layout of the ring ngons differed. Keep the 1 mm overshoot as the default for robustness (float drift, oblique cuts), but a flush cut that passes the integrity gate and the visual checkpoint is acceptable, not an automatic fail. The gate reports ngons as warnings, never as failures (LL-120).

### Rule 10: loft cross-sections for compound shapes

Boxes and beams cannot make a pistol grip, a stock, a bottle or an ergonomic handle. The technique for those is cross-section lofting: define a 2D profile, sweep it along a 3D path, and scale it per section. This is the standard parametric approach for weapon grips and receivers.

Helpers: `ellipse_profile(rx, ry, n)`, `rounded_rect_profile(hw, hh, r, seg)`, `loft_profile(name, profile, path, scales, close_caps)`.

Pattern for a grip: `rounded_rect_profile` swept down a slightly curved path with scales such as `[1.0, 1.05, 0.95, 0.9]` (palm swell, then taper). The path points come from the connection map, and the top ring must overlap the receiver by at least 5 mm. The helper recalculates face normals, so winding is verified, not assumed. Degenerate rings (duplicate path points) still produce zero-area faces, so run `verify_mesh_integrity` after every loft. If the result looks faceted in review, raise the profile's `n`.

### Rule 11: fine detail goes to the normal map, not to LOD0

Knurling, grip stippling, screw threads, stamped text, fine panel seams: modeled as geometry these blow the poly budget and still read worse than a bake. The game industry standard is the high to low pass, and it fits the DayZ texture pipeline directly (the `_nohq` normal map, and ambient occlusion multiplied into the `_co`):

1. Build the part twice from the same build script: **high** (bevel segments 4 to 6, knurl and thread geometry, deep panel lines) and **low** (game budget, Rules 1 to 10 only). One script with two parameter sets, never two scripts that drift apart.
2. Unwrap the low mesh: `smart_uv(obj)`. Smart UV Project is acceptable for hard surface, and the islands need a margin or the bake bleeds. It also shatters the mesh into tiny islands (a median of 2 to 4 faces per island is the classic failure), which makes an atlas nobody can paint detail on. For a DayZ visual asset, unwrap by logical sections with contiguous islands and an atlas a person can read; the gate is a person reading the atlas. The full reference and the audit scripts are in the `uv-clean-atlas` skill.
3. Bake from high to low with `bake_map(high, low, 'NORMAL', ...)` and `bake_map(high, low, 'AO', ...)` (Cycles, selected to active).

Known pitfalls, all reproduced in community reports and all controllable:

- No UVs on the low mesh is a hard error. Run `smart_uv` first.
- High and low not occupying the same space, or `ray` too small or too large, gives patchy garbage in the map. Set `max_ray_distance` slightly above the largest gap between the high and low surfaces; use a cage for parts with deep recesses. The default `ray=0.01` was validated by fixture F6 (clean 1024 px NORMAL and AO bakes at a gap of about 4 mm).
- Blender bakes tangent normals in the OpenGL convention (Y+). DayZ's `_nohq` is the DirectX convention (Y-): invert the green channel (G' = 255 - G) on every Cycles bake before export. The source author resolved this on 2026-06-10 with fixture F7, a calibration against a vanilla `_nohq` (LL-123, LL-125); it is not checked on `P:\` here. Before F7 this rule said to verify the convention empirically and not to guess. The same verdict notes that a `.paa` `_nohq` stores X in alpha (the DXT5nm swizzle), so un-swizzle before auditing a converted map; the full verdict and the calibration chain are in the `dayz-texture-pipeline` skill (`references/map-conventions.md`).

The output feeds `dayz-model-pipeline` and `/dayz-pack-texture`: the normal PNG becomes `_nohq.paa`, and the AO PNG becomes a multiply layer in the `_co` composite.

## Phase 3: verify after every part

Call these after creating each part. Catching a defect immediately is far cheaper than debugging an exploded or broken model later. All three are in the helper library.

**`verify_bounds(name)`** prints and returns the world-space bounding box of a part.

**`verify_overlap(name_a, name_b, axis, min_overlap)`** confirms two parts physically overlap on the given axis. Run it for every joint in the connection map before moving to the next part. If it shows a gap, fix the position before continuing.

**`verify_mesh_integrity(name, require_closed, allow_ngons)`** is the broken-geometry gate. `verify_bounds` proves position and passes happily on a non-manifold mess. This gate proves the mesh itself is sound. Run it after every boolean, every modifier apply, every loft, and once per part at finalization. Reading the result:

- `non_manifold_edges > 0`: an edge shared by 3 or more faces, almost always a boolean leftover or two parts joined without merging. Fix it at the operation that caused it; do not patch around it.
- `duplicate_verts > 0`: run `remove_doubles` on the real mesh (the gate's own pass runs on a throwaway copy).
- `boundary_edges > 0` with `require_closed=True`: a hole. Collision geometry must be closed. For a visual mesh with intentional openings, call with `require_closed=False` and record why in a comment in the build script.
- `ngons`: on curved surfaces they shade badly and decimate badly, so triangulate or inset again. On large flat faces they are tolerable, which is why this is a warning and not a failure.

A failed gate means stop and fix before the next part. The discipline and the reason are the same as for `verify_overlap`: broken geometry compounds.

**Component checkpoint.** For complex parts (lofts, pieces with many booleans), also take one quick visual capture of the part alone before building on top of it (`blender-visual-review`). Numbers verify topology; only eyes verify intent.

**Moving mechanisms: check the fit over the whole travel and the whole length** (SP-451, added 2026-10-01, measured offline). A vertical mechanism checked on one representative section failed twice on the SecretRock R7 model: standing leaves checked only at their widest section (y = 0.8) stuck out of the rock by up to 0.96 m elsewhere, and a platform checked only at the top touched the lining at the hangar end by up to 1.1 m.

**Sampling once per frame skips short collisions** (measured offline). Folding a 2.46 m leaf hinged on its top edge brings each lower corner 4.7 mm closer in the first degrees, a collision shorter than one frame. Sweep the kinematics with angles set by hand and a fine step near 0 degrees, with the actions unhooked so the depsgraph does not override the angles. Keyframe clearance in presentation renders is covered in `blender-visual-review`, checklist A, "Animated parts".

## Phase 4: finalization

Apply to every mesh object: `finalize(name)` (transforms applied, origin set, shade smooth), then `audit_all()` to confirm rotation (0,0,0) and scale (1,1,1) across the whole scene. Both are in the helper library.

## Rules from the author's lessons log (added 2026-07-27)

Each rule keeps the `LL-NNN` number of the lesson it came from. The lessons log itself (symptom, origin, evidence) is the author's private file and is not in this repo.

- **LL-065.** Do not use booleans to carve open or non-watertight organic meshes; prefer extruding the boundary loop or bridging by hand. If you do use a boolean, operate between closed solids and validate raycast, boundary and non-manifold before continuing.
- **LL-121.** After changing `location`, `rotation` or `scale` through the API, call `bpy.context.view_layer.update()` before reading `matrix_world`. Put the update in the helper that reads, and use fixtures that vary all axes.
- **LL-122.** For closed tubes, enable `use_fill_caps`, convert to mesh and weld with `remove_doubles(1e-5)`. Keep the `require_closed` gate; do not lower it for boundary edges.
- **LL-126.** Always call `transform_apply(location=False, rotation=<bool>, scale=<bool>)` with all three arguments explicit. Create copy sources at the world origin before baking transforms.
- **LL-127.** Call `finalize()` immediately on the newly created active object; do not loop over names expecting the helper to look them up. Check the helper's real contract, and confirm name to bounding box after renaming.
- **LL-128.** For planar curved pieces, build a 2.5D loft with a fixed width on a world axis and the depth derived from the planar tangent. Run `remove_doubles` and `dissolve_degenerate` after each loft.
- **LL-129.** In hollow pieces, size each cutter to cross only the target wall, overshooting into the hollow without reaching the opposite wall. Run the integrity gate after each boolean.
- **LL-132.** Keep the components of each cutter disjoint, and apply circles and slots in separate passes. Make the gate fail if a mesh is left with zero vertices, and raise an alert if successive operations produce identical signatures.
- **LL-133.** Do not use `panel_recess` on loft caps or ngons; use an oriented boolean or leave the detail to the bake. Position cutters from the analytical path, scales and profile, never by sampling bands of the resulting mesh.

## Workflow checklist

Every Blender model, every time:

1. **Route first.** Parametric hard surface stays here; organic or sculpted goes to AI generation (`ai-3d-to-dayz`, and the optional external `hunyuan3d-local`).
2. **Connection map.** Every joint, written before any `bpy` code.
3. **Detail list.** Scanned by zone (`grid-3x3` or `component-zones`), at or above the count floor for its complexity, every row mapped to a technique or a texture channel, at least 3 feature types on a hero object, reference image in hand.
4. **`size=2`** for all cube primitives: scale is the half-extent.
5. **`make_beam()`, `make_cable()`, `loft_profile()`** for A to B and compound shapes: no Euler rotations.
6. **`transform_apply(scale=True)` immediately** after every scale assignment, inside the loop.
7. **Spanning dimensions from `verify_bounds()`**: measured, never guessed.
8. **Booleans by protocol.** Scale applied, cutter overshoots by at least 1 mm, EXACT, cleanup, gate.
9. **Bevel every visible part.** Angle-limited, applied, after all booleans.
10. **Fine detail to the bake.** High and low twins from one script, `smart_uv` plus `bake_map` (NORMAL and AO), never knurling on LOD0.
11. **`verify_bounds()` and `verify_overlap()`** after every part and every joint.
12. **`verify_mesh_integrity()`** after every boolean or modifier apply, after every loft, and at finalization.
13. **Component checkpoint.** One quick `vr_capture` of each complex part (lofts, boolean-heavy pieces) before building on top.
14. **`finalize()` and `audit_all()`**: transforms clean across the scene.
15. **Hand off to `blender-visual-review`.** Numbers verify topology; only eyes verify intent.
