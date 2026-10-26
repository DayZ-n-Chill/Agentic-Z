# Texture and material pack

Tier 3 cookbook for DayZ textures (`.paa`) and materials (`.rvmat`): suffixes, sizes, shaders, stages and recipes for cloth, metal, glass and skin. Written for `dayz-asset-specialist`; any DayZ worker may load one file of it when a task needs it. Tier 1 and Tier 2 (`_shared/conventions/assets.md`) still apply on top.

Every game fact here cites the vanilla file on `P:\` it came from, or `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg` for how ImageToPAA packs a suffix. Counts come from a scan of the unpacked vanilla data under `P:\DZ`; damage and destruct variants are left out of them unless a line says otherwise. A line marked **tool knowledge** comes from Object Builder or Bohemia's shader notes, not from a vanilla text file, so confirm it on the screen.

## Which file to open

| Question | File |
|---|---|
| Which suffix a texture needs, what ImageToPAA does with it, which size to make it, and the procedural placeholder for an empty slot | `suffixes-and-sizes.md` |
| What each `.rvmat` key and stage does in the Super and Skin shaders, plus damage, destruct and thermal variants | `rvmat-stages.md` |
| Which vanilla material to copy for cloth, metal, glass or skin, and which values to change | `surface-recipes.md` |
| What to tell the user to look at in Object Builder and in game once the files are written | `checking-the-look.md` |

Related packs: `dayz-p3d-audit/references/config-rvmat-checks.md` (the `.rvmat` checks the model audit makes), `_shared/wearables/references/color-variants.md` (hidden selections and one texture per color) and `/dayz-pack-texture` (packs the images).

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| Surface looks flat, no bumps | `Stage1` points at a missing or wrongly suffixed normal map, or still holds the flat placeholder | `rvmat-stages.md`, `suffixes-and-sizes.md` |
| Cloth shines like plastic | Specular and `specularPower` copied from a metal or glass material | `surface-recipes.md` |
| Metal looks dull grey | `_smdi` almost black, or `Stage7` holds a dark color instead of an environment map | `surface-recipes.md` |
| Glass is opaque | The color texture is `_co` (no alpha) instead of `_ca`, or the alpha is white | `surface-recipes.md` |
| Item looks the same at every health level | `healthLevels[]` points every level at the same `.rvmat` | `rvmat-stages.md` |
| Texture rejected by `/dayz-pack-texture` | Filename has no vanilla suffix | `suffixes-and-sizes.md` |
