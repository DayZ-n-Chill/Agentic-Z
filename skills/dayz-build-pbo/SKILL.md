---
name: dayz-build-pbo
description: "Packs a mod from workspace/<ModName>/ into a binarized .pbo at P:\\Mods\\@<ModName>\\Addons\\ with DayZ Tools AddonBuilder. Checks afterwards that the mod's scripts and models are really in the PBO. Use when a mod's source changed and you need a fresh PBO before /dayz-launch-test, a clean rebuild to chase a stale-asset bug, or the pre-build and post-build checks for a mod that packs but does nothing in game."
argument-hint: "<ModName> [--clean]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-build-pbo

Package a mod scaffold into a deployable `.pbo` under `P:\Mods\@<ModName>\Addons\`, where the engine loads it. Path discovery comes from `dayz-preflight/preflight.py`; the preflight gate, project cache and ownership-marker rules come from `skills/_shared/skill_helpers.py`.

Follow `skills/_shared/dayz-conventions.md`.

## How to run

```cmd
python "<skill-dir>\build.py" <ModName> [--clean]
```

| Argument | Required? | Notes |
|---|---|---|
| `<ModName>` | yes | Must match a scaffold under `workspace/<ModName>/` in the project cached by `/dayz-init`, with the `P:\<ModName>\` junction in place. |
| `--clean` | no | Passes `-clear` to AddonBuilder, wiping `P:\Mods\@<ModName>\Addons\` before building. Use after large refactors or when chasing a stale-asset bug. Refused while `Addons\` holds any PBO other than `<ModName>.pbo` (payload copied in by `/dayz-deploy-pbo`) or any `.bisign` signature, since AddonBuilder makes neither and `-clear` would delete them. |

## What it does

1. **Project** - reads the project root cached by `/dayz-init`.
2. **Preflight gate** - runs `/dayz-preflight`; halts on non-zero, so an unmounted `P:\` is the first error shown.
3. **Workspace check** - `workspace/<ModName>/` exists and contains `config.cpp` and `$PBOPREFIX$`, and `$PBOPREFIX$` holds exactly `<ModName>` (surrounding whitespace and a BOM are ignored; case must match). The build always packs a staged copy of the mod at `P:\temp\_stage\<ModName>\` with `-prefix=<ModName>` (the `P:\<ModName>\` junction only lets the mod's `P:\` paths resolve), so a different prefix means the mod's config paths expect another root; it refuses rather than build a PBO whose paths do not resolve. A payload-only bundle (prebuilt `Addons\*.pbo` and no `config.cpp`) has nothing to build, so it is refused with a pointer to `/dayz-deploy-pbo <ModName>`. This check runs before lint, so a missing file gets its own repair hint rather than a lint error.
4. **Lint gate** - runs `/dayz-lint <ModName>`, both of its stages: the mod setup checks (`config.cpp`, `CfgPatches`, `$PBOPREFIX$`, script modules, files) and the code rules of the script validator (Enforce Script, `.layout`, `inputs.xml`, `.rvmat`). It stops with `[FAIL]` and each `file:line` if either stage finds an error, so a code error stops the build too. Lint warnings print as `[WARN]` and the build goes on. The build passes no `--external-scripts`, so for a mod that depends on another mod the rule `ES-UNDEFINED-CLASS-REF` is not checked here; run `/dayz-lint <ModName> --external-scripts <folder>` for its verdict. The `P:\<ModName>\` link is left to step 6, which gives the repair hint.
5. **P:\Mods junction check** - `P:\Mods\` is a junction to the DayZ `!Workshop` folder.
6. **Mod junction check** - `P:\<ModName>\` is a link pointing at `workspace/<ModName>/` (created by `/dayz-new-mod` or `/dayz-import-mod`).
7. **Tools check** - resolves `AddonBuilder.exe` through `find_dayz_tools()` (env var, registry, Steam libraries).
8. **Ownership gate** - if `P:\Mods\@<ModName>\` already exists, it must contain `.agentic-z-scaffold` with content `<ModName>`. An unmarked folder could be a subscribed or hand-placed mod, so the build refuses to write into it or `-clear` it. This is the same rule `/dayz-deploy-pbo` uses.
9. **Clean gate** (`--clean` only) - refuses if `P:\Mods\@<ModName>\Addons\` holds any `.pbo` other than `<ModName>.pbo`, or any `.bisign`, and names each one. AddonBuilder makes neither, so `-clear` would delete deployed payload or a hand-made signature for good.
10. **Ownership marker** - when this run creates `P:\Mods\@<ModName>\`, it writes `.agentic-z-scaffold` there before AddonBuilder starts, so a failed first build leaves a marked folder that the next build accepts. The marker sits above `Addons\`, so `-clear` keeps it. `/dayz-clean-workspace` only removes deployed folders that carry it. If the marker cannot be written, the build prints `[FAIL]` and exits 1 without running AddonBuilder.
11. **Stale temp** - removes `P:\temp\<ModName>\` if an earlier build left it, and stops with `[FAIL]` if the folder cannot be emptied or is still there afterwards. AddonBuilder syncs the source into its temp dir incrementally, so files left there can be packed in place of the current source while the build still says "Build Successful".
12. **Stage** - copies `workspace/<ModName>/` to `P:\temp\_stage\<ModName>\`, leaving out every file that matches `exclude.lst`, and prints how many files it copied and left out. A folder pattern such as `.git\*` drops every file in that folder, including files with no extension. Read-only files are staged read-only and still removed by the next build. If a file in the old stage or in the source cannot be removed or copied (a crashed AddonBuilder or Workbench still holds it), the build prints `[FAIL]` with that file's path and a hint (close the program, or `taskkill /im AddonBuilder.exe /f`) and exits 1.
13. **Build** - runs `AddonBuilder.exe P:\temp\_stage\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill-dir>\include.lst [-clear]`. Binarization is on. There is no `-exclude=`: AddonBuilder 1.0.240639 crashes on it with `ArgumentNullException` in `TextureHeaderBinazrizeTask`, because it leaves its exclude-list path empty when the flag is given, so the stage step applies the list instead. The command is echoed as an `[AddonBuilder]` line with quoted arguments, so it can be pasted and re-run by hand.
14. **Result code** - reads the last `Build finished. [ResultCode]=` line of `<DayZ Tools>\Bin\Logs\AddonBuilder.rpt`. AddonBuilder exits 0 when CfgConvert or binarize fails; only its log says `[ResultCode]=1`. On a failed result the build prints `[FAIL]` with what the two tools wrote to stderr during this build (for example `config.cpp, line 17: /CfgVehicles/MyItem.scope: Member already defined.`, the DayZ 1.30 stop on a member defined twice) and exits 1. A missing log, or one whose last result is older than this build, is skipped.
15. **Verify output** - `P:\Mods\@<ModName>\Addons\<ModName>.pbo` exists and is newer than the build start. AddonBuilder can exit 0 while leaving an old PBO in place; that case fails as a stale PBO.
16. **Content check** - reads the PBO's entry table with `pbo_entries.py` (no unpacking) and compares it with the staged source. The expected entries are every staged file that `include.lst` lets through, so there is no hand-kept list to go stale. It fails with `[FAIL]` when a staged `.c` or `.p3d` is not in the PBO, when the PBO holds neither `config.bin` nor `config.cpp`, or when the header prefix is not `<ModName>`: each of those loads as a mod that silently does nothing. Other missing files, entries that came from no staged file, and a PBO without its 21-byte checksum trailer print `[WARN]`. A missing file under a folder named `Source`, `Temp` or `Doc` gets a hint, because the packer drops those folders at any depth. On success it prints how many entries the PBO holds and how many staged files match no `include.lst` pattern.
17. **Signature check** - AddonBuilder does not sign, so any `<ModName>.pbo.*.bisign` already in `Addons\` was made for an earlier PBO. Each one gets a `[WARN]`: re-sign the new PBO with `DayZ Tools\Bin\DsUtils\DSSignFile.exe`, or delete the old signature.
18. **Cleanup** - removes `P:\temp\<ModName>\` and the stage on success. On failure it keeps both and prints both paths for debugging.

## include.lst

`include.lst` (next to `build.py`) is passed to AddonBuilder as `-include=`. It is one line of `;`-separated wildcard patterns naming the file types AddonBuilder copies into the PBO: scripts, configs, layouts, models, textures, materials, sounds, and data files such as `.json`, `.xml`, `.csv` and `.txt`. A file whose extension is not listed is silently left out of the PBO. If your mod ships another file type, add its pattern to that line.

## exclude.lst

`exclude.lst` (next to `build.py`) is applied by `build.py` while it stages the mod: files matching its patterns (one per line, `;` starts a comment) are not copied, so they stay out of the final PBO. Each pattern matches the whole path relative to the mod root, ignoring case, and `*` crosses folders. It drops `.gui-sources\` (the sprite source PNGs for `/dayz-build-imageset`; only the packed atlas and `.imageset` under `gui/imagesets/` ship), the `workbench\` folder, Workbench plugins under `scripts\editor\`, version-control folders, binarization logs, archives, signatures and keys, and the `Source\`, `Doc\` and `Temp\` folders at the mod root. Those three are anchored to the root, so staging keeps a nested folder with the same name (for example `scripts\4_World\Temp\` or `data\doc\`), but it still does not ship: FileBank packs with DayZ Tools' own `Bin\PboUtils\exclude.lst`, whose `*\Source\*`, `*\Temp\*` and `*\Doc\*` patterns drop those folders at any depth. Rename such a folder; the content check in step 16 flags files lost this way.

## Refuses to run if

- `<ModName>` fails the mod name pattern (a letter first, then letters, digits and underscores, at most 64 characters), so a name such as `..\Other` never reaches the disk. This check runs first.
- No project is cached (run `/dayz-init`).
- `/dayz-preflight` fails, or `P:\Mods\` is not a valid junction to `!Workshop`.
- `workspace/<ModName>/` is a payload-only bundle (prebuilt `Addons\*.pbo`, no `config.cpp`). There is nothing to build; deploy it with `/dayz-deploy-pbo <ModName>`.
- `workspace/<ModName>/`, its `config.cpp`, or its `$PBOPREFIX$` is missing (`/dayz-add-scaffold` adds the files).
- `$PBOPREFIX$` holds anything other than `<ModName>`. Set it to that single line, and make sure `config.cpp` paths use `<ModName>\` as their root.
- `P:\<ModName>\` is missing, is a real folder, or points somewhere other than `workspace/<ModName>/`. The hint points at `/dayz-add-scaffold <ModName> --piece junction`, which creates the link.
- `AddonBuilder.exe` is not found (set `DAYZ_TOOLS_PATH` or install DayZ Tools).
- `P:\Mods\@<ModName>\` exists without a matching ownership marker. If it is yours, remove it: `cmd /c rmdir /s /q P:\Mods\@<ModName>`.
- `--clean` is passed while `Addons\` holds PBOs other than `<ModName>.pbo`, or any `.bisign`.
- A file in `P:\temp\_stage\<ModName>\` or in the source cannot be removed or copied (locked by a crashed AddonBuilder or by Workbench).
- `P:\temp\<ModName>\`, left by an earlier build, cannot be emptied or survives its removal (a program holds it open).
- AddonBuilder exits non-zero (its exit code propagates), logs a `[ResultCode]` other than 0, or produces no fresh PBO. The temp and stage dirs are kept for inspection, and both paths are printed.
- The built PBO lacks a staged `.c` or `.p3d`, holds no config, or has a header prefix other than `<ModName>`. The PBO stays on disk but the build exits 1; do not test with it.

## Output

```
DayZ preflight

