# Post-build gates

How to prove a built PBO is the one you meant to build: its scripts, stringtable and models are inside, its entries match the source, its config points at files it really holds, and the gate you rely on can fail. Comparing two builds is in `comparing-builds.md`; checks on the PBO the game actually loads are in `deployed-pbo-checks.md`.

This is measured behaviour of AddonBuilder, binarize and the game's loader, not vanilla data, so it is not checked on `P:\`.

## What `build.py` already checks

| Gate | In `build.py` |
|---|---|
| Scripts and models are in the PBO | `check_pbo_contents`: every staged `.c` and `.p3d` that `include.lst` lets through must be an entry, or the build fails. Other missing files are a warning. |
| Manifest from the source, and extras | Same function: the expected entries come from the staged source, never a hand-kept list. Entries with no source file are a warning; `texHeaders.bin`, the prefix file and `config.bin` are allowed. |
| Header prefix | The PBO's `prefix` property must equal `<ModName>`. |
| 21-byte checksum trailer | `pbo_entries.py` checks it; a PBO without one gets a warning. |
| Fresh PBO, real result | The PBO must be newer than the build start, and `[ResultCode]` in AddonBuilder's log must be 0. |
| Stale `-temp` tree | The temp folder is removed before the build, and the build stops if it survives. |

Everything else here is manual: the negative control, the size and marker checks, the property gate and the model path gate.

## Binarize drops `.c` and `.csv`

`build.py` always passes `-include=include.lst`, which lists `*.c` and `*.csv`, so neither loss happens in its builds and its content check proves that each time. This section is for a hand-run AddonBuilder and for a PBO somebody else built.

AddonBuilder's default binarizing mode does not copy `.c` files; they are not in its include list. A scripts-only addon built with a plain `AddonBuilder src dst -clear` can pack to a config-only PBO (`config.bin` and the `CfgMods` path strings) while printing `Build Successful`. In game the mod mounts, and its `CfgPatches` name shows in the server `script.log` `defines:` list, but no script runs: no modded class merges and no hook fires. One scripts mod packed to 662 bytes this way; `-packonly` gave the right 124 KB PBO with all its `.c`.

`.csv` is dropped the same way. A two-file addon binarized to a PBO with `config.bin` and no `stringtable.csv`, while `-packonly` on the same source kept it. An addon that only carries a stringtable then mounts and translates nothing.

| Addon | Pack mode |
|---|---|
| Scripts only, no `.p3d` or `.paa` | `-packonly`: everything is copied as is, and `config.cpp` stays text, which DayZ loads. |
| Models and scripts (vehicles, items) | Binarize for the `.p3d`, and make sure the include list copies `*.c` and `*.h`, or the scripts vanish and a `CarScript` vehicle loads but never simulates. |

Check right after packing; it is cheap:

```powershell
$txt = [System.IO.File]::ReadAllText($pbo, [System.Text.Encoding]::GetEncoding('ISO-8859-1'))
$txt.Contains('YourKnownClassName')   # must be True; look at the PBO size too
```

When the mod loads but no script runs, grep the deployed PBO for a known class string before you chase the script logic, the mission class or server checks.

## `-include` is not the final PBO manifest

AddonBuilder has two input paths. Its own binarizing path handles `config.cpp`, `.p3d` and face-referenced `.rvmat`, and these can enter the PBO even when their suffix is missing from `-include`. The ordinary sync path carries `.c`, `.paa`, `.ogg`, `.layout` and `.csv`; with a fresh temp, a suffix left out of the list is dropped without a word. So `-include` is an exclusive filter for the sync pass only, not for the final PBO.

An `.rvmat` left out of `include.lst` still entered and was binarized because three `.p3d` files cited it. That does not change the rule in `addonbuilder-rules.md`, "Materials named only in `config.cpp` stay out": an `.rvmat` only `config.cpp` names may still be missing.

Never add material suffixes to `include.lst` as a precaution and treat that as proof. List, count and name the built PBO's entries, compare the ordinary payload with the source tree, and check the full set of `.rvmat` that `config.cpp` names separately. A suffix in the list does not prove an entry was packed, and a suffix missing from it does not prove a native input was dropped.

## A content gate that can fail

A content gate built on a hand-kept list of files goes stale both ways at once: it names files that were deleted, which kills the build at start, and it misses files the PBO now ships, so a pass proves nothing about them.

