# Axes and winding

How geometry from Blender, FBX, OBJ, glTF or an AI generator is mapped into DayZ space, which way faces must be wound in each LOD, and how to tell a correct export from an inside out or mirrored one.

Nothing here can be checked on `P:\`: vanilla models are binarized, and winding is a property of the MLOD source. The rules come from in-game tests on DayZDiag 1.29 and 1.30 with mod models, and from offline measurements with the py3d in `scripts/tools/py3d`. The audit side is in `dayz-p3d-audit/references/winding-methodology.md`, `winding-diagnostics.md` and `winding-absolute-check.md`, and the collision fault itself is killer 1 in `dayz-p3d-audit/references/p3d-killers.md`.

## The rule

Blender is right handed with Z up. DayZ is left handed: X east, Y up, Z north, and vehicles face -Z. A map that keeps the shape between them must be a reflection:

1. Map every point and every normal of every LOD through `(x,y,z) -> (x,z,y)` (determinant -1).
2. Keep each face's vertex order. After the reflection it is already the MLOD order, with the cross product of the first two edges pointing into the solid.
3. Negate every normal. MLOD stores shading normals inward too.

With py3d 1.8.0 or later, `py3d.blender_to_dayz(model)` does all three in one call, proxy triangles included. Call it once, before adding anything built directly in DayZ space (collision boxes made in code), which must not go through the map.

`P3D.transform(((1,0,0),(0,0,1),(0,1,0)))` maps points and normals and, because the determinant is negative, also reverses every face. Reverse them back and negate the normals and the result is the same as `blender_to_dayz`. `py3d.BLENDER_TO_DAYZ` is the old rotation `(x,y,z) -> (x,z,-y)` (determinant +1), kept as `py3d.ROT_X_NEG90`; do not use it for this map.

### What the three exports did in game

One chiral model exported three ways, binarized and loaded in DayZDiag 1.29:

| Export | In game |
|---|---|
| The reflection above, face order kept, normals negated | Solid, text reads correctly |
| The rotation `(x,z,-y)` with faces reversed and normals negated | Solid, but mirrored: text and logos read backwards |
| `P3D.transform(py3d.BLENDER_TO_DAYZ)` alone | Inside out and mirrored |

With the reflection, the Geometry, View Geometry and Fire Geometry components registered `scene_raycast` hits in `geom`, `view` and `fire` from both sides; after the rotation alone they registered none.

A rotation always mirrors a model that starts in Blender coordinates. On a symmetric prop the mirror is invisible, which is how the rotation recipe passed offline gates on five symmetric models before an asymmetric one showed it. **Winding checks cannot see a mirror.** Check chirality on an asymmetric feature (text, a logo, a one sided part) in game, or compare one lateral memory point against a vanilla model: vanilla weapons carry the ejection port point `nabojnicestart` at +Z.

## Per source

| Source | What to do |
|---|---|
| Geometry built or edited in Blender, FBX through Blender | The rule above |
| GLB or glTF imported through Blender | The rule above. glTF front faces are counter clockwise by spec, as Blender's are, and Blender's glTF importer turns Y up into Z up with a rotation that keeps them so. Reversing the faces after the reflection turns them outward, which rendered see-through on an imported car; keeping the order rendered solid on that car and on an imported rifle |
| A glTF node with a mirrored global transform, brought through Blender | It arrives as an object with negative scale. This case was not measured: read that part's winding in the exported MLOD (signed volume per closed shell, `check_dayz_winding.py` of `/dayz-model-tools`, `tools-winding-gate.md`) before trusting it |
| glTF read without Blender | It is Y up. Bake each node's global transform into its mesh, reverse the faces of every instance whose global transform has a negative determinant (glTF winds those clockwise), then derive a reflection from the asset's own frame and keep the order through it. Not measured in game |
| OBJ | It is in the frame its exporter wrote. Exported from Blender with forward Y and up Z it holds Blender's own coordinates and takes the rule above (`blender-headless.md`, "Export"). Blender's default axes write `(x, z, -y)`; from those the map is `(x,y,z) -> (x,y,-z)`, which writes the same bytes as the rule on the tested model |
| AI generated mesh reworked in Blender (retopology, UVs, bake) | Blender geometry by then: the rule above, whatever format the generator wrote. A giant infected built this way read correctly in game with the reflection and was mirrored with the rotation recipe it first shipped with |
| Imported vehicle from another game | Its own measured profile, not this one: `_shared/vehicles/README.md` and the vehicle import material. A ripped game asset in a `.glb` can carry its game's frame rather than the glTF spec's, so the measured transform and the source lineage decide whether its winding is kept or flipped |

Reverse the vertex order of every visual face only for a source whose own lineage was measured to need it: an in-game A/B against the variant with every visual face flipped, plus a chirality check. Never reverse proxy triangles on their own account; their shape carries the attachment frame (`proxy-frames.md`).

## Collision LODs

Every non proxy face of every `ComponentNN` in Geometry, View Geometry and Fire Geometry must have its cross product pointing into its component. Decide it per component, never by matching the Visual LOD:

- **Prerequisites.** Every non proxy face belongs to a `ComponentNN` selection, every component is closed and convex, and no face is degenerate. Short of that the check confirms nothing.
- **The check.** For each face, `outward = face_centroid - component_centroid` and `n = normalize(cross(v1-v0, v2-v0))`. `dot(outward, n) < 0` is right. A face reading `> 0` is wound outward, and the engine's view and fire raycasts treat it as a back face and miss it. Read every face, not most.
- **Signed volume** gives the same answer per closed component: `sum(dot(v0, cross(v1, v2))) / 6` is negative in the DayZ convention. A generator that writes a box should measure it and fail closed unless the volume is negative.
- **Fix.** Reverse only the faces that read outward, set their stored normals as killer 1's fix says, and leave every healthy component, the proxy triangles and the Visual LOD alone. Reversing a whole LOD moves the fault onto any healthy component in it.
- **Symptoms.** All three at once: bullets pass through, a hologram falls to the ground when stacking, nothing can be placed on top, and the action cursor does not find the object. A walk-through does not point at winding: 2 m boxes wound outward still stopped the player in game, the same box with no `ComponentNN` selection let the player through, and a 0.49 m kit let the player through with either winding.

`/dayz-p3d-audit` relays py3d's `ERR_WINDING_INVERTED` when a collision LOD and the Visual LOD are uniform and opposite. It is a trigger for the per component check, not a verdict: it also fires on healthy collision LODs under an inside out Visual LOD, or under a room meant to be seen from inside.

## Visual LODs

- A census of `dot(cross(v1-v0, v2-v0), mean_stored_normal)` per face says whether the stored normals agree with the winding, not which side renders. A reflection export stores both inward, so it reads about 100 % agreement; one shell reversed together with its normals still reads 100 %.
- The direction comes from the signed volume by winding of each closed shell, never from the sum over the LOD: negative for a solid seen from outside, positive for a room seen from inside. Open sheets and double sided parts need a visibility test instead (below).
- Do not compare census ratios across ODOL, MLOD converted back from ODOL, raw MLOD from another tool and vanilla references: the stored normal convention differs by origin. One older pipeline stored normals outward against an inward winding, so its threshold (95 % negative means solid) reads a correct reflection export as inverted.
- Normals stored outward render solid but light the surface inverted.
- Decimate in collapse mode can zero or invert corner normals, which py3d reports as `WARN_WINDING_NORMAL_MISMATCH`. Where a corner normal is about zero or points against its face, use the face's geometric normal.

The final verdict on a visual LOD stays an in-game A/B between the candidate and a variant with every visual face flipped, plus a chirality check, since both variants of that A/B share the same map.

## Open geometry and see-through faults

- Before trusting an aggregate orientation metric, move the model several metres and measure again. A changed verdict means the metric does not work on that geometry.
- For open sheets, render a battery of directions with and without back face culling and compare the nearest surface with the drawn one. Count a defect only when the depth gap passes a calibrated distance; report it in bands (under 2 mm, 2 mm to 2 cm, 2 to 10 cm, over 10 cm), and calibrate a known good and a known inverted control first.
- A tolerance for coincident twin faces must be smaller than the thinnest sheet in the model. Measure the separation before calling a pair intentional double sided geometry.
- Flip a suspect component and measure again. If the defect goes away it was winding; if it moves to the other side, the sheet needs two sided geometry. Flipping a two sided sheet only moves the hole: 313 faces of a tank lip flipped on a motorbike made the front lip vanish from above.
- The seal that never removes what was visible is an inverted twin with its own UVs and normals, in the same animation selections. Twins cost vertices against the resolved vertex budget (`lods.md`, "Limits"). For a real hole, close it and back it with a dark inset sheet.
- To see what the game draws, render with Blender Workbench and back face culling on; it discards back faces before depth as the engine does. Use it to find see-through pixels, not to decide the winding sign (`_shared/vehicles/visual-gates-and-winding.md`). Cycles with a transparent back face also skips the coincident twin, and red overlays per face come out mottled on double layers: neither shows what the player sees.
- On a model with a pilot view LOD (resolution 1100), a seal for what only the seat sees, twin or closure, goes in that LOD alone: on a motorbike, closures and twins added to LOD0 drew black slivers seen from outside.
- After any mesh fix, compare before and after from the viewpoint the defect was reported from, not only the face counts.

How to catch a flip in Blender before export is in `blender-visual-review.md`, "Winding flips".

## A vanilla model to compare against

Compare your binarized model with a vanilla one through the same reader, for example the collision boxes of `P:\DZ\gear\camping\wooden_case.p3d` or the tread band of a vanilla wheel, and require readable text in game. The ODOL versions to expect are in `dayz-1-30-models.md`.
