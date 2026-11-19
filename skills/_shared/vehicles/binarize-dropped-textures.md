# Textures dropped by binarize

Why a vehicle that looks right with file patching renders white or untextured on a dedicated server, which assets the binarize step does not pack, and the two ways to ship them.

`/dayz-build-pbo` passes its own `include.lst`, which already lists `*.paa` and `*.rvmat`. The traps below hit a hand-written or scripts-only include list. The AddonBuilder behaviour is **tool knowledge**, measured on test vehicle builds, not read from `P:\`.

## Binarize packs only what the model references

AddonBuilder's binarize step packs the assets the `.p3d` geometry references. Assets named only in `config.cpp` are not tracked and are left out of the PBO:

| Config key | What it holds | Vanilla example |
|---|---|---|
| `hiddenSelectionsTextures[]` | Swappable body, colour and seat textures | `P:\DZ\vehicles\wheeled\config.cpp:1292` |
| `hiddenSelectionsMaterials[]` | Paint, seat and light `.rvmat` files | `:1314` |
| `frontReflectorMatOn` and `Off`, `brakeReflectorMatOn` and `Off`, `ReverseReflectorMatOn` and `Off`, `TailReflectorMatOn` and `Off`, `dashboardMatOn` and `Off` | Light and dashboard material switches | `dashboardMatOn`, `dashboardMatOff` and `frontReflectorMatOn` at `:1336` to `:1338` |

The body paint uses the `color` selection, a paint `.rvmat` plus a `_co.paa`, both named only in config. Both go missing, so the largest surface of the car turns white. On a test vehicle, 26 such assets in the source folder were missing from the binarized PBO, while a pack only PBO held all of them.

File patching hides the fault: it loads loose files from the mod folder, where every asset exists. The PBO is only used once the mod is deployed, so the fault stays hidden until a real server loads it. This is not a `P:\` path problem (`build-packaging-and-debug.md`).

## An include list replaces the default copy list

AddonBuilder's `-include` is not added to its default copy list; it becomes the only list. A scripts-only list (`*.c;*.asi;*.anm`) silently drops every `.paa` and `.rvmat` the geometry does not reference, which includes the body textures and materials named only in config. On a test car this dropped 47 files, 28 `.paa` and 19 `.rvmat`, all body swatches.

For a binarize build use `*.c;*.asi;*.anm;*.paa;*.rvmat`. Then compare the PBO's file list with the source tree by extension: `config.cpp` turning into `config.bin` is fine, a baked `model.cfg` is fine, and every `.p3d`, `.paa`, `.rvmat` and `.c` must be there.

Binarize also drops an authored ShadowVolume LOD at resolution 1e4: the binarized vanilla sedan (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`) has none (**model knowledge**). An authored shadow LOD ships only through MLOD, that is a pack only build. If you move to ODOL, check shadows in game again before trusting the face budget.

## Two fixes

Choose by whether the model must be protected.

- Pack only. `AddonBuilder <src> <dst> -prefix=<Mod> -packonly` copies the whole folder without binarizing. Every asset ships, the `.p3d` stays MLOD and `config.cpp` stays text. Nothing can be left out by asset tracking, but the model can be read back and the config ships in clear.
- Binarize with `-include`. Pass `-include=<list.lst>` covering `*.paa;*.rvmat` so the loose assets are copied next to the binarized geometry. The `.p3d` stays ODOL and every texture ships. A malformed or ignored include list rescues nothing and gives no warning, so check the result.

Check the PBO's contents before you hand it out, whichever fix you use (`build-packaging-and-debug.md`). A clean build log does not mean the assets are in.
