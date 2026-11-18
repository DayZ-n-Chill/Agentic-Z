# Worn models: skeleton, frame and weights

Covers what the worn models (`_m` and `_f`) of a wearable must look like to bind to the player: the skeleton name, the coordinate frame and its handedness, the selections and weights, the `model.cfg`, how to build and check them, and the failures that give no error in the log. Fitting plates that bind but sit off the body is in `fitting-worn-models.md` and `autofit-on-official-rig.md`.

Two kinds of fact are in this file. A fact with a `P:\` path was read from the vanilla file. A fact marked **Measured** was measured while building a body armor, delivered as worn models, into a working item on DayZ 1.29 diag, or in the test runs named beside it; those are not yet checked on `P:\`, because the vanilla worn models there are binarized and Agentic-Z ships no reader for their vertex data.

## Skeleton: `DayzTemporarySkeleton`

Every vanilla worn model is compiled against a skeleton named `DayzTemporarySkeleton`. A byte scan finds the name, followed by 159 bone and parent pairs, in `P:\DZ\characters\tops\chainmail_m.p3d`, `P:\DZ\characters\tops\armbend_dynamic_m.p3d`, `P:\DZ\characters\tops\hoodie_m.p3d` and `P:\DZ\characters\vests\plate_carrier_m.p3d`. The list starts with `pelvis`, `launcher`, `weapon` and ends with `camera` and `righthand_dummy`. The ground model `P:\DZ\characters\tops\chainmail_g.p3d` has no skeleton.

- The 159 pairs are in the `model.cfg.template` that ships with the worn-model scripts (find it with Glob), in the same order as the vanilla models; a test beside it compares the template with `chainmail_m.p3d`.
- **Measured:** the bones and hierarchy are those of the player skeleton `OFP2_ManSkeleton`; only the name differs. The name is a placeholder the engine swaps for the wearer's skeleton when the item is put on.
- **Measured:** with `skeletonName="OFP2_ManSkeleton"` in `model.cfg` the engine treats the model as having its own skeleton and never binds it to the wearer. The item renders as a rigid block anchored above the player, floating about 1 m up, and does not animate. A `model.cfg` with a 114-bone `OFP2_ManSkeleton` fails clothing twice, on the bone count and on the name. The fix: rename the `CfgSkeletons` class and every `skeletonName =` in the clothing `model.cfg` to `DayzTemporarySkeleton`, then binarize again.

### Which name vanilla ships

A text search inside the binarized models (binary files, so no line numbers):

- `P:\DZ\characters\tops\hoodie_m.p3d`, `P:\DZ\characters\tops\chainmail_m.p3d` and `P:\DZ\characters\tops\armbend_dynamic_m.p3d` each contain `DayzTemporarySkeleton` and do not contain `ofp2_manskeleton`.
- So do the bodies: the infected body `P:\DZ\characters\zombies\hermit_above0.p3d` and the survivor body parts model `P:\DZ\characters\bodies\bodyparts_above0.p3d`. Of the 63 models under `P:\DZ\characters\zombies\`, 62 contain `DayzTemporarySkeleton`; the one without is a static prop.
- Of the 897 models under `P:\DZ\characters\`, 584 contain `DayzTemporarySkeleton` and only 4 contain `ofp2_manskeleton`: `P:\DZ\characters\pants\jeans_m_above0.p3d`, `P:\DZ\characters\tops\tshirt_m_above0.p3d` and the two `shirt_*_new_anim_system.p3d` models in `tops`. No vanilla `config.cpp` under `P:\DZ\characters\` names those four.

A custom infected body built with `OFP2_ManSkeleton` as its `model.cfg` skeleton name did animate in game as an infected, so a body that is its own entity worked under that name; a worn item did not. When in doubt, use the name vanilla uses.

## `model.cfg`

Copy the template and keep its `CfgSkeletons` block exactly as it is (`DayzTemporarySkeleton`, the 159 bone pairs, `isDiscrete=0`). Add one `CfgModels` class per worn `.p3d`, named like the file, with `skeletonName="DayzTemporarySkeleton"` and its `sections[]`. After binarizing, check the name in the built model (a byte scan for `DayzTemporarySkeleton` is enough to see it is there).

## Canonical worn frame

**Measured** on `chainmail_m` and `hoodie_m`:

- **-Z = chest (front)**, **+X = the anatomical left**, **+Y = up**, origin at the feet (ground at Y = 0). The mesh is authored over the vanilla A-pose body.
- Torso clothing spans about Y 0.61 to 1.66 m. The reference garment for overlay checks is `P:\DZ\characters\tops\chainmail_m.p3d` (body armor, full-body bone set).
- Measure the orientation with anatomical components, never with a histogram of all Z values: both halves hold about 55 and 45 % of the mass on real clothing, so the histogram misses a 180 degree flip. Reliable signals: front detail (the hoodie drawstrings at Z -0.14 to -0.07), the centroids of the vertices weighted to pelvis and spine (vanilla about Z -0.04 to -0.08), and the centroids of the `left*` selections on +X.

### Handedness

**Measured** (2026-10-01):

- The frame holds a body that is not mirrored, in DayZ's left-handed space. A Blender garment (right-handed; front -Y and left +X, like the official rig) lands on it with `(x, y, z) -> (x, z, y)`: determinant -1, faces in Blender order, normals negated (the export rule, derived in `body-rigging.md` section 6). With py3d 1.8.0 or newer that is `py3d.blender_to_dayz()`.
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

## Build

Build with `/dayz-build-pbo <ModName>`, then test with `/dayz-launch-test`. The points below are what the armor build taught; they matter most when you build by hand.

1. **Stage the mod before binarizing.** `/dayz-build-pbo` stages for you. **Measured:** binarizing with the whole of `P:\` as the addon root stops on any broken third-party `config.cpp` in the tree, with "Error 3" naming the wrong culprit.
2. **Stage every file the models name outside the mod's prefix**, the vanilla penetration `.rvmat` of the Fire Geometry included. **Measured** (2026-10-03): otherwise binarize embeds those materials empty; the armor's binarized model carried `dz\data\data\penetration\armor_5mm_plate.rvmat` empty.
3. **`model.cfg` sits next to the `.p3d`** in the staged copy. After the build, the binarized model must hold the skeleton name `DayzTemporarySkeleton`.
4. **Check the PBO**: the class name is in the config, the worn models start with `ODOL`, and every `.paa` and `.rvmat` (the damage ones too) is there.
5. **The gate is in game**: spawn it (does it register?), equip it (does the worn model render on the body?), move (does it follow the animations?). A worn item cannot be validated offline only.

**Measured, for a build by hand:** the mod was staged to a temp folder outside `P:\`; one full AddonBuilder pass binarized the models; then a pack tree of `config.cpp` as text, `model.cfg`, the binarized models and all `.paa` and `.rvmat` files (damage and destruct ones included) was packed with AddonBuilder `-packonly`, using a separate `-temp` folder. The PBO was then checked (class name present, no `config.bin`, models starting with `ODOL`). The staging rules behind this are in `skills/dayz-build-pbo/references/addonbuilder-rules.md`.

## Diagnosis

| Symptom | Cause | Check with |
|---|---|---|
| Item unknown or cannot be spawned, no RPT error | The class did not register (failure 1) | Spawn it in game; list the PBO entries |
| Worn item is a rigid block anchored above the player, not animating | Skeleton name is not `DayzTemporarySkeleton` (failure 3) | The skeleton name in the built model against a vanilla one |
| Worn item is exploded into separate rigid pieces floating about 1 m above the player | Mesh frame flipped 180 degrees (failure 2) | Z signs of anatomical components against the chainmail |
| It fits, but plates are misaligned on arms or legs | The source's proportions differ from the canonical bind | `fitting-worn-models.md` |
| Body or arms invisible when equipped | Expected: classes in the torso slots hide the skin | Wear it with the intended slot class |
| Coarse joints while moving | 0 or 1 plate weights, no transition bones | A weight-smoothing pass (2 to 4 influences at the joints) |
| Gas mask worn, still takes biological or gas damage | Since 1.30 the GP5 and Airborne masks get that protection from the attached filter | `protection-and-insulation.md`, "Masks with a filter slot" |
| Custom backpack cannot attach the NBC pack | Its `attachments[]` lacks `"NBCBag"` | `slots-and-cargo.md`, "`NBCBag` on backpacks" |

**Config or model?** One rebuild of the config alone answers which side is broken. Add two test classes: your slot class with a vanilla worn model (the chainmail), and a vanilla clothing class (an armband) with your worn model. Vanilla model fine and your model broken in both classes: it is the model. Both fine: it is a field of your main class. Both broken: it is the build. On the armor build this, the skeleton name in the built model and the parity check below isolated the fault in about six in-game cycles.

**Parity with a vanilla worn model.** With a reader for binarized models, compare against a vanilla worn model: skeleton name and 159 bones, weight sums per vertex, the sub-skeleton palette (unused palette entries with weight 0 are normal in vanilla), sections (`camomale` alone on tops; the four `_big_a`, `_big_b`, `_small_a`, `_small_b` variants only on armbands, as in `P:\DZ\characters\tops\armbend_dynamic_m.p3d`), the empty Geometry LOD with `autocenter=0`, and the model info flags. This repo ships no such reader; the tool folder `scripts/tools/dayz-odol-strict` is an adapter around an external one. **Measured:** vertex positions of vanilla character bodies decoded corrupt with that reader, while worn clothing (armband, chainmail, hoodie) decoded fine.
