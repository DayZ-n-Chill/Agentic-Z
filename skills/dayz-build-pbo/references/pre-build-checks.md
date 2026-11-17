# Pre-build checks for a DayZ addon

What to check in a mod folder before it is packed: folder structure, `config.cpp`, `model.cfg`, texture and
material paths, `.p3d` LODs, the stringtable, scripts and vehicle wheel slots, with the report format, the
`$PBOPREFIX$` rules and a manual checklist.

Not yet checked on `P:\`: unless a line cites a vanilla file, what follows is measured tool and build
behaviour (AddonBuilder, binarize, the game's loader) and findings from mod projects, not vanilla data.

## What `/dayz-build-pbo` already runs

| Check below | Run by | Notes |
|---|---|---|
| 1 Folder structure | `/dayz-lint` (inside `/dayz-build-pbo`) | `config.cpp`, `$PBOPREFIX$`, the `P:\` link, missing files and bad suffixes. Of the stale files, `.bak` and `.psd` are dropped by `exclude.lst`; `.blend`, `.xcf`, `.tmp` and `.swp` stay out because `include.lst` has no pattern for them. Spaces, upper-case extensions and large files are manual. |
| 2 `config.cpp` | `/dayz-lint` | Syntax, `CfgPatches`, `requiredAddons`, script modules. Duplicate members (1.30) stop binarize; `build.py` then prints the binarize error from AddonBuilder's log. |
| 3 `model.cfg`, 5 `.p3d` LODs, 8 wheel slots | `/dayz-p3d-audit` | Run it by hand before a build; `/dayz-build-pbo` does not call it. |
| 4 Texture and material paths | `/dayz-lint` (missing files) and `/dayz-p3d-audit` | A reference starts with the PBO prefix and resolves from the `P:\` root, not from the addon folder. Capitalisation and `.png`/`.dds` checks are manual. |
| 6 Stringtable | none | Manual, or the validator shape in `validation-scripts.md`. |
| 7 Scripts | `/dayz-lint` (modules, modded classes, then the code rules of the script validator in `scripts/tools/dayz-script-validator/`) | A code error already stops the build. Run the validator separately only to pass `--external-scripts` or to compare before and after a change; see `script-linter-and-compile-gate.md`. |

Version note. Until 1.29: the folder structure, `stringtable.csv`, include list and duplicate class name check
below are the 1.29 contract. Since 1.30: binarize also **stops** when a member is defined more than once in one
class, and an unpacked `-mod` folder is a diag iteration path, not a substitute for a shipped PBO. Details:
`dayz-1-30-pbo-build.md`.

## Overview

A pre-build review walks seven checks in sequence over a DayZ addon folder (check 8 applies to vehicles only):

1. **Folder Structure** – Required files ($PBOPREFIX$, config.cpp), naming conventions, stale files
2. **config.cpp Syntax** – Brace balance, semicolons, class hierarchy, hiddenSelections matching
3. **model.cfg Validation** – Skeleton bones, named selections, animation references
4. **Texture/Material Paths** – Every .paa and .rvmat exists and is accessible
5. **.p3d LOD Structure** – LOD types, geometry mass, vertex budgets, named selections consistency
6. **Stringtable Completeness** – All #STR_ keys present and accounted for
7. **Script Validation** – Enforce Script syntax, #include paths, common pitfalls

Each check reports **PASS**, **WARN**, or **FAIL** status. The final summary shows all blockers before packing.

---

## Validation Checks (Detailed)

### 1. Folder Structure Validation

**Checks performed:**
- **REQUIRED:** `config.cpp` exists at addon root (a 1.30 `gui`-prefix shadow PBO holding only layouts loaded without one on 1.30.164289: `dayz-1-30-pbo-build.md`)
- **REQUIRED:** `$PBOPREFIX$` file exists (single line: `mymod\myaddon` format)
- **RECOMMENDED:** `data/` folder (for textures, .rvmat, .p3d files)
- **RECOMMENDED:** `scripts/` folder (for .c, .cpp, .h files)
- **REQUIRED:** No spaces in folder names (DayZ tools reject these)
- **REQUIRED:** No uppercase file extensions (.PAA, .CPP are flagged)
- **FAIL:** Stale files found (.bak, .blend, .psd, .xcf, .tmp, .swp—these bloat PBOs)
- **WARN:** Large asset files > 10MB (texture atlases, unoptimized meshes)
- **Release package (manual; the checks above do not run it):** every class a player places, or that otherwise
  persists in the world, has an entry with an explicit lifetime in the `types.xml` the release ships. Without
  one it runs out after 30 to 60 minutes of server time (the dayz-persistence skill,
  `references/lifetime-and-storage.md`).
- **Publishing to the Workshop (manual):** signing with DsUtils, the item folder, the Publisher or SteamCMD,
  and why a SteamCMD login with the Steam client's account kicks that client off: `workshop-publish.md`.
  On Linux (dayzmake, `meta.cpp`, Workshop tags, the `workshop` uploader): `dayzmake-linux.md`.
- **REQUIRED (the mod folder, after the build):** every PBO sits in `@Mod/addons/`. A PBO at the mod folder root
  (`@MyMod/MyMod.pbo`) is silently ignored: no config, no scripts, no error, while the folder still shows in the
  boot log's `ANIMATION (E): Can't load @MyMod/...` pass, which is not loading. Its `modded class` overrides then
  silently never run, and an A/B test of a fix reads as "the fix did not work". Measured on the native
  Linux 1.30 server; the probe that proves it is in `dayz-test-ingame/references/linux-native-server.md`,
  section 4. The Workshop Publisher also refuses an upload with PBOs outside `addons/`.

