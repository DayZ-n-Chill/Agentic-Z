# Fitting worn models to the body

Covers the two ways to fix plates or panels that bind but sit off the body: fitting them by hand in the alignment viewer, and sending the models to an artist as FBX. Both start from worn models that already pass the three checks of `worn-models.md` (class registered, canonical frame, `DayzTemporarySkeleton`). Fitting a new garment on the official rig by script is in `autofit-on-official-rig.md`.

The scripts named here (`alignment_viewer_extract.py`, `alignment_viewer_build.py`, `apply_alignment_json.py`, `export_clothing_fbx.py`) ship with `/dayz-model-tools`, whose `SKILL.md` gives their command lines. They read MLOD models only (the `.p3d` Object Builder saves), not binarized ones, and need the py3d DayZ fork in `scripts/tools/py3d/` (1.6.0 or newer). This is tool knowledge, measured on a plate body armour and offline, not checked on `P:\`.

## Which route

| Situation | Route |
|---|---|
| Plates on arms or legs are slightly off, the topology is fine | Alignment viewer |
| The fit needs sculpting, new weights or a person's eye | Artist handoff, usually the best route |
| A new garment mesh with no weights yet | `autofit-on-official-rig.md` |

## Alignment viewer

A browser page with rotation and offset sliders per region, masked by weight and turning about the region's pivot, with left and right mirroring, front, back and side views, and an export of the adjustments as JSON. A vanilla worn model can be shown as a green wireframe to fit against.

1. **Extract.** The extract script reads a worn MLOD and writes the mesh, region weights and pivots as JSON. Regions default to the arms, forearms and thighs plus `abdomen` (the `pelvis` and `spine` selections together); a regions list and named combinations change them, and a LOD option picks the visual LOD (a lower LOD makes a lighter page). The usual reference wireframe is `P:\DZ\characters\tops\chainmail_m.p3d`, which is binarized and needs an external ODOL reader; an MLOD reference needs nothing extra.
2. **Build.** The build script writes `alignment_viewer.html` next to the data. Open it in a browser with a network connection (three.js loads from a CDN). The page comes from the shared viewer core, `skills/_shared/viewer_core.py`.
3. **Fit.** Move the sliders until the plates hug the reference, press "Generate adjustments JSON" and save the text as a `.json` file.
4. **Apply.** The apply script moves the points of every LOD with the same math as the page (the three.js XYZ Euler order), backs each file up to a `_backups` folder, saves and reads the file back. Use the same region combinations as in step 1. To prove the math matches before any file changes, give it one weight 1 sample point per region before and after, read from the page (`basePos` and `livePos` in the browser console); the run stops if they differ by 1e-4 m or more. On the armour they differed by about 1e-8.

## Artist handoff

When a person does the fitting, send an FBX package.

- **What the FBX holds.** The geometry, the UVs (V flipped for Blender), the diffuse as PNG (convert the `.paa` with DayZ Tools ImageToPAA first), and the bone weights carried by an armature with one bone per selection (ten by default: `leftarm`, `rightarm`, `leftforearm`, `rightforearm`, `leftupleg`, `rightupleg`, `neck`, `pelvis`, `spine`, `spine3`). That armature is not the game rig; it only keeps the groups.
- **FBX drops vertex groups no armature deforms.** Without the armature the groups vanish on import; with it all ten come back with exact weight sums. The export script imports each FBX again in a clean scene, prints the counts, groups and a weight sum, and fails if a group was lost. Read that output before sending.
- **Axis map DayZ to Blender: `(x, z, y)`**, determinant -1 and its own inverse. The artist sees the garment like the official rig: Z up, front -Y, left +X, faces outward. The way back is the same map with the faces in the order they return and the normals negated; with py3d 1.8.0 or newer that is `py3d.blender_to_dayz()` on the model rebuilt from the FBX in Blender coordinates. On an armour `_m` model the round trip is exact to 2.7e-7 m with the same face order; the `leftarm` centroid sits at x = +0.34, the pelvis and spine centroid at y = -0.045, and the signed volume is +0.026 in Blender, so the faces point outward.
- **Older packages.** An export with `(x, -z, y)` (determinant +1) shows the artist a mirror image (front +Y, left +X) with inward faces (signed volume -0.026). Such a package returns through `(x, z, -y)`, which is `transform(py3d.ROT_X_NEG90)` (the deprecated `py3d.BLENDER_TO_DAYZ` still works), never through `py3d.blender_to_dayz()`, which would land it facing +Z, mirrored and inside out.
- **The package** holds the FBX files, the PNG, the MLOD models, the `model.cfg` and a README for the artist (a template ships with the export script). The README states the three fixes not to undo (the canonical frame, the `DayzTemporarySkeleton` name, complete weights that sum to 1.0), the one rule that matters (move, rotate or sculpt vertices; never rename or empty a vertex group) and the way back. If the artist keeps the topology (same vertex count and order), the model goes back into the mod automatically.

## After either route

Binarize with the `model.cfg` of `worn-models.md`, then run the gate in game: spawn, equip, move. A worn item cannot be validated offline only.
