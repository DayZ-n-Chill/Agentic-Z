# Checking a Blender build

What to check after each part of a model built in Blender over MCP, how to finish the scene, the rules that catch the rarer faults, and the two render traps over MCP. The planning and geometry rules are in `blender-assembly.md`; every helper named here is in `skills/dayz-model-tools/scripts/blender_helpers.py`. This is Blender tool behaviour, not a fact about the game.

## After every part

Check each part as soon as it exists. A fault caught now is far cheaper than an exploded or broken model found later.

| Helper | What it proves | When |
|---|---|---|
| `verify_bounds(name)` | Prints and returns the part's world bounding box | After every part |
| `verify_overlap(name_a, name_b, axis, min_overlap)` | The two parts really overlap on that axis | For every joint in the connection map, before the next part |
| `verify_mesh_integrity(name, require_closed, allow_ngons)` | The mesh itself is sound; `verify_bounds` happily passes a broken one | After every boolean, modifier apply and loft, and once per part when finishing |

Reading the integrity result:

- `non_manifold_edges > 0`: an edge with no face, or shared by three or more faces; almost always a boolean leftover or two parts joined without merging. Fix the operation that caused it; do not patch around it.
- `duplicate_verts > 0`: run `remove_doubles` on the real mesh (the check works on a throwaway copy).
- `boundary_edges > 0` with `require_closed=True`: a hole. Collision geometry must be closed. For a visual mesh with intended openings, call it with `require_closed=False` and say why in a comment in the build script.
- `ngons`: they shade and decimate badly on curved surfaces, so triangulate or inset again; on large flat faces they are fine, which is why they only warn.

A failed check means stop and fix it before the next part; broken geometry compounds.

For complex parts (lofts, parts with many booleans), take one quick capture of the part alone before building on top (`vr_capture`, `blender-visual-review.md`). Numbers check topology; only eyes check intent.

## Moving parts

- Check the fit over the whole travel and the whole length, not at one section. Measured offline on one model: standing leaves checked only at their widest section stuck out of the rock by up to 0.96 m elsewhere, and a platform checked only at the top touched the lining at the far end by up to 1.1 m.
- Sampling once per frame skips short collisions. Folding a 2.46 m leaf hinged on its top edge brings each lower corner 4.7 mm closer in the first few degrees, a contact shorter than one frame. Sweep the angles by hand with a fine step near 0 degrees, with the actions unhooked so the depsgraph does not override them. Clearance in presentation renders is in `blender-review-checklist.md`, "Animated parts".

## Finishing the scene

Call `finalize(name)` on each part right after creating it, while it is still the active object. It renames and transforms `bpy.context.active_object` (transforms applied, origin set, smooth shading) and does not look the name up, so never loop over names expecting it to; check name against bounding box after renaming. When every part is built, run `audit_all()` to confirm rotation `(0,0,0)` and scale `(1,1,1)` across the scene.

## Rarer faults

- **Organic meshes.** Never carve open or non watertight organic meshes with booleans; extrude the boundary loop or bridge by hand. If you must, cut between closed solids and check raycast, boundary and non manifold edges before going on.
- **Stale matrices.** After changing `location`, `rotation` or `scale` through the API, call `bpy.context.view_layer.update()` before reading `matrix_world`. Put the update in the helper that reads, and test with values on every axis.
- **Closed tubes.** Turn on `use_fill_caps`, convert to mesh and weld with `remove_doubles(1e-5)`. Keep `require_closed`; never relax it for boundary edges.
- **`transform_apply` arguments.** Always pass `location`, `rotation` and `scale` explicitly. Create copy sources at the world origin before baking transforms.
- **Flat curved pieces.** Build a 2.5D loft with a fixed width on a world axis and the depth taken from the flat tangent. Run `remove_doubles` and `dissolve_degenerate` after each loft.
- **Hollow pieces.** Size each cutter to cross only the target wall, passing into the hollow without reaching the far wall. Run the integrity check after each boolean.
- **Compound cutters.** Keep the parts of each cutter separate, and cut circles and slots in separate passes. Fail the check when a mesh ends with zero vertices, and flag it when successive operations leave identical signatures.
- **Recesses on caps and ngons.** Never use `panel_recess` on loft caps or ngons; use an oriented boolean or leave the detail to the bake. Place cutters from the path, scales and profile, never by sampling bands of the resulting mesh.

## Checklist for every model

1. Route first: parametric hard surface stays here; organic or sculpted goes to `ai-generation.md`.
2. Connection map of every joint, before any `bpy` code.
3. Detail list scanned by zone (`grid-3x3` or `component-zones`), at or above the count floor for its complexity, each row mapped to a technique or a texture channel, at least 3 feature kinds on a main object, reference image in hand.
4. `size=2` for every cube, so scale is the half extent.
5. `make_beam()`, `make_cable()` and `loft_profile()` for spans and compound shapes; no Euler rotations.
6. `transform_apply(location=False, rotation=False, scale=True)` straight after every scale, inside the loop.
7. Spanning sizes from `verify_bounds()`, never guessed.
8. Booleans with scale applied, a 1 mm overshoot, EXACT, cleanup and the integrity check.
9. A bevel on every visible part, angle limited, applied, after all booleans.
10. Fine detail to the bake: high and low from one script, the low mesh unwrapped (by logical sections for a DayZ visual asset, `smart_uv` only where nobody paints the atlas), then `bake_map` for NORMAL and AO.
11. `verify_bounds()` and `verify_overlap()` after every part and joint.
12. `verify_mesh_integrity()` after every boolean, modifier apply and loft, and when finishing.
13. One `vr_capture` of each complex part before building on top.
14. `finalize()` and `audit_all()`.
15. Hand off to the visual review (`blender-visual-review.md`).

## Render traps over MCP

Two traps make a render over the Blender MCP disagree with the mesh data.

**The render keeps the mesh from before an in-place edit.** `obj.data.transform()` and other low level writes update the data (reading the vertices shows it), but the render depsgraph keeps a frozen copy, and every `render.render()` shows the old mesh. `data.update()`, `update_tag()`, `view_layer.update()` and `evaluated_depsgraph_get().update()` do not clear it, and `mesh.copy()` inherits it; new objects render fine. Write the edited geometry to a new datablock with `bm.to_mesh(new_mesh)`, link it on a new object, and remove the old object and mesh. Otherwise the renders contradict your measurements; on one weapon model this nearly got a correct orientation called wrong. To tell, add spheres at known coordinates and render: spheres in the right place next to an old mesh means this cache, not your maths.

**The scene changes between calls.** `bpy.context.scene` can quietly switch back to the user's scene between MCP calls. Pin `bpy.context.window.scene` and pass `scene=` to `render.render()` on every call, or you render the wrong scene.