**Example output:**
```
[PASS] config.cpp found at addon root
[PASS] $PBOPREFIX$ file present: mymod\myaddon
[WARN] .blend file found: data\model_source.blend (should not be packed)
[PASS] Folder names follow conventions (lowercase, no spaces)
```

---

### 2. config.cpp Syntax Validation

This check is critical—most DayZ mod failures start here.

**Checks performed:**
- **Brace balance:** Count `{` and `}` to detect unclosed classes
- **Semicolons:** Every class property and array must end with `;`
- **Required CfgPatches class:**
  - Must exist with at least one patch subclass
  - Each patch should have `units[]`, `weapons[]`, `requiredVersion` and `requiredAddons[]`, as vanilla `CfgPatches` at `P:\DZ\gear\tools\config.cpp:1` does. The engine tolerates a patch without them: vanilla `DZ_data_aiconfigs` at `P:\DZ\data\aiconfigs\config.cpp:3` has an empty body. `/dayz-lint` warns on a missing `units[]` or `weapons[]`, fails on a missing `requiredAddons[]` (without it the load order after the vanilla classes the mod changes is not guaranteed), and does not check `requiredVersion`.
- **Class inheritance verification:**
  - Validate parent classes exist (e.g., Inventory_Base, Container_Base, Land_Stone_*)
  - Warn if parent class is not a known DayZ base (may not exist in vanilla)
- **hiddenSelections matching (warning, not a requirement):**
  - `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` are each read index-by-index against `hiddenSelections[]`, so entry N retextures selection N. Giving each array (when present) the same length as `hiddenSelections[]` is a mod-side recommendation that makes every selection's texture and material explicit
  - The engine accepts a shorter array: vanilla `Flashlight` at `P:\DZ\gear\tools\config.cpp:278-295` has 4 `hiddenSelections` entries, 4 `hiddenSelectionsTextures` entries and 1 `hiddenSelectionsMaterials` entry. A length mismatch is a WARN, never a FAIL
  - Simple vanilla shape: one `hiddenSelections` entry at `P:\DZ\gear\tools\config.cpp:79` and one `hiddenSelectionsTextures` entry at `P:\DZ\gear\tools\config.cpp:83`
  - Example: `hiddenSelections[] = {"skin1", "skin2", "metal"}` (3 items) → `hiddenSelectionsTextures[]` has 3 entries and `hiddenSelectionsMaterials[]` has 3 entries
- **AnimationSources reference check:**
  - Any AnimationSource defined here must be referenced in model.cfg (if model.cfg exists)
- **Duplicate class names:** Same class cannot be defined twice
- **Duplicate members (since 1.30):** Same member cannot be defined twice inside one class body — binarizer **stops**. Not the same as `class Foo;` forward + `class Foo: Bar {}` definition. See `common-validation-failures.md` and `dayz-1-30-pbo-build.md`.
- **No syntax helpers:** Reject obvious Python/macro syntax in .cpp (these get missed at compile time)

