# `_smdi` channels and map levels

What goes in each channel of an `_smdi`, how to get there from a metallic and roughness set, how to set `_smdi`, `_as` and `_co` levels against a vanilla asset of the same kind, and the border fault a per material change can leave in a DXT atlas.

How ImageToPAA swizzles an `_smdi`, and the vanilla procedural `SMDI` values, are in `suffixes-and-sizes.md`. A value called a starting point is one to adapt, not a vanilla measurement.

## Contents

- [The channels](#the-channels)
- [From a metallic map to the green channel](#from-a-metallic-map-to-the-green-channel)
- [Packing an `_smdi` from a specular and a roughness map](#packing-an-_smdi-from-a-specular-and-a-roughness-map)
- [Setting levels against a vanilla asset](#setting-levels-against-a-vanilla-asset)
- [A stale rim after a per material change](#a-stale-rim-after-a-per-material-change)

## The channels

| Channel | Meaning | Starting point |
|---|---|---|
| R | Not used by the map; ImageToPAA forces it to 255 for `*_smdi.*` | 255 |
| G | Specular strength | dark for matte, brighter for shiny |
| B | Gloss (specular power) | roughness inverted |
| A | Forced to 255 by ImageToPAA | |

The vanilla battery charger shows the layout: `P:\DZ\gear\camping\data\battery_charger_smdi.paa` decodes with red and alpha at 255 on every pixel, green from 0 to 255 and blue from 90 to 115. The searchlight, battery adapter and a housing decode the same way, with the data in G and B. The case of the suffix does not matter; ImageToPAA swizzles `x_SMDI.png` like `x_smdi.png` (**tool knowledge**).

Starting points by material. These are generic rows, not vanilla measurements:

| Material | G | B | Notes |
|---|---|---|---|
| Worn painted metal | 70 to 130 | 80 to 170 | Add edge wear in G and B. |
| Raw steel | 150 to 220 | 150 to 230 | Avoid a mirror unless a vanilla asset matches. |
| Black rubber | 20 to 60 | 30 to 80 | Weak, broad highlight. |
| Matte plastic | 35 to 90 | 60 to 120 | Raise B for polished plastic. |
| Glass or chrome | 180 to 255 | 180 to 255 | Also needs the right fresnel and environment map. |
| Wood | 20 to 70 | 30 to 90 | Weak, broad highlight. |

Vanilla paint can sit far below these rows: the red paint of the vanilla `motorbike_02` body has a G median of 5. Set levels against a vanilla asset of the same kind before trusting a row (below).

## From a metallic map to the green channel

Unverified (not tested in game): never copy a metallic map straight into specular. Metallic is a blend factor between insulator and metal, not a reflectance. Copied as specular, its black (wood, cloth, plastic) becomes zero specular, while real insulators reflect about 4 % at normal incidence (2 to 16 %) and metals 70 to 100 %. Replace the black with `#383838` and keep the bright metal.

- The arithmetic: 4 % linear encoded as sRGB is 0.2209, which is 56, `0x38`. Read back as sRGB it is 3.95 %. 56 sits inside the G ranges above for rubber, plastic and wood.
- Whether the Super shader decodes `_smdi` green as sRGB is not known. If it reads green as raw linear, `0x38` is 0.22 of full scale, about 5.6 times the intended 4 %, and that green behaves like a physical F0 at all is not established either. Two hints point against the sRGB reading: `TexConvert.cfg` labels the color classes (`_co`, `_ca`, macro) "sRGB color space" and gives `*_smdi.*` no such label, and the vanilla motorbike paint sits at 5, not 56. Treat `0x38` as a sensible start, not a calibrated value.
- One ImageMagick recipe lays solid `#383838` over the metallic map with the inverted metallic map as the mask. By ImageMagick's masked composite rule for opaque inputs (worked out, not run) that gives `out = m*m + 0.2196*(1 - m)`, so 0 gives 56, 64 gives 58, 128 gives 92 and 255 gives 255. That is right for a black and white metallic map and darkens grey or antialiased edges (m squared where m was meant). The textbook form is the linear blend `out = 0.2196 + (1 - 0.2196)*m`, where 128 gives 156. Pick one on purpose.
- Metal comes out at the metallic value (white is 255), not at the albedo's color. DayZ's green is one number per texel, so that loss comes with the format.
- The result is a greyscale specular map, usually saved as `<name>_Specular.<ext>` beside the source. It is the green source of an `_smdi`, not an `_smdi`: pack R = 255, G = this map, B = gloss (inverted roughness).

## Packing an `_smdi` from a specular and a roughness map

One ImageMagick `-combine` call packs the map: R filled white, G the specular as grey, B the gloss as grey, negated when the source is roughness. A batch file can do it by name: given `<base>_Specular`, it looks for `<base>_gloss`, `_glossy`, `_glossiness`, `_rough`, `_roughness` or `_r` with the same extension and writes `<base>_SMDI<ext>`. What to check in a packer of that kind (read, not run):

- Roughness wins over gloss when the roughness loop runs after the gloss loop and overwrites the match. With both `<base>_gloss` and `<base>_rough` present, B is the inverted roughness.
- Only exact siblings match: the same `<base>` and the same extension. A `.png` specular beside a `.tga` roughness gives "Could not find a matching gloss or roughness map". `_r` means `<base>_r<ext>` only, but a red mask named that way is still read as roughness.
- The name match ignores case, wherever `_Specular` sits in the name. A path with `!` in it breaks the lookup.
- The output keeps the input's extension, so a `.jpg` specular gives a lossy `_SMDI.jpg`. Whether ImageMagick writes the `.tga` compressed is not checked; if it does, ImageToPAA rejects it (`suffixes-and-sizes.md`).
- The inputs must share a size. How `-combine` handles a mismatch is not checked, so resize first.
- Write 8 bits per channel. A 16-bit greyscale PNG fails ImageToPAA (`suffixes-and-sizes.md`) and 16-bit RGB is untested. On a Q16 ImageMagick build force `-depth 8` (not run); a packer that passes no `-depth` leaves it to the build.

## Setting levels against a vanilla asset

Before choosing `_smdi`, `_as` and `_co` levels, measure the closest vanilla asset of the same kind whose material constants match yours. The map works together with the material's `specular[]`, `specularPower`, fresnel and environment map, so the same green reads differently under other constants.

The vanilla motorbike body material, `P:\DZ\vehicles\singletrack\Motorbike_02\data\motorbike_02_body.rvmat`, sets:

- `specular[]={1.1,1.1,1.1,1}` and `specularPower=160` (`:5` and `:6`)
- `fresnel(0.53,0.22)` in `Stage6` (`:71`)
- `env_land_optic_co.paa` in `Stage7` (`:83`)

A mod motorbike whose material already used those four values looked worse than the vanilla one in gloss and color, side by side in game (DayZ 1.30). Its body atlas against the vanilla `motorbike_02_body_red_co.paa`, `_smdi.paa` and `_as.paa`, decoded with ImageToPAA at the top mip, `_smdi` and `_as` resampled to the `_co` size, over texels whose `_co` is not black (largest channel above 6), luminance as 0.299 R + 0.587 G + 0.114 B:

| | Vanilla `motorbike_02_body` | Mod atlas before tuning |
|---|---|---|
| `_co` luminance p10 / p50 / p90 | 24 / 56 / 99 | 30 / 41 / 112 |
| `_smdi` G (specular) p50 / p90 | 4 / 101 | 30 / 125 |
| `_smdi` B (gloss) p50 / p90 | 49 / 156 | 107 / 154 |
| `_as` G mean / median | 121 / 120 | 171 / 175 |

The vanilla body split by surface, from its `_co` over the same texels:

| Vanilla surface | Luminance p50 | `_smdi` G p50 / p90 | `_smdi` B p50 / p90 | `_as` G mean / median |
|---|---|---|---|---|
| Red paint (saturation 0.35 or more, red 20 over green and blue) | 92 | 5 / 52 | 55 / 82 | 137 / 146 |
| Light metal (luminance above 110, saturation under 0.15) | 138 | 28 / 243 | 50 / 148 | 207 / 215 |
| Mid grey (luminance 60 to 110, saturation under 0.15) | 73 | 49 / 174 | 47 / 159 | 183 / 201 |
| Dark (luminance under 35) | 25 | 0 / 12 | 41 / 206 | 56 / 8 |

- Half of this body's texels have G at 4 or less, and its red paint sits at a G median of 5. The high values are in the p90 of the light metal and mid grey surfaces. The generic "worn painted metal" row (G 70 to 130) is 14 to 26 times that paint median.
- The mod's darkest tenth is lighter (p10 of 30 against 24) and its ambient shadow weaker (`_as` G median 175 against 120). With matching material constants, the maps are the likely cause; normals and viewing conditions were not compared.
- Always name the statistic and the texels it covers. On the vanilla dark surface the `_as` G mean is 56 and the median 8. On the mod atlas the `_as` G median is 154 over all texels and 175 without the black ones.
- A factor worked out over faces plus padding left one surface of the mod at luminance 48 against a target of 28; compute it over the faces only.

The procedure, as a starting point: decode the shipped `.paa` files of the closest vanilla asset and of the mod, not the PNG sources. Check that the material constants match. Set G and B per surface with the vanilla figure beside each, naming texels and statistic. Then look in game next to the vanilla asset under the same light. If G goes up toward a mirror, the `Stage7` environment map may need to change too (`rvmat-cookbook.md`, "Stage7: choose the environment map").

## A stale rim after a per material change

Seen in game on a mod motorbike; not checked on `P:\`:

- A per material `_smdi` change raised a fuel tank's mirror paint from about G/B 100/190 to 205/237 and left the logo panel that shares its UV island with no surface class. The export step keeps the old value in every 4 x 4 DXT block that holds texels of another material, so DXT1 never mixes two islands. That left 74 % of the mirror texels within 2 px of the logo at a G of about 100, and 33 % of those 2 to 4 px away. With the logo given the class of the paint around it, the stale rim dropped to 0 %.
- In game the rim showed as a sawtooth line under the logo up close, and as a two tone tank with matte bands around the logo and a mirror centre. With the fix the tank read as one tone from above.

Starting points from that case:

- Give a decal or logo under clear coat the class of the paint around it, never no class.
- Before accepting a per material change, measure by distance to the border with each neighbour in the same island: the share of border texels that did not change while the interior did. A rim of 2 to 4 texels that kept the old value is this fault.
- Keeping whole DXT blocks next to another island is one export step's choice, not a general rule; DXT1 shares one palette per 4 x 4 block anyway. Check the border of both islands and tell kept values apart from compression artifacts.
