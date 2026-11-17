---
name: dayz-clothing
description: "Builds, fixes and diagnoses worn DayZ clothing (the _m and _f models of a wearable): the three failures that leave no log error, the worn model and model.cfg contract, a staged build, an alignment viewer for fitting plates to the body, an FBX handoff to an artist, and the 1.30 clothing changes. Use for a clothing mod, a worn model, ClothingTypes, a vest or armor, clothing that floats, stays rigid or is rotated, the Vest, Body or Armband slot, NBCHead, NBCTop, NBCPants, NBCBoots, NBCGloves, NBCBag, Waterskin, a gas mask filter, headSelectionsToHide or wet clothing. Also triggers on the Spanish phrases chaleco, armadura, la ropa flota, la ropa rígida, la ropa girada. Not for humanoid characters or rigging (use dayz-characters) and not for proxy triangles."
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-clothing

Takes a wearable from "the worn model does not sit on the player" to a working item. It covers the worn models only (`_m` and `_f`); the config side of a wearable (parent class, slots, cargo, protection, colors) is in the wearables pack.

Follow `skills/_shared/dayz-conventions.md`. The four scripts here work offline on the files you name and do not run `/dayz-preflight`; packing and testing go through `/dayz-build-pbo` and `/dayz-launch-test`, which do.

Everything marked **Measured** was found while building the ArmorHneck body armor (a third-party armor delivered as worn models) on DayZ 1.29 diag: about six in-game test cycles to separate three independent failures that leave no log error. The worn model contract is the same on 1.30.

## What to read

| Question | Read |
|---|---|
| Which skeleton name, frame, handedness, selections and weights must a worn model have, and why? | `skills/_shared/wearables/references/worn-models.md` |
| What did 1.30 change (NBC slots, mask filters, shoe sizes, Waterskin), what breaks, how do I migrate? | `skills/_shared/wearables/references/changes-in-1-30.md` |
| Which parent class, slot, cargo, protection or color setup? | The other files of `skills/_shared/wearables/README.md` |
| How do I fit a garment on the official rig in Blender and take weights from its body? What was tried and failed? | `references/autofit-from-official-rig.md` |
| What does the `model.cfg` of a worn model look like? | `templates/model.cfg.template` |
| What do I send an artist with the FBX? | `templates/README-ARTIST.template.md` |

| Script | What it does |
|---|---|
| `alignment_viewer_extract.py` | Reads a worn MLOD model and writes the mesh, region weights and pivots as JSON. |
| `alignment_viewer_build.py` | Builds the HTML alignment viewer from that JSON. |
| `apply_alignment_json.py` | Applies the adjustments exported by the viewer to the MLOD models. |
| `export_clothing_fbx.py` | Runs in Blender: exports worn MLOD models to FBX with their weights, for an artist. |

The three Python scripts need the DayZ fork of py3d, 1.6.0 or newer, from the repo folder `scripts/tools/py3d`; they add that folder to the path themselves. They read MLOD models only (the `.p3d` Object Builder saves), not binarized ones.

## Check these three first, in this order

A worn item can fail in three independent ways, and none of them writes an error to the RPT log. Any one of them wastes test cycles if you chase the others first. The evidence for each is in `worn-models.md`.

1. **The class is registered.** Spawn the class name in game. Never trust a reading of the PBO for "it registered". **Measured, one setup:** a `config.bin` made with CfgConvert did not register (`CreateObjectEx` gave an unknown type), and packing `config.cpp` as text fixed it. That is not a rule: `/dayz-build-pbo` lets AddonBuilder binarize the config, and that is how this repo's mods are built and loaded. Whichever way it is packed, the spawn is the test.
2. **The worn mesh is in the canonical clothing frame**: -Z is the chest, +X the anatomical left, +Y up, origin at the feet. A mesh built facing +Z renders as exploded rigid pieces floating about 1 m above the player. Rotating 180 degrees about +Y (do not touch the winding) and swapping the `left*` and `right*` selection pairs in every LOD makes it bind but keeps a mirror; with the Blender source at hand, export it again with `(x, y, z) -> (x, z, y)` instead.
3. **The clothing skeleton is named `DayzTemporarySkeleton`.** Every vanilla worn model is compiled with that name. With `skeletonName="OFP2_ManSkeleton"` the item renders as a rigid block anchored above the player and does not animate. Start from `templates/model.cfg.template`.

## The clothing contract

`config.cpp`:

- The class inherits a vanilla clothing class for the slot (`Armband_ColorBase`, `Chainmail`, a vest or top base). `model` names the ground model (`*_g.p3d`).
- `class ClothingTypes { male="..._m.p3d"; female="..._f.p3d"; };`
- `inventorySlot[]` names the worn slots. Since 1.30 the NBC bases also list a second slot (`"NBCHead"`, `"NBCTop"`, `"NBCPants"`, `"NBCBoots"`, `"NBCGloves"`); see `changes-in-1-30.md`.
- `hiddenSelections[]` has one entry per model section, with the texture and material arrays in the same order.
- Since 1.30 the values `headSelectionsToHide[]`, `hideSelectionsByinventorySlot`, `varWetMax`, `temperaturePerQuantityWeight` and `EnvironmentWetnessIncrements` are read once per item type. An item that fits two slots (a bandana, a shemag) still sets `hideSelectionsByinventorySlot = 1` and `simpleHiddenSelections[]`.
- Damage `.rvmat` files named only in `healthLevels[]` must end up in the PBO. `/dayz-build-pbo` packs every `.rvmat`; check a PBO built any other way.

Worn models (`_m`, `_f`):

- The visual LODs are skinned by named selections whose names are the bone names in lowercase (`leftarm`, `rightarm`, `leftforearm`, `rightforearm`, `leftupleg`, `rightupleg`, `neck`, `pelvis`, `spine`, `spine3`). More is better: vanilla also weights the shoulder, roll and extra transition bones for smooth joints.
- The weights of each vertex sum to 1.0. Weights of only 0 or 1 (rigid plates) work but articulate coarsely.
- Camo sections: tops and vests use `camoMale` or `camoFemale` alone. Only armbands carry the four variants per gender (`camoMale_big_a`, `camoMale_big_b`, `camoMale_small_a`, `camoMale_small_b`). Everything else goes in `zbytek`.
- Keep the empty Geometry LOD with `autocenter=0`; it is the vanilla worn pattern.
- The ground model (`_g`) is a normal item model: Geometry LOD with mass and `Component01`, memory points, View Geometry, and Fire Geometry with a penetration `.rvmat`.

`model.cfg`:

- Copy `templates/model.cfg.template` and keep its `CfgSkeletons` block exactly as it is (`DayzTemporarySkeleton`, the 159 bone pairs, `isDiscrete=0`). Add one `CfgModels` class per `.p3d`, named like the file, with `skeletonName="DayzTemporarySkeleton"` and its sections.

## Build

Build with `/dayz-build-pbo <ModName>`, then test with `/dayz-launch-test`. The points below are what the armor build taught; they matter most when you build by hand.