**Example output:**
```
[FAIL] config.cpp line 15: Unclosed brace (expected 0, found 1 extra {)
[FAIL] config.cpp line 42: Missing semicolon after property "units[]"
[PASS] CfgPatches structure valid (1 patch: MyMod_Item01)
[WARN] Class inheritance: parent "CustomBase_Broken" not recognized (may not exist)
[PASS] hiddenSelections arrays aligned (3 selections, 3 textures, 3 materials)
[FAIL] Duplicate class name "Item_Torch" defined at lines 28 and 105
[FAIL] Duplicate member "scope" defined twice in class "MyItem" (1.30 binarizer stop)
```

---

### 3. model.cfg Validation

Only checked if `model.cfg` exists in the addon.

**Checks performed:**
- **CfgSkeletons section:**
  - Every bone listed in `skeletonBones[]` must exist
  - Check that bone names follow DayZ naming conventions (lowercase with underscores)
  - Verify no circular parent references
- **CfgModels section:**
  - Class name must match the .p3d filename (case-sensitive: `Item_Compass` class → `Item_Compass.p3d`). **Mismatch is silent and severe:** the engine falls back to `CfgModels.Default` (no skeleton/sections) for that model, so a WEAPON's attachment proxies stop rendering — attachments still attach (visible in slots) and the standalone item still renders in the world, but are INVISIBLE on the weapon (in-hands, inventory preview, ground), with NO RPT error. Common trigger: renaming a model `.p3d` (e.g. `body.p3d`→`body_raised.p3d` for a grip tweak) without updating CfgModels. Fix: `class <new>: <old> {};`. Re-run this check after ANY model rename.
  - Each class inherits `Default` or another class declared in the same `CfgModels`
- **Animations within CfgModels:**
  - `selection` must exist as a named selection in the corresponding .p3d
  - `axis` must exist as a memory point pair in the p3d (e.g., `axis_lever`, `axis_lever_end`)
  - `source` must match an AnimationSource name from config.cpp
- **Memory point pairs:** Any animation with `axis` requires matching memory points in p3d

**Example output:**
```
[PASS] Skeletons defined correctly (5 bones)
[FAIL] model.cfg class "Item_Watch" doesn't match .p3d filename (found: Item_WatchGold.p3d)
[WARN] Animation "door_open": selection "door_frame" not found in named selections
[FAIL] Animation "lever_rotate" references axis "lever_axis_end" (axis endpoint not found in p3d)
[PASS] Animation source "click_anim" matches config.cpp AnimationSources
```

---

### 4. Texture/Material Path Validation

Scans all texture references and verifies files exist.

**Checks performed:**
- **Scan sources:**
  - config.cpp: `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`, any quoted `.paa` or `.rvmat`
  - .rvmat files: extract referenced texture paths
  - .p3d face textures (if py3d available)
