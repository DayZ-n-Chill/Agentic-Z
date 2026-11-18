# Pre-build checks

What to check in a mod folder before it is packed, which of those checks `/dayz-build-pbo` already runs, how to report the result, and what `$PBOPREFIX$` must hold. Each group of checks has its own file, listed below.

The checks rest on vanilla files where a line cites `P:\`; the rest is measured tool and build behaviour (AddonBuilder, binarize, the game's loader) and experience from mod projects.

## Which file to open

| Question | File |
|---|---|
| Is the folder laid out right, and what does `$PBOPREFIX$` hold? | `pre-build-checks.md` |
| Is `config.cpp` sound (braces, `CfgPatches`, `hiddenSelections`, duplicates), and does `model.cfg` match the models? | `config-and-model-checks.md` |
| Do all texture and material paths resolve, are the LODs complete, and do the wheel slots of a vehicle simulate? | `asset-checks.md` |
| Is every `#STR_` key in a `stringtable.csv` that DayZ reads, and do the scripts avoid what Enforce Script rejects? | `stringtable-and-script-checks.md` |
| I have no tools: what do I tick by hand? | `manual-build-checklist.md` |
| A check failed: what is the usual cause? | `common-validation-failures.md` |

## What `/dayz-build-pbo` already runs

| Check | Run by | Notes |
|---|---|---|
| Folder structure | `/dayz-lint`, inside `/dayz-build-pbo` | `config.cpp`, `$PBOPREFIX$`, the `P:\` link, missing files and bad suffixes. Of the stale files, `.bak` and `.psd` are dropped by `exclude.lst`; `.blend`, `.xcf`, `.tmp` and `.swp` stay out because `include.lst` has no pattern for them. Spaces, upper-case extensions and large files are manual. |
| `config.cpp` | `/dayz-lint` | Syntax, `CfgPatches`, `requiredAddons`, script modules. A member defined twice stops binarize on 1.30, and `build.py` prints the binarize error from AddonBuilder's log. |
| `model.cfg`, LODs, wheel slots | `/dayz-p3d-audit` | Run it by hand before a build; `/dayz-build-pbo` does not call it. |
| Texture and material paths | `/dayz-lint` (missing files) and `/dayz-p3d-audit` | A path starts with the PBO prefix and resolves from the `P:\` root, not from the addon folder. Capitalisation and `.png` or `.dds` checks are manual. |
| Stringtable | None | Manual, or the validator plan in `validation-scripts.md`. |
| Scripts | `/dayz-lint`: modules, modded classes, then the code rules of the script validator in `scripts/tools/dayz-script-validator/` | A code error already stops the build. Run the validator on its own only to pass `--external-scripts` or to compare before and after a change (`script-linter-and-compile-gate.md`). |

Up to 1.29 the folder structure, `stringtable.csv`, the include list and the duplicate class name check below were the whole contract. Since 1.30 binarize also stops on a member defined twice in one class, and an unpacked `-mod` folder is a way to iterate in diag, not a substitute for a shipped PBO (`dayz-1-30-pbo-build.md`).

## Folder structure

| Check | Level |
|---|---|
| `config.cpp` at the addon root, opening with `CfgPatches` as vanilla's do (`P:\DZ\gear\tools\config.cpp:1`) | Required. A 1.30 shadow PBO with the prefix `gui` that holds only layouts loads without one (`dayz-1-30-pbo-build.md`). |
| `$PBOPREFIX$` file, one line such as `mymod\myaddon` | Required |
| No spaces in folder names | Required; the DayZ tools reject them |
| No upper-case extensions (`.PAA`, `.CPP`) | Required |
| No stale files: `.bak`, `.blend`, `.psd`, `.xcf`, `.tmp`, `.swp` | Fail; they bloat the PBO |
| Asset files over 10 MB | Warning: a texture atlas or an unoptimised mesh |
| A `data/` folder for textures, materials and models, a `scripts/` folder for `.c` and `.h` | Recommended |

Two checks belong to the release, not the folder:

- Every class a player places, or that otherwise persists in the world, needs an entry with an explicit lifetime in the `types.xml` the release ships. Without one it disappears after 30 to 60 minutes of server time (`skills/_shared/persistence/lifetime-and-storage.md`).
- Signing and publishing: `workshop-publish.md` on Windows (DsUtils, the item folder, the Publisher or SteamCMD, and why a SteamCMD login with the Steam client's account kicks that client off), `dayzmake-linux.md` on Linux.

After the build, every PBO must sit in `@Mod\addons\`. A PBO at the mod folder root (`@MyMod/MyMod.pbo`) is ignored without a word: no config, no scripts, no error, while the folder still shows in the boot log's `ANIMATION (E): Can't load @MyMod/...` pass, which is not loading. Its `modded class` overrides never run, so an A/B test of a fix reads as "the fix did not work". This was measured on the native Linux 1.30 server; the probe is in `skills/dayz-launch-test/references/linux-native-server.md`, "Read the result". The Workshop Publisher also refuses an upload with PBOs outside `addons/`.

## `$PBOPREFIX$`

The file sits at the addon root beside `config.cpp` and holds one line:

```text
mymod\myaddon
```

- Use backslashes, with no trailing backslash, no quotes and no extra whitespace.
- Keep it unique across all addons, since two addons with one prefix make one of them invisible. The exception is a PBO that sets the 1.30 header property `fsShadowing=1` to shadow vanilla files on purpose (`dayz-1-30-pbo-build.md`).
- The packed PBO carries `prefix=mymod\myaddon` in its header. AddonBuilder names the file after the source folder (`myaddon.pbo`), not after the prefix (`post-build-gates.md`, "After every build").
- `/dayz-build-pbo` builds single-segment prefixes only: `$PBOPREFIX$` must hold exactly `<ModName>`. A nested prefix such as `mymod\myaddon` is valid for the game but `build.py` refuses it.

```text
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

## Reporting the result

Each check reports PASS, WARN or FAIL, and the summary lists every blocker before packing. Keep the report plain:

```text
DayZ addon validation report
Addon: mymod\myaddon
Path:  P:\mymod\myaddon

[PASS] Folder structure: config.cpp found, $PBOPREFIX$ is mymod\myaddon, no stale files
[PASS] config.cpp: 12 classes, 1 patch, braces balanced, hiddenSelections arrays equal
[WARN] model.cfg: animation "lever_rotate" names axis "lever_axis"; check the memory points in Item_Watch.p3d
[FAIL] Texture not found: mymod\myaddon\data\textures\body_co.paa (config.cpp line 45, class Item_Shirt)
[FAIL] stringtable.csv: missing key STR_MYMOD_DEVICE_NAME (config.cpp line 23, class Item_Device)
[PASS] LODs: Item_Watch.p3d has LOD0 (2104 vertices), LOD1 (800), Geometry and Memory with ce_center
[PASS] Scripts: 3 files, no Enforce Script faults

Summary: 4 pass, 1 warn, 2 fail
Blocked. Fix before packing:
  1. Add P:\mymod\myaddon\data\textures\body_co.paa
  2. Add STR_MYMOD_DEVICE_NAME to stringtable.csv (column 1, no leading #)
Then run AddonBuilder.
```

## Which checks a request needs

| Request | Checks |
|---|---|
| "Validate my mod", "is it ready to pack?", "what's missing?" | All of them, with the summary led by the failures |
| "Check config.cpp", "I have config errors" | `config.cpp`, with line numbers |
| "Check the textures" | Texture and material paths |
| "Check my p3d" | LODs |
| "Validate for AddonBuilder" | All of them, then the next step |
