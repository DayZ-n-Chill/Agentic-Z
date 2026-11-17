# Import rule, version 4, and the model path: what decides whether the build loads and renders

The axis swap, normals and winding rule for importing a weapon mesh, the `model=` path rule, and why the test must use the binarized build. Mesh assembly, LODs and textures belong to the dayz-model-pipeline and `dayz-texture-pipeline` skills; packing belongs to `/dayz-build-pbo`.

Everything here was measured on the author's A6_MK47 project and tested in game (build v12c). It is a third-party project: its files (`A6_MK47_dev\...`) are not on `P:\`, and none of it was measured again for Agentic-Z. Marks: `[VERIFIED in-game]` means a real in-game test recorded in that project, `[UNVERIFIED]` means inferred. For checking face winding on any model see `skills/dayz-p3d-audit/references/winding-methodology.md`.

## The import rule

`[VERIFIED in-game]` MK47 v12c (`A6_MK47_dev\HANDOFF.md:26-32` and the project's notes):

> A pure swap (x,y,z) to (x,z,y), determinant -1, with normals treated as pseudovectors (-S·n), `REVERSE_WINDING=False`, and the build served binarized. Binarize flips the winding (100% of faces) and passes normals through as they are. Target pattern (the vanilla `akm.p3d` as binarized): about 70% of faces pointing outward, and stored normal dot geometric normal about -0.98.

Where it comes from: the Blender weapon frame is long along X (muzzle toward -X), Z up, Y sideways (right is +Y); the swap turns Blender's Z up into DayZ's Y up. In the project it is implemented in `assemble_mk47.py:68-87`.

**The check.** The author's validator `compare_outwardness.py` (a script of his own that is not part of the knowledge pack) passes a model when at least 60% of faces point outward and stored dot geometric is -0.85 or lower. v12c measured 63.2% and -0.88, a pass. Do not go back to iterating winding and normals: check future changes offline against the AKM pattern with the same two numbers, and with the model path check below.

**Derive the swap again for each weapon; never copy it.** SR2M has a different Blender frame: long axis Y, muzzle toward -Y, Z up (the SR2M project's "fixed decisions" list: the import swap is derived again and validated with `compare_outwardness.py`). MK47's swap applied to SR2M would flip it the wrong way. Derive the frame from the actual Blender file and validate against the same AKM pattern.

## W-BUILD1: the model path

`[VERIFIED in-game]` `A6_MK47_dev\HANDOFF.md:9-24`, finding number 1, the root cause of every failed build from v1 to v12b:

- `config.cpp` had `model=` pointing at `\A6_MK47\mk47_body.p3d` (the PBO root), but the `.p3d` lives under `data\`.
- Builds made without a clean temp folder carried an old unbinarized `mk47_body.p3d` at the PBO root. That was the model the engine loaded, which made every offline winding and normal measurement meaningless: they described the binarized model while the game showed the raw one. It also means the difference between "pack only" and "binarize" in the project's winding table for builds v6 to v11 was not real; all of those builds ran the root copy.
- The clean build v12 removed the old copy, `model=` then resolved to nothing, and the result was "invisible, and a crash on equip or on opening the inventory". Three unrelated theories were disproved with data before the real fix.
- Fix: `model="\A6_MK47\data\mk47_body.p3d"` and a clean rebuild, v12c, the first build whose binarized model actually rendered (the author's lesson LL-145).

**The rule:** `model=` points at the real path inside the PBO (under `data\`), and the build runs with a clean temp folder after any change to the folder structure (`/dayz-build-pbo <ModName> --clean`). `/dayz-lint` reports a `model=` path that names no file in the mod as `missing-model`; the knowledge pack added a check of the same kind to its own PBO build skill after this (LL-145). The project keeps it as a closed rule (`A6_MK47_dev\HANDOFF.md:67-69`): the config `model=` points into `data\` and is checked against the PBO's contents on each build.

## W-BUILD2: test the binarized build; use the retail game for the A6 family

`[VERIFIED in-game]` `A6_MK47_dev\HANDOFF.md:99-105` and `:41`:

- **Serve the binarized build.** The winding and normals rule above is only correct on the binarized model, because binarize flips the winding. A build that serves the unbinarized model measures the wrong thing.
- **Retail game, not the Diag build, for mods of the A6 family.** The A6 weapon pack uses script without braces (`override typename GetInputType() return X;` in its optic and weapon scripts) that the strict compiler of the Diag build rejects as an error while the retail build accepts it with a warning. LBmaster is also incompatible with the Diag build. This is a note about the test environment; it is repeated here because it decides whether the weapon can be tested at all. `/dayz-launch-test` starts the Diag build.

The MK47 project's own launcher enforces both: retail executable, clean build, binarized PBO (`A6_MK47_dev\tools\dayz-test.ps1`).

## Build order, entity side

1. Assemble the `.p3d` with the swap derived for this weapon and validated against the binarized AKM pattern (at least 60% outward, stored dot geometric -0.85 or lower). Mesh assembly and LODs: the dayz-model-pipeline skill.
2. `config.cpp`: `model="\<Mod>\data\<weapon>.p3d"`, the real path inside the PBO (W-BUILD1).
3. Build binarized with a clean temp folder: `/dayz-build-pbo <ModName> --clean`.
4. Test with the retail game for mods of the A6 family (W-BUILD2).

## Cite, then verify

The swap direction, the pass band and the model path are all easy to half remember, and each cost the MK47 project many builds. Read the measured values again and run the outwardness check again before calling a winding change good; never trust a swap copied from another weapon.