- **Path existence:**
  - Every referenced `.paa` and `.rvmat` file MUST exist. A reference is a root path that starts with a PBO
    prefix, not a path relative to the addon: vanilla writes `"dz\gear\tools\data\alarmclock_blue_co.paa"`
    (`P:\DZ\gear\tools\config.cpp:85`), and a mod with prefix `mymod\myaddon` writes
    `"mymod\myaddon\data\body_co.paa"`. Resolve it from the `P:\` root, where the addon sits at `P:\<prefix>`
  - Paths are case-sensitive on Linux/server (always check capitalization)
- **File format checks:**
  - WARN if `.png` file referenced (should be `.paa` for DayZ)
  - WARN if `.dds` file referenced (use `.paa` instead)
  - .rvmat must reference valid texture paths within the addon or from common DayZ paths
- **Texture atlas validation:**
  - If multiple selections reference the same texture, verify texture has enough area for all UVs

**Example output:**
```
[FAIL] Texture not found: mymod\myaddon\data\textures\body_co.paa (referenced in config.cpp line 45, class Item_Shirt)
[WARN] PNG file detected: data\textures\logo.png (convert to PAA for better compression)
[PASS] All 12 texture references validated and found
[WARN] Texture path capitalization: referenced as "Textures\Cloth_Co.paa" but file is "textures\cloth_co.paa"
[PASS] .rvmat materials reference valid texture paths
```

---

### 5. .p3d LOD Structure Validation

Only checked if py3d is available and .p3d files exist.

**Checks performed:**
- **LOD types present:**
  - REQUIRED: At least 1 Resolution LOD (LOD 0.0) for in-game appearance
  - REQUIRED: Geometry LOD for collision/physics
  - REQUIRED: Memory LOD (named selections + memory points)
- **Geometry LOD integrity:**
  - All components must have mass > 0 (0 mass = ignored by engine)
  - Faces must not be zero-area (degenerate triangles)
  - Warn if geometry LOD vertices > 3000 for small items (performance impact)
- **Memory LOD:**
  - Should have the `ce_center` memory point (the object's centre for actions and the vicinity list, read by `GetCenter` at `P:\scripts\3_game\entities\object.c:1363`; it is not the centre of mass)
  - No collision check here: collision comes from the Geometry LOD above, not from memory points (a byte scan of all 8,256 vanilla models under `P:\DZ` finds no `ce_geom` point)
- **Named selections:**
  - Consistent across LODs (if named_sel exists in LOD0, should exist in LOD2)
  - Warn if asymmetric (e.g., "Left_Arm" exists but no "Right_Arm")
- **Vertex count budgeting:**
  - LOD0: up to 3000 vertices for small items (warn if higher)
  - LOD1: 40-60% of LOD0
  - LOD2 (far): 10-20% of LOD0

**Example output:**
```
[PASS] All required LOD types present (Resolution + Geometry + Memory)
[PASS] Geometry LOD mass valid (all components > 0)
[FAIL] Memory LOD missing ce_center point
[WARN] LOD0 vertex count: 4200 (high for small item, consider optimization)
[PASS] Named selections consistent across LODs (8 selections)
```

---

### 6. Stringtable Validation

DayZ uses **`stringtable.csv`**, not the `stringtable.xml` of Arma 3. Measured on a DayZ
mod project tree: zero `stringtable.xml`, 38 `stringtable.csv`, and the two deployed PBOs
checked each carry `stringtable.csv` and no XML. Following the XML form produces a
file the engine never reads, and the engine does not complain — an unresolved key prints
its own name and logs **nothing** (measured: zero RPT lines for a missing key across a
49,340-byte client log), so this fails silently all the way to the player's screen.

**Format**, as two shipping mods carry it: a header row `"Language","original","english",…` followed
by one row per key. The key sits in column 1 **without the leading `#`** — the `#` belongs
only to the reference in code, config or `.layout`. UTF-8, no BOM, LF.

**An unresolved stringtable is a CSV-header problem, not an addon-size problem.** Measured
in game on 2026-08-21 with two bisection ladders: a three-file addon
(`$PBOPREFIX$` + minimal config.cpp + stringtable.csv) resolves its keys, and two data
rows are enough — provided the CSV carries the full 7-column reference header
(`"Language","original","english","spanish","german","russian","chinesesimp"`). With a
4-column header (no german/russian/chinesesimp) every key stays unresolved at any corpus
size, even though the PBO mounts and serves files and the client's own language column is
present with text. Fill untranslated columns with the english text. The size of the addon
is not the cause. Full rule and evidence:
`skills/dayz-ui-development/references/localization.md`.

Vanilla's own header, for comparison, starts with `"Language","original","english"` and carries 15 columns, the
four named above among them (`P:\languagecore\stringtable.csv:1`).

**Checks performed:**
- **Scan all script files (.c, .cpp) for `#STR_` references**
- **Scan config.cpp and every `.layout` for `#STR_` references** (displayName, description,
  and widget `text` alike)
- **`stringtable.csv` existence:**
  - If `#STR_` found but no `stringtable.csv` → FAIL
  - If it exists, check the header row and that every data row has the same column count
- **Key coverage:**
  - Every `#STR_KEY` referenced must appear in column 1 of some `stringtable.csv`, minus the `#`
  - WARN about orphaned keys (defined in stringtable but never used)
  - Prefer a mod-specific key prefix: names like `STR_UI_YES` invite collisions with other mods
- **Language completeness:**
  - Check that all languages (English, Russian, etc.) have values for each key
  - WARN if translation is missing or empty

