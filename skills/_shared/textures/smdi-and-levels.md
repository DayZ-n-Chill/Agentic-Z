# `_smdi` packing and map levels

What goes in each channel of an `_smdi`, how to get there from a metallic and roughness set, how to set `_smdi`, `_as` and `_co` levels against a vanilla asset of the same family, and the border fault a per material change can leave in a DXT atlas.

How to read it: a `P:\` citation was checked on the vanilla files. "Measured" blocks carry their date and were not rechecked here. "Starting point" marks a value to adapt, not a vanilla measurement. How ImageToPAA swizzles an `_smdi`, and the vanilla procedural `SMDI` values, are in `suffixes-and-sizes.md`.

## Contents

- [The channels](#the-channels)
- [From a metallic and roughness set to the green channel](#from-a-metallic-and-roughness-set-to-the-green-channel)
- [Packing the `_smdi` from a specular map and a roughness map](#packing-the-_smdi-from-a-specular-map-and-a-roughness-map)
- [Calibrating against a vanilla asset of the same family](#calibrating-against-a-vanilla-asset-of-the-same-family)
- [The DXT block staircase after a per material change](#the-dxt-block-staircase-after-a-per-material-change)

## The channels

| Channel | Meaning | Starting point |
|---|---|---|
| R | Unused by the map: ImageToPAA forces it to 255 for `*_smdi.*` | 255 |
| G | Specular strength | dark for matte, brighter for shiny |
| B | Gloss (specular power) | roughness inverted |
| A | Forced to 255 by ImageToPAA | |

Starting points by material. These rows are generic, not measured vanilla values:

| Material | G | B | Notes |
|---|---|---|---|
| worn painted metal | 70 to 130 | 80 to 170 | Add edge wear in G and B. |
| raw steel | 150 to 220 | 150 to 230 | Avoid a mirror unless a vanilla asset matches. |
| black rubber | 20 to 60 | 30 to 80 | Weak, broad highlight. |
| matte plastic | 35 to 90 | 60 to 120 | Raise B for polished plastic. |
| glass or chrome | 180 to 255 | 180 to 255 | Also needs the right fresnel and environment map. |
| wood | 20 to 70 | 30 to 90 | Weak, broad highlight. |

On the vanilla `motorbike_02` body the red paint measures a G median of 5, far below the "worn painted metal" row. Calibrate against a vanilla asset of the same family before trusting a row (below).

- The case of the file name does not matter: a test on 2026-10-07 found `x_SMDI.png` swizzled like `x_smdi.png`.
- Measured vanilla files (2026-09-21): the `_smdi` of the searchlight, battery adapter, a housing and the battery charger decode with R at 255 everywhere; G and B carry the data.

## From a metallic and roughness set to the green channel

A rule that is not verified in game: do not copy a metallic map straight into specular. Metallic is a blend factor between insulator and metal, not a reflectance. Copied as specular, its black (wood, cloth, plastic) becomes zero specular, while real insulators reflect about 4 % at normal incidence (2 to 16 %) and metals 70 to 100 %. Replace the black with `#383838` and keep the bright metal.

