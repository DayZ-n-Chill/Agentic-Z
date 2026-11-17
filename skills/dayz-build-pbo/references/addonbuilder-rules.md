# AddonBuilder and binarize rules

How AddonBuilder and binarize behave when they pack a mod: the command line, which source tree a build really
uses, staging, what binarize resolves and where, `-temp`, where the ODOL lands, and matching the build mode of a
PBO you compare against.

Not yet checked on `P:\`: unless a line cites a vanilla file, what follows is measured tool and build
behaviour (AddonBuilder, binarize, the game's loader) and project findings from the mods named in the text,
kept as the knowledge pack's author recorded them. This repo has not repeated those measurements.

## How this maps to `/dayz-build-pbo`

- `build.py` stages `workspace\<ModName>\` in `P:\temp\_stage\<ModName>\` and packs the stage with
  `-prefix=<ModName> -temp=P:\temp\<ModName> -include=<skill-dir>\include.lst`. The stage keeps the mod's
  name, which is rule 4 of the SP-069 list below (source folder named as the prefix).
- It empties `P:\temp\<ModName>\` before every build and stops if the folder survives, which closes the
  stale temp trap below.
- It reads `[ResultCode]` from `<DayZ Tools>\Bin\Logs\AddonBuilder.rpt`, because AddonBuilder exits 0 on a
  failed build (SP-155 rule 1), and prints what CfgConvert and binarize wrote to stderr.
- Open point: SP-155 rule 1 says binarize resolves the files a `.p3d` cites under the parent of the source
  folder. For `build.py` that parent is `P:\temp\_stage\`, which holds no `dz\` data. Whether a vanilla
  material cited by a model's faces is then embedded empty in a `/dayz-build-pbo` build has not been measured
  in this repo. Until it is, check a model that cites vanilla `dz\...` materials with rule 5 below.

## AddonBuilder Workflow

After validation passes, use AddonBuilder to pack and binarize.

**Location:** DayZ Tools, a separate Steam app (`/dayz-preflight` finds it)
```
<DayZ Tools>\Bin\AddonBuilder\
```

### Locate the authoritative build source before validation (SP-343)

Do not infer the source tree from the checkout that is easiest to find. Before basing a fix,
audit, or rebuild on a mod tree:

1. Read `build_*.ps1` and resolve the value assigned to `$source`; that is the tree the build
   script actually feeds to AddonBuilder.
2. Compare a known byte-stable payload artifact from that tree (for example, a `.c` entry),
   by content hash, with the corresponding entry in the deployed PBO. A matching path or
   timestamp is not evidence of identity.
3. Reject trees marked as display-only, archived, or not-for-build, even when their folder
   names look canonical.

A matching artifact locates the candidate source; it does not prove release closure. Before
release, apply the full-tree provenance gate in LL-367: canonical commit/source tree ->
complete build tree -> PBO.

**Command line (canonical invocation):**
```batch
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> [-clear]
```

**Command line (pack only, skip binarization):**
```batch
AddonBuilder.exe P:\<ModName> P:\Mods\@<ModName>\Addons -prefix=<ModName> -temp=P:\temp\<ModName> -clear -packonly
```

**Temp-stale trap:** without `-clear` the `-temp` sync is INCREMENTAL and can serve stale
source — a changed `.c` may not be re-copied, so the PBO keeps packing old code while the
build reports success. If the PBO does not reflect your changes, wipe `P:\temp\<ModName>`
(or pass `-clear`) before rebuilding. Never place staging or sources inside the folder
passed as `-temp`: AddonBuilder clears its `-temp` before copying. (The source said "under `P:\temp\*`";
`build.py` stages in `P:\temp\_stage\<ModName>\`, beside the `-temp` folder `P:\temp\<ModName>\` and not inside it.)

**Binarized-build preflight rules (SP-155, verified 2026-08-03 ArmorHneck build; rule 1 corrected
2026-10-03 from measurements of 2026-09-27 and 2026-10-01; rule 5 added the same day; rules 1, 3
and 5 extended 2026-10-24, SP-468):**

1. **Staging is mandatory for binarized builds, and binarize looks for everything under the
   staging folder.**
   AddonBuilder passes binarize `-addon="<parent of the source folder>"` (the `[Arguments]=`
   lines of `DayZ Tools\Bin\Logs\AddonBuilder.rpt`): `P:\<Mod>` gives `-addon="P:"`, a staged
   `…\src\<Mod>` gives `-addon="…\src"`. Under that folder binarize:
   - **parses every `config.cpp`, recursively and through junctions**, and aborts on the first
     broken one. The canonical `AddonBuilder P:\<Mod> …` therefore dies on any broken foreign
     config on `P:\` (e.g. `P:\temp\Utopia_PC\…\legacy_generic_attempt\config.cpp`, or another
     project's test fixture). A broken `config.cpp` in a folder beside the staged mod, or behind
     a junction beside it, stops the build the same way (binarize exit 1, no PBO).
   - **resolves every file the p3d cite (`dz\…`, another mod's prefix) under that folder, never
     under `P:\`.** A face material it cannot find is embedded EMPTY in the ODOL: no shader, no
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
   after the build (rule 5). `CocaLab_dev\tools\build.py` does all three (staging, cited files,
   ODOL check);
   `ArmorHneck_dev\tools\build.ps1` stages but does not provide the cited files.
   - `-project=<source>` narrows `-addon` to the source itself and is not a way out: the PBO came
     out with no `.paa`, no `.rvmat` and no `texHeaders.bin` ("no textures found"; 606 KB
     against 16.5 MB).
   - Cost: `-addon` over a whole projects folder took 249-251 s; the dedicated folder 6-13 s.
   - Measured with AddonBuilder 1.0.240639 and BINARIZE rev.163709. DayZ MCP v1.3.1 spike,
     SimpleGroup, 11 builds (2026-10-01): with the mod alone in its folder, `T1_FlagKit.p3d`
     came out 43,376 B, with `dz\gear\consumables\data\rags_bandages.rvmat` (visual LOD) and
     `dz\data\data\penetration\wood.rvmat` (collision LODs) embedded empty. With a `DZ` junction
     beside it, it came out 55,221 B with both resolved, byte-identical to the build whose
     `-addon` was the whole projects folder. CocaLab (2026-09-27): a staged build embedded
     `dz\data\data\penetration\metalplate.rvmat`, present on `P:\dz`, and a DrugsPLUS leaf
     material empty. With the cited files staged there were none, and the gate's control
     without them failed (6 failures).
   - Not measured: what an empty material does in game.
   - **A direct `binarize.exe` call needs a dedicated `-addon` folder too** (SP-468, the H2R
     import, 2026-10, source outside `P:\`; claim: CLAIM-BINARIZE-DIRECT-ADDON-STALL), as the
     direct-call templates have it (dayz-model-pipeline SKILL.md and
     `references/py3d-direct-generation.md`, `skills/_shared/vehicles/p3d-vehicle-killers.md`).
     Without it (BINARIZE 1.30.164078.38) the first model loaded about 5 min after launch on
     2026-10-16; on 2026-10-19 none had come out after 30 min (a timeout; right after it, other
     processes held more than 10 of the 16 threads) or after 13 (stopped by hand). With
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

   *(corrected 2026-10-03)* This rule used to end: «"Material not loaded" / "Note: creating
   empty class" messages from the staging are tolerable (verified: HH-60G heli and ArmorHneck
   clothing both build and work). Validated end-to-end template: `ArmorHneck_dev\tools\build.ps1`.»
   For materials cited by p3d faces that is false: they are embedded empty (above). The
   ArmorHneck ODOL deployed on 2026-08-04 carries its Fire Geometry material
   `dz\data\data\penetration\armor_5mm_plate.rvmat` empty. "Work" meant the item loads and
   renders; its penetration was not tested. "Creating empty class" was not measured on its own.

2. **RVMATs referenced only from config.cpp do NOT enter the PBO.** The binarize whitelist
   (`*.p3d;*.paa`) + face-reference scan only pulls materials referenced by p3d FACES. An rvmat
   referenced solely from config.cpp (healthLevels damage/destruct, hiddenSelectionsMaterials
   on variants) is silently omitted, and the build still prints "Build Successful". Deferred
   in-game symptom: no visual damage swap / RPT "Material not loaded" when the item breaks.
   **Rule:** after the build, parse the PBO ENTRIES and compare against the full rvmat list
   from config.cpp (not just a classname grep). Copy any missing rvmat into
   `abtemp\<mod>\data\` and re-package with `-packonly` — use a SEPARATE `-temp` path
   (with `-clear`, the temp is wiped before the copy lands).

3. **Parallelism.** Binarize without high `-maxProcesses` is slow on dense skinned p3d
   (>5 min for 3 models at 18k pts in series). Use AddonBuilder's default parallelism and
   run in background; an apparent hang may just be serial + skinning, or, on a direct
   `binarize.exe` call, the wait before the first model seen without `-addon` (rule 1).

4. **config.bin may silently fail to register in the engine (most severe).** The mod mounts
   (engine reads the dir, zero RPT errors) but `CreateObjectEx` returns `unknown_type` and the
   item does not exist for VPP. The SAME PBO re-packaged with config.cpp as TEXT registers and
   spawns (bisection with control vanilla Armband_Pink). Correlated symptom: `unRap` exit 255
   on that config.bin. **Rule:** (a) pack config.cpp as TEXT in local PBOs (the full-build
   binarize is only exploited for p3d ODOL); (b) the "it actually mounts" gate is an in-game
   spawn (world_spawn from the bridge or console), NEVER just strings/entries of the PBO —
   static analysis of config.bin reported "healthy" while the engine ignored it.

5. **Check that binarize can find every file the p3d cite: before the build, and in the ODOL
   after it** (added 2026-10-03; CocaLab's build since 2026-09-27).
   - **Before — the gate.** List every path the faces cite, in every LOD: `face.texture` and
     `face.material` with py3d (`scripts/tools/py3d/py3d/__init__.py:1855-1856`; CocaLab scans the MLOD
     bytes for `*.paa`/`*.rvmat` paths). Stop if one does not exist under the staging folder:
     rule 1 says binarize looks for it there and nowhere else. Stage each cited `.rvmat` with
     the textures it names (CocaLab staged the DrugsPLUS `.rvmat` with its three `.paa`; a
     texture missing on its own was not tested).
   - **After — the control.** Read the ODOL with the ODOL reader of
     an external ODOL->MLOD converter (not part of this repo). Every unresolved material read
     so far showed, in every LOD that cites it: `pixel_shader == 0`, `vertex_shader == 0`,
     `surface_file == ""`, no stage texture (the thermal `StageTI`, `stage_ti`, included) and
     the engine's default colours (diffuse and ambient 1,1,1,1, emissive 0,0,0,1). A match is a
     lead, not a verdict: bare vanilla materials match most of those fields in Bohemia's own
     ODOLs — `dz\data\data\half_lighted_default.rvmat` in `dz\data\cl_feathers2.p3d`,
     `dz\water\streambed\data\streambed_leaves.rvmat` in `water.pbo`'s
     `Streambed\streambed_leaf_short_straight.p3d` — and `dz\data\data\default_2pass.rvmat`
     in `dz\data\data\penetration\impact_test_object.p3d` matches all of them. Confirm a lead
     against the material's text `.rvmat`: an extracted copy, or a binarized one (`raP`)
     decoded first. CfgConvert decoded `dz.pbo`'s `wood.rvmat` with `CfgConvert.exe -txt -dst
     <name>.cpp <name>.bin`, run from the file's folder; given the `.rvmat` name it exited 0
     and wrote nothing. A file you cannot read as text confirms nothing. Run the control once:
     the same build without the cited files must turn their materials into leads.
   - Compare ODOLs by those fields, not by hash: three SimpleGroup flagpoles varied by up to
     67 B across five builds that resolved the same files (2026-10-01; same trap in
     `scripts/tools/py3d/KNOWN-ISSUES.md`).
   - **The H2R import is a confounded case of a texture missing on its own** (SP-468, 2026-10;
     claim: CLAIM-BINARIZE-DIRECT-MATERIALS-EMPTY). Its direct `binarize.exe` calls (BINARIZE
     1.30.164078.38, source outside `P:\`) logged `Material not loaded` for the same 65 `.rvmat`
     with a dedicated `-addon` folder as without one (plus one added that day), and the control
     above reads every material entry of both builds' 8 ODOLs empty (189 of 189 and 190 of 190;
     the same reader finds shaders and stage textures in vanilla `Motorbike_02`), confirmed for
     three against their text `.rvmat`. The mod's own sat at their cited path under `-addon`,
     but each names a vanilla texture that was not staged (`dz\data\data\env_land_co.paa` or
     `env_land_optic_co.paa`); the other 7 are vanilla penetration `.rvmat`, not staged either
     (rule 1), and they failed without `-addon` too, though present on `P:\dz`. Not measured
     which keeps them from loading: the unstaged texture, the source outside `P:\`
     (dayz-model-pipeline `references/py3d-direct-generation.md`, LFQuad), or what the direct
     call lacks against AddonBuilder 1.0.240639 (`-binpath`, `-textures`, `-exclude`,
     `-maxProcesses`, `-targetBonesInterval`, `-silent`, and the `-addon` folder as working
     directory, per its rpt of 2026-10-23). AddonBuilder builds staged outside `P:\` resolved
     their files (rule 1). What these entries do in the kit that packs these ODOLs is rule 1's
     open point.

The orchestrated build path (temp wipe + deploy + launch) lives in dayz-test-ingame's
`dayz-test.ps1` template.


**Binarize via AddonBuilder CLI (SP-069, LFHeli OH-1 2026-07-19):**

1. **`-temp` for binarize: `P:\` is the habit, not a measured requirement.** On 2026-07-19,
   with `-temp` outside `P:\`, the "Binarizing" step died in ~4 s with "Process ended with
   non-zero code. Exit code: 1", empty stderr and zero p3d produced — AddonBuilder still
   exited 0 ("Build failed" only in its log) — and `-temp` took the blame. That explanation
   did not reproduce in four later builds with `-temp` outside `P:\` and the work drive mounted
   (`post-build-gates.md`, item 6), nor in nine binarized builds with `-temp` in a
   local folder on 2026-10-01, all with their ODOL (SP-155 rule 1). A binarize exit 1 within a
   second is also what a broken `config.cpp` under `-addon` gives, so rule that out first.
   Keeping `-temp` on `P:\` (canonical: `-temp=P:\temp\<ModName>`) costs nothing; none of
   those builds ran with the work drive unmounted. *(corrected 2026-10-03: the heading said
   «**`-temp` for binarize must stay under `P:\`.**»)*
   `-packonly` still accepts local folders outside `P:\`, so local staging remains valid.

2. **ODOL output is neither the source nor the target.** It lands in
   `<temp>\<prefix>\...` (e.g. `-temp=P:\x\temp -prefix=LFHeli` → ODOL in
   `P:\x\temp\LFHeli\models\`). The PBO AddonBuilder leaves in the target in binarize
   mode can be a tiny-PBO (~1 KB) that still prints "Build Successful".

3. **Verified release pattern** (binarized assets + scripts in a separate mod):
   binarize → collect ODOL from `<temp>\<prefix>\` → stage ODOL + raw `config.cpp` →
   `-packonly -prefix=<prefix>` → content gate (`config.cpp` present, no `config.bin`,
   N ODOL magics, prefix correct).

4. **Binarizing, name the source folder exactly as its single-segment `$PBOPREFIX$`
   (measured 2026-10-09, AddonBuilder 1.0.240639, DayZ-MCP 222d acceptance).** With source
   folder `LFHeli_OH1` and `-prefix=LFHeli`, binarize wrote the ODOL to
   `<temp>\LFHeli\` (temp + prefix) while FileBank packed `<temp>\lfheli_oh1\` (temp + the
   lowercased folder name). The PBO had the right prefix, the textures, the rvmat files and
   `config.bin`, but none of the 7 models, and the log still said "Build Successful". With the
   prefix equal to the folder name (SimpleGroup) the same build packed everything. If the
   folder cannot carry the prefix's name, build `-packonly` or use the release pattern above.
   Either way, accept a binarized build only when the PBO has one ODOL entry per `.p3d`, never
   by its log. Pipeline inbox fb-20261010-150630-25af.

**What AddonBuilder does:**
1. Names the PBO after the source folder (the source skill said after `$PBOPREFIX$`; its own build appendices and `build.py` say the folder)
2. Binarizes config.cpp (text → binary, ~90% smaller, faster load)
3. Optimizes .p3d files (binary format, LOD structure intact)
4. Packs all files into .pbo container
5. Generates PBO header with prefix

**Output:** `<source folder name>.pbo`, to place in `@YourMod/addons/`


**Comparison builds: match the mode to the reference artifact.** AddonBuilder has two modes and both produce a PBO that loads:
- **with `-packonly`**: packs raw, does not binarize `.p3d`. Large PBO.
- **without `-packonly`**: binarizes `.p3d` to ODOL. Much smaller PBO.

When the PBO is going to be used as a comparison term (compile gate, module measurement, A/B footprint, RED/GREEN of fixtures), **it must be built with the SAME mode as the artifact it is compared against**. Verify by size before deploying: a PBO that differs from the reference by a factor of 3–4× is not a variation of your code, it is a different build mode.

---
