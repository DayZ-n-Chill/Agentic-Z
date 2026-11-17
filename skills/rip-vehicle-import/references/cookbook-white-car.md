# Cookbook: white car

For a family B car that renders white or untextured on a dedicated server: the AddonBuilder include list that drops textures, which assets binarize does not track, and the two fixes.

The AddonBuilder behaviour and the SUB_BRZ and LFQuad measurements are not yet checked on `P:\`; the config keys named below cite a vanilla example on `P:\`. In this repo `/dayz-build-pbo` passes its own `include.lst`, which already lists `*.paa` and `*.rvmat`; the trap below is for a hand-written or scripts-only include list.

## AddonBuilder `-include` replaces its default copy list

Added 2026-07-06 from the SUB_BRZ binarize experiment.

A binarize build that has scripts and assets must list `*.paa;*.rvmat` too, or the PBO ships without textures: the white car. The usual scripts-only include file (`*.c;*.asi;*.anm`) is not additive. It becomes the only copy list and silently drops every `.paa` and `.rvmat` that config.cpp does not reference. Measured on SUB_BRZ: 47 files dropped (28 paa and 19 rvmat, all body swatches), a PBO of 8.7 MB instead of 11.6 MB, and the classic white car on a dedicated server.

Use `-include` with `*.c;*.asi;*.anm;*.paa;*.rvmat` for binarize builds. Then diff the entry list of the PBO that came out against the source tree by extension, with explicit allowances: `config.cpp` becoming `config.bin` is fine, a baked `model.cfg` is fine, and every `.p3d`, `.paa`, `.rvmat` and `.c` is required. The import project's wrapper with that diff is `<vehicle-import>\scripts\rip_binarize_experiment.ps1`.

A related fact from the same experiment, verified against the vanilla civiliansedan ODOL (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`): binarize drops the authored ShadowVolume LOD at resolution 1e4. An authored shadow LOD ships only through MLOD or a pack-only build. If you adopt ODOL, check the shadows in game again before trusting the budget.

## Binarize drops config-only assets

**Symptom.** The vehicle renders white or untextured on a dedicated server but looks correct with local file patching. This is the most common "ships broken" failure of an imported vehicle. It is not a `P:\` path problem (the `P:\` paths section of the packaging and debug topic in the vehicles pack, `skills/_shared/vehicles/build-packaging-and-debug.md`).

**Root cause.** AddonBuilder's binarize dependency tracker packs only the assets the geometry (`.p3d`) references. Assets declared only in `config.cpp` are not tracked and are left out of the PBO:

- `hiddenSelectionsTextures[]`, the swappable body, colour and seat textures (vanilla example: `P:\DZ\vehicles\wheeled\config.cpp:1292`; in LFQuad's own config at its lines 290 to 304).
- `hiddenSelectionsMaterials[]`, the paint, seat and light `.rvmat` files (vanilla example: `P:\DZ\vehicles\wheeled\config.cpp:1314`; LFQuad lines 305 to 319).
- The reflector material switches `frontReflectorMatOn/Off`, `brakeReflectorMatOn/Off`, `ReverseReflectorMatOn/Off`, `TailReflectorMatOn/Off` and `dashboardMatOn/Off` (vanilla example: `dashboardMatOn` and `frontReflectorMatOn` at `P:\DZ\vehicles\wheeled\config.cpp:1336-1338`; LFQuad lines 320 to 329).

The body paint uses the `color` selection, which maps to `B_PAINT.rvmat` plus a `*_co.paa`. Both are config-only, so both are missing from the PBO and the largest visible surface of the vehicle goes white. Measured on LFQuad: 26 such assets present in the folder were absent from the 5.4 MB binarized PBO, and the 18 MB pack-only PBO had all of them.

**Why file patching hides it.** File patching loads the loose files from the mod folder, where every asset exists. The PBO is exercised only on deploy, so the bug stays invisible until a real server loads it.

**Fixes.** Either works; choose by whether the model must be protected.

- **Pack only.** `AddonBuilder <src> <dst> -prefix=<Mod> -packonly` copies the whole folder with no binarize. Every asset ships, the `.p3d` stays MLOD and `config.cpp` stays text. It is the simplest option and has no asset tracking to get wrong. The cost: the model can be debinarized and the config ships in clear.
- **Binarize plus `-include`.** Pass `-include=<list.lst>` covering `*.paa;*.rvmat` so the loose assets are copied next to the binarized geometry. This keeps the `.p3d` as ODOL (protected) and still ships every texture. The cost: you must verify the result. A malformed or ignored include list rescues nothing, with no warning, and you ship the same broken PBO.

Always verify the PBO before distributing it (the PBO verification section of the same packaging and debug topic). A green build log does not mean the assets are in.
