# AddonBuilder rules

How AddonBuilder behaves when it packs a mod: the command line, the `-temp` folder, which source tree a build really uses, where the ODOL lands, what it leaves out, and how to judge whether a build worked. Where binarize looks for the files a model cites is its own topic, in `binarize-file-lookup.md`.

This is measured behaviour of AddonBuilder, binarize and the game's loader, not vanilla data, so it is not checked on `P:\`.

## How `/dayz-build-pbo` uses it

- `build.py` stages `workspace\<ModName>\` in `P:\temp\_stage\<ModName>\` and packs the stage with `-prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill-dir>\include.lst`. The stage keeps the mod's name, as "Name the source folder after the prefix" below asks.
- It empties `P:\temp\<ModName>\` before every build and stops if the folder survives, which closes the stale temp trap below.
- It reads `[ResultCode]` from `<DayZ Tools>\Bin\Logs\AddonBuilder.rpt`, because AddonBuilder exits 0 on a failed build, and prints what CfgConvert and binarize wrote to stderr.
- It packs a binarized `config.bin`. If a class of a built mod does not spawn while the logs are clean, test the cause under "A `config.bin` that never registers".
- Open point: binarize looks for the files a `.p3d` cites under the parent of the source folder. For `build.py` that parent is `P:\temp\_stage\`, which holds no `dz\` data. Whether a vanilla material cited by a model's faces is then embedded empty in a `/dayz-build-pbo` build is not measured. Until it is, check a model that cites vanilla `dz\...` materials as `binarize-file-lookup.md` describes.

## The command line

AddonBuilder is in `<DayZ Tools>\Bin\AddonBuilder\`; DayZ Tools is a separate Steam app, and `/dayz-preflight` finds it.

```bat
rem Full build, binarizing models and config
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear

rem Pack only, no binarizing
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear -packonly
```

What a full build does:

1. Names the PBO after the source folder, not after `$PBOPREFIX$`, so the output is `<source folder name>.pbo`, to place in `@YourMod\addons\`.
2. Binarizes `config.cpp` to `config.bin`, about 90% smaller and faster to load.
3. Binarizes `.p3d` files to ODOL with the LOD structure intact.
4. Packs all files into the PBO and writes the header with the prefix.

## Judge a build by its result code and its PBO

AddonBuilder.exe exits 0 when the build fails; the rpt says `Build finished. [ResultCode]=1`, and the tool does not name the culprit (with `-noLogs -silent` the path never appears). Judge a build by the rpt's `[ResultCode]` or by the PBO itself, present and rebuilt, never by the exit code. "Build Successful" in the log proves no more: the cases below all print it.

## The `-temp` folder

- **Without `-clear` the temp sync is incremental and can serve stale source.** A changed `.c` may not be copied again, so the PBO keeps old code while the build reports success. If the PBO does not show your change, wipe `P:\temp\<ModName>` or pass `-clear` before rebuilding.
- **Never put staging or sources inside the `-temp` folder.** With `-clear`, AddonBuilder wipes its `-temp` before copying. `build.py` stages in `P:\temp\_stage\<ModName>\`, beside `P:\temp\<ModName>\` and not inside it.
- **Keeping `-temp` on `P:\` is a habit, not a measured need.** One build with `-temp` outside `P:\` died in the binarizing step within about 4 seconds ("Process ended with non-zero code. Exit code: 1", empty stderr, no `.p3d` produced, AddonBuilder still exiting 0), and `-temp` was blamed. That did not reproduce in four later builds with `-temp` outside `P:\` and the work drive mounted, nor in nine binarized builds with `-temp` in a local folder, all of which wrote their ODOL. A binarize exit 1 within a second is also what a broken `config.cpp` under the source's parent gives, so rule that out first. `-temp=P:\temp\<ModName>` costs nothing; none of those builds ran with the work drive unmounted. `-packonly` accepts local folders outside `P:\` either way.

## Where the ODOL lands

The ODOL is written to neither the source nor the target but to `<temp>\<prefix>\...`: with `-temp=P:\x\temp -prefix=MyMod` the models land in `P:\x\temp\MyMod\models\`. The PBO AddonBuilder leaves in the target can then be a tiny one, about 1 KB, that still prints "Build Successful".

For a release with binarized assets and scripts in a separate mod: binarize, collect the ODOL from `<temp>\<prefix>\`, stage the ODOL with the text `config.cpp`, pack with `-packonly -prefix=<prefix>`, then check the content (`config.cpp` present, no `config.bin`, one ODOL per model, the right prefix).

## Name the source folder after the prefix

When binarizing, name the source folder exactly as its single-segment `$PBOPREFIX$`. With a source folder `MyMod_Heli` and `-prefix=MyMod`, binarize wrote the ODOL to `<temp>\MyMod\` (temp plus prefix) while FileBank packed `<temp>\mymod_heli\` (temp plus the lower-cased folder name). The PBO had the right prefix, the textures, the `.rvmat` files and `config.bin`, but none of the seven models, and the log said "Build Successful". With the prefix equal to the folder name the same build packed everything.

If the folder cannot carry the prefix's name, build `-packonly` or use the release pattern above. Either way, accept a binarized build only when the PBO has one ODOL entry per `.p3d`.

## Materials named only in `config.cpp` stay out

Binarize copies `*.p3d` and `*.paa` and pulls in the materials that `.p3d` faces cite. An `.rvmat` named only in `config.cpp`, such as a `healthLevels` damage or destruct material or a `hiddenSelectionsMaterials` entry on a variant, is left out without a word, and the build prints "Build Successful". In game the damage swap never shows, and the RPT logs "Material not loaded" when the item breaks.

After the build, list the PBO entries and compare them with every `.rvmat` path in `config.cpp`, not a class name grep. Copy any missing material into the mod's `data\` folder in the build temp and pack again with `-packonly`, using a separate `-temp` path, since `-clear` wipes the temp before the copy lands.

## A `config.bin` that never registers

The mod mounts (the engine reads the folder, no RPT errors), but `CreateObjectEx` returns `unknown_type` and the item is in no spawn list. The same PBO packed again with `config.cpp` as text registers and spawns; this was narrowed down with vanilla `Armband_Pink` as the control. A related sign: `unRap` exits 255 on that `config.bin`.

When it happens, pack `config.cpp` as text and use the full binarizing build only for the ODOL. Prove that a mod mounts with an in-game spawn from the debug console, never with the strings or entries of the PBO: static analysis of that `config.bin` reported it healthy while the engine ignored it.

## Speed

Binarize without a high `-maxProcesses` is slow on dense skinned models: more than 5 minutes for three models of 18k points in series. Use AddonBuilder's default parallelism and run it in the background. An apparent hang may be serial work and skinning, or, on a direct `binarize.exe` call without a dedicated `-addon` folder, the wait described in `binarize-file-lookup.md`.

## Calling CfgConvert yourself

Run from PowerShell with quoted paths through `Start-Process -ArgumentList`, `CfgConvert -bin -dst` exited 0 and wrote nothing. What works: set `-WorkingDirectory` to the config's folder and pass relative paths without quotes (`CfgConvert -bin -dst config.bin config.cpp`). Check the output by its timestamp and exact location, not by a file of that name existing: an old `config.bin` in the working folder nearly went into a PBO.

## Find the source a build really uses

`/dayz-build-pbo` always packs `workspace\<ModName>\`. For a mod with its own build script, never guess the source tree from the checkout that is easiest to find. Before basing a fix, an audit or a rebuild on a tree:

1. Read the mod's build script and resolve the folder it hands AddonBuilder as the source; in a PowerShell script it is usually the value of `$source`.
2. Compare a byte-stable file from that tree, such as a `.c` entry, by content hash with the same entry in the deployed PBO. A matching path or timestamp proves nothing.
3. Reject trees marked display only, archived or not for build, even when their folder names look right.

A matching file finds the candidate source; it does not prove the release is complete. Before a release, trace the whole chain from the commit or source tree through the full build tree to the PBO (`comparing-builds.md`, "Trace a release to its whole source tree").

## Match the build mode of a PBO you compare against

AddonBuilder has two modes, and both produce a PBO that loads. With `-packonly` it packs raw and does not binarize `.p3d`, so the PBO is large; without it the `.p3d` become ODOL and the PBO is much smaller.

When a PBO is the measure for something else (a compile check, a module measurement, an A/B footprint, pass or fail of test files), build it in the same mode as the PBO it is compared against. Check the size before deploying: a PBO three or four times larger or smaller than the reference is a different build mode, not a change in your code.
