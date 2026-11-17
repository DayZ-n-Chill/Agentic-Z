# Winding-flip detection in Blender

How to catch a reversed face winding in Blender before an export to an engine that culls by winding, why a lit render hides it, and the measurements that show a vision model cannot answer the question either. Everything here was measured in Blender and in game on the dates given; none of it can be checked against files on `P:\`. The final authority on an exported `.p3d` stays `/dayz-p3d-audit` and an in-game look.

## Why a lit render cannot show it

Blender's standard shading lights a surface by the declared normals of its vertices. The winding of a triangle (the order of its vertices) does not affect the render unless specific conditions are switched on. So a model with reversed winding and correct normals renders well in Blender and badly in any engine that culls by winding: DayZ, Arma 3, Arma Reforger, or Unity with back-face culling. Declared or custom split normals mask the flip.

- In Blender: silhouettes, shadows and color all look right.
- In game: the front faces are invisible and the back faces are textured, so the texture appears on the inside of the object.

**Reproduced case (a car imported from glTF, 2026-06-24).** The car's shell passed all 4 views of this skill. In game only the back faces of the body were textured. Cause: the glTF to DayZ transform had det = -1 (a mirror), and `reverse_winding=True` was chosen to compensate and leave the normals pointing outward, but the winding ended up reversed. DayZ culls by winding, so the front faces vanished.

## Two mechanisms that read the winding

Both read the orientation derived from the winding and ignore the declared normals.

1. **Face Orientation overlay** (set up under "Setup that keeps captures honest" in `SKILL.md`). From outside the model, any red face has flipped winding. Take a screenshot of the 4 standard angles with the overlay on. A uniformly red exterior means the whole mesh is flipped.
2. **A second render with backface culling.** `vr_capture` renders with Workbench, which ignores the material flag `mat.use_backface_culling`; turn culling on in the scene's Workbench shading instead, render the same 4 angles again, and compare each with its original render using `vr_delta.py`, one angle at a time. Faces that vanish (holes, or a silhouette IoU under 0.95 on any view) had flipped winding. The verdict is `FLIPPED_LIKELY`: do not approve the export.

```python
scene = bpy.context.scene
scene.display.shading.show_backface_culling = True   # Workbench: the setting vr_capture's engine reads
# ... render the 4 angles again with vr_capture(..., tag="culled"), then set it back:
scene.display.shading.show_backface_culling = False
```

If you render the pair with EEVEE instead, set `mat.use_backface_culling = True` on every material and render both images of the pair with EEVEE, so the only difference between them is the culling.

A render-side alternative to the overlay is a shader that colors by the sign of `dot(geometric_normal, view_direction)`: back faces red, front faces green.

Record the result with the review notes, for example:

```json
{"winding_check": {"ran": true, "delta_silhouette_pct": 0.0, "verdict": "OK"}}
```

with `"verdict": "FLIPPED_LIKELY"`, a failed check, when the silhouette changes by more than 5% (IoU under 0.95) after the culled render.

## Do not verify with a normals recalculation

Do not "verify" a suspected flip by running `normals_make_consistent` and rendering again. The recalculation rewrites the winding itself, so the new render comes back clean and the check gives a false negative. Recalculation is a repair tool. The repair decision for a DayZ export belongs to the import-transform rules of `dayz-model-pipeline` (its Rule 12): the Blender to DayZ map is the det = -1 reflection `(x,y,z) -> (x,z,y)` with the face order kept and the normals negated; the older `(x,z,-y)` rotation renders solid but mirrored.

## When to run

- Any import from glTF, FBX or OBJ, where an axis flip (a transform with det = -1) is possible.
- Any pipeline with a configurable `reverse_winding`.
- Any build for an engine that culls by winding: DayZ, Arma, Arma Reforger and other Bohemia engines.

It does not apply to cinematic renders in Blender, or to models that will never be culled.

This is a free early warning that saves an in-game cycle. Absolute authority on the exported `.p3d` stays the topology check of `/dayz-p3d-audit`.

## Measured: the defect is not in the pixels (2026-08-21)

The guardrail was reproduced from the other direction, on a probe built so that its winding is reversed by construction: the same object, camera and shading, with only the winding different.

| Capture | Faces reversed | Pixels changed |
|---|---|---|
| This skill's own settings (Workbench with `show_cavity`, culling off) | 62 (face 0 normal dot -1.0001) | 0.00% |
| The same, with backface culling on | 62 | 36.92% |

Two variants at different severities came out byte identical to each other. The defect is absent from the pixels, so no reviewer can answer from a lit render.

**Consequence for `checks_hardsurface.json`.** Its fifth entry (Q5), "Are there any black, inside-out or wrongly shaded faces visible?", asks a vision model the one question a render cannot answer, over captures without culling. It carries `skip` and is routed to the culling comparison above; it is never sent to the vision model or scored by it. A gate that cannot go red for the cause it targets is decoration.

**It is not a limit of local models.** Given the culled pair, where the flip changes 36.92% of the image and the inside of the cylinder is plainly visible, `ornith-1.5:9b`, `qwen3-vl:30b` and `muse-glimmer:30b` each answered NO on both variants across 3 seeds: 0 of 3 separation for all three. Each justified it fluently ("the visible faces are the front cap and the exterior side of the cylinder"), about a render where the front cap is culled away and the interior is what is on screen. The failure is a confident green, not a refusal.
