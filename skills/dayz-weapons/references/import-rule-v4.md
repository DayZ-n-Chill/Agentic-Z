# Import rule, version 4, and the model path: what decides whether the build loads and renders

The axis swap, normals and winding rule for importing a weapon mesh, the `model=` path rule, and why the test must use the binarized build. Mesh assembly, LODs and textures belong to the dayz-model-pipeline and `dayz-texture-pipeline` skills; packing belongs to `/dayz-build-pbo`.

Everything here was measured in game on one custom weapon build, a 7.62x39 rifle made from an AI generated mesh that inherits a third-party weapon pack (the first build that rendered is called v12c below). That is third-party mod behaviour, not vanilla: the rifle's files are not on `P:\`, and the measurements have not been repeated on a second weapon. Marks: `[VERIFIED in-game]` means measured in game on that rifle, `[UNVERIFIED]` means inferred. For checking face winding on any model see `skills/dayz-p3d-audit/references/winding-methodology.md`.

## The import rule

`[VERIFIED in-game]` on the rifle, build v12c:

> A pure swap (x,y,z) to (x,z,y), determinant -1, with normals treated as pseudovectors (-S·n), `REVERSE_WINDING=False`, and the build served binarized. Binarize flips the winding (100% of faces) and passes normals through as they are. Target pattern (the vanilla `akm.p3d` as binarized): about 70% of faces pointing outward, and stored normal dot geometric normal about -0.98.

Where it comes from: the Blender weapon frame is long along X (muzzle toward -X), Z up, Y sideways (right is +Y); the swap turns Blender's Z up into DayZ's Y up.

**The check.** A model passes when at least 60% of faces point outward and stored dot geometric is -0.85 or lower. v12c measured 63.2% and -0.88, a pass. Agentic-Z ships no script that prints these two numbers; `skills/dayz-p3d-audit/references/winding-methodology.md` describes how to measure winding. Do not go back to iterating winding and normals: check future changes offline against the AKM pattern with the same two numbers, and with the model path check below.

**Derive the swap again for each weapon; never copy it.** The second custom weapon, a 9x19 SMG, has a different Blender frame: long axis Y, muzzle toward -Y, Z up, so its import swap was derived again and validated against the same pass band. The rifle's swap applied to the SMG would flip it the wrong way. Derive the frame from the actual Blender file and validate against the same AKM pattern.

## W-BUILD1: the model path

`[VERIFIED in-game]` on the rifle. This was the root cause of every failed build from v1 to v12b:

- `config.cpp` had `model=` pointing at `\<Mod>\<weapon>.p3d` (the PBO root), but the `.p3d` lives under `data\`.
- Builds made without a clean temp folder carried an old unbinarized copy of the `.p3d` at the PBO root. That was the model the engine loaded, which made every offline winding and normal measurement meaningless: they described the binarized model while the game showed the raw one. It also means the difference between "pack only" and "binarize" measured for builds v6 to v11 was not real; all of those builds ran the root copy.
- The clean build v12 removed the old copy, `model=` then resolved to nothing, and the result was "invisible, and a crash on equip or on opening the inventory". Three unrelated theories were disproved with data before the real fix.
- Fix: `model="\<Mod>\data\<weapon>.p3d"` and a clean rebuild, v12c, the first build whose binarized model actually rendered.

**The rule:** `model=` points at the real path inside the PBO (under `data\`), and the build runs with a clean temp folder after any change to the folder structure (`/dayz-build-pbo <ModName> --clean`). `/dayz-lint` reports a `model=` path that names no file in the mod as `missing-model`. Check the config `model=` against the PBO's contents on each build.

## W-BUILD2: test the binarized build; use the retail game for a pack with loose scripts

`[VERIFIED in-game]` on the rifle:

- **Serve the binarized build.** The winding and normals rule above is only correct on the binarized model, because binarize flips the winding. A build that serves the unbinarized model measures the wrong thing.
- **Retail game, not the Diag build, for a mod built on a weapon pack with loose scripts.** The third-party weapon pack the rifle inherits from uses script without braces (`override typename GetInputType() return X;` in its optic and weapon scripts) that the strict compiler of the Diag build rejects as an error while the retail build accepts it with a warning. Other third-party mods in a load order can fail on the Diag build the same way. This is a note about the test environment; it is repeated here because it decides whether the weapon can be tested at all. `/dayz-launch-test` starts the Diag build.

A launcher for such a weapon enforces both: retail executable, clean build, binarized PBO.

## Build order, entity side

1. Assemble the `.p3d` with the swap derived for this weapon and validated against the binarized AKM pattern (at least 60% outward, stored dot geometric -0.85 or lower). Mesh assembly and LODs: the dayz-model-pipeline skill.
2. `config.cpp`: `model="\<Mod>\data\<weapon>.p3d"`, the real path inside the PBO (W-BUILD1).
3. Build binarized with a clean temp folder: `/dayz-build-pbo <ModName> --clean`.
4. Test with the retail game when the mod is built on a weapon pack with loose scripts (W-BUILD2).

## Cite, then verify

The swap direction, the pass band and the model path are all easy to half remember, and each cost the rifle many builds. Read the measured values again and run the outwardness check again before calling a winding change good; never trust a swap copied from another weapon.