[OK]    P:\ is mounted
...     (rest of the /dayz-preflight report)

Preflight complete.
[OK]    workspace\MyMod\ found
[OK]    $PBOPREFIX$ matches MyMod
[WARN]  lint config.cpp:9: requiredAddons lists DZ_Data twice in MyMod.
[OK]    /dayz-lint passed
[OK]    P:\Mods junction valid
[OK]    P:\MyMod junction valid
[OK]    AddonBuilder: C:\...\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe
[OK]    P:\Mods\@MyMod\ ownership marker valid

[OK]    Staged 9 files in P:\temp\_stage\MyMod (2 left out by exclude.lst)

[AddonBuilder] "C:\...\DayZ Tools\Bin\AddonBuilder\AddonBuilder.exe" P:\temp\_stage\MyMod P:\Mods\@MyMod\Addons -prefix=MyMod -temp=P:\temp\MyMod -include=...\include.lst

... AddonBuilder's own output, streamed live ...

[OK]    Built: P:\Mods\@MyMod\Addons\MyMod.pbo (12,345 bytes)
[OK]    MyMod.pbo holds 10 entries; all 8 packable staged files are in it
[OK]    Cleaned temp and stage dirs
```

The preflight gate runs first, then the workspace check, then the lint gate. Each `/dayz-lint` warning prints as a `[WARN]  lint` line and does not stop the build; any lint error stops it before the junction and tools checks. The ownership line appears only when `@MyMod` already exists. A `[WARN]` for each old `MyMod.pbo.*.bisign` follows the `Built:` line. If a temp or stage folder cannot be removed, a `[WARN]` names it and the `Cleaned` line is left out. Failures print `[FAIL]  <reason>` followed by an indented hint.

## References

Deep material lives in `<skill-dir>\references\`. `build.py` runs none of it beyond the steps above; open the file that answers the question.

| Question | File |
|---|---|
| What should I check in the mod folder before packing (config, `model.cfg`, textures, LODs, stringtable, scripts, wheel slots), and what does `$PBOPREFIX$` have to hold? | `references/pre-build-checks.md` |
| A check failed: what is the usual cause and fix? | `references/common-validation-failures.md` |
| How do AddonBuilder and binarize behave: source tree, staging, where binarize looks for cited files, `-temp`, where the ODOL lands, `-packonly` against a binarized build? | `references/addonbuilder-rules.md` |
| The build said "Build Successful": is the PBO really the one I meant (scripts inside, entries match, two builds compared, the right one deployed, a gate that can fail)? | `references/post-build-gates.md` |
| How do I run the script validator before packing, what does green prove, and how do I show the deployed mod compiles? | `references/script-linter-and-compile-gate.md` |
| What did DayZ 1.30 change for packing (duplicate members, unpacked mods, `fsShadowing`)? | `references/dayz-1-30-pbo-build.md` |
| How do I sign the PBO and publish it to the Workshop with the Publisher or SteamCMD? | `references/workshop-publish.md` |
| How do I build, sign and publish on Linux with dayzmake? | `references/dayzmake-linux.md` |
| Is there validator code I can adapt for a CI pipeline? | `references/validation-scripts.md` |
| What do I check in each kind of file (`config.cpp`, script, networking, layout, action, `.rvmat`, persistence, refactor) before it counts as written? | `references/file-checklists.md` |

To study a PBO somebody else built, use `/dayz-import-mod` (its `pbo_inventory.py` lists what a PBO holds). Building is one step of the mod loop in `skills/dayz-launch-test/references/mod-loop.md` (look up, write, build, boot on a local server, verify, publish).

## Do not

- Don't write the PBO anywhere except `P:\Mods\@<ModName>\Addons\`; that is where the engine loads in-development mods.
- Don't create or repair the `P:\<ModName>\` junction here; `/dayz-new-mod` and `/dayz-import-mod` create it, and `/dayz-add-scaffold <ModName> --piece junction` repairs it.
