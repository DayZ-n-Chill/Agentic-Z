# Worn models

What the worn models (`_m` and `_f`) of a wearable must look like to bind to the player: the skeleton name, the coordinate frame and its handedness, the selections and weights, the `model.cfg`, how to build and check them, and the three failures that leave no error in the log. Fitting plates that bind but sit off the body is in `fitting-worn-models.md` and `autofit-on-official-rig.md`.

A fact with a `P:\` path was read from the vanilla file. The vanilla worn models on `P:\` are binarized and this repo ships no reader for their vertex data, so a fact marked measured comes from building a plate body armour into a working item, or from a test garment in game, and is not checked on `P:\`.

## Skeleton: `DayzTemporarySkeleton`

Every vanilla worn model is compiled against a skeleton named `DayzTemporarySkeleton`. A byte scan finds the name, followed by 159 bone and parent pairs, in `P:\DZ\characters\tops\chainmail_m.p3d`, `P:\DZ\characters\tops\armbend_dynamic_m.p3d`, `P:\DZ\characters\tops\hoodie_m.p3d` and `P:\DZ\characters\vests\plate_carrier_m.p3d`. The list starts with `pelvis`, `launcher`, `weapon` and ends with `camera` and `righthand_dummy`. The ground model `P:\DZ\characters\tops\chainmail_g.p3d` has no skeleton.

- The 159 pairs are in the `model.cfg.template` that ships with `/dayz-model-tools`, in vanilla order; a test beside it compares the template with `chainmail_m.p3d`.
- The bones and hierarchy are those of the player skeleton `OFP2_ManSkeleton`; only the name differs. The name is a placeholder the engine swaps for the wearer's skeleton when the item is put on (measured).
- With `skeletonName="OFP2_ManSkeleton"` in `model.cfg` the engine treats the model as having its own skeleton and never binds it to the wearer: the item renders as a rigid block floating about 1 m above the player and does not animate (measured). A `model.cfg` with a 114 bone `OFP2_ManSkeleton` fails twice, on the bone count and on the name. Rename the `CfgSkeletons` class and every `skeletonName =` in the clothing `model.cfg` to `DayzTemporarySkeleton`, then binarize again.

### Which name vanilla ships

A text search inside the binarized models (binary, so no line numbers):

- `hoodie_m.p3d`, `chainmail_m.p3d` and `armbend_dynamic_m.p3d` in `P:\DZ\characters\tops\` each contain `DayzTemporarySkeleton` and not `ofp2_manskeleton`.
- So do the bodies: the infected body `P:\DZ\characters\zombies\hermit_above0.p3d` and the survivor body parts model `P:\DZ\characters\bodies\bodyparts_above0.p3d`. Of the 63 models under `P:\DZ\characters\zombies\`, 62 contain `DayzTemporarySkeleton`; the one without is a static prop.
- Of the 897 models under `P:\DZ\characters\`, 584 contain `DayzTemporarySkeleton` and only 4 contain `ofp2_manskeleton`: `P:\DZ\characters\pants\jeans_m_above0.p3d`, `P:\DZ\characters\tops\tshirt_m_above0.p3d` and the two `shirt_*_new_anim_system.p3d` models in `tops`. No vanilla `config.cpp` under `P:\DZ\characters\` names those four.

A custom infected body with `OFP2_ManSkeleton` as its `model.cfg` skeleton name did animate in game, so a body that is its own entity works under that name; a worn item does not. When in doubt, use the name vanilla uses.

## `model.cfg`

Copy the template and keep its `CfgSkeletons` block exactly as it is (`DayzTemporarySkeleton`, the 159 bone pairs, `isDiscrete=0`). Add one `CfgModels` class per worn `.p3d`, named like the file, with `skeletonName="DayzTemporarySkeleton"` and its `sections[]`. After binarizing, a byte scan of the built model for `DayzTemporarySkeleton` shows the name is there.

## Canonical worn frame

Measured on `chainmail_m` and `hoodie_m`:

- Chest (front) on -Z, the anatomical left on +X, up on +Y, origin at the feet (ground at Y = 0). The mesh is authored over the vanilla A-pose body.
- Torso clothing spans about Y 0.61 to 1.66 m. The reference garment for overlay checks is `P:\DZ\characters\tops\chainmail_m.p3d`, body armour with the full bone set.
- Check orientation with anatomical parts, never with a histogram of all Z values: both halves of real clothing hold about 55 and 45 % of the mass, so a histogram misses a 180 degree flip. Reliable signs are front detail (the hoodie drawstrings at Z -0.14 to -0.07), the centroids of the vertices weighted to pelvis and spine (vanilla about Z -0.04 to -0.08), and the `left*` centroids on +X.

### Handedness

- The frame holds a body that is not mirrored, in DayZ's left handed space. A Blender garment (right handed; front -Y and left +X, like the official rig) lands on it with `(x, y, z)` to `(x, z, y)`: determinant -1, faces in Blender order, normals negated (`body-export.md`, section "The export map"). With py3d 1.8.0 or newer that is `py3d.blender_to_dayz()`.
- A determinant +1 map mirrors the garment: `(x, z, -y)` faces +Z, and `(-x, z, y)` faces -Z with `left*` on -X. A mesh that needs "rotate 180 degrees and swap left and right" was exported with such a map; the armour models as received were the `(x, z, -y)` export of their Blender file.
- Rotating and swapping makes the item bind but keeps the mirror: text, logos, buckles and one-sided straps read reversed. The right fix is to export the Blender source again with `(x, z, y)` and no swap.
- With only the `.p3d`, reflect it on the axis its state calls for. One received from `(x, z, -y)`, never rotated or swapped, takes `z` to `-z`. One that already had "rotate 180 degrees and swap", which is `(-x, z, y)`, takes `x` to `-x` with the swap undone (`z` to `-z` on it would face +Z again). Either reflection moves every point, memory points included, reverses every face and reflects the normals; py3d's `P3D.transform()` with that diagonal matrix (determinant -1) does all three.

### Chiral check in game

The anatomical test rules out a determinant +1 export only while the left and right selections were never swapped by hand; a swapped build needs an asymmetric feature. Put an "F" in relief on the left chest of a test garment, weighted 100 % to `spine3`. Export it once with `(x, z, y)` and once with the old `(x, z, -y)` plus rotate and swap as the control, wear each with an item in hand, and set the camera in front. Pass: the "F" reads correctly and sits on the side opposite the item hand (items sit on `RightHand_Dummy`). The control shows the "F" mirrored on the item side. On a real garment, compare one asymmetric detail with its Blender source instead.

Measured on a vest-like test garment in the `Armband` slot, binarized with `DayzTemporarySkeleton`: the `(x, z, y)` build, worn with a crowbar in the right hand, shows the "F" correct on the wearer's left chest, opposite the crowbar. The control (`ROT_X_NEG90`, every face reversed and every normal negated, then 180 degrees about +Y) shows the "F" mirrored on the right chest, read on a `SurvivorM_Francis` facing the camera.

Measured with sleeves on 1.30, on an `Armband_ColorBase` test garment binarized to ODOL v56 with `DayzTemporarySkeleton`: a `spine3` torso tube with a left chest "F", two shoulder to elbow sleeves (one weighted to `leftarm`, one to `rightarm`) and a ring on the left sleeve only, checked front and back, standing still and during the greeting gesture, which raises the left arm.

| Build | Result |
|---|---|
| `(x, z, y)`, no selection swap | "F" reads correctly on the left chest, the ring is on the left arm, each sleeve follows its arm |
| `(-x, z, y)` with `leftarm` and `rightarm` swapped | "F" mirrored on the right chest, ring on the right arm, each sleeve still follows its arm |
| `(-x, z, y)` without the swap | "F" and ring mirrored. Standing still, both sleeves float at head height; with the left arm raised, the left sleeve stays at head height while the right one drops to the lower back |

Not covered: the armour models themselves, and a female body.

## What a worn model holds

- **Selections are the skin.** The visual LODs are skinned by named selections whose names are the bone names in lowercase: `leftarm`, `rightarm`, `leftforearm`, `rightforearm`, `leftupleg`, `rightupleg`, `neck`, `pelvis`, `spine`, `spine3`. Vanilla also weights the shoulder, roll and extra bones for smooth joints, a set of 44 names (measured).
- **Weights sum to 1.0 per vertex.** Vanilla stores raw bytes that sum to 255 (measured). Weights of only 0 or 1, each plate rigid on one bone, work but articulate coarsely.
- **Camo sections.** Tops and vests use `camoMale` in the male model and `camoFemale` in the female one, plus `zbytek` for the rest (`camomale` and `zbytek` are in `P:\DZ\characters\tops\chainmail_m.p3d`). Armbands carry four variants per gender; see `color-variants.md`.
- **Empty Geometry LOD.** Vanilla worn models have a Geometry LOD with no mesh and the property `autocenter` = `0` (in `P:\DZ\characters\tops\chainmail_m.p3d` and `P:\DZ\characters\vests\plate_carrier_m.p3d`). Keep it.
- **Ground model.** The `_g` model is a normal item model: Geometry LOD with mass and `Component01`, memory points, View Geometry, and Fire Geometry with a penetration `.rvmat` (`_shared/models/lods.md`).

## Config side

- The class inherits a vanilla clothing class for the slot (`classes-and-parents.md`). `model` names the ground model and `ClothingTypes` the worn ones, as `Chainmail` does (`P:\DZ\characters\tops\config.cpp:9279`).
- `hiddenSelections[]` has one entry per model section, with the texture and material arrays in the same order (`color-variants.md`).
- In an AddonBuilder build by hand, damage `.rvmat` files named only in `healthLevels[]` are left out of the PBO and must be added to the pack step. `/dayz-build-pbo` passes its own include list, which names `*.rvmat`, so it packs them; with any other build, check the PBO.
- In one setup a `config.bin` made with CfgConvert did not register the class (`CreateObjectEx` gave an unknown type and the item was missing from an admin tool's spawn list, with no log error), and packing `config.cpp` as text fixed it. That is one setup, not a rule: `/dayz-build-pbo` binarizes configs with AddonBuilder and those mods load. Whichever way you pack, prove the class registered by spawning it in game, not by reading the PBO.

## Three failures with no log error

A worn item can fail three independent ways, and none writes an error to the RPT. Check them in this order, because chasing one while another is present wastes test runs.

| Order | Failure | What you see | Check |
|---|---|---|---|
| 1 | The class did not register | The item is unknown and cannot be spawned | Spawn the class in game |
| 2 | The worn mesh is not in the canonical frame (built facing +Z) | Rigid pieces floating about 1 m above the player: each plate is moved by its bone from a flipped frame | The anatomical signs above, against the chainmail |
| 3 | The skeleton is not named `DayzTemporarySkeleton` | A rigid block above the player that does not animate | The skeleton name in the built model |

For failure 2, a 180 degree turn about +Y (determinant +1, so the winding is untouched) plus swapping the `left*` and `right*` selection pairs in every LOD makes the item bind but keeps a mirror (section "Handedness"). With the Blender source at hand, export it again with `(x, z, y)` instead.

## Build

Build with `/dayz-build-pbo <ModName>`, then test with `/dayz-launch-test`. The points below matter most when you build by hand.

1. **Stage the mod before binarizing.** `/dayz-build-pbo` does it for you. Binarizing with the whole of `P:\` as the addon root stops on any broken third-party `config.cpp` in the tree, with "Error 3" naming the wrong file.
2. **Stage every file the models name outside the mod's prefix**, the vanilla penetration `.rvmat` of the Fire Geometry included. Otherwise binarize embeds those materials empty; the armour's built model carried `dz\data\data\penetration\armor_5mm_plate.rvmat` empty.
3. **`model.cfg` sits next to the `.p3d`** in the staged copy, and the built model must hold the name `DayzTemporarySkeleton`.
4. **Check the PBO**: the class name is in the config, the worn models start with `ODOL`, and every `.paa` and `.rvmat` (the damage ones too) is there.
5. **Gate in game**: spawn it (does it register?), equip it (does the worn model render on the body?), move (does it follow the animations?). A worn item cannot be validated offline only.

A build by hand that works: stage the mod to a temp folder outside `P:\`, run one full AddonBuilder pass to binarize the models, then pack a tree of `config.cpp` as text, `model.cfg`, the binarized models and every `.paa` and `.rvmat` (damage and destruct ones included) with AddonBuilder `-packonly` and a separate `-temp` folder, and check the PBO. The staging rules are in `skills/dayz-build-pbo/references/addonbuilder-rules.md`.

## Symptom to cause

| Symptom | Cause | Check with |
|---|---|---|
| Item unknown or cannot be spawned, no RPT error | The class did not register (failure 1) | Spawn it in game; list the PBO entries |
| A rigid block above the player, not animating | Skeleton name is not `DayzTemporarySkeleton` (failure 3) | The skeleton name in the built model against a vanilla one |
| Separate rigid pieces floating about 1 m above the player | Mesh frame flipped 180 degrees (failure 2) | Z signs of anatomical parts against the chainmail |
| It fits, but plates are off on arms or legs | The source's proportions differ from the canonical bind | `fitting-worn-models.md` |
| Body or arms invisible when equipped | Expected: classes in the torso slots hide the skin | Wear it with the intended slot class |
| Coarse joints while moving | 0 or 1 plate weights, no transition bones | A smoothing pass, 2 to 4 influences at the joints |
| Gas mask worn, still takes biological or gas damage | Since 1.30 the GP5 and Airborne masks get that protection from the filter | `protection-and-insulation.md`, section "Masks with a filter slot" |
| Custom backpack cannot attach the NBC pack | Its `attachments[]` lacks `"NBCBag"` | `slots-and-cargo.md`, section "`NBCBag` on backpacks" |

**Config or model?** One rebuild of the config alone answers it. Add two test classes: your slot class with a vanilla worn model (the chainmail), and a vanilla clothing class (an armband) with your worn model. Vanilla model fine and yours broken in both: it is the model. Both fine: it is a field of your main class. Both broken: it is the build.

**Parity with a vanilla worn model.** With a reader for binarized models, compare against a vanilla worn model: skeleton name and 159 bones, weight sums per vertex, the sub skeleton palette (unused entries with weight 0 are normal), sections (`camomale` alone on tops; the four `_big_a`, `_big_b`, `_small_a` and `_small_b` variants only on armbands, as in `P:\DZ\characters\tops\armbend_dynamic_m.p3d`), the empty Geometry LOD with `autocenter=0`, and the model info flags. This repo ships no such reader; `scripts/tools/dayz-odol-strict` is an adapter around an external one. That reader decodes worn clothing (armband, chainmail, hoodie) correctly but the vertex positions of vanilla character bodies come out corrupt (measured).
