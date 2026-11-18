# AddonBuilder and binarize rules

How AddonBuilder and binarize behave when they pack a mod: the command line, which source tree a build really
uses, staging, what binarize resolves and where, `-temp`, where the ODOL lands, and matching the build mode of a
PBO you compare against.

Not checkable on `P:\`: unless a line cites a vanilla file, what follows is measured behaviour of AddonBuilder,
binarize and the game's loader, with the tool version named where it was recorded. Vanilla files on `P:\`
cannot confirm it.

## How this maps to `/dayz-build-pbo`

- `build.py` stages `workspace\<ModName>\` in `P:\temp\_stage\<ModName>\` and packs the stage with
  `-prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill-dir>\include.lst`. The stage keeps the mod's
  name, which is command-line rule 4 below (source folder named as the prefix).
- It empties `P:\temp\<ModName>\` before every build and stops if the folder survives, which closes the
  stale temp trap below.
- It reads `[ResultCode]` from `<DayZ Tools>\Bin\Logs\AddonBuilder.rpt`, because AddonBuilder exits 0 on a
  failed build (binarized-build rule 1), and prints what CfgConvert and binarize wrote to stderr.
- It packs a binarized `config.bin`. Binarized-build rule 4 describes a case where such a config did not
  register; if a class of a built mod does not spawn while the logs are clean, test that cause.
- Open point: binarized-build rule 1 says binarize resolves the files a `.p3d` cites under the parent of the
  source folder. For `build.py` that parent is `P:\temp\_stage\`, which holds no `dz\` data. Whether a vanilla
  material cited by a model's faces is then embedded empty in a `/dayz-build-pbo` build has not been measured.
  Until it is, check a model that cites vanilla `dz\...` materials with binarized-build rule 5.

## AddonBuilder Workflow

After validation passes, use AddonBuilder to pack and binarize.

**Location:** DayZ Tools, a separate Steam app (`/dayz-preflight` finds it)
```
<DayZ Tools>\Bin\AddonBuilder\
```

**Calling CfgConvert yourself.** Run from PowerShell with quoted paths passed through
`Start-Process -ArgumentList`, `CfgConvert -bin -dst` exited 0 and wrote nothing. What worked: set
`-WorkingDirectory` to the config's folder and pass relative paths without quotes
(`CfgConvert -bin -dst config.bin config.cpp`). Check the output by its timestamp and exact location,
not by a file of that name existing: an old `config.bin` in the working folder nearly went into a
PBO. Reported tool behaviour, not checked on `P:\`.

### Locate the authoritative build source before validation

This applies to a mod that has its own build script; `/dayz-build-pbo` always packs `workspace\<ModName>\`.
Do not infer the source tree from the checkout that is easiest to find. Before basing a fix,
audit, or rebuild on a mod tree:

1. Read the mod's build script and resolve the folder it hands to AddonBuilder as the source
   (in a PowerShell script, usually the value assigned to `$source`).
2. Compare a known byte-stable payload artifact from that tree (for example, a `.c` entry),
   by content hash, with the corresponding entry in the deployed PBO. A matching path or
   timestamp is not evidence of identity.
3. Reject trees marked as display-only, archived, or not-for-build, even when their folder
   names look canonical.

A matching artifact locates the candidate source; it does not prove release closure. Before
release, trace the whole chain: canonical commit or source tree, complete build tree, PBO
(`post-build-gates.md`, "Further build rules").

**Command line (canonical invocation):**
```batch
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

**Command line (pack only, skip binarization):**
```batch
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear -packonly
```

