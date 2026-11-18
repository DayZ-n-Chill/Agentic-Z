# Texture and material pack

Tier 3 cookbook for DayZ textures (`.paa`) and materials (`.rvmat`): suffixes, sizes, shaders, stages and recipes for cloth, metal, glass and skin. Written for `dayz-asset-specialist`; any DayZ worker may load one file of it when a task needs it. Tier 1 and Tier 2 (`_shared/conventions/assets.md`) still apply on top.

Every game fact here cites the vanilla file on `P:\` it came from, or `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg` for how ImageToPAA packs a suffix. Counts come from a scan of the unpacked vanilla data under `P:\DZ`; damage and destruct variants are left out of them unless a line says otherwise. A line marked **tool knowledge** comes from Object Builder or Bohemia's shader notes, not from a vanilla text file, so confirm it on the screen. A block marked **measured in game** records a test run with no vanilla file behind it; repeat the test before a design depends on it.

## Which file to open

| Question | File |
|---|---|
| Which suffix a texture needs, what ImageToPAA does with it, which size to make it, which images ImageToPAA refuses, and the procedural placeholder for an empty slot | `suffixes-and-sizes.md` |
| What each `.rvmat` key and stage does in the Super and Skin shaders, plus damage, destruct and thermal variants | `rvmat-stages.md` |
| Which vanilla material to copy for cloth, metal, glass or skin, and which values to change | `surface-recipes.md` |
| Which material route fits a goal, the Super template, damage Stage3, emissive, glass, alpha decals, the environment map, penetration materials, and how to run the `.rvmat` template writer and linter | `rvmat-cookbook.md` |
| Which way a normal map points, how to measure a source map's convention, what a packed `_nohq` holds, a normal map from albedo brightness | `normal-maps.md` |
| What a high to low normal bake in Blender must get right | `normal-bake.md` |
| What goes in each `_smdi` channel, from metallic and roughness to `_smdi`, setting map levels against vanilla, the DXT border fault | `smdi-and-levels.md` |
| How `hiddenSelectionsTextures[]`, `hiddenSelectionsMaterials[]`, `healthLevels[]` and the vehicle light material keys look in config | `config-wiring.md` |
| When the Multi shader is worth it, which mask color picks which material, painting the mask | `multi-materials.md` |
| Which shader a vehicle or hard surface part needs, tiled detail on overlapping UVs, color variants, generated wear | `vehicle-materials.md` |
| The MatPBR and `.emat` route for a metallic and roughness set, and what vanilla ships of it | `matpbr-emat.md` |
| Why an `_as` looks wrong, what a borrowed vanilla material brings along, whether this is the right atlas, converting a `.paa` back, Linux | `baked-atlas-checks.md` |
| Loading screen, menu and map textures: the tone curve, screen sized images, and why not to write an `.edds` by hand | `ui-textures.md` |
| Which script call changes a texture or material, what health levels and wetness do to it, and why a material set from script does not show | `runtime-material-swaps.md` |
| What to check before handing the work over, what to ask first, and what to tell the user to look at in Object Builder and in game | `checking-the-look.md` |

## Workflow

1. Name the asset type, its selections, its UV sets and what should happen at run time; ask what is unknown (`checking-the-look.md`, "Questions to ask").
2. Read the nearest `.rvmat`, `config.cpp` and texture paths in the mod or under `P:\DZ`. Never edit a file on `P:\`.
3. Pick the route with `rvmat-cookbook.md` ("Pick the route"), taking the lowest risk route that meets the goal, and open the file it names.
4. Make the maps by `normal-maps.md` and `smdi-and-levels.md`; for a bake, `normal-bake.md`.
5. Write the `.rvmat` from `rvmat_template.py` or from a vanilla copy, and lint it with `rvmat_lint.py`. Both scripts, and `normal_convention.py`, ship with `/dayz-pack-texture`, which also converts the images to `.paa`.
6. Go through "Before handing over" in `checking-the-look.md`, then hand the user its Object Builder and in-game lists. A mod that must build and load continues with `/dayz-gate`.

Related packs: `dayz-p3d-audit/references/config-rvmat-checks.md` (the `.rvmat` checks the model audit makes), `_shared/wearables/references/color-variants.md` (hidden selections and one texture per color), `_shared/models/multi-rvmat-texturing.md` (the model side of a Multi material: stage roles, the two UV sets, faces with no texture).

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| Surface looks flat, no bumps | `Stage1` points at a missing or wrongly suffixed normal map, or still holds the flat placeholder | `rvmat-stages.md`, `suffixes-and-sizes.md` |
| Cloth shines like plastic | Specular and `specularPower` copied from a metal or glass material | `surface-recipes.md` |
| Metal looks dull grey | `_smdi` almost black, or `Stage7` holds a dark color instead of an environment map | `surface-recipes.md` |
| Glass is opaque | The color texture is `_co` (no alpha) instead of `_ca`, or the alpha is white | `surface-recipes.md` |
| Item looks the same at every health level | `healthLevels[]` points every level at the same `.rvmat` | `rvmat-stages.md` |
| Texture rejected by `/dayz-pack-texture` | Filename has no vanilla suffix | `suffixes-and-sizes.md` |
| Material set from script does not show | The engine's health level material replaced it, or the getter was trusted | `runtime-material-swaps.md` |
| Bumps look pushed in | The normal map is OpenGL style (Y+); `_nohq` is DirectX style (Y-) | `normal-maps.md`, `suffixes-and-sizes.md` |
| ImageToPAA says `Loading of img failed` | RLE compressed TGA, 16-bit PNG, or a PNG saved by Blender | `suffixes-and-sizes.md` |
| A loading screen looks brighter or banded after a tone change | The curve was changed from an offline model, or linear data was stored in DXT1 | `ui-textures.md` |
| A hand written `.edds` loads (`LoadImageFile` returns `true`) and shows nothing | Hand written `.edds` files do not render; ship an ImageToPAA `.paa` | `ui-textures.md` |
| Wrong texture on the model after a UV change | The atlas itself is the wrong one | `baked-atlas-checks.md` |
