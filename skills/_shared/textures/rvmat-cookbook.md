# rvmat cookbook

Which material route fits a goal, a seven stage Super starting point and where its values come from, and the patterns for damage, emissive, glass, alpha decals, the environment map and penetration materials. Clone the nearest working vanilla `.rvmat` first whenever one exists.

How to read it: a `P:\` citation was checked on the vanilla files. "Measured" blocks carry their date and were not rechecked here. "Starting point" marks a value to adapt. What each key and stage does is in `rvmat-stages.md`, and which vanilla file to copy for cloth, metal, glass and skin is in `surface-recipes.md`; this file does not repeat them.

## Contents

- [Pick the route](#pick-the-route)
- [Super template](#super-template)
- [Moving existing materials to Super](#moving-existing-materials-to-super)
- [Damage and destruct Stage3](#damage-and-destruct-stage3)
- [Emissive materials](#emissive-materials)
- [Snow or moss on top, and wind on plants](#snow-or-moss-on-top-and-wind-on-plants)
- [Glass and chrome](#glass-and-chrome)
- [Alpha decal on a vehicle](#alpha-decal-on-a-vehicle)
- [Stage7: choose the environment map](#stage7-choose-the-environment-map)
- [Penetration materials](#penetration-materials)
- [The template writer and the linter](#the-template-writer-and-the-linter)

## Pick the route

| Goal | Prefer | Avoid |
|---|---|---|
| Recolor or skin only | A `_co.paa` and `hiddenSelectionsTextures[]` (`config-wiring.md`) | A new `.rvmat`, unless the surface response changes |
| Change normal, specular or gloss | A Super `.rvmat` with `_nohq` and `_smdi` | Baking the highlight into the `_co` |
| A look per health level | Normal, damage and destruct `.rvmat` files through `healthLevels[]` | A procedural Stage3 tint as the only damage look, unless that is wanted |
| Light on and off | A config material swap between an emissive and a plain `.rvmat` | Texture swaps from script for a material property |
| Glass or chrome | A clone of a vanilla glass or chrome `.rvmat` | A generic opaque Super material |
| Bullet and surface response | A penetration `.rvmat` on the collision faces | A visual `.rvmat` on a collision LOD |
| One mesh with many tiled materials | The Multi shader, after the UV sets and mask are checked (`multi-materials.md`) | Multi on a small item where selections are simpler |
| A part with a constant color and no `_co` | `NormalMapSpecularMap` (`vehicle-materials.md`) | Super, which expects the color from the face texture |
| A metallic and roughness set, with no damage look and not terrain | The MatPBR route (`matpbr-emat.md`), which no vanilla file on `P:\` confirms | MatPBR when either of those is needed |

Full vanilla Super materials to read side by side: a vehicle body, `P:\DZ\vehicles\wheeled\van_01\data\van_01_body.rvmat:7-83`, and a weapon, `P:\DZ\weapons\shotguns\saiga\data\saiga.rvmat:7-77`.

## Super template

`rvmat_template.py super` prints this starting point. Replace every path, then replace the values with those of the nearest vanilla material of the same kind.

```cpp
ambient[]={1,1,1,1};
diffuse[]={1,1,1,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0.4,0.4,0.4,1};
specularPower=80;
PixelShaderID="Super";
VertexShaderID="Super";
class Stage1
{
	texture="mymod\data\asset_nohq.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage2
{
	texture="#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage3
{
	texture="#(argb,8,8,3)color(0,0,0,0,MC)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage4
{
	texture="#(argb,8,8,3)color(1,1,1,1,AS)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage5
{
	texture="mymod\data\asset_smdi.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage6
{
	texture="#(ai,32,1,1)fresnel(1.12,0.78)";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
class Stage7
{
	texture="dz\data\data\env_land_co.paa";
	uvSource="tex";
	class uvTransform { aside[]={1,0,0}; up[]={0,1,0}; dir[]={0,0,1}; pos[]={0,0,0}; };
};
```

Where the template's values come from:

- The Stage6 texture is the van body's: `fresnel(1.12,0.78)` at `P:\DZ\vehicles\wheeled\van_01\data\van_01_body.rvmat:71`. Seven materials under `P:\DZ\vehicles` use it, all the van's. It is not a common value; the common ones per folder are in `surface-recipes.md`.
- The Stage2 placeholder, the two ways Stage6 is written and the two `dir[]` values vanilla uses are all in `rvmat-stages.md` and `suffixes-and-sizes.md`. A review should not fail a material on any of those differences alone. Measured on one mod (2026-09-02): a gate that required `dir[]={0,0,1}` rejected 26 stages copied word for word from a vanilla file.
- A whole vanilla file that is nothing but the seven stage Super layout is `P:\DZ\vehicles\parts\data\aircraft_battery.rvmat`. Its Stage2 holds `color(0.5,0.5,0.5,1,DT)` with a `uvTransform` whose `aside[]` and `up[]` are all zeroes (`P:\DZ\vehicles\parts\data\aircraft_battery.rvmat:23-28`); that is how vanilla wrote it, not a slip. Its Stage6 is `fresnel(0.4,0.4)` (`P:\DZ\vehicles\parts\data\aircraft_battery.rvmat:71`) and its Stage7 the black `color(0,0,0,1,CO)`, meaning no reflection (`P:\DZ\vehicles\parts\data\aircraft_battery.rvmat:83`).

## Moving existing materials to Super

Starting points from one mod's move of 13 materials to a baked atlas (2026-09-02):

- Keep the old `ambient[]` and `diffuse[]` while the model has no `_co` yet. Vanilla Super materials write `{1,1,1,1}` because the color comes from the texture; copying that onto a part with no texture leaves it white.
- Keep `specular[]` and `specularPower` in the first pass. The `_smdi` already changes them per texel, and changing the map and the constants together makes a difference in game impossible to pin on either.

## Damage and destruct Stage3

In a damage or destruct material, Stage3 holds a wear macro texture, not only a procedural tint. What else changes between the three materials, and the clothing macros, is in `rvmat-stages.md` ("Damage and destruct materials"). The weapon set:

- Pristine: the placeholder `color(0,0,0,0,MC)` in `Stage3` (`P:\DZ\weapons\shotguns\saiga\data\saiga.rvmat:35`).
- Damage: `weapons_damage_generic_mc.paa`, tiled four times (`rvmat-stages.md`).
- Destruct: `weapons_destruct_generic_mc.paa` in `Stage3` (`P:\DZ\weapons\shotguns\saiga\data\saiga_destruct.rvmat:35`), with the same `aside[]={4,0,0}` tiling (`P:\DZ\weapons\shotguns\saiga\data\saiga_destruct.rvmat:39-40`).

`rvmat_template.py damage` writes this Stage3. The config side is in `config-wiring.md`.

## Emissive materials

Use an on and off pair when config or script swaps the state; the vanilla pair, which differs only in the last number of `emmisive[]`, is in `rvmat-stages.md`. `rvmat_template.py emissive --strength <n>` writes `emmisive[]={1,1,1,<n>}`. The vehicle config keys that name the pair are in `config-wiring.md`.

## Snow or moss on top, and wind on plants

- **Top projection** puts a layer of a multi material on faces that point up, as on the Sakhal snow rocks: `multiTopProjectionLayer=3;`, `degAngleTopProjectionStart=50;`, `degAngleTopProjectionEnd=70;`, `multiTopProjectionBlend=0;`, `multiTopProjectionLayerNormal=-1;` (`P:\DZ\rocks\snow_rocks\data\rock_apart1\rock_apart1.rvmat:7-11`). Copy that block and change the layer and the angles.
- **Plant wind** is one line in the plant's material, `plantWind[]={...}` with four numbers (`P:\DZ\plants\bush\data\b_betulahumilis_1s_leaves.rvmat:1`). Reported, not checked: the numbers are speed, stiffness, smoothness and light, and stiffness 0 holds the plant still.

## Glass and chrome

Start from a vanilla glass or chrome material near the target (`surface-recipes.md` lists one per kind of glass). The usual traits are a high `specularPower`, a fresnel stage, an environment map and sometimes render flags. The van's window:

- `specularPower=500` (`P:\DZ\vehicles\wheeled\van_01\data\van_01_glass.rvmat:6`)
- `fresnel(0.78,0.15)` in `Stage6` (`P:\DZ\vehicles\wheeled\van_01\data\van_01_glass.rvmat:71`)
- `env_land_co.paa` in `Stage7` (`P:\DZ\vehicles\wheeled\van_01\data\van_01_glass.rvmat:83`)

## Alpha decal on a vehicle

The vanilla pattern, Super plus `renderFlags[]` holding `"nozwrite"`, and how often vanilla uses it are in `rvmat-stages.md`. What a mod decal adds:

- **Measured in game** on a mod car: labels with real alpha in a `_ca`, on a Super material with no render flags, rendered opaque. Adding the flag fixed them; changing the shader was not needed. This is one mod's decal, not a rule that Super ignores alpha: the vanilla window material `P:\DZ\vehicles\wheeled\data\auta_skla.rvmat` is Super with no `renderFlags[]` at all and its glass is see-through. For a decal lying on paint, copy the sticker material; for a window, copy a window.
- What the flag does not cover, so check it in game: sorting against other see-through surfaces, z-fighting when the decal is almost in the same plane as the paint, and that a symbol does not light itself at night without `emmisive[]`. DXT5 keeps the alpha and softens its edges.
- When the source is a decal with the icon in its alpha channel, build the texture as RGB = the swatch color per pixel and alpha = the real alpha. Never flatten the alpha onto the RGB: a white on black bake is what made an opaque decal look like a shader fault.

## Stage7: choose the environment map

Which maps vanilla ships in `P:\DZ\data\data\` is in `surface-recipes.md`. Among them: `env_land_co.paa` (the common one), `env_land_chrome_co.paa` and `env_chrome_co.paa` for chrome, `env_land_optic_co.paa` for lenses, `env_mirror_co.paa` and `env_land_plastic_co.paa`. The black `#(argb,8,8,3)color(0,0,0,1,CO)` means no reflection.

Measured 2026-11-02: mean RGB of the lower (ground) and upper (sky) halves of mip 0 of the 256 x 256 files, decoded with ImageToPAA:

| Environment map | Ground half | Sky half |
|---|---|---|
| `env_land_optic_co` | 80 / 79 / 54 (blue 25 under) | 169 / 182 / 200 |
| `env_land_co` | 39 / 40 / 33 | 160 / 173 / 187 |
| `env_land_chrome_co` | 62 / 64 / 59 | 206 / 210 / 213 |
| `env_chrome_co` | 132 / 131 / 129 | 194 / 198 / 204 |
| `env_mirror_co` | 123 / 127 / 114 | 171 / 180 / 193 |
| `env_land_plastic_co` | 127 / 127 / 127 | 192 / 194 / 198 |

- Seen in game on a mod motorbike (2026-10-28, no stored evidence): the vanilla motorbike body uses `env_land_optic_co` with its red paint at an `_smdi` G median of 5 (`smdi-and-levels.md`). A mod body kept that map with a silver paint raised to G/B 205/237, and its side panels and tank read olive in game. With `env_land_chrome_co` in the body material the silver read neutral; the damage and light materials built from the base material inherited the fix.
- Starting points: if your G stays near the vanilla asset's, keep its environment map. If you raise G toward a mirror, measure the ground half of the map first; do not inherit `env_land_optic_co` only because the vanilla asset uses it. For mirror, chrome or silver with a high G, use a neutral map such as `env_land_chrome_co`.

## Penetration materials

Faces of a collision LOD need a penetration `.rvmat` when bullet and surface behaviour matters. The file names a `.bisurf` in `surfaceInfo` and uses the flat shader pair. The whole vanilla file `P:\DZ\data\data\penetration\wood_desk.rvmat:1-9`:

```cpp
surfaceInfo="dz\data\data\penetration\wood_desk.bisurf";
ambient[]={0.78799999,0.55000001,0,1};
diffuse[]={0.78799999,0.55000001,0,1};
forcedDiffuse[]={0,0,0,0};
emmisive[]={0,0,0,1};
specular[]={0,0,0,1};
specularPower=1;
PixelShaderID="Normal";
VertexShaderID="Basic";
```

`rvmat_template.py penetration --surface <path.bisurf>` writes this shape. Point a mod's collision faces at the vanilla `dz\data\data\penetration\*.rvmat` that matches the surface when one exists. `/dayz-p3d-audit` reports collision faces with no material.

## The template writer and the linter

Both ship with `/dayz-pack-texture`, in its `scripts\` folder, and use the standard library only. `<skill-dir>` is that skill's folder.

**Write a starter `.rvmat`:**

```cmd
python "<skill-dir>\scripts\rvmat_template.py" <super|damage|emissive|multi> --prefix <packed\path\name> [--output <file.rvmat>]
python "<skill-dir>\scripts\rvmat_template.py" penetration [--surface <packed\path.bisurf>] [--output <file.rvmat>]
```

`--prefix` is the packed path without suffix, for example `MyMod\data\vest`; the template names `<prefix>_nohq.paa` and `<prefix>_smdi.paa`. `damage` takes `--overlay <macro.paa>` (default: the vanilla weapon damage macro) and `emissive` takes `--strength <n>`. Without `--output` the template is printed. Every template is a draft until it holds the mod's real paths, selections and UV sets and was compared with the nearest vanilla material.

**Lint one or more `.rvmat` files:**

```cmd
python "<skill-dir>\scripts\rvmat_lint.py" <file.rvmat> [<more.rvmat> ...] [--pdrive-root P:\] [--warnings-as-errors] [--json]
```

| Argument | Notes |
|---|---|
| `<file.rvmat>` | One or more files. A companion `.emat` of the same name next to a stub `.rvmat` is read too (`matpbr-emat.md`). |
| `--pdrive-root <folder>` | Also check that each texture path exists under this folder (`P:\` for vanilla `dz\...` paths, or the folder that holds the mod's prefix). A folder that does not exist is an error with exit code 2, so an unmounted `P:\` is not reported as a list of missing textures. |
| `--warnings-as-errors` | Exit 1 on warnings too. |
| `--json` | Print the findings as a JSON list. |

Each finding is one line, `file:line: ERROR|WARN CODE: message`. Exit code 0 means no error (warnings allowed), 1 means at least one error or a missing file, 2 means bad arguments or a missing `--pdrive-root` folder. Errors are mistakes a mod material should not ship with (a source `.png` path, a local disk path, a missing or mismatched shader ID, a Multi material without Stage0 to Stage4). A few vanilla files under `P:\DZ` still trip them (absolute paths in 18 places, a missing `PixelShaderID` in 35 and a missing `VertexShaderID` in 37, a missing Multi base stage in 5), so a run over vanilla is not clean. Differences that depend on the kind of asset are warnings, among them a Multi mask that does not read `tex1`.

Both scripts take `--help` and `--self-test`. `/dayz-lint` checks other things in a `.rvmat` (the `NormalMapMacro` shader, `P:\` paths, missing mod files, unclosed strings), and `/dayz-p3d-audit --rvmat` checks the `.rvmat` files a model names; run them too before a build.