**Example output:**
```
[FAIL] stringtable.csv not found, but 5 #STR_ references in config.cpp
[PASS] stringtable.csv header valid (7 columns, every row matches)
[FAIL] Missing key: #STR_MYMOD_DEVICE_NAME (used in config.cpp line 23)
[WARN] Orphaned key: #STR_OLD_DESCRIPTION (defined in stringtable but never referenced)
[WARN] Incomplete translation: Russian text missing for #STR_ITEM_DESC (only English present)
[PASS] All 12 #STR_ references have stringtable entries
```

---

### 7. Script Validation (Basic)

`/dayz-build-pbo` already runs the script validator's code rules through `/dayz-lint`; how to run it on its own
and how to read its result is in `script-linter-and-compile-gate.md`. The heuristics below are the fallback when
the validator is not available, and a useful second pass when it is.

Checked if scripts exist in `scripts/` folder.

**Checks performed:**
- **Enforce Script (real gotchas; the language supports `++`/`--` and `foreach`, see the note after the examples):**
  - No ternary (`cond ? a : b`): write `if`/`else`
  - Add to arrays with `.Insert()` / `.InsertAll()` (no array `+=` concatenation operator)
  - No bare function calls without assignment or statement context
- **#include path resolution:**
  - Every `#include "path/file.h"` must point to existing file
  - Check both relative and absolute paths
- **Common pitfalls:**
  - `GetGame()` used in destructors without null check
  - `Print()` left in debug code (warn, not fail)
  - Infinite loops detected (while true without break)
  - Missing return statements in non-void functions
- **Syntax basics:**
  - Unclosed strings, invalid escape sequences
  - Invalid class declarations or stray tokens

**Example output:**
```
[WARN] scripts/Item_Base.c line 42: array '+=' concatenation not supported - use .InsertAll()
[PASS] No #include path errors (5 includes resolved)
[PASS] No unsupported array '+=' concatenation
[WARN] scripts/Item_Base.c line 103: GetGame() called in destructor without null check
[FAIL] #include "scripts\missing.h" not found
[PASS] Script syntax valid (no orphaned braces or quotes)
```

Ternary, `++` and `foreach`: on `P:\scripts` a search of every `.c` file finds no ternary, which
matches `skills/_shared/enscript/patterns/language_workarounds.md` ("No vanilla script uses `cond ? a : b`").
`foreach` and `++` are vanilla: `foreach` at `P:\scripts\3_game\tools\cameratools.c:14`, `last_index++` at `P:\scripts\3_game\tools\tools.c:200`.
So a check flags ternary and must not flag `++`, `--` or `foreach`.

---

### 8. Wheeled-vehicle wheel-slot <-> FireGeometry consistency (P1, release-blocking)

Vehicles only. For PhysX to seat a wheel (`WheelCountPresent() > 0`), the selection
named by `config.cpp > CfgSlots > <wheel-slot>.selection` MUST exist in the body's
**FireGeometry LOD**. A selection present only in visual LODs binds the slot as
inventory but the wheel never simulates: `WheelCountPresent()=0`, no traction, no
spin, NO RPT error - a silent killer (see `references/vehicle-scripting.md` of the enforce-script-reference
skill and rule 20 in `references/critical-rules.md` of the dayz-model-pipeline skill).

This check lives in the `dayz-p3d-audit` validator. Run it pre-build and
treat a CRITICAL as release-blocking:

```
python "<skill-dir>\..\dayz-p3d-audit\scripts\audit_p3d.py" --scan-dir P:\<Mod>
```

`--scan-dir` auto-discovers the mod's `config.cpp` and cross-checks every wheel
slot's selection against the body FireGeometry. Outcomes:
- CRITICAL `Wheel-slot selection '<n>' (from CfgSlots) is missing from Fire Geometry LOD[<i>]`
  -> the wheel will not simulate. **BLOCK the release**; add the Fire Geometry wheel proxy
  face to a selection named `<n>` with py3d, keeping its other selections, before packing.
- NOTE `Wheel-slot check not run: ...` -> the mapping could not be read (a config that
  reuses the vanilla wheel slots has no `CfgSlots` of its own); verify by hand.

`audit_p3d.py` exits 1 on any CRITICAL, so wiring `--scan-dir` into the pre-build
gate (alongside the config/texture/LOD checks above) blocks a silently-broken
vehicle from being packed. A wheeled body whose Geometry LOD lacks the named property
`class=vehicle` is reported as CRITICAL too; that is parity with vanilla, not what makes
the wheels simulate.

---
## Output Format

After all checks complete, write a structured report:

```
=================================
DayZ Addon Validation Report
=================================

Addon: mymod\myaddon
Path: P:\mymod\myaddon
Date: 2026-03-28

--- VALIDATION RESULTS ---

[PASS] Folder structure valid
  └─ config.cpp found
  └─ $PBOPREFIX$ correct (mymod\myaddon)
  └─ No stale files detected

[PASS] config.cpp syntax OK
  └─ 12 classes, 3 patches (CfgPatches valid)
  └─ All braces balanced, semicolons correct
  └─ hiddenSelections arrays have equal lengths

[WARN] model.cfg: animation "lever_rotate" references axis "lever_axis"
  └─ Verify this axis exists as memory point pair in Item_Watch.p3d

[FAIL] Texture not found: mymod\myaddon\data\textures\body_co.paa
  └─ Referenced in config.cpp line 45, class Item_Shirt
  └─ Expected at: P:\mymod\myaddon\data\textures\body_co.paa

[FAIL] stringtable.csv: missing key #STR_MYMOD_DEVICE_NAME
  └─ Used in config.cpp line 23, class Item_Device displayName
  └─ Add a row: "STR_MYMOD_DEVICE_NAME","Device Name","Device Name",...

[PASS] All textures and materials found (8 references)

[PASS] .p3d LOD structure valid
  └─ Item_Watch.p3d: LOD0 (2104 verts), LOD1 (800 verts), Geometry, Memory
  └─ All named selections consistent across LODs
  └─ Memory LOD has ce_center

[PASS] Scripts: no Enforce violations found (3 files checked)

--- SUMMARY ---
✓ 5 PASS
⚠ 1 WARN
✗ 2 FAIL

Status: BLOCKED - Fix 2 critical errors before packing
  1. Add P:\mymod\myaddon\data\textures\body_co.paa
  2. Add STR_MYMOD_DEVICE_NAME to stringtable.csv (column 1, no leading #)

Next: Run AddonBuilder after corrections are complete
```

---

## Quick Commands

Use these prompts to trigger specific validation paths:

| User Says | Checks Run |
|-----------|-----------|
| "validate my mod" | All checks |
| "check config.cpp" | Check 2 only |
| "check textures" | Check 4 only |
| "check my p3d" | Check 5 only |
| "is my mod ready for PBO?" | All checks, focused summary on blockers |
| "what's missing?" | All checks, emphasize FAILs |
| "validate for AddonBuilder" | All checks, suggest next steps |
| "I have config errors" | Check 2 with detailed line numbers |

---

## Understanding $PBOPREFIX$

The `$PBOPREFIX$` file is critical for DayZ's mod loading system.

**File location:** Addon root (same folder as config.cpp)
**File contents:** Single line, e.g.:
```
mymod\myaddon
```

**Rules:**
- Use backslashes `\` (not forward slashes)
- No trailing backslash
- No quotes or extra whitespace
- Must be unique across all addons (namespace collision = invisible mod), unless the PBO sets the 1.30 header property `fsShadowing=1` to shadow vanilla files on purpose (`dayz-1-30-pbo-build.md`)

**Example folder structure:**
```
DayZ_Addons\
  mymod\
    myaddon\
      config.cpp
      $PBOPREFIX$
      data\
        model.p3d
        texture.paa
      scripts\
        Item_Custom.c
