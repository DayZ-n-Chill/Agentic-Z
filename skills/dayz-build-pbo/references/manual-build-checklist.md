# Manual build checklist

What to tick by hand before and after a build when the automated checks are not available. `/dayz-lint` and `/dayz-p3d-audit` cover most of the blocks before the build; the reasons behind each line are in `pre-build-checks.md` and the files it indexes.

## Folder structure

- [ ] `config.cpp` exists at the addon root.
- [ ] `$PBOPREFIX$` exists as a one-line text file, not a folder.
- [ ] `$PBOPREFIX$` uses backslashes and has no trailing slash (`mymod\myaddon`; for `/dayz-build-pbo`, exactly `<ModName>`).
- [ ] No spaces in folder or file names.
- [ ] No upper-case extensions (`.PAA`, `.CPP`).
- [ ] No stale files: `.bak`, `.blend`, `.psd`, `.xcf`, `.tmp`, `.swp`.
- [ ] `data/` holds the textures and models, and `scripts/` the `.c` files when the mod has scripts.

## `config.cpp`

- [ ] All braces balance, and every property ends with a semicolon.
- [ ] `CfgPatches` exists with at least one patch class, and each patch has `units[]`, `weapons[]`, `requiredVersion` and `requiredAddons[]`.
- [ ] No class name defined twice, and no member defined twice in one class (1.30).
- [ ] Parent class names are right (for example `ItemBase`, `Clothing_Base`).
- [ ] `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` each have as many entries as `hiddenSelections[]`. This is a habit, not an engine rule: vanilla `Flashlight` (`P:\DZ\gear\tools\config.cpp:261`) has a shorter material array (`:278` to `:295`).

## `model.cfg`, when present

- [ ] `CfgModels` class names match the `.p3d` file names.
- [ ] Every bone in `CfgSkeletons` is unique.
- [ ] Animation selections exist as named selections in the `.p3d`.
- [ ] Animation axis memory points exist in the `.p3d` (for example `axis_lever`, `axis_lever_end`).
- [ ] Animation sources match `AnimationSources` in `config.cpp`.

## Textures and materials

- [ ] Every referenced `.paa` and `.rvmat` exists.
- [ ] Texture paths use the capitalisation of the files on disk.
- [ ] No `.png` or `.dds` is referenced; convert them to `.paa`.
- [ ] Each `.rvmat` names textures that exist.

## LODs

- [ ] At least one resolution LOD (LOD 0.0), a Geometry LOD and a Memory LOD. A `ce_center` point there is optional; without it script uses the object's origin (`asset-checks.md`, "LODs").
- [ ] Every Geometry component has a mass above 0.
- [ ] Named selections match across LODs.
- [ ] LOD0 stays under about 3,000 vertices for a small item.
- [ ] No zero-area faces.

## Stringtable

- [ ] When `#STR_` references exist, `stringtable.csv` is at the addon root.
- [ ] Every `#STR_` key used has a row, with the key in column 1 without the leading `#`.
- [ ] The header row carries the seven columns `Language`, `original`, `english`, `spanish`, `german`, `russian`, `chinesesimp`. Measured in game: a four-column header leaves every key unresolved while the PBO mounts and serves files.
- [ ] The file is UTF-8 with no BOM and LF line endings, header row first.
- [ ] Every language has an entry for each key, and no key goes unused.
- [ ] The built PBO holds `stringtable.csv`: a binarizing pass without `*.csv` in its include list drops it, as it drops `.c`. The `include.lst` of `/dayz-build-pbo` lists both.

## Scripts

- [ ] No ternary (`condition ? a : b`); use `if` and `else`.
- [ ] No `+=` on arrays; use `.Insert()` or `.InsertAll()`.
- [ ] Every `#include` points at an existing file.
- [ ] No `GetGame()` in a destructor without a null check.
- [ ] No endless loop without a `break`.
- [ ] All strings closed; no stray tokens or unclosed braces.

`++`, `--` and `foreach` are not on this list because vanilla uses them (`foreach` at `P:\scripts\3_game\tools\cameratools.c:14`, `last_index++` at `P:\scripts\3_game\tools\tools.c:200`).

## After the build

- [ ] List, count and name the entries of the built PBO; never infer them from `include.lst`.
- [ ] Expect `config.cpp`, `.p3d` and face-referenced `.rvmat` to enter even without a matching `-include` suffix.
- [ ] The ordinary `.c`, `.paa`, `.ogg`, `.layout` and `.csv` payload matches the source tree by count and name.
- [ ] Every `.rvmat` that `config.cpp` names is present, including materials no `.p3d` face cites.
- [ ] Treat a suffix in the include list as intent only; the built PBO's contents decide.

`build.py` lists the entries and compares the payload on every build (`post-build-gates.md`); the `.rvmat` check is manual.