**Temp-stale trap:** without `-clear` the `-temp` sync is incremental and can serve stale
source: a changed `.c` may not be re-copied, so the PBO keeps packing old code while the
build reports success. If the PBO does not reflect your changes, wipe `P:\temp\<ModName>`
(or pass `-clear`) before rebuilding. Never place staging or sources inside the folder
passed as `-temp`: with `-clear`, AddonBuilder wipes its `-temp` before copying. `build.py` stages in
`P:\temp\_stage\<ModName>\`, beside the `-temp` folder `P:\temp\<ModName>\` and not inside it.

**Binarized-build rules** (measured with AddonBuilder 1.0.240639 unless a line names another version):

1. **Staging is mandatory for binarized builds, and binarize looks for everything under the
   staging folder.**
   AddonBuilder passes binarize `-addon="<parent of the source folder>"` (the `[Arguments]=`
   lines of `DayZ Tools\Bin\Logs\AddonBuilder.rpt`): `P:\<Mod>` gives `-addon="P:"`, a staged
   `…\src\<Mod>` gives `-addon="…\src"`. Under that folder binarize:
   - **parses every `config.cpp`, recursively and through junctions**, and aborts on the first
     broken one. The canonical `AddonBuilder P:\<Mod> …` therefore dies on any broken foreign
     config on `P:\` (a leftover test config under `P:\temp\`, or another project's test
     fixture). A broken `config.cpp` in a folder beside the staged mod, or behind
     a junction beside it, stops the build the same way (binarize exit 1, no PBO).
   - **resolves every file the p3d cite (`dz\…`, another mod's prefix) under that folder, never
     under `P:\`.** A face material it cannot find is embedded empty in the ODOL: no shader, no
     stage texture, no `.bisurf`. A section with an alpha-cutout texture also loses bit `0x200`
     of its special flags (`0x24200` → `0x24000`). The build still says "Build Successful", and
     AddonBuilder's log carries no line about the missing material, so grepping it finds
     nothing.

   AddonBuilder.exe exits 0 when the build fails (`Build finished. [ResultCode]=1` in the rpt)
   and does not name the culprit (with `-noLogs -silent` the path never appears). Judge a build
   by the rpt's `[ResultCode]` or by the PBO (present, and rebuilt), never by the exit code.

   **Rule:** stage the mod in a dedicated folder that holds nothing else:
   `%TEMP%\<mod>_build_<stamp>\src\<Mod>`, plus every file its p3d cite outside its own prefix.
   Copy each at its cited path (`src\dz\data\data\penetration\metalplate.rvmat`, taken from the
   files the game loads), or reach the vanilla ones through a junction `src\DZ` → the extracted
   vanilla data. A junction target is parsed too, so it must hold no broken `config.cpp`. These
   files only feed binarize: AddonBuilder packs the source folder alone. Check them before and
   after the build (rule 5).
   - `-project=<source>` narrows `-addon` to the source itself and is not a way out: the PBO came
     out with no `.paa`, no `.rvmat` and no `texHeaders.bin` ("no textures found"; 606 KB
     against 16.5 MB).
   - Cost: `-addon` over a whole projects folder took 249-251 s; the dedicated folder 6-13 s.
   - Measured with AddonBuilder 1.0.240639 and BINARIZE rev.163709 over 11 builds of a flagpole
     mod: with the mod alone in its folder, a flag kit model came out 43,376 B, with
     `dz\gear\consumables\data\rags_bandages.rvmat` (visual LOD) and
     `dz\data\data\penetration\wood.rvmat` (collision LODs) embedded empty. With a `DZ` junction
     beside it, it came out 55,221 B with both resolved, byte-identical to the build whose
     `-addon` was the whole projects folder. In a second mod, a staged build embedded
     `dz\data\data\penetration\metalplate.rvmat`, present on `P:\dz`, and a leaf material of a
     mod it depends on empty. With the cited files staged there were none, and the gate's
     control without them failed (6 failures).
   - Not measured: what an empty material does in game.
   - **A direct `binarize.exe` call needs a dedicated `-addon` folder too** (BINARIZE
     1.30.164078.38, a vehicle mod whose source sat outside `P:\`), as the direct-call
     templates have it (`skills/dayz-model-pipeline/references/py3d-direct-generation.md`,
     `skills/_shared/vehicles/p3d-vehicle-killers.md`).
     Without it the first model loaded about 5 min after launch in one run; in a later run
     none had come out after 30 min (a timeout; right after it, other processes held more
     than 10 of the 16 threads) or after 13 (stopped by hand). With
     `-addon=<parent of the staged source>` the first model loaded within a second of the start
     (one run timed), and all six builds with it converted their 8 models, each log spanning
     under 3.5 min. Why the wait grew is not established: by birth time, under 0.3 % of the
     drive's folders, files and `config.cpp` were created between the two runs. Over 10 s a
     stalled run read nothing, held a flat working set of about 15 MB and did about 183,000
     other I/O operations (Windows `OtherOperationCount`); the `-addon` run did about 100,000,
     with reads and a growing working set. That binarize walks `P:` meanwhile is inferred, not
     traced, and one fact cuts against it: vanilla penetration `.rvmat` present on `P:\dz` still
     failed to load without `-addon` (rule 5). Signal: binarize alive, no reads, a flat working
     set, an empty output folder.

   "Material not loaded" and "Note: creating empty class" messages from a staged build are not
   harmless for materials cited by p3d faces: such a material is embedded empty (above). A
   clothing item built that way loaded and rendered with its Fire Geometry material
   `dz\data\data\penetration\armor_5mm_plate.rvmat` empty; its penetration was not tested.
   "Creating empty class" was not measured on its own.

2. **RVMATs referenced only from config.cpp do not enter the PBO.** The binarize whitelist
   (`*.p3d;*.paa`) and the face-reference scan only pull materials referenced by p3d faces. An rvmat
   referenced solely from config.cpp (healthLevels damage/destruct, hiddenSelectionsMaterials
   on variants) is silently omitted, and the build still prints "Build Successful". Deferred
   in-game symptom: no visual damage swap, and "Material not loaded" in the RPT when the item breaks.
   **Rule:** after the build, parse the PBO entries and compare against the full rvmat list
   from config.cpp (not just a classname grep). Copy any missing rvmat into the mod's `data\`
   folder in the build temp and re-package with `-packonly`, using a separate `-temp` path
   (with `-clear`, the temp is wiped before the copy lands).

3. **Parallelism.** Binarize without high `-maxProcesses` is slow on dense skinned p3d
   (more than 5 min for 3 models at 18k points in series). Use AddonBuilder's default parallelism and
   run in background; an apparent hang may just be serial work and skinning, or, on a direct
   `binarize.exe` call, the wait before the first model seen without `-addon` (rule 1).

4. **config.bin may silently fail to register in the engine (most severe).** The mod mounts
   (engine reads the dir, zero RPT errors) but `CreateObjectEx` returns `unknown_type` and the
   item is in no spawn list. The same PBO re-packaged with config.cpp as text registers and
   spawns (bisection with vanilla `Armband_Pink` as the control). Correlated symptom: `unRap` exit 255
   on that config.bin. **Rule:** (a) when this happens, pack config.cpp as text (the full-build
   binarize is then only used for the p3d ODOL); (b) the "it actually mounts" gate is an in-game
   spawn (through the dayz-mcp verification in `skills/dayz-launch-test/references/mcp/README.md`, or the debug console), never just the strings or entries
   of the PBO: static analysis of config.bin reported "healthy" while the engine ignored it.

5. **Check that binarize can find every file the p3d cite: before the build, and in the ODOL
   after it.**
   - **Before: the gate.** List every path the faces cite, in every LOD: `face.texture` and
     `face.material` with py3d (`scripts/tools/py3d/py3d/__init__.py:1866-1867` and `1881-1882`), or scan the MLOD
     bytes for `*.paa`/`*.rvmat` paths. Stop if one does not exist under the staging folder:
     rule 1 says binarize looks for it there and nowhere else. Stage each cited `.rvmat` with
     the textures it names (a texture missing on its own was not tested).
   - **After: the control.** Read the ODOL with an ODOL reader (this repo ships none). Every
     unresolved material read so far showed, in every LOD that cites it: `pixel_shader == 0`,
     `vertex_shader == 0`,
     `surface_file == ""`, no stage texture (the thermal `StageTI`, `stage_ti`, included) and
     the engine's default colours (diffuse and ambient 1,1,1,1, emissive 0,0,0,1). A match is a
     lead, not a verdict: bare vanilla materials match most of those fields in Bohemia's own
     ODOLs (`dz\data\data\half_lighted_default.rvmat` in `dz\data\cl_feathers2.p3d`,
     `dz\water\streambed\data\streambed_leaves.rvmat` in `water.pbo`'s
     `Streambed\streambed_leaf_short_straight.p3d`), and `dz\data\data\default_2pass.rvmat`
     in `dz\data\data\penetration\impact_test_object.p3d` matches all of them. Confirm a lead
     against the material's text `.rvmat`: an extracted copy, or a binarized one (`raP`)
     decoded first. CfgConvert decoded `dz.pbo`'s `wood.rvmat` with `CfgConvert.exe -txt -dst
     <name>.cpp <name>.bin`, run from the file's folder; given the `.rvmat` name it exited 0
     and wrote nothing. A file you cannot read as text confirms nothing. Run the control once:
     the same build without the cited files must turn their materials into leads.
   - Compare ODOLs by those fields, not by hash: three flagpole models varied by up to
     67 B across five builds that resolved the same files (`post-build-gates.md`, "AddonBuilder
     non-determinism").
   - **A texture missing on its own has only a confounded case.** A vehicle mod's direct
     `binarize.exe` calls (BINARIZE
     1.30.164078.38, source outside `P:\`) logged `Material not loaded` for the same 65 `.rvmat`
     with a dedicated `-addon` folder as without one (plus one added later), and the control
     above reads every material entry of both builds' 8 ODOLs empty (189 of 189 and 190 of 190;
     the same reader finds shaders and stage textures in vanilla `Motorbike_02`), confirmed for
     three against their text `.rvmat`. The mod's own sat at their cited path under `-addon`,
     but each names a vanilla texture that was not staged (`dz\data\data\env_land_co.paa` or
     `env_land_optic_co.paa`); the other 7 are vanilla penetration `.rvmat`, not staged either
     (rule 1), and they failed without `-addon` too, though present on `P:\dz`. Not measured
     which keeps them from loading: the unstaged texture, the source outside `P:\`
     (`/dayz-model-pipeline` `references/py3d-direct-generation.md`), or what the direct
     call lacks against AddonBuilder 1.0.240639 (`-binpath`, `-textures`, `-exclude`,
     `-maxProcesses`, `-targetBonesInterval`, `-silent`, and the `-addon` folder as working
     directory, per its rpt). AddonBuilder builds staged outside `P:\` resolved
     their files (rule 1). What these entries do in game is rule 1's open point.

In this repo the build path is `/dayz-build-pbo` (temp wipe, stage, result code, content check). The
dayz-mcp launcher `skills/dayz-launch-test/scripts/dayz-test.ps1` carries a weaker build of its own; build
with `/dayz-build-pbo` and launch it without `-Build`.


**Binarize through the AddonBuilder command line** (command-line rules):

1. **`-temp` for binarize: `P:\` is the habit, not a measured requirement.** In one build
   with `-temp` outside `P:\`, the "Binarizing" step died in about 4 s with "Process ended with
   non-zero code. Exit code: 1", empty stderr and zero p3d produced (AddonBuilder still
   exited 0, with "Build failed" only in its log), and `-temp` took the blame. That explanation
   did not reproduce in four later builds with `-temp` outside `P:\` and the work drive mounted
   (`post-build-gates.md`, item 6), nor in nine binarized builds with `-temp` in a
   local folder, all with their ODOL (binarized-build rule 1). A binarize exit 1 within a
   second is also what a broken `config.cpp` under `-addon` gives, so rule that out first.
   Keeping `-temp` on `P:\` (canonical: `-temp=P:\temp\<ModName>`) costs nothing; none of
   those builds ran with the work drive unmounted.
   `-packonly` still accepts local folders outside `P:\`, so local staging remains valid.

2. **ODOL output is neither the source nor the target.** It lands in
   `<temp>\<prefix>\...` (e.g. `-temp=P:\x\temp -prefix=MyMod` → ODOL in
   `P:\x\temp\MyMod\models\`). The PBO AddonBuilder leaves in the target in binarize
   mode can be a tiny PBO (about 1 KB) that still prints "Build Successful".

3. **Release pattern** (binarized assets, with scripts in a separate mod):
   binarize → collect ODOL from `<temp>\<prefix>\` → stage ODOL + raw `config.cpp` →
   `-packonly -prefix=<prefix>` → content gate (`config.cpp` present, no `config.bin`,
   N ODOL magics, prefix correct).

4. **Binarizing, name the source folder exactly as its single-segment `$PBOPREFIX$`**
   (AddonBuilder 1.0.240639). With source
   folder `MyMod_Heli` and `-prefix=MyMod`, binarize wrote the ODOL to
   `<temp>\MyMod\` (temp + prefix) while FileBank packed `<temp>\mymod_heli\` (temp + the
   lowercased folder name). The PBO had the right prefix, the textures, the rvmat files and
   `config.bin`, but none of the 7 models, and the log still said "Build Successful". With the
   prefix equal to the folder name the same build packed everything. If the
   folder cannot carry the prefix's name, build `-packonly` or use the release pattern above.
   Either way, accept a binarized build only when the PBO has one ODOL entry per `.p3d`, never
   by its log.

**What AddonBuilder does:**
1. Names the PBO after the source folder, not after `$PBOPREFIX$`
2. Binarizes config.cpp (text → binary, about 90% smaller, faster load)
3. Optimizes .p3d files (binary format, LOD structure intact)
4. Packs all files into .pbo container
5. Generates PBO header with prefix

**Output:** `<source folder name>.pbo`, to place in `@YourMod/addons/`


**Comparison builds: match the mode to the reference artifact.** AddonBuilder has two modes and both produce a PBO that loads:
- **with `-packonly`**: packs raw, does not binarize `.p3d`. Large PBO.
- **without `-packonly`**: binarizes `.p3d` to ODOL. Much smaller PBO.

When the PBO is going to be used as a comparison term (compile gate, module measurement, A/B footprint, pass/fail of fixtures), it must be built with the same mode as the artifact it is compared against. Verify by size before deploying: a PBO that differs from the reference by a factor of 3 to 4 is not a variation of your code, it is a different build mode.
