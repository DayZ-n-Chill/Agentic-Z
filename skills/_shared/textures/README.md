# Texture and material pack

Tier 3 cookbook for DayZ textures (`.paa`) and materials (`.rvmat`): suffixes, sizes, shaders, stages and recipes for cloth, metal, glass and skin. Written for `dayz-asset-specialist`; any DayZ worker may load one file of it when a task needs it. Tier 1 and Tier 2 (`_shared/conventions/assets.md`) still apply on top.

Every game fact here cites the vanilla file on `P:\` it came from, or `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg` for how ImageToPAA packs a suffix. Counts come from a scan of the unpacked vanilla data under `P:\DZ`; damage and destruct variants are left out of them unless a line says otherwise. A line marked **tool knowledge** comes from Object Builder or Bohemia's shader notes, not from a vanilla text file, so confirm it on the screen. A block marked **measured in game** records a test run with no vanilla file behind it; repeat the test before a design depends on it.

## Which file to open

| Question | File |
|---|---|
| Which suffix a texture needs, what ImageToPAA does with it, which size to make it, and the procedural placeholder for an empty slot | `suffixes-and-sizes.md` |
| What each `.rvmat` key and stage does in the Super and Skin shaders, plus damage, destruct and thermal variants | `rvmat-stages.md` |
| Which vanilla material to copy for cloth, metal, glass or skin, and which values to change | `surface-recipes.md` |
| What to tell the user to look at in Object Builder and in game once the files are written | `checking-the-look.md` |
| Which script call changes a texture or material, what health levels and wetness do to it, and why a material set from script does not show | `runtime-material-swaps.md` |

Related packs: `dayz-p3d-audit/references/config-rvmat-checks.md` (the `.rvmat` checks the model audit makes), `_shared/wearables/references/color-variants.md` (hidden selections and one texture per color), `/dayz-pack-texture` (packs the images) and the `dayz-texture-pipeline` skill (`dayz-texture-pipeline/SKILL.md`: map conventions per suffix, the `.rvmat` cookbook, config and damage wiring, Multi materials, vehicle materials, baked atlases, the MatPBR `.emat` route, UI textures, and an `.rvmat` linter, template writer and normal map convention check).

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
| Bumps look pushed in | The normal map is OpenGL style (Y+); `_nohq` is DirectX style (Y-) | `suffixes-and-sizes.md` |
| ImageToPAA says `Loading of img failed` | RLE compressed TGA, 16-bit PNG, or a PNG saved by Blender | `suffixes-and-sizes.md` |
