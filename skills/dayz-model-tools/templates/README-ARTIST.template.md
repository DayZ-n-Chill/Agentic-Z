# <Garment>: corrected worn models (delivery for fine-tuning)

Date: <date>. Worn models of the <Garment> mod, with the structural corrections that make the garment work in game (checked in DayZ <version>). Fine-tuning the fit (<areas still to fit, for example arms, legs, abdominal protector>) is still open: that is the task of this delivery.

Fill in every `<...>` value before sending this file. The example values come from the body armor this template was first written for.

## Contents

- `<garment>_m.fbx` / `<garment>_f.fbx`: **for working in Blender, Max or Maya** (geometry, UVs and the skinning weights as vertex groups on an armature)
- `<garment>_co.png`: diffuse texture (the FBX references it)
- `<garment>_m.p3d` / `<garment>_f.p3d`: the same models in MLOD (editable in Object Builder, if that route is preferred)
- `model.cfg`: the correct model.cfg for binarizing these models

## The FBX

- **Axes**: standard Blender, Z up. The character stands facing -Y (Blender's Front view) with the anatomical left at +X: the same frame as the official DayZ rig. Units: meters. Origin at the character's feet. (Packages made before 2026-10-01 faced +Y and were a mirror image; return those the way they were delivered.)
- **The armature (<N> bones) is a weight carrier, not the game rig**: its bones sit at the centroid of each region only so the FBX keeps the vertex groups. It is not for animating. What matters are the groups: <group list, lowercase; for example leftarm, rightarm, leftforearm, rightforearm, leftupleg, rightupleg, neck, pelvis, spine, spine3>.
- **Golden rule**: move, rotate or sculpt vertices to fit the plates to the body. Do not rename vertex groups and do not empty them. Re-weighting is allowed if you want better deformation (see "Optional improvement"), as long as each vertex still sums to 1.0 and the group names stay the same.
- If the topology is kept (same vertex count and order), the model goes back into the mod automatically. If you retopologize, still deliver the FBX with its groups and we rebuild it.

## What was already corrected (do not undo)

1. **Orientation**: the original mesh was modeled facing backwards (180 degrees). These models are already in the canonical DayZ clothing frame (in the .p3d: -Z = front, +X = anatomical left, Y up, origin at the feet; the FBX is already translated to Blender axes). If the model is re-exported from an old source without rotating it, the bug returns.
2. **Skeleton**: model.cfg declares `DayzTemporarySkeleton` (159 bones, the exact vanilla hierarchy). All vanilla clothing is compiled this way. With `OFP2_ManSkeleton` as the name, the engine does not re-bind the garment to the player and it renders rigid and floating. Always binarize with this model.cfg.
3. Complete and normalized weights (sum 1.0 per vertex).

## The assignment (fine-tuning)

Align the plates to the body in the canonical DayZ A-pose:

- **<Area 1, for example Arms>**: <what is off; for example: pauldrons and forearm plates sit apart from the character's arm and sag, because the canonical bind has the arms more horizontal than this model>. The reference for where clothing should fall is the vanilla chainmail worn model (`dz\characters\tops\chainmail_m.p3d`).
- **<Area 2, for example Legs and abdominal protector>**: <what is off; for example: minor fit>.

## Optional improvement

The current skinning is rigid per plate (<percent> % of the vertices on a single bone, without the shoulder, roll, extra, spine1 and spine2 transition bones). It works, but the joints are crude in motion. Smoothing the weights at the joints (2 to 4 influences, like vanilla clothing) would improve the deformation a lot.

## Return workflow

Deliver the modified FBX (or the .blend). We convert it to .p3d with the same axis map that produced this FBX (the map is its own inverse), rebuild the selections from the vertex group weights, and binarize with the included model.cfg. Do not mirror the model or flip its normals: the garment is meant to look in game as it does in Blender, text and logos included.
