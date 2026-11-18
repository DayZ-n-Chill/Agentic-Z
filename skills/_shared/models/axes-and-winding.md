# Axes and winding

How geometry from Blender, FBX, OBJ, glTF or a generator is mapped into DayZ space, which way faces must be wound in each LOD, and how to tell a correct export from an inside out or mirrored one.

Vanilla models on `P:\` are binarized and winding belongs to the MLOD source, so nothing here can be read off a vanilla file. The rules were measured in game on mod models and offline with the py3d in `scripts/tools/py3d`. The audit side is in `dayz-p3d-audit/references/winding-methodology.md`, `winding-diagnostics.md` and `winding-absolute-check.md`; the collision fault itself is section 1 of `dayz-p3d-audit/references/p3d-killers.md`.

## The map from Blender to DayZ

Blender is right handed with Z up. DayZ is left handed: X east, Y up, Z north, and vehicles face -Z. A map that keeps the shape between the two must be a reflection:

1. Map every point and every normal of every LOD through `(x,y,z)` to `(x,z,y)` (determinant -1).
2. Keep each face's vertex order. After the reflection it is already the MLOD order, with the cross product of the first two edges pointing into the solid.
3. Negate every normal. MLOD stores shading normals inward as well.

With py3d 1.8.0 or later, `py3d.blender_to_dayz(model)` does all three in one call, proxy triangles included. Call it once, before you add anything built directly in DayZ space (collision boxes made in code), which must not go through the map.

`P3D.transform(((1,0,0),(0,0,1),(0,1,0)))` maps points and normals and, because the determinant is negative, also reverses every face. Reverse them back and negate the normals and you have `blender_to_dayz`. `py3d.BLENDER_TO_DAYZ` is the old rotation `(x,y,z)` to `(x,z,-y)` (determinant +1), also named `py3d.ROT_X_NEG90`; never use it for this map.

One asymmetric model exported three ways and loaded in game:

| Export | In game |
|---|---|
| The reflection, face order kept, normals negated | Solid, text reads correctly |
| The rotation `(x,z,-y)`, faces reversed, normals negated | Solid but mirrored: text and logos read backwards |
| `P3D.transform(py3d.BLENDER_TO_DAYZ)` alone | Inside out and mirrored |

With the reflection, the Geometry, View Geometry and Fire Geometry components took `scene_raycast` hits in `geom`, `view` and `fire` from both sides; after the rotation alone they took none.

Proxy triangles drawn in Blender as py3d raw triangles and converted with the model get the same engine frames as `add_proxy(space="engine")` with the matching rotation, and render in the pose drawn in Blender. That settles the proxy frame, not a seated rider: only the identity crew frame is known to work in game, and a tilted one turned the rider left instead of leaning him forward (`proxy-frames.md`).

A rotation always mirrors a model that starts in Blender coordinates, and on a symmetric prop the mirror is invisible. Winding checks cannot see a mirror. Check chirality on an asymmetric feature (text, a logo, a one sided part) in game, or compare one side memory point with a vanilla model: vanilla weapons carry the ejection port point `nabojnicestart` at +Z.

## What to do for each source

| Source | What to do |
|---|---|
| Geometry built or edited in Blender, or FBX through Blender | The map above |
| GLB or glTF imported through Blender | The map above. glTF front faces are counter clockwise, as Blender's are, and the importer turns Y up into Z up with a rotation that keeps them so. Reversing faces after the reflection turned them outward and rendered see-through on an imported car; keeping the order rendered solid on that car and on an imported rifle |
| A glTF node with a mirrored global transform, through Blender | It arrives as an object with negative scale. Not measured: read that part's winding in the exported MLOD (signed volume per closed shell, `check_dayz_winding.py` of `/dayz-model-tools`, `tools-winding-gate.md`) before trusting it |
| glTF read without Blender | It is Y up. Bake each node's global transform into its mesh, reverse the faces of every instance whose global transform has a negative determinant, then derive a reflection from the asset's own frame and keep the order through it. Not measured in game |
| OBJ | It is in the frame its exporter wrote. Exported from Blender with forward Y and up Z it holds Blender coordinates and takes the map above (`blender-headless-export.md`). Blender's default axes write `(x, z, -y)`; from those the map is `(x,y,z)` to `(x,y,-z)`, which writes the same bytes on the tested model |
| A generated mesh reworked in Blender | Blender geometry by then: the map above, whatever format the generator wrote. A giant infected built this way read correctly with the reflection and was mirrored with the rotation |
| A vehicle from another game | Its own measured profile: `_shared/vehicles/README.md`. A ripped asset in a `.glb` can carry its game's frame rather than glTF's, so the measured transform decides whether its winding is kept or flipped |

Reverse every visual face only for a source that was measured to need it: an in-game comparison against the variant with every visual face flipped, plus a chirality check. Never reverse proxy triangles on their own; their shape carries the attachment frame (`proxy-frames.md`).

## Collision LODs

Every non proxy face of every `ComponentNN` in Geometry, View Geometry and Fire Geometry must have its cross product pointing into its component. Decide it per component, never by matching the visual LOD.

- **Before you check.** Every non proxy face belongs to a `ComponentNN` selection, every component is closed and convex, and no face is degenerate. Short of that the check proves nothing.
- **The check.** For each face, `outward = face_centroid - component_centroid` and `n = normalize(cross(v1-v0, v2-v0))`. `dot(outward, n) < 0` is right. A face above zero is wound outward; the engine's view and fire raycasts treat it as a back face and miss it. Read every face, not most.
- **Signed volume** gives the same answer per closed component: `sum(dot(v0, cross(v1, v2))) / 6` is negative in DayZ's convention. A generator that writes a box should measure it and stop unless the volume is negative.
- **The fix.** Reverse only the faces that read outward, set their stored normals as `p3d-killers.md` section 1 says, and leave every healthy component, the proxy triangles and the visual LOD alone. Reversing a whole LOD moves the fault onto its healthy components.
- **Symptoms**, all at once: bullets pass through, a hologram drops to the ground when stacking, nothing can be placed on top, and the action cursor does not find the object. Walking through does not point at winding: 2 m boxes wound outward still stopped the player, the same box with no `ComponentNN` selection let the player through, and a 0.49 m kit let the player through with either winding.

`/dayz-p3d-audit` passes on py3d's `ERR_WINDING_INVERTED` when a collision LOD and the visual LOD are uniform and opposite. Treat it as a reason to run the per component check, not as a verdict: it also fires on healthy collision LODs under an inside out visual LOD, or under a room meant to be seen from inside.

## Visual LODs

- A per face census of `dot(cross(v1-v0, v2-v0), mean_stored_normal)` says whether the stored normals agree with the winding, not which side renders. A reflection export stores both inward and reads about 100% agreement; one shell reversed together with its normals still reads 100%.
- Take the direction from the signed volume of each closed shell, never from the sum over the LOD: negative for a solid seen from outside, positive for a room seen from inside. Open sheets and double sided parts need a visibility test instead (below).
- Never compare census ratios across ODOL, MLOD converted back from ODOL, raw MLOD from another tool and vanilla references: the stored normal convention differs by origin. An older pipeline stored normals outward against an inward winding, so its threshold (95% negative means solid) reads a correct reflection export as inverted.
- A visual LOD wound the wrong way shows the texture on the inside, looks transparent from outside, or renders solid black.
- Normals stored outward render solid but light the surface inverted.
- Decimate in collapse mode can zero or flip corner normals, which py3d reports as `WARN_WINDING_NORMAL_MISMATCH`. Where a corner normal is near zero or points against its face, use the face's geometric normal.

The final word on a visual LOD is an in-game comparison between the candidate and a variant with every visual face flipped, plus a chirality check, since both variants share the same map.

## Open geometry and see-through faults

- Before trusting an orientation metric over the whole model, move the model several metres and measure again. If the verdict changes, the metric does not work on that geometry.
- For open sheets, render several directions with and without back face culling and compare the nearest surface with the drawn one. Count a defect only when the depth gap passes a calibrated distance, report it in bands (under 2 mm, 2 mm to 2 cm, 2 to 10 cm, over 10 cm), and calibrate on a known good and a known inverted control first.
- A tolerance for coincident twin faces must be smaller than the thinnest sheet in the model. Measure the gap before calling a pair intentional double sided geometry.
- Flip a suspect component and measure again. If the defect goes, it was winding; if it moves to the other side, the sheet needs two sided geometry. Flipping a two sided sheet only moves the hole: flipping 313 faces of a motorbike's tank lip made the front lip vanish from above.
- The seal that never hides what was visible is an inverted twin with its own UVs and normals, in the same animation selections. Twins cost vertices against the vertex budget (`lods.md`, "Limits"). For a real hole, close it and back it with a dark inset sheet.
- To see what the game draws, render with Blender Workbench and back face culling on; it drops back faces before depth as the engine does. Use it to find see-through pixels, never to decide the winding sign (`_shared/vehicles/visual-gates-and-winding.md`). Cycles with a transparent back face also skips the coincident twin, and red overlays per face come out mottled on double layers; neither shows what the player sees.
- On a model with a pilot view LOD (resolution 1100), a seal for what only the seat sees goes in that LOD alone: on a motorbike, closures and twins added to LOD0 drew black slivers from outside.
- After any mesh fix, compare before and after from the viewpoint the defect was reported from, not only the face counts.

Catching a flip in Blender before export is in `blender-winding-flips.md`.

## A vanilla model to compare against

Read your binarized model and a vanilla one through the same reader: the collision boxes of `P:\DZ\gear\camping\wooden_case.p3d`, or the tread band of a vanilla wheel. Require readable text in game. The ODOL versions to expect are in `dayz-1-30-models.md`.
