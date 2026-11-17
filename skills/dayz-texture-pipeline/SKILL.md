---
name: dayz-texture-pipeline
description: "Plans, writes and checks DayZ texture and material work: which map each suffix needs (_co, _ca, _nohq, _smdi, _as, _mc, _dt), .rvmat authoring (Super, Multi, emissive, glass, penetration, damage and destruct), hiddenSelectionsTextures and hiddenSelectionsMaterials wiring, healthLevels materials, material swaps from script, baked atlases from Blender or Substance, and the MatPBR .emat route. Ships an .rvmat linter, an .rvmat template writer and a normal map convention check (OpenGL or DirectX). Use when a texture looks wrong in game, a normal map may be inverted, a new .rvmat is needed, or a metallic and roughness set has to become DayZ maps. Converting images to .paa is /dayz-pack-texture."
argument-hint: "<file.rvmat ...> [--pdrive-root <folder>] | <super|damage|emissive|penetration|multi> --prefix <packed-path> | --normal <normal.png> --albedo <albedo.png>"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-texture-pipeline

Design, write, check and hand over DayZ texture and material work: the maps, the `.rvmat`, the config wiring, damage materials, emissive and glass variants, penetration materials and Multi masks. Three small scripts do the mechanical checks; the references hold the depth.

Follow `skills/_shared/dayz-conventions.md`. The three scripts only read the files they are given and print a report or a template, so they do not run `/dayz-preflight`. This skill does not convert images: `/dayz-pack-texture` does, and it is the only step here that needs DayZ Tools.

## How to run

**Lint one or more `.rvmat` files** (standard library only):

```cmd
python "<skill-dir>\scripts\rvmat_lint.py" <file.rvmat> [<more.rvmat> ...] [--pdrive-root P:\] [--warnings-as-errors] [--json]
```

