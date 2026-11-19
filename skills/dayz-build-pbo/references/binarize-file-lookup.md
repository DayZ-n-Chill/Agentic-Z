# Where binarize looks for cited files

How binarize finds the materials and textures a `.p3d` cites, what it writes when it cannot find one, how to stage a build so it finds them all, and how to check the ODOL afterwards. The command line and the rest of AddonBuilder's behaviour are in `addonbuilder-rules.md`.

This is measured tool behaviour, not vanilla data. The vanilla files named below exist on `P:\` as cited paths, for example `P:\DZ\data\data\penetration\wood.rvmat`.

## Binarize looks only under the parent of the source folder

AddonBuilder passes binarize `-addon="<parent of the source folder>"`, as the `[Arguments]=` lines of `DayZ Tools\Bin\Logs\AddonBuilder.rpt` show: `P:\<Mod>` gives `-addon="P:"`, and a staged `...\src\<Mod>` gives `-addon="...\src"`. Under that folder binarize does two things.

- **It parses every `config.cpp`, recursively and through junctions, and stops on the first broken one.** So `AddonBuilder P:\<Mod> ...` dies on any broken config anywhere on `P:\`, such as a leftover test config under `P:\temp\` or another project's test file. A broken `config.cpp` in a folder beside the staged mod, or behind a junction beside it, stops the build the same way: binarize exits 1 and no PBO is written.
- **It resolves every file the models cite (`dz\...`, another mod's prefix) under that folder, never under `P:\`.** A face material it cannot find is embedded empty in the ODOL: no shader, no stage texture, no `.bisurf`. A section with an alpha-cutout texture also loses bit `0x200` of its special flags (`0x24200` becomes `0x24000`). The build still says "Build Successful", and AddonBuilder's log has no line about the missing material, so grepping it finds nothing.

"Material not loaded" and "Note: creating empty class" from a staged build are therefore not harmless for materials that model faces cite. A clothing item built that way loaded and rendered with its Fire Geometry material `dz\data\data\penetration\armor_5mm_plate.rvmat` empty; its penetration was not tested. "Creating empty class" was not measured on its own, and what an empty material does in game is not measured either.

## Stage the build in a folder of its own

Stage the mod in a folder that holds nothing else, `%TEMP%\<mod>_build_<stamp>\src\<Mod>`, together with every file its models cite outside its own prefix. Copy each one to its cited path (`src\dz\data\data\penetration\metalplate.rvmat`, taken from the files the game loads), or reach the vanilla ones through a junction `src\DZ` to the extracted vanilla data. A junction target is parsed too, so it must hold no broken `config.cpp`. These files only feed binarize; AddonBuilder packs the source folder alone. Check them before and after the build (below).

- `-project=<source>` narrows `-addon` to the source itself and is no way out: the PBO came out with no `.paa`, no `.rvmat` and no `texHeaders.bin` ("no textures found"), 606 KB against 16.5 MB.
- A dedicated folder is also fast: `-addon` over a whole projects folder took 249 to 251 seconds, the dedicated folder 6 to 13.

What staging changes, measured on a flag pole mod: with the mod alone in its folder, a flag kit model came out with `dz\gear\consumables\data\rags_bandages.rvmat` (visual LOD) and `dz\data\data\penetration\wood.rvmat` (collision LODs) embedded empty. With a `DZ` junction beside it, both resolved and the model was byte identical to the build whose `-addon` was the whole projects folder. In a second mod, a staged build embedded `dz\data\data\penetration\metalplate.rvmat` empty although it is on `P:\DZ`, and a leaf material of a mod it depends on as well. With the cited files staged there were none, and the control build without them failed the check.

## A direct `binarize.exe` call needs a dedicated `-addon` too

Call binarize directly only with `-addon=<parent of the staged source>`, as the direct-call templates do (`skills/_shared/models/py3d-collision-and-mass.md`, `skills/_shared/vehicles/p3d-vehicle-killers.md`). On a vehicle mod whose source sat outside `P:\`, the first model loaded about 5 minutes after launch in one run without it; in later runs none had come out after 13 or 30 minutes. With the dedicated `-addon` the first model loaded within a second and every build converted all eight models in under 3.5 minutes.

The stalled run's signal: binarize alive, no file reads, a flat working set of about 15 MB, and an empty output folder. Over 10 seconds a stalled run did about 183,000 other I/O operations (the Windows `OtherOperationCount` counter), against about 100,000 for a run with the dedicated `-addon`, which also read files and grew its working set. Why the wait grew is not established. That binarize walks `P:` meanwhile is a guess, and one fact cuts against it: vanilla penetration materials on `P:\DZ` still failed to load without `-addon`.

## Before the build: every cited file is staged

List every path the faces cite, in every LOD: `face.texture` and `face.material` with py3d (`scripts/tools/py3d/py3d/__init__.py:1866` and `:1867`, read at `:1881` and `:1882`), or scan the MLOD bytes for `*.paa` and `*.rvmat` paths. Stop if one does not exist under the staging folder, because binarize looks there and nowhere else. Stage each cited `.rvmat` together with the textures it names; a texture missing on its own is not cleanly tested (below).

## After the build: read the ODOL

Read the ODOL with an ODOL reader; this repo ships none. Every unresolved material seen so far shows, in every LOD that cites it:

| Field | Value |
|---|---|
| `pixel_shader`, `vertex_shader` | `0` |
| `surface_file` | `""` |
| Stage textures | None, the thermal `StageTI` (`stage_ti`) included |
| Colours | The engine defaults: diffuse and ambient `1,1,1,1`, emissive `0,0,0,1` |

A match is a lead, not a verdict. Bare vanilla materials match most of those fields in Bohemia's own ODOLs: `dz\data\data\half_lighted_default.rvmat` in `dz\data\cl_feathers2.p3d`, and `dz\water\streambed\data\streambed_leaves.rvmat` in `water.pbo`'s `Streambed\streambed_leaf_short_straight.p3d`. `dz\data\data\default_2pass.rvmat` in `dz\data\data\penetration\impact_test_object.p3d` matches all of them.

Confirm a lead against the material's text `.rvmat`: an extracted copy, or a binarized one (`raP`) decoded first. CfgConvert decodes one with `CfgConvert.exe -txt -dst <name>.cpp <name>.bin`, run from the file's folder; given the `.rvmat` name it exits 0 and writes nothing. A file you cannot read as text confirms nothing. Run the control once: the same build without the cited files must turn their materials into leads.

Compare ODOLs by those fields, not by hash. Three flag pole models varied by up to 67 bytes across five builds that resolved the same files (`comparing-builds.md`).

## A texture missing on its own: not settled

The one case seen is confounded. A vehicle mod's direct `binarize.exe` calls, source outside `P:\`, logged `Material not loaded` for the same 65 `.rvmat` with a dedicated `-addon` folder as without one. The ODOL check above reads every material entry of both builds' eight models as empty (189 of 189 and 190 of 190; the same reader finds shaders and stage textures in vanilla `Motorbike_02`), confirmed for three against their text `.rvmat`. The mod's own materials sat at their cited paths under `-addon`, but each names a vanilla texture that was not staged (`dz\data\data\env_land_co.paa` or `env_land_optic_co.paa`). The other seven are vanilla penetration materials, not staged either, and they failed without `-addon` too, though present on `P:\DZ`.

Not measured which of these keeps them from loading: the unstaged texture, the source outside `P:\` (`skills/_shared/models/py3d-collision-and-mass.md`), or what the direct call lacks against AddonBuilder's (`-binpath`, `-textures`, `-exclude`, `-maxProcesses`, `-targetBonesInterval`, `-silent`, and the `-addon` folder as working directory, per its rpt). AddonBuilder builds staged outside `P:\` resolved their files.