1. **Stage the mod before binarizing.** `/dayz-build-pbo` stages for you. **Measured:** binarizing with the whole of `P:\` as the addon root stops on any broken third-party `config.cpp` in the tree, with "Error 3" naming the wrong culprit.
2. **Stage every file the models name outside the mod's prefix**, the vanilla penetration `.rvmat` of the Fire Geometry included. **Measured** (2026-10-03): otherwise binarize embeds those materials empty; the armor's binarized model of 2026-08-04 carries `dz\data\data\penetration\armor_5mm_plate.rvmat` empty.
3. **`model.cfg` sits next to the `.p3d`** in the staged copy. After the build, the binarized model must hold the skeleton name `DayzTemporarySkeleton`; a byte scan of the `.p3d` for that name shows it.
4. **Check the PBO**: the class name is in the config, the worn models start with `ODOL`, and every `.paa` and `.rvmat` (the damage ones too) is there.
5. **The gate is in game**: spawn it (does it register?), equip it (does the worn model render on the body?), move (does it follow the animations?). A worn item cannot be validated offline only.

**Measured, for a build by hand:** the mod was staged to a temp folder outside `P:\`; one full AddonBuilder pass binarized the models; then a pack tree of `config.cpp` as text, `model.cfg`, the binarized models and all `.paa` and `.rvmat` files (damage and destruct ones included) was packed with AddonBuilder `-packonly`, using a separate `-temp` folder. The PBO was then checked (class name present, no `config.bin`, models starting with `ODOL`) and deployed only when its hash differed from the deployed one. The staging rules behind this are rule SP-155 of `/dayz-build-pbo` (`skills/dayz-build-pbo/references/addonbuilder-rules.md`).

## Diagnosis

| Symptom | Cause | Check with |
|---|---|---|
| Item unknown or cannot be spawned, no RPT error | The class did not register (failure 1) | Spawn it in game; list the PBO entries |
| Worn item is a rigid block floating about 1 m up, rotated, not animating | Skeleton name is not `DayzTemporarySkeleton` (failure 3) | The skeleton name in the built model against a vanilla one |
| Worn item is exploded into separate pieces above the head | Mesh frame flipped 180 degrees (failure 2) | Z signs of anatomical components against the chainmail |
| It fits, but plates are misaligned on arms or legs | The source's proportions differ from the canonical bind | The alignment viewer below, or an artist pass |
| Body or arms invisible when equipped | Expected: classes in the torso slots hide the skin | Wear it with the intended slot class |
| Coarse joints while moving | 0 or 1 plate weights, no transition bones | An optional weight-smoothing pass |
| Gas mask worn, still takes biological or gas damage | Since 1.30 the GP5 and Airborne masks get that protection from the attached `GasMask_Filter` | The mask's `Protection` class against the `GasMaskFilter` slot |
| Custom backpack cannot attach the NBC pack | Since 1.30: its `attachments[]` lacks `"NBCBag"` (not every vanilla bag has it) | Compare `TaloonBag_ColorBase` with `SmershBag` and `ChildBag_ColorBase` |

**Config or model?** One rebuild of the config alone answers which side is broken. Add two test classes: your slot class with a vanilla worn model (the chainmail), and a vanilla clothing class with your worn model. Vanilla model fine and your model broken in both classes: it is the model. Both fine: it is a field of your main class. Both broken: it is the build.

**Parity with a vanilla worn model.** With a reader for binarized models, compare against a vanilla worn model: skeleton name and 159 bones, weight sums per vertex, the sub-skeleton palette (unused palette entries with weight 0 are normal in vanilla), sections, and the model info flags. This repo ships no such reader; the tool folder `scripts/tools/dayz-odol-strict` is an adapter around an external one. **Measured:** vertex positions of vanilla character bodies decoded corrupt with that reader, while worn clothing (armband, chainmail, hoodie) decoded fine.

## Alignment viewer

Fits plates to the body by hand: a page with rotation and offset sliders per region, weight-masked and around the region's pivot, with left and right mirroring, front, back and side views, and an export of the adjustments as JSON. A vanilla worn model can be shown as a green wireframe to fit against.

```cmd
python "<skill-dir>\alignment_viewer_extract.py" path\to\garment_m.p3d --out path\to\work
python "<skill-dir>\alignment_viewer_build.py" --data path\to\work\align_data.json
python "<skill-dir>\apply_alignment_json.py" --adjust path\to\adjust.json path\to\garment_m.p3d path\to\garment_f.p3d
```

1. **Extract.** Regions default to the arms, forearms and thighs plus `abdomen` (the `pelvis` and `spine` selections added together). `--regions a,b,c` and `--combo name=part+part` change them; `--lod` picks the visual LOD (default 0; a lower-detail LOD makes a lighter page). `--ghost <p3d>` adds the reference wireframe. The usual reference is `P:\DZ\characters\tops\chainmail_m.p3d`, which is binarized, so it needs an external reader: pass its folder with `--odol-backend` or set `DAYZ_ODOL_BACKEND_ROOT`. An MLOD reference needs nothing extra.
2. **Build.** Writes `alignment_viewer.html` next to the data. Open it in a browser with a network connection (three.js loads from a CDN). The page comes from the shared viewer core, `viewer_core.py`; `--viewer-core <path>` names it if the script does not find it.
3. **Fit.** Move the sliders until the plates hug the reference, press "Generate adjustments JSON", and save the text as a `.json` file.
4. **Apply.** The script moves the points of every LOD with the same math as the page (the three.js XYZ Euler order), backs each file up to `_backups` first, saves, and reads the file back. Give `--combo` the same way as in step 1 if you used it. To prove the math matches before any file changes, pass `--samples <json>` with one weight-1 point per region before and after, read from the page (`basePos` and `livePos` in the browser console hold the positions); the run stops if they differ by 1e-4 m or more. **Measured:** the difference on the armor was about 1e-8.

Exit codes: 0 done; 1 the sample cross-check failed or an input could not be used (a LOD index out of range, a binarized reference with no reader); 2 py3d or the viewer core is missing or the wrong version.

## Artist handoff

When a person does the fitting, which is usually the best route, send them an FBX.

```cmd
blender -b --python "<skill-dir>\export_clothing_fbx.py" -- --out path\to\package --texture path\to\garment_co.png path\to\garment_m.p3d path\to\garment_f.p3d
```

- The FBX holds the geometry, the UVs (V flipped for Blender), the diffuse as PNG (convert the `.paa` with DayZ Tools ImageToPAA first), and the bone weights carried by a weight-carrier armature with one bone per selection (ten by default; `--bones` changes the list). FBX drops vertex groups that no armature deforms: **Measured**, without an armature the groups vanish on import, and with it all ten come back with exact weight sums.
- The script imports each FBX again in a clean scene and prints the counts, the vertex groups and a weight sum; it exits 1 if a group was lost. Read that output before shipping.
- Axis map DayZ to Blender: `(x, z, y)`, determinant -1 and its own inverse. The artist sees the garment like the official rig: Z up, front -Y, left +X, faces outward. The return trip is the same map with the faces in the order they come back and the normals negated; with py3d 1.8.0 or newer that is `py3d.blender_to_dayz()` on the model rebuilt from the FBX in Blender coordinates. **Measured** (offline, 2026-10-01, armor `_m` model, Blender 5.1.1 and py3d 1.7.0): the FBX round trip back to DayZ is exact to 2.7e-7 m with the same face order; the `leftarm` centroid is at x = +0.34, the pelvis and spine centroid at y = -0.045; the signed volume is +0.026 in Blender, so the faces point outward.
- Until 2026-10-01 the script used `(x, -z, y)` (determinant +1). The artist then saw a mirror image (front +Y, left +X) with inward faces (signed volume -0.026). A package made by that old script returns through `(x, z, -y)`, which is `transform(py3d.ROT_X_NEG90)` (the old name `py3d.BLENDER_TO_DAYZ` still works but is deprecated and warns), never through `py3d.blender_to_dayz()`, which would land it facing +Z, mirrored and inside-out.
- Package: the FBX files, the PNG, the MLOD models, the `model.cfg`, and a README written from `templates/README-ARTIST.template.md`. The README states the three fixes not to undo, the rule to keep the vertex groups, and the way back.

For fitting on the official rig by script instead of by hand, and for what that cannot do, read `references/autofit-from-official-rig.md` first.

## DayZ 1.30

The three failures, the canonical frame, `DayzTemporarySkeleton` and the build are unchanged. What 1.30 adds is a config and script contract around slots, protection, wetness, and one renamed class. `skills/_shared/wearables/references/changes-in-1-30.md` lists each change with its vanilla line, what breaks for a 1.29 mod, and a migration checklist. In short:

- NBC clothing lists a second, NBC-only slot, so it can be worn with regular clothing.
- Nine backpack bases take the NBC pack in the `NBCBag` slot; `SmershBag` and `ChildBag_ColorBase` do not.
- The GP5 and Airborne masks get biological and breathing protection from the attached `GasMask_Filter`. The sealed `GasMask` keeps its own. There is no class named `FilterBase`.
- Most shoes are three cells wide instead of four; `LeatherShoes_ColorBase` stays `{4,2}`.
- `WaterPouch_*` config classes are now `Waterskin_*`.
- Making an armband from a flag no longer needs an empty flag.
- New wash head and wet clothing actions wet each worn slot and lower the thermal bias.
- Scripts for new regional garments (kameez, shalwar, pakol, dust goggles and others) exist without config classes.

## On Linux

Everything above is the Windows workflow. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in the Linux and Proton notes (`skills/_shared/linux-proton.md`). What changes for this skill, all of it **Measured** by the notes' author and not checked here:

- Pack, sign and binarize with dayzmake 1.0.0 or newer, a DayZ fork of armake2 (https://github.com/bzed/dayzmake), pinned to `v1.0.0`: the release binary `dayzmake-v1.0.0-debian-trixie-x86_64.tar.gz` from the `v1.0.0` release page of that repository, or `cargo install --git https://github.com/bzed/dayzmake --tag v1.0.0`. Use `dayzmake build`, `keygen`, `sign`, and `build --proton-binarize` where needed. Upstream armake2 is no substitute: it is built for Arma, its V3 file hash leaves out `*.c` files (dayzmake `v1.0.0` includes them), and it lacks the DayZ-only functions dayzmake keeps adding. The helper script `skills/_shared/scripts/dayz-mod-pack.sh` wraps them (`init`, `keygen`, `build [--binarize-models]`, `check`, `publish-hint`); its notes are in `skills/dayz-build-pbo/references/dayzmake-linux.md`. A textured-cube comparison of 2026-11-03 against Bohemia's binarize from a `P:` root matched byte for byte (fork commit `7dcb3cf`, when the fork was still named armake2; `v1.0.0` contains it); that is not an in-game check of a binarized model.
- `P:\` is a plain directory mapped by `dayz-proton.sh init <dir>` (the script is `skills/_shared/scripts/dayz-proton.sh`); a `P:\<Mod>\...` path in this skill is `<dir>/<Mod>/...`.
- Object Builder and TexView run under Proton (`dayz-proton.sh gui ObjectBuilder <p3d>`, `gui TexView <paa>`). Object Builder opened and displayed a model; editing in it was not exercised. The Python checks and the scripts of this skill run natively.
- In-game checks on Linux: the Linux notes of the `dayz-test-ingame` skill (`skills/dayz-test-ingame/references/linux.md`).

## Building, testing and publishing the mod

When the work has to end in a mod that builds, loads and ships (`config.cpp` and `CfgMods`, `requiredAddons`, the PBO and its signature, a boot on a local server, the Workshop), run `/dayz-lint`, `/dayz-build-pbo` and `/dayz-launch-test`, or `/dayz-gate` for all of them in one pass. The full loop and the rules every mod task needs are in the `dayz-mod-dev` skill (`skills/dayz-mod-dev/SKILL.md`).