| Argument | Notes |
|---|---|
| `<file.rvmat>` | One or more files. A companion `.emat` of the same name next to a stub `.rvmat` is read too. |
| `--pdrive-root <folder>` | Also check that each texture path exists under this folder (`P:\` for vanilla `dz\...` paths, or the folder that holds the mod's prefix). A folder that does not exist is an error with exit code 2, so an unmounted `P:\` is not reported as a list of missing textures. |
| `--warnings-as-errors` | Exit 1 on warnings too. |
| `--json` | Print the findings as a JSON list. |

Each finding is one line, `file:line: ERROR|WARN CODE: message`. Exit code 0 means no error (warnings allowed), 1 means at least one error or a missing file, 2 means bad arguments or a missing `--pdrive-root` folder. Errors are things no vanilla file does (a source `.png` path, a local disk path, a Multi mask not on `tex1`, mismatched shader IDs). Differences that depend on the kind of asset are warnings.

**Write a starter `.rvmat`** (standard library only):

```cmd
python "<skill-dir>\scripts\rvmat_template.py" <super|damage|emissive|multi> --prefix <packed\path\name> [--output <file.rvmat>]
python "<skill-dir>\scripts\rvmat_template.py" penetration [--surface <packed\path.bisurf>] [--output <file.rvmat>]
```

`--prefix` is the packed path without suffix, for example `MyMod\data\vest`; the template names `<prefix>_nohq.paa` and `<prefix>_smdi.paa`. `damage` takes `--overlay <macro.paa>` (default: the vanilla weapon damage macro) and `emissive` takes `--strength <n>`. Without `--output` the template is printed. Every template is a starting point: replace the paths, then the values, from the nearest vanilla material.

**Measure a normal map's convention** (needs numpy and Pillow; install them once):

```cmd
python -m pip install -r "<skill-dir>\requirements.txt"
python "<skill-dir>\scripts\normal_convention.py" --normal <normal.png> --albedo <albedo.png> [--json]
```

Both images are PNG files of the same size and the same UV layout. Decode a `.paa` with ImageToPAA first.

Exit code 0 prints a candidate, `DirectX` or `OpenGL`. Exit code 2 is `INCONCLUSIVE`. Exit code 1 is bad input, including numpy or Pillow not being installed. A candidate is not proof; rule 3 below says how to confirm it.

Each script also takes `--help`, and the two `.rvmat` scripts take `--self-test`.

Outside an agent session, `scripts\dayz\rvmat-lint.bat`, `scripts\dayz\rvmat-template.bat` and `scripts\dayz\normal-convention.bat` run `rvmat_lint.py`, `rvmat_template.py` and `normal_convention.py` with the same arguments.

## Rules

1. **Check before you write.** Read every path, config key and material pattern in the mod or in the unpacked vanilla data on `P:\` before it goes into an answer or a file. Never edit a file on `P:\`.
2. **Take the lowest risk route that meets the goal:**
   - a skin: a `_co.paa` and `hiddenSelectionsTextures[]`;
   - a different highlight, relief or glow: a `.rvmat`;
   - a look per health level: damage and destruct `.rvmat` files through `healthLevels[]`;
   - bullet and surface response: a penetration `.rvmat` with a `.bisurf` on the collision LOD;
   - many tiled materials on one static mesh: the Multi shader, only once the section count and the two UV sets justify it;
   - a metallic and roughness set with no damage look and not terrain: the MatPBR route, which is reported by the community only. Prefer Super when either of those is needed.
3. **`_nohq` is DirectX style, Y-.** An OpenGL (Y+) source needs its green channel inverted before the final export. Do not guess a source's convention from where it came from: run `normal_convention.py` for a candidate, then confirm the candidate another way, with the baker's export setting or a raking light render. That render confirms only when the light crosses V, the known groove runs along U, and the copy with the green inverted reads the groove as a ridge. Do not read a shipped `_nohq` as plain RGB: it is stored swizzled. Details and limits: `references/map-conventions.md`.
4. **Copy the closest vanilla `.rvmat` of the same kind first.** Do not invent stage constants where vanilla examples differ by kind of asset. The same holds for map levels: before choosing `_smdi`, `_as` and `_co` levels, measure the closest vanilla asset whose material constants match yours. The generic `_smdi` table is far brighter than the vanilla motorbike paint that was measured.
5. **A template is a draft** until it holds the mod's real paths, selections and UV sets and was compared with a vanilla reference.
6. **UI textures** (loading screens, menu backgrounds, map images): never change the tone curve from an offline model, and ship a `.paa` from ImageToPAA, not a hand written `.edds`. Both rules, with what was measured, are in `references/ui-textures-and-edds.md`.
7. **Before borrowing a vanilla `.rvmat`**, measure its `_as` per channel and check Stage4, Stage5 and every `uvSource`. **Before changing UV orientation or winding**, decode the atlas and draw the affected faces over it. Both checks are in `references/baked-atlas-to-paa.md`.
8. **A material set from script is judged by the frame**, not by `GetObjectMaterial`, and a health level change wipes it: `skills/_shared/textures/runtime-material-swaps.md`.

## Workflow

1. Name the asset type, its selections, its UV sets and what should happen at run time.
2. Read the nearest `.rvmat`, `config.cpp` and texture paths in the mod or under `P:\DZ`.
3. Pick the route with the table in `references/rvmat-cookbook.md` and open the reference it names.
4. Make the maps by `references/map-conventions.md`. For a bake, follow `references/normal-bake-checklist.md`.
5. Write the `.rvmat`, from `rvmat_template.py` or from a vanilla copy, and lint it with `rvmat_lint.py`.
6. Convert the images with `/dayz-pack-texture`.
7. Go through `references/validation-checklist.md`, then hand the user the in-game list in `skills/_shared/textures/checking-the-look.md`.

When the work has to end in a mod that builds and loads, the next steps are `/dayz-lint`, `/dayz-build-pbo` and `/dayz-launch-test`, or `/dayz-gate` for all of them. Model faults behind a texture symptom (no material on collision faces, `P:\` paths in a `.rvmat`) are `/dayz-p3d-audit`.

## Ask before writing final files

Ask when any of these is unknown:

- the mod's root folder and packed path;
- the exact selections that get a texture or material swap;
- whether the model has one UV set or two;
- whether the texture is cosmetic only or must change surface, damage, glass, light or penetration behaviour;
- whether the result is a change to the mod or a standalone reference.

## Which file answers which question

| Question | File |
|---|---|
| Is this normal map OpenGL or DirectX, how is `_nohq` stored, what goes in each `_smdi` channel, how do I get from metallic and roughness to `_smdi`, which levels does vanilla use | `references/map-conventions.md` |
| Which route fits, the Super template and its values, `uvTransform` values, damage Stage3, emissive, glass, alpha decals, which environment map, penetration materials | `references/rvmat-cookbook.md` |
| How do `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`, `healthLevels[]` and the vehicle light material keys look in config | `references/config-and-damage.md` |
| When is the Multi shader worth it, its stages, UV sets and mask | `references/multi-rvmat-section-texturing.md` |
| Which shader for a vehicle part, tiled detail on overlapping UVs, color variants, generated wear | `references/vehicle-materials-and-color-variants.md` |
| How does the MatPBR and `.emat` route work, and what does vanilla ship of it | `references/matpbr-emat-pipeline.md` |
| What must a high to low normal bake in Blender get right | `references/normal-bake-checklist.md` |
| Why does an `_as` look wrong, what does a borrowed material bring along, is this the right atlas, why does ImageToPAA refuse this image, what changes on Linux | `references/baked-atlas-to-paa.md` |
| How do I treat a loading screen or menu texture, and why not write an `.edds` by hand | `references/ui-textures-and-edds.md` |
| What do I check before handing over | `references/validation-checklist.md` |

The shared texture pack holds the vanilla facts these files build on. Open one of its files when the question is about the game, not about the workflow:

| Question | File |
|---|---|
| Which suffix, what ImageToPAA does with it, which size, the procedural placeholders | `skills/_shared/textures/suffixes-and-sizes.md` |
| What each `.rvmat` key and stage does | `skills/_shared/textures/rvmat-stages.md` |
| Which vanilla material to copy for cloth, metal, glass or skin | `skills/_shared/textures/surface-recipes.md` |
| Which script call changes a texture or material, what health levels and wetness do to it, why a material set from script does not show | `skills/_shared/textures/runtime-material-swaps.md` |
| What the user checks in Object Builder and in game | `skills/_shared/textures/checking-the-look.md` |