```

With `$PBOPREFIX$` containing: `mymod\myaddon`

When packed, the PBO carries `prefix=mymod\myaddon` in its header. AddonBuilder names the file after the source
folder (`myaddon.pbo`), not after the prefix (`post-build-gates.md`, build appendices, item 3).

`/dayz-build-pbo` builds single-segment prefixes only: `$PBOPREFIX$` must hold exactly `<ModName>`. A nested
prefix such as `mymod\myaddon` is valid for the game but is refused by `build.py`.

---

---

## Manual checklist before a build

Tick these by hand when the automated checks are not available. `/dayz-lint` and `/dayz-p3d-audit` cover most of
the first five blocks.

**Folder structure**

- [ ] `config.cpp` exists at the addon root
- [ ] `$PBOPREFIX$` exists (a single-line text file, not a folder)
- [ ] `$PBOPREFIX$` content uses backslashes and has no trailing slash (`mymod\myaddon`; for `/dayz-build-pbo`, exactly `<ModName>`)
- [ ] No spaces in folder or file names
- [ ] No upper-case file extensions (`.PAA`, `.CPP`)
- [ ] No stale files: `.bak`, `.blend`, `.psd`, `.xcf`, `.tmp`, `.swp`
- [ ] `data/` holds textures and models
- [ ] `scripts/` holds the `.c` files, if the mod has scripts

**config.cpp**

- [ ] All braces are balanced
- [ ] Every property ends with a semicolon
- [ ] `CfgPatches` exists and has at least one patch subclass
- [ ] Each patch has `units[]`, `weapons[]`, `requiredVersion` and `requiredAddons[]`
- [ ] No duplicate class names, and no member defined twice in one class (1.30)
- [ ] Parent class names look correct (for example `ItemBase`, `Clothing_Base`)
- [ ] `hiddenSelectionsTextures[]` and `hiddenSelectionsMaterials[]` each have as many entries as `hiddenSelections[]` (recommended; vanilla `Flashlight` at `P:\DZ\gear\tools\config.cpp:278-295` shows the engine accepts a shorter array)

**model.cfg (if present)**

- [ ] Class names in `CfgModels` match the `.p3d` file names
- [ ] Skeleton bones in `CfgSkeletons` are all unique
- [ ] Animation selections exist as named selections in the `.p3d`
- [ ] Animation axis memory points exist in the `.p3d` (for example `axis_lever`, `axis_lever_end`)
- [ ] Animation sources in `model.cfg` match `AnimationSources` in `config.cpp`

**Textures and materials**

- [ ] All referenced `.paa` files exist
- [ ] All referenced `.rvmat` files exist
- [ ] Texture paths use the capitalisation of the files on disk
- [ ] No `.png` or `.dds` files are referenced (convert to `.paa`)
- [ ] `.rvmat` files reference valid texture paths

**.p3d LODs**

- [ ] At least one resolution LOD (LOD 0.0)
- [ ] Geometry LOD present
- [ ] Memory LOD present, with a `ce_center` point
- [ ] All geometry components have mass above 0
- [ ] Named selections are consistent across LODs
- [ ] LOD0 vertex count is reasonable (under 3000 for small items)
- [ ] No zero-area faces

**Stringtable**

- [ ] If `#STR_` references exist, `stringtable.csv` is at the addon root
- [ ] Every `#STR_` key used has a row in `stringtable.csv`
- [ ] The key sits in column 1 without the leading `#` (the `#` belongs only to the reference)
- [ ] `stringtable.csv` is UTF-8 with no BOM, LF line endings, header row first
- [ ] All languages have an entry for each key
- [ ] No orphaned keys (never referenced)
- [ ] The built PBO holds `stringtable.csv`: a binarizing pass without `*.csv` in its include list drops it, like `.c` (`include.lst` of `/dayz-build-pbo` lists both)
- [ ] The header row carries the full seven reference columns (`Language`, `original`, `english`, `spanish`,
      `german`, `russian`, `chinesesimp`); a four-column header was measured on 2026-08-21 to leave every key
      unresolved while the PBO mounted and served files

**Scripts**

- [ ] No ternary (`condition ? a : b`); write `if`/`else`
- [ ] No `+=` on arrays (use `.Insert()` or `.InsertAll()`)
- [ ] All `#include` paths point at existing files
- [ ] No `GetGame()` in a destructor without a null check
- [ ] No endless loop without a `break`
- [ ] All strings are closed; no stray tokens or unclosed braces

`++`/`--` and `foreach` are not on this list: vanilla uses them
(`foreach` at `P:\scripts\3_game\tools\cameratools.c:14`, `last_index++` at `P:\scripts\3_game\tools\tools.c:200`).

**After the build**

- [ ] List, count and name the entries of the built PBO; do not infer them from `include.lst`
- [ ] `config.cpp`, `.p3d` and face-referenced `.rvmat` may enter without a matching `-include` suffix
- [ ] The ordinary `.c`, `.paa`, `.ogg`, `.layout` and `.csv` payload matches the source tree by count and name
- [ ] Every `.rvmat` that `config.cpp` references is present, including materials no `.p3d` face references
- [ ] Treat presence in the include list as intent only; the built PBO's contents decide the gate

`build.py` runs the entry listing and the payload comparison on every build (`post-build-gates.md`); the
`.rvmat` check is manual.
