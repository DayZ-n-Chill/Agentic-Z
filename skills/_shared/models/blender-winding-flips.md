# Winding flips in Blender

Why a Blender render cannot judge DayZ face winding, the two Blender checks that still catch a reversed winding before export, and why a vision model cannot answer the question either. Measured in Blender and in game on mod models; none of it can be checked against files on `P:\`, where vanilla models are binarized. The final word on an exported `.p3d` is `/dayz-p3d-audit` and a look in game. The review loop this belongs to is in `blender-visual-review.md`.

## A render cannot judge winding

Blender, like a Three.js viewer, renders right handed; DayZ culls left handed. A model that looks solid in Blender can render inside out in game: a render once was used to declare the normals right, and the exterior turned out transparent in game. Why a right handed check misleads is in `skills/dayz-p3d-audit/references/winding-methodology.md`.

- Never conclude from a Blender render or screenshot that DayZ winding or normal direction is right. `/dayz-p3d-audit` (its edge pair topology check) and the game decide it.
- The only visual signal that means anything is relative: the model winds the same way as a vanilla model imported beside it.
- The Blender to DayZ map is the reflection `(x,y,z)` to `(x,z,y)` with normals negated (`axes-and-winding.md`). A render cannot judge the result either: the older rotation recipe renders solid in Blender and in DayZ and is still mirrored. Check chirality in game on text or a one sided part.

Everything else (orientation, proportion, scale, exploded parts, ride height, likeness) a render judges well. Winding is the one thing it cannot.

Blender's normal shading lights a surface by its vertex normals, and a triangle's vertex order does not change the render unless culling is on. So a model with reversed winding and correct normals looks right in Blender, with good outline, shadows and colour, and in an engine that culls by winding (DayZ, Arma 3, Arma Reforger, Unity with back face culling) its front faces vanish and the texture shows on the inside. Declared or custom split normals hide the flip. A car imported from glTF showed this: its shell passed all four views of the review, and in game only the back faces of the body were textured. The glTF to DayZ transform was a mirror, `reverse_winding=True` was chosen to keep the normals outward, and the winding ended up reversed.

## Two checks that read the winding

Both read the orientation that comes from the vertex order and ignore the declared normals. Run them on any import from glTF, FBX or OBJ (where a mirroring transform is possible), on any pipeline with a `reverse_winding` setting, and on any build for an engine that culls by winding. They do not apply to cinematic renders.

1. **Face Orientation overlay** (`blender-visual-review.md`, "Setting up an honest view"). Seen from outside the model, any red face has flipped winding. Screenshot the four standard angles with the overlay on; an all red exterior means the whole mesh is flipped.
2. **A second render with back face culling.** `vr_capture` renders with Workbench, which ignores the material flag `mat.use_backface_culling`, so turn culling on in the scene's Workbench shading, render the same four angles again, and compare each with its first render using `vr_delta.py`, one angle at a time. Faces that vanish (holes, or a silhouette IoU under 0.95 on any view) had flipped winding: the verdict is `FLIPPED_LIKELY`, and the export is not approved.

```python
scene = bpy.context.scene
scene.display.shading.show_backface_culling = True   # the setting Workbench reads
# render the four angles again with vr_capture(..., tag="culled"), then:
scene.display.shading.show_backface_culling = False
```

If you render the pair with EEVEE instead, set `mat.use_backface_culling = True` on every material and render both images with EEVEE, so culling is the only difference. A shader that colours by the sign of `dot(geometric_normal, view_direction)` (back faces red, front green) is another way to see it in a render.

Record the result with the review notes, `"verdict": "FLIPPED_LIKELY"` when the silhouette changes by more than 5%:

```json
{"winding_check": {"ran": true, "delta_silhouette_pct": 0.0, "verdict": "OK"}}
```

Never "check" a suspected flip by running `normals_make_consistent` and rendering again: it rewrites the winding, so the new render comes back clean and hides the fault. It is a repair tool, and the repair for a DayZ export follows the map in `axes-and-winding.md`.

## The fault is not in the pixels

A test object built with reversed winding, rendered with the same object, camera and shading as a correct one:

| Capture | Faces reversed | Pixels changed |
|---|---|---|
| The review's own settings (Workbench with `show_cavity`, culling off) | 62 | 0.00% |
| The same with back face culling on | 62 | 36.92% |

Two variants of different severity came out byte identical. The fault is not in a lit render's pixels, so no reviewer can answer from one. That is why the checklist question "Are there any black, inside-out or wrongly shaded faces visible?" in `checks_hardsurface.json` carries `skip` and is routed to the culling comparison above; it is never sent to a vision model.

It is not a limit of small models either. Given the culled pair, where the flip changes 36.92% of the image and the inside of the cylinder is plainly on screen, three local vision models of 9 to 30 billion parameters each answered "no fault" on both variants over 3 seeds, and each explained it fluently ("the visible faces are the front cap and the exterior side of the cylinder") about a render where the front cap was culled away. The failure is a confident pass, not a refusal.