- **Derive the manifest from the source tree** at build time. A derived manifest cannot miss a file that is there.
- **Check the PBO for extras**: list its entries and flag any that are not in the derived manifest. That is what a closed list was really for.
- **Allow the metadata AddonBuilder writes**: `$PBOPREFIX$.txt` and `texHeaders.bin` (the `.paa` index) have no source file by design.
- **Add a negative control.** For every line or file the build was meant to remove, assert that it is absent from the PBO. Presence-only checks pass with stale content still inside.
- **Check stale anchors against the deployed PBO.** Before you treat a missing anchor, such as a `CreateAttachment("...")` call, as a regression, extract the deployed PBO and look for it there. If it is missing there too, the anchor is stale and nothing regressed; only an anchor present in the deployed PBO and missing from your new build is a real regression.

## Choose a marker only the change contains

A gate that checks for a string in the packed PBO catches a build made from an old tree, but only if the string is unique to the change. One gate for a variant that enabled smoothing only when a mode field equalled 1 required the text `Mode == 1` and passed; the base build already held that text in an unrelated function:

```c
// present since before the change
return m_Tuning.Mode == 0 || m_Tuning.Mode == 1;
```

That gate would have passed on the build without the variant, so it proved only that the file was still there. Make the marker unique to the change, not to its area: a new constant name (`MYMOD_REST_PROBE_ARM_MPS`) or a new log tag (`[MYMOD-REST]`) does not exist before; an expression on a field already in use does. In the same run, two markers on new symbols told the builds apart and one on an existing symbol did not, with the same command.

Before you trust a gate, run it against the build without the change and watch it fail. A gate you have only seen pass is not calibrated.

## After every build

Exit 0 and "Build Successful" are not enough. One build reported success with a 613-byte PBO because its sync to the temp folder copied no files (probably a clash with OneDrive), and the PBO that got measured was left over from an earlier build, because AddonBuilder names the PBO after the source folder.

1. **Size.** A script mod is about 15 to 30 KB; about 600 bytes is a packed empty folder; a 2 KB PBO of a model mod means the model fell out.
2. **Content.** Grep the PBO for expected strings, the `.c` file names and a code literal from your latest change: `[Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($pbo)) -match "my_marker"`.
3. **Name.** The PBO is `<SourceFolderName>.pbo`. When you build from a staging folder, name it exactly like the mod (`%TEMP%\<Mod>\`), or you deploy and measure the wrong file.
4. **Local staging.** Keep the build source out of OneDrive: AddonBuilder's sync from OneDrive paths can copy no files and report no error.
5. **Model count from the entry table.** Size alone passes a PBO with no models. One build exited 0 with "Build Successful" and an 8.0 MB PBO of 132 entries, none of them the ten `.p3d`, because the stage path held the addon folder name higher up (`...\<Mod>_stage0\stage\<Mod>`). Renaming only the stage's parent folder gave full PBOs again: 21.5 MB, 140 of 140 entries, 10 of 10 ODOL. Count the `.p3d` or ODOL entries against the stage before you trust any build, and measure again before you trust either explanation of a tiny or model-less PBO (`addonbuilder-rules.md`, "The `-temp` folder").
6. **Properties, per LOD.** A hash manifest compares the same file on both sides, so it passes even when the packed `.p3d` were built before a property reached the model generators. On a helicopter mod, `autocenter=0` was added to the hull's visual LOD in both generators after the `.p3d` were generated, the PBO was packed from the older `.p3d`, and the manifest passed; of the 48 extracted `.p3d`, the 8 sub-models had the property and the 40 hulls did not. Read the property per LOD from a table of expectations: property, expected value, reason and explicit exclusions (Memory LODs have no geometry to recentre).

The expectation table must also name the controls that should not change, such as the control arm of an A/B build or a frozen copy, each with its expected value and reason. A blanket "all LODs" rule rejects healthy controls and ends up switched off.

## Every config path resolves inside the PBO

On a weapon mod, `model=` pointed at the PBO root while the binarized model lived in `data\`. Builds from a dirty temp had put a raw MLOD at the PBO root, and the engine loaded that file for 11 versions, so every offline gate checked a model the game never used. Before you call a build good:

1. Extract or list the deployed PBO and read its compiled `config.bin`; class names and paths survive rapifying as plain strings.
2. For every `model=` and every texture and material path the config names, check that it resolves to an entry inside the PBO under its prefix, ignoring case.
3. Treat a second copy of the main `.p3d` at a path nothing names (usually the PBO root) as the sign of a dirty AddonBuilder temp plus a wrong `model=`. Fix the path and rebuild with `-clear`.
4. Run this on the PBO the engine loads, never only on the source tree or the build temp.
