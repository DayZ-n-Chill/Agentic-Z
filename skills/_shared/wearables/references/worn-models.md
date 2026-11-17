# Worn models: skeleton, frame and weights

Covers what the worn models (`_m` and `_f`) of a wearable must look like to bind to the player: the skeleton name, the coordinate frame and its handedness, the selections and weights, and the three failures that give no error in the log. The steps and scripts that go with it are in the `dayz-clothing` skill (`skills/dayz-clothing/SKILL.md`).

Two kinds of fact are in this file. A fact with a `P:\` path was read from the vanilla file. A fact marked **Measured** was measured while building a body armor, delivered as worn models, into a working item on DayZ 1.29 diag, or in the test runs named beside it; those are not yet checked on `P:\`, because the vanilla worn models there are binarized and Agentic-Z ships no reader for their vertex data.

## Skeleton: `DayzTemporarySkeleton`

Every vanilla worn model is compiled against a skeleton named `DayzTemporarySkeleton`. A byte scan finds the name, followed by 159 bone and parent pairs, in `P:\DZ\characters\tops\chainmail_m.p3d`, `P:\DZ\characters\tops\armbend_dynamic_m.p3d`, `P:\DZ\characters\tops\hoodie_m.p3d` and `P:\DZ\characters\vests\plate_carrier_m.p3d`. The list starts with `pelvis`, `launcher`, `weapon` and ends with `camera` and `righthand_dummy`. The ground model `P:\DZ\characters\tops\chainmail_g.p3d` has no skeleton.

- The 159 pairs are in `skills/dayz-clothing/templates/model.cfg.template`, in the same order as the vanilla models. A test in the skill compares the template with `chainmail_m.p3d`.
- **Measured:** the bones and hierarchy are those of the player skeleton `OFP2_ManSkeleton`; only the name differs. The name is a placeholder the engine swaps for the wearer's skeleton when the item is put on.
- **Measured:** with `skeletonName="OFP2_ManSkeleton"` in `model.cfg` the engine treats the model as having its own skeleton and never binds it to the wearer. The item renders as a rigid block anchored above the player and does not animate. A `model.cfg` with a 114-bone `OFP2_ManSkeleton` fails clothing twice, on the bone count and on the name.
- In `model.cfg`, each worn model gets one `CfgModels` class named after the file, with `skeletonName="DayzTemporarySkeleton"`, `isDiscrete=0` on the skeleton, and its `sections[]`. After binarizing, check the name in the built model (a byte scan for `DayzTemporarySkeleton` is enough to see it is there).

## Canonical worn frame

**Measured** on `chainmail_m` and `hoodie_m`:

- **-Z = chest (front)**, **+X = the anatomical left**, **+Y = up**, origin at the feet (ground at Y = 0). The mesh is authored over the vanilla A-pose body.
- Torso clothing spans about Y 0.61 to 1.66 m. The reference garment for overlay checks is `P:\DZ\characters\tops\chainmail_m.p3d` (body armor, full-body bone set).
- Measure the orientation with anatomical components, never with a histogram of all Z values: both halves hold about 55 and 45 % of the mass on real clothing, so the histogram misses a 180 degree flip. Reliable signals: front detail (the hoodie drawstrings at Z -0.14 to -0.07), the centroids of the vertices weighted to pelvis and spine (vanilla about Z -0.04 to -0.08), and the centroids of the `left*` selections on +X.

### Handedness

**Measured** (2026-10-01):

- The frame holds a body that is not mirrored, in DayZ's left-handed space. A Blender garment (right-handed; front -Y and left +X, like the official rig) lands on it with `(x, y, z) -> (x, z, y)`: determinant -1, faces in Blender order, normals negated (Rule 12 of the dayz-model-pipeline skill). With py3d 1.8.0 or newer that is `py3d.blender_to_dayz()`.
- A determinant +1 map mirrors the garment: `(x, z, -y)` faces +Z, and `(-x, z, y)` faces -Z with `left*` on -X. A mesh that needs "rotate 180 degrees and swap left and right" was exported with such a map. The body armor models as received were the `(x, z, -y)` export of their Blender file.
- Rotating and swapping fixes the binding but keeps the mirror: text, logos, buckles and one-sided straps read reversed. The properly handed fix is to export the Blender source again with `(x, z, y)`, with no swap.
- With only the p3d, reflect it on the axis its state calls for. A p3d as received from `(x, z, -y)` (facing +Z, never rotated or swapped) takes `z -> -z`. One that already had "rotate 180 degrees and swap left and right", which is `(-x, z, y)`, takes `x -> -x` and the left and right swap undone (`z -> -z` on it would face +Z again). Either reflection moves every point (memory points included), reverses every face and reflects the normals the same way; `P3D.transform()` of py3d with that diagonal matrix (determinant -1) does all three.

### Chiral check in game

The anatomical test rules out a determinant +1 export only while the left and right selections were never swapped by hand. A swapped build needs an asymmetric feature. Put an "F" in relief on the left chest of a test garment (weighted 100 % to `spine3`). Export it once with `(x, z, y)` and once with the old `(x, z, -y)` plus rotate and swap as the control, wear each with an item in hands, and set the camera in front. Pass: the "F" reads correctly and sits on the side opposite the item hand (items sit on `RightHand_Dummy`). Expected on the control: the "F" mirrored, on the item side. On a real garment, compare one asymmetric detail against its Blender source file instead.

**Measured** (run 2026-10-02, DayZDiag 1.29.163709), on a vest-like test garment worn in the `Armband` slot, binarized with skeleton `DayzTemporarySkeleton`:

- The `(x, z, y)` build (`py3d.blender_to_dayz()`), worn by the player with a crowbar in the right hand, shows the "F" reading correctly on the wearer's left chest, opposite the crowbar.
- The control (`ROT_X_NEG90`, every face reversed and every normal negated, then 180 degrees about +Y) shows the "F" mirrored on the wearer's right chest. The garment carries only `spine3`, so the control's left and right swap renamed nothing. The in-game test bridge that drove the run cannot take a worn item off the player, so the control was worn by a `SurvivorM_Francis` spawned beside the player, facing the camera with empty hands; its right side was read from its facing.

**Measured** with left and right sleeves (run 2026-11-12, DayZDiag 1.30.164289.70), on a test garment of `Armband_ColorBase` classes in the `Armband` slot, binarized to ODOL v56 with `DayzTemporarySkeleton`: a `spine3` torso tube with a left-chest relief "F", two shoulder-to-elbow sleeves (one weighted to `leftarm`, one to `rightarm`) and a protruding ring on the left sleeve only. It was worn by the player and checked front and back, standing still and during the greeting gesture (which raises the left arm). The garment rendered grey (untextured), so the "F" and the ring were read from the geometry.

| Build | Result |
|---|---|
| `(x, z, y)`, no selection swap | "F" reads correctly on the left chest, the ring is on the left arm, each sleeve follows its arm. |
| The reflected `(-x, z, y)` export with `leftarm` and `rightarm` swapped | "F" mirrored on the right chest, ring on the right arm, each sleeve still follows its arm. |
| The same `(-x, z, y)` export without the swap | "F" and ring mirrored as above. Standing still, both sleeves float at head height off the arms; with the left arm raised, the left-side sleeve stays at head height while the right-side sleeve drops to the lower back. |

Not covered by either run: the body armor models themselves, and a female body.

## Structure of a worn model

- **Selections are the skin.** The visual LODs are skinned by named selections whose names are the bone names in lowercase: `leftarm`, `rightarm`, `leftforearm`, `rightforearm`, `leftupleg`, `rightupleg`, `neck`, `pelvis`, `spine`, `spine3`. More is better: vanilla also weights the shoulder, roll and extra transition bones for smooth joints. **Measured:** vanilla worn models use a set of 44 such names.
- **Weights sum to 1.0 per vertex.** **Measured:** vanilla models store raw bytes that sum to 255. Weights of only 0 or 1 (each plate rigid on one bone) work but articulate coarsely.
- **Camo sections.** Tops and vests use `camoMale` in the male model and `camoFemale` in the female model, plus `zbytek` for the rest (`camomale` and `zbytek` are in `P:\DZ\characters\tops\chainmail_m.p3d`). Armbands carry four variants per gender instead; see `color-variants.md`.
- **Empty Geometry LOD.** The vanilla worn pattern is a Geometry LOD with no mesh and the property `autocenter` = `0` (the property and its value are in `P:\DZ\characters\tops\chainmail_m.p3d` and `P:\DZ\characters\vests\plate_carrier_m.p3d`). Keep it.
- **Ground model.** The `_g` model is a normal item model: Geometry LOD with mass and `Component01`, memory points, View Geometry, and Fire Geometry with a penetration `.rvmat`. See `skills/_shared/models/lods.md`.

## Config side

- The class inherits a vanilla clothing class for the slot (see `classes-and-parents.md`). `model` names the ground model, and `ClothingTypes` names the worn ones, as `Chainmail` does at `P:\DZ\characters\tops\config.cpp:9279`.
- `hiddenSelections[]` has one entry per model section, with the texture and material arrays in the same order (`color-variants.md`).
- **Measured:** in a hand-run AddonBuilder build, damage `.rvmat` files that are named only in `healthLevels[]` were left out of the PBO by AddonBuilder's file list and had to be added to the pack step by hand. `/dayz-build-pbo` passes its own include list, which names `*.rvmat`, so it packs them; with any other build, check the PBO for them.
- **Measured, one environment:** a `config.bin` made with CfgConvert did not register the class (`CreateObjectEx` gave an unknown type and the item did not show in the spawn list of an admin tool, with no error in the log). Packing `config.cpp` as text fixed it, and every working local mod in that setup shipped its config as text. This is a result from one setup, not a rule: `/dayz-build-pbo` binarizes configs with AddonBuilder and those mods load. Whichever way the PBO is packed, the test that the class registered is spawning it in game, not reading the PBO.

## Three failures with no log error

A worn item can fail in three independent ways, and none writes an error to the RPT log. Check them in this order, because chasing one while another is present wastes test cycles.

| Order | Failure | What you see | Check |
|---|---|---|---|
| 1 | The class did not register (in the measured case: a CfgConvert `config.bin`). | The item is unknown and cannot be spawned. | Spawn the class in game. |
| 2 | The worn mesh is not in the canonical frame (built facing +Z). | Exploded rigid pieces floating about 1 m above the player: each plate is moved by its bone from a flipped frame. | The anatomical signals above, against the chainmail. |
| 3 | The skeleton is not named `DayzTemporarySkeleton`. | A rigid block anchored above the player that does not animate. | The skeleton name in the built model. |

For failure 2, rotating 180 degrees about +Y (determinant +1, so the winding is untouched) and swapping the `left*` and `right*` selection pairs in every LOD makes the item bind, but keeps a mirror (see "Handedness"). With the Blender source at hand, export it again with `(x, z, y)` instead.

The full symptom table, the test that tells a config fault from a model fault, and the build steps are in `skills/dayz-clothing/SKILL.md`.