- Arithmetic, checked offline: 4 % linear encoded to sRGB is 0.2209, which is 56, `0x38`. Read back as sRGB it is 3.95 %. 56 sits inside the G ranges of the table above for rubber, plastic and wood.
- **Not verified: whether the Super shader decodes `_smdi` green as sRGB.** If it reads green as raw linear, `0x38` is 0.22 of full scale, about 5.6 times the intended 4 %. That green behaves like a physically based F0 at all is not established either. A hint against the sRGB reading: `TexConvert.cfg` comments the color classes (`_co`, `_ca`, macro) as "sRGB color space" and gives `*_smdi.*` no such comment. A second hint: the vanilla motorbike paint below sits at 5, not 56. Treat `0x38` as a sensible starting point, not a calibrated value.
- One ImageMagick recipe composites solid `#383838` over the metallic map using the inverted metallic map as the mask. Worked out from ImageMagick's masked composite rule for opaque inputs, not run: `out = m*m + 0.2196*(1 - m)`, so 0 gives 56, 64 gives 58, 128 gives 92 and 255 gives 255. That is correct for a black and white metallic map and darkens grey or antialiased transitions (m squared where m was meant). Starting point: the textbook form is the linear blend `out = 0.2196 + (1 - 0.2196)*m` (128 gives 156). Pick one on purpose.
- Metal comes out at the metallic value (white is 255), not at the albedo's color. DayZ's green is one number per texel, so that loss comes with the packing.
- The result is a greyscale specular map, usually saved as `<name>_Specular.<ext>` beside the source. That file is the green source of an `_smdi`, not an `_smdi`: pack R = 255, G = this map, B = gloss (inverted roughness).

## Packing the `_smdi` from a specular map and a roughness map

One ImageMagick `-combine` call packs the map: R filled white, G the specular as grey, B the gloss as grey (negated when the source is roughness). That matches the channel table. A batch file can do it by name: given an image named `<base>_Specular`, it looks for `<base>_gloss`, `_glossy`, `_glossiness`, `_rough`, `_roughness` or `_r` with the same extension and writes `<base>_SMDI<ext>`. One such batch file was read, not run. What to check in a packer of that kind:

- **Roughness beats gloss** when the roughness loop runs after the gloss loop and overwrites the match. With both `<base>_gloss` and `<base>_rough` present, B is the inverted roughness.
- **Only exact siblings match**: the same `<base>` and the same extension. A `.png` specular next to a `.tga` roughness gives "Could not find a matching gloss or roughness map". The `_r` suffix means `<base>_r<ext>` only, but a red mask named that way would still be read as roughness.
- The name match ignores case, wherever `_Specular` sits in the name. A path that contains `!` breaks the lookup.
- The output keeps the input's extension: a `.jpg` specular gives a lossy `_SMDI.jpg`. Whether ImageMagick writes the `.tga` compressed is not verified; if it does, ImageToPAA rejects it (`suffixes-and-sizes.md`).
- The inputs must share a size. How `-combine` handles a mismatch is not verified, so resize first.
- **Write 8 bits per channel.** A 16-bit greyscale PNG fails ImageToPAA (`suffixes-and-sizes.md`). 16-bit RGB was not tested, so 8 bits is the safe target. On a Q16 ImageMagick build force `-depth 8` (not run here); a packer that passes no `-depth` leaves the depth to the build.

## Calibrating against a vanilla asset of the same family

Before choosing `_smdi`, `_as` and `_co` levels, measure the closest vanilla asset of the same family whose material constants match yours. The map works together with the material's `specular[]`, `specularPower`, fresnel and environment map, so the same green can read differently under other constants.

The vanilla motorbike body material sets, in `P:\DZ\vehicles\singletrack\Motorbike_02\data\motorbike_02_body.rvmat`:

- `specular[]={1.1,1.1,1.1,1}` and `specularPower=160` (`P:\DZ\vehicles\singletrack\Motorbike_02\data\motorbike_02_body.rvmat:5-6`)
- `fresnel(0.53,0.22)` in `Stage6` (`P:\DZ\vehicles\singletrack\Motorbike_02\data\motorbike_02_body.rvmat:71`)
- `env_land_optic_co.paa` in `Stage7` (`P:\DZ\vehicles\singletrack\Motorbike_02\data\motorbike_02_body.rvmat:83`)

Measured 2026-11-02 (DayZ 1.30.164014): the vanilla `motorbike_02_body_red_co.paa`, `_smdi.paa` and `_as.paa` against the body atlas of a mod motorbike before its calibration. The mod's material already used the four values above, and it looked worse than the vanilla in gloss and color side by side in game. Mip 0 decoded with ImageToPAA, `_smdi` and `_as` resampled to the `_co` size. Both columns cover the texels whose `_co` is not black (largest channel above 6). Luminance is 0.299 R + 0.587 G + 0.114 B.

