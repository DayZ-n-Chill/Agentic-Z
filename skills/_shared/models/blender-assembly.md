# Building a model in Blender

How to build a hard surface model in Blender through a Blender MCP server without exploded parts, wrong sizes, broken booleans or bare boxes: planning the joints and the detail, the geometry rules, and the normal bake. The checks to run after each part, finishing, and the render traps over MCP are in `blender-assembly-checks.md`.

Read this before writing any Blender Python that makes geometry with primitives, bmesh, curves, modifiers or booleans. It needs a Blender MCP server connected to the session; this repo configures none, so a worker agent without one hands its brief to the main session. It is a Blender method, not a fact about the game; where it touches DayZ (the `_nohq` convention, LOD budgets) the files it links carry the evidence.

The failures it prevents:

- **Cube size.** `primitive_cube_add(size=1)` puts vertices at 0.5 either side, so `scale=0.4` gives a half extent of 0.2, not 0.4. Every size halves and every connected part lands wrong.
- **Rotated cylinders.** Pointing a cylinder with Euler angles often lands it on the wrong axis, because of the XYZ rotation order.
- **Gaps.** Parts placed close but not overlapping look exploded in a render. A 5 mm gap shows at model scale.
- **Bare boxes.** Nothing asked for detail, so none was built. The detail list and the geometry rules below fix that.
- **Broken meshes.** Booleans and joins leave open edges, doubled vertices and degenerate faces that a bounding box check never sees. The integrity check in `blender-assembly-checks.md` catches them.

| Question | Read |
|---|---|
| The helper functions (run the file in Blender at session start) | `skills/dayz-model-tools/scripts/blender_helpers.py` |
| Scanning a reference zone by zone for the detail list, and where texture detail lands | `blender-detail-scan.md` |
| The checks after each part, finishing, the checklist, render traps over MCP | `blender-assembly-checks.md` |
| Checking the finished model by eye | `blender-visual-review.md` |

## The helper library

Every helper lives in `skills/dayz-model-tools/scripts/blender_helpers.py`, with its version in the docstring. At session start, read the file and run it whole through the Blender MCP; never paste single functions again, or the copies drift apart. A new helper joins the library only after it passes a test in Blender. The library is tested on Blender 5.1.

## Build it or generate it

This method covers parametric hard surface work: anything defined by sizes, joints and repeated features (furniture, machines, crates, frames, pipes, electrical devices, weapons). Organic or densely decorated shapes (statues, creatures, sculpted surfaces) are expensive to build by hand; send those to a generator first, then clean them up here (`ai-generation.md`). Decide before writing any geometry code. A half sculpted bmesh blob is the worst of both.

## Plan the joints first

Before any geometry, write a connection map of every joint: the two parts, which face or edge of each meets the other, and the overlap, at least 5 mm. Put it as a comment block in the first code cell, before any `bpy` call.

```text
Connection Map:
  tabletop_bottom (Z=0.73) <-> leg_top (Z=0.74)     overlap: 0.01m on Z
  leg_bottom (Z=0.01)      <-> floor (Z=0.00)        sits on floor
  drawer_back              <-> desk_body_front        overlap: 0.01m on Y
```

## Plan the detail

The connection map makes the model hold together; it does not stop it shipping as bare boxes. A model with no detail features is not finished: nothing real has perfect 90 degree edges. Next to the map, write a detail list: for each visible part, the features the real object has, the technique for each, and its rough size. Work from the reference photo, not from the primitive.

```text
Detail List:
  housing      edge chamfer        bevel 3mm/2seg      all exterior edges
  housing      side vent recess    inset+sink          0.12 x 0.06m, depth 5mm
  housing      corner bolts        place_copies        4 per corner plate
  front panel  panel line          inset+sink          2mm wide, 1mm deep
  frame        cable run           make_cable r=6mm    junction box to motor
  grip         compound shape      loft_profile        palm swell + taper
  grip         stippling           bake                normal map, not geometry
```

A model below these floors is not done:

- Every exterior edge of every visible part gets a bevel, background parts included. Unbevelled edges read as computer graphics at any distance.
- A main object carries at least 3 kinds of detail feature (for example bevel, recess and hardware). With fewer, go back to the reference before coding.
- Budget by LOD: the full list on LOD0, then drop hardware and recesses step by step on lower LODs. Vertex budgets are in `lods.md`, "Limits".
- Fine surface detail (knurling, threads, stippling, stamped text) goes to the bake, never to LOD0 geometry.

Get a reference image before you start; the visual review compares against it later, and a list written from memory gives generic detail. A list written from one glance misses the small marks that give the object its identity, so scan the reference zone by zone (`blender-detail-scan.md`).

## Geometry rules

**Make cubes with `size=2`.** A cube with `size=S` has vertices at `S/2` either side, so after `scale=K` the half extent is `K * S/2`. With `size=2` the half extent equals `K` and the factor of two disappears. Cylinders and spheres take `radius`, which is already the real radius.

```python
# right: size=2, scale is the half extent
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0.75))
obj.scale = (0.60, 0.30, 0.02)   # 1.2 m wide, 0.6 m deep, 0.04 m tall

# wrong: size=1, scale read as the full extent
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.75))
obj.scale = (0.60, 0.30, 0.02)   # only 0.6 m wide
```

**Never rotate a cylinder into place.** For anything that spans from one point to another (legs, beams, axles, struts, rails), build it from explicit vertex positions with `make_beam(name, start, end, hw, hh)`. Skip it for parts already on a world axis (vertical posts, wheels, hubs). Round sections (pipes, cables, trigger guards) use `make_cable`; changing sections (grips, stocks) use `loft_profile`.