| | Vanilla `motorbike_02_body` | Mod atlas before calibration |
|---|---|---|
| `_co` luminance p10 / p50 / p90 | 24 / 56 / 99 | 30 / 41 / 112 |
| `_smdi` G (specular) p50 / p90 | 4 / 101 | 30 / 125 |
| `_smdi` B (gloss) p50 / p90 | 49 / 156 | 107 / 154 |
| `_as` G mean / median | 121 / 120 | 171 / 175 |

| Vanilla class (by `_co`, same texels) | Luminance p50 | `_smdi` G p50 / p90 | `_smdi` B p50 / p90 | `_as` G mean / median |
|---|---|---|---|---|
| red paint (saturation at least 0.35, red 20 over green and blue) | 92 | 5 / 52 | 55 / 82 | 137 / 146 |
| light metal (luminance above 110, saturation under 0.15) | 138 | 28 / 243 | 50 / 148 | 207 / 215 |
| mid grey (luminance 60 to 110, saturation under 0.15) | 73 | 49 / 174 | 47 / 159 | 183 / 201 |
| dark (luminance under 35) | 25 | 0 / 12 | 41 / 206 | 56 / 8 |

- Half of this body's texels have G at 4 or less, and its red paint sits at a G median of 5. The high values are in the p90 of the light metal and mid grey classes. The generic "worn painted metal" row (G 70 to 130) is 14 to 26 times that paint median.
- The mod's darkest tenth was lighter (luminance p10 of 30 against 24) and its ambient shadow weaker (`_as` G median 175 against 120). Since the material constants matched, the maps are the likely cause of the difference; other inputs, normals and viewing conditions were not compared.
- Name the statistic and the texels it covers. On the vanilla dark class the `_as` G mean is 56 and the median 8. On the mod atlas the `_as` G median is 154 over all texels and 175 without the black ones.
- A related trap, not part of the measurement: a factor computed over faces plus padding left one class of the mod at luminance 48 against a target of 28.

Procedure (a starting point): decode the shipped `.paa` files of the closest vanilla asset of the same family and of the mod, not the PNG sources. Check that the material constants match. Set G and B per surface class with the vanilla figure beside each, stating the texels and the statistic. Then look in game next to the vanilla asset under the same light. If G is raised toward a mirror, the environment map in `Stage7` may need to change too (`rvmat-cookbook.md`, "Stage7: choose the environment map").

## The DXT block staircase after a per material change

Seen on a mod motorbike (2026-10-28), with no stored evidence:

- A per material `_smdi` recalibration raised a fuel tank's mirror paint from about G/B 100/190 to 205/237 and gave no class to the logo panel that shares its UV island. The export step used there keeps the old value in every 4 x 4 DXT block that holds texels of another material, so that DXT1 does not mix two islands. That step left 74 % of the mirror texels within 2 px of the logo at G of about 100, and 33 % of those 2 to 4 px away. With the logo given the class of the paint around it, that stale rim measured 0 %.
- In game before the fix: a sawtooth line under the logo seen up close, and a two tone tank with matte bands around the logo and a mirror centre. After it the tank read as one tone from above; the close-up was not looked at again.

What follows from that one case (starting points):

- Give a decal or logo under clear coat the class of the paint around it, not "no class".
- Before accepting a per material change, measure by distance to the border with each neighbour in the same island: the share of border texels that did not change while the interior did. A rim of 2 to 4 texels that kept the old value is the staircase.
- Keeping whole DXT blocks next to a foreign island was that pipeline's tradeoff, not a general rule. DXT1 shares one palette per 4 x 4 block anyway. Check the border of both islands and tell kept values apart from compression artifacts.