**Apply scale straight after setting it.** In a loop, `bpy.context.active_object` can point at another object by the end, so a late scale lands on the wrong mesh. Call `bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)` right after each scale assignment, inside the loop.

**Size spanning parts from their neighbours.** Never hard code a part that must reach between two others. Read both neighbours with `verify_bounds()` and compute the size from their real extents: `half_span = (b_b['x'][1] - b_a['x'][0]) / 2`. A guessed `0.28` is wrong as soon as a neighbour moves.

**Allow for subsurf shrinkage.** A subdivision surface pulls geometry in; a box from 0 to 0.30 m may reach only 0.26 m after level 2. Build 10 to 15% past the target (`build_to = target_reach * 1.13`) and check the result, or use a bevel modifier on structural parts, which smooths edges without shrinking.

**Bevel every exterior edge.** Bevels make most of the difference between a primitive and an object. Add an angle limited bevel to every visible part as the last step, after all booleans: `add_bevel(obj, width=0.003, segments=2, angle_deg=40)`; 2 to 4 mm reads right at prop scale. Apply it so decimation and export see real geometry. Scale must already be applied, or the width comes out uneven. Run `verify_mesh_integrity` afterwards.

**Recesses through bmesh.** Panel lines, vents, screens and recessed faces are an inset plus a sink: `panel_recess(obj, near_point, inset, depth)`. It picks the face by its world position, never by index, which changes with any earlier edit. For a raised panel, move along `+face.normal` instead. Chain two insets (frame, then sink) for vents.

**Repeated hardware.** Model one low poly bolt or rivet (8 segments is plenty) and place copies in an explicit loop with `place_copies(src, positions)`; it is easier to check than an Array modifier. Each copy overlaps its mount by at least 1 mm.

**Cables, pipes and hoses.** Never chain rotated cylinders. `make_cable(name, points, radius)` builds a bevelled Bezier curve through explicit points and converts it to mesh. Take the end points from `verify_bounds()` of the parts it joins, with at least 5 mm into each.

**Booleans.** Booleans break more meshes than anything else:

1. Apply scale on both operands first. A boolean on a live scale gives garbage intersections.
2. Let the cutter pass every surface it cuts by at least 1 mm. A flush cutter leaves coplanar faces, the first cause of slivers and open holes.
3. Use the `'EXACT'` solver.

`boolean_cut(target, cutter, op)` sets the EXACT solver and cleans up (`remove_doubles`, `dissolve_degenerate`); the caller applies scale and sizes the cutter. Run `verify_mesh_integrity` after every boolean, before building on top. On Blender 5.1 the EXACT solver handled an exactly flush, axis aligned cutter cleanly (same pocket and volume as the overshoot cut, clean counters, only the ngon layout differed), so a flush cut that passes the integrity check and the visual check is acceptable. Keep the 1 mm overshoot as the default for oblique cuts and float drift.

**Loft compound shapes.** Boxes and beams cannot make a pistol grip, a stock, a bottle or a handle. Sweep a 2D profile along a 3D path and scale it per section with `ellipse_profile(rx, ry, n)`, `rounded_rect_profile(hw, hh, r, seg)` and `loft_profile(name, profile, path, scales, close_caps)`. For a grip, sweep `rounded_rect_profile` down a slightly curved path with scales such as `[1.0, 1.05, 0.95, 0.9]` (palm swell, then taper), with the top ring at least 5 mm into the receiver. The helper recalculates normals, but duplicate path points still make zero area faces, so run `verify_mesh_integrity` after every loft. If it looks faceted, raise the profile's `n`.

## Fine detail goes to the bake

Knurling, stippling, threads, stamped text and fine seams blow the polygon budget as geometry and still look worse than a bake. Bake them into the `_nohq` normal map and multiply ambient occlusion into the `_co`:

1. Build the part twice from one script with two parameter sets: high (bevel segments 4 to 6, knurl and thread geometry, deep panel lines) and low (game budget, the geometry rules only). Never two scripts that drift apart.
2. Unwrap the low mesh. `smart_uv(obj)` works for a quick hard surface bake, but it shatters the mesh into islands of 2 to 4 faces that nobody can paint. For a DayZ visual asset, unwrap by logical sections into an atlas a person can read (`tools-uv-atlas.md`; the audit scripts are in `dayz-model-tools`). Islands need a margin or the bake bleeds.
3. Bake high to low with `bake_map(high, low, 'NORMAL', ...)` and `bake_map(high, low, 'AO', ...)` (Cycles, selected to active).

What goes wrong:

- A low mesh with no UVs is a hard error. Unwrap it first.
- High and low not in the same space, or a ray distance too short or too long, gives patchy maps. Set `max_ray_distance` a little above the largest gap between the surfaces, and use a cage for deep recesses. The default `ray=0.01` gave clean 1024 px normal and AO bakes at a gap of about 4 mm.
- Blender bakes tangent normals green up (OpenGL). DayZ's `_nohq` is green down (DirectX), so invert green (`G' = 255 - G`) on every Cycles bake before export. This was calibrated against a vanilla `_nohq`, not checked on `P:\`. A `.paa` `_nohq` stores one minus X in alpha and one minus the source alpha in red (DayZ Tools `Bin\ImageToPAA\TexConvert.cfg`, class `normalmap_hq`: `channelSwizzleA = "1-R"`, `channelSwizzleR = "1-A"`). That is not the usual DXT5nm layout, so recover X as one minus the stored alpha before auditing a converted map. The calibration is in `_shared/textures/normal-maps.md`.

The normal PNG then goes through `/dayz-pack-texture` to `_nohq.paa`, and the AO PNG becomes a multiply layer in the `_co`.
