# Texture map conventions

How each DayZ texture map is oriented, packed and levelled: the normal map convention and how to measure it, how `_nohq` and `_smdi` are stored, how to get from a metallic and roughness set to `_smdi`, and how to calibrate levels against a vanilla asset.

How to read it: a `P:\` citation was checked on the vanilla files. "Measured" blocks carry their date and were not rechecked here unless the line says "rechecked". "Starting point" marks a value to adapt, not a vanilla measurement. The suffix table and what ImageToPAA does with each suffix are in `_shared/textures/suffixes-and-sizes.md`, not here.

## Contents

- [Normal maps](#normal-maps)
- [Measuring a source map's convention](#measuring-a-source-maps-convention)
- [How `_nohq` is stored](#how-_nohq-is-stored)
- [A normal map from albedo brightness](#a-normal-map-from-albedo-brightness)
- [SMDI packing](#smdi-packing)
- [From a metallic and roughness set to the green channel](#from-a-metallic-and-roughness-set-to-the-green-channel)
- [Packing the `_smdi` from a specular map and a roughness map](#packing-the-_smdi-from-a-specular-map-and-a-roughness-map)
- [Calibrating against a vanilla asset of the same family](#calibrating-against-a-vanilla-asset-of-the-same-family)
- [The DXT block staircase after a per material change](#the-dxt-block-staircase-after-a-per-material-change)
- [Export and path rules](#export-and-path-rules)

## Normal maps

- DayZ `_nohq` is tangent space, DirectX style: X+ and Y-, green pointing down. 3ds Max and Unreal use the same convention by default.
- Blender, Cycles and many bakers write OpenGL style, Y+, by default. Invert the green channel of such a source before the final export.
- Do not guess the convention of a source from where it came from. `normal_convention.py` proposes a candidate, and the candidate is then confirmed another way (next section).
- About 3 % of vanilla `_nohq` files are consistent with OpenGL by their own features (at least 25 of 848 measured, see below). Do not take a vanilla file as a sign reference without checking it.

## Measuring a source map's convention

```cmd
python "<skill-dir>\scripts\normal_convention.py" --normal <normal.png> --albedo <albedo.png> [--json]
```

It needs the normal map and the albedo of the same UV layout, at the same size, as PNG. Decode a `.paa` with DayZ Tools ImageToPAA first. It takes two independent readings and proposes a convention only when they agree.

- **Albedo reading.** A high-pass of the albedo marks the hollows (a pixel darker than its blurred surroundings). Across a hollow, d(nx)/dx and d(ny)/dy have the same sign in DirectX and opposite signs in OpenGL. The red channel calibrates the sign, so an albedo that is darker on the ridges than in the hollows gives the same answer. No answer when a correlation is under 0.02 or undefined (a flat or clean albedo).
- **Curl reading.** With p = -nx/nz and q = ny/nz, the slopes of a height field satisfy d(p)/d(row) = d(q)/d(col) under OpenGL and d(p)/d(row) = -d(q)/d(col) under DirectX. The convention whose median residual is under 0.8 of the other's wins, provided the two medians differ by more than one 8-bit step of the normal (2/255); otherwise no answer. That floor is a heuristic, not a bound on rounding noise. Where the normals are nearly flat (nz close to 1), rounding to 8 bits moves p and q by up to about half a step and the residual by up to about one step; where they tilt, dividing by a smaller nz amplifies the error (one unit normal with nz = 0.4 already moves p by about 4 half steps). The floor was added after a vanilla map whose residuals sat half a step apart read OpenGL.
- **Block stability.** When the two readings agree, the map is cut into a 6 x 6 grid of blocks and each block gets each reading from its own pixels, with the derivatives, masks and thresholds of the whole map. Among the blocks that name a convention, at most 1 in 10 may name the other one for the curl reading and 1 in 3 for the albedo reading, and at least one must name the candidate; otherwise no answer. A convention that is really inverted inverts a reading wherever there is relief. The albedo reading gets more room because it can flip legitimately where the surface curves opposite ways along x and y. The check was added after a flat brick decal (`decal_bricks_01_nohq`) and a cloth bag (`bagpack_nohq`), both DirectX by their own features, read OpenGL with readings that agreed on the whole map; block by block, the decal's curl reading and the bag's albedo reading split.

Exit code 0 means a candidate, `DirectX` or `OpenGL`. Exit code 2 is `INCONCLUSIVE` or bad arguments (for example no `--albedo`). Exit code 1 is bad input. With `--json` the block counts are `curl_blocks_agree`, `curl_blocks_opposed`, `albedo_blocks_agree`, `albedo_blocks_opposed` and `blocks_stable` (null when the readings do not agree).

**A candidate is not proof.** A review built maps of known DirectX convention that both readings call OpenGL: a valid tangent space bake on a sphere patch (the curved frame turns the slopes the readings assume into something else) and undersampled tileable detail. The block check cannot see an error that is the same in every block: the tileable detail still reads OpenGL in all 36 blocks. Confirm a candidate before inverting a channel, with the baker's export setting or with a render under a raking light in which a known groove reads as a groove.

### What a raking light render confirms, and what it does not

Inverting the green channel changes the shading only through the light's V component (n.L moves by 2 x ny x Ly). So the render confirms a convention only when all three hold:

- The light crosses V: it comes from the top or the bottom of the texture, or diagonally, not only from a side. A light parallel to U renders the map and its inverted green copy identically: maximum difference 0.0 on a tileable fixture against 0.51 with the light along V (0.0 against 0.92 on vanilla `bull_brown_nohq`).
- The known groove has relief along V: it runs along U, so its walls face the top and the bottom of the image. A groove that runs along V renders the same with either green under any light.
- The same render with the green inverted reads that groove as a ridge.

When the two renders look the same, the check is inconclusive, not a confirmation. On a mesh, U and V are the texture's axes as the UV island lies on the surface, so a rotated island changes which light in the scene crosses V.

### Measured results

- A downloaded heater model that did not state its convention: candidate DirectX both ways. Albedo reading red -0.130 and green -0.085 over 491,775 of 1,048,576 pixels (2026-09-21); curl residuals 0.013 under DirectX against 0.024 under OpenGL (2026-10-03). With the block check it stays DirectX: curl 19 blocks for and 0 against, albedo 29 for and 2 against. Not confirmed another way and not checked in game.
- Vanilla `_nohq` and `_co` pairs decoded with ImageToPAA (2026-10-04):
  - On 284 pairs never used to design the block check (every tenth pair under `P:\DZ`, offset 2) the script gave 157 `DirectX`, 119 `INCONCLUSIVE` (41.9 %) and 8 `OpenGL`.
  - Each of the 8 `OpenGL` answers is consistent with OpenGL by its own features: ring targets, knobs, perforation holes, pores. None was a wrong candidate (0 of 165).
  - The `DirectX` answers are presumed right, not checked one by one.
  - On the two samples used to design the check, 1 of the 18 `OpenGL` answers is wrong: `kancel_008_nohq` (below).
  - Over the three samples (848 valid pairs, 502 candidates): 1 wrong candidate, and `INCONCLUSIVE` on about 41 % of the pairs.

### Known limits

- **A map that mixes the two conventions inside every block.** The block check only sees a convention that changes from one region to another. A map whose features disagree a few pixels apart, the same way in every block, passes it and can get a wrong candidate. Vanilla `kancel_008_nohq` is a door whose glass panes read DirectX by their own edges (7 of 7 that count), while its hinge bolts and the outer step of its windows read OpenGL. The script calls it OpenGL with stable blocks (curl 28 for and 0 against, albedo 27 for and 4 against). Measured rate: 1 wrong candidate in 502 over three vanilla samples, 0 in the 165 of the sample not used to design the check. Before inverting a channel, check features of known relief of more than one kind (a recessed panel and a raised bolt, for example).
- **Each reading alone.** The albedo reading is wrong, with strong correlations, on a surface that curves one way along x and the other along y (ribs whose amplitude grows down the image), and the two readings then disagree. The curl reading has no signal on a surface that is a sum of one function of x and one of y. Painted dark marks with no relief dilute the albedo reading. Each limit has a fixture in `test_texture_pipeline_normal_convention.py`, next to the script.
- **An inverted green rerun is no control.** It flips both readings, so it cannot disagree with the first run. The controls are the fixtures of known convention in the test file.
- **Which channel is off.** Both readings compare the sign of the green channel with the red one, so they cannot tell which of the two disagrees with the real relief. A map whose red is inverted against the relief (X-, Y-) reads `OpenGL` like a map whose green is inverted, and inverting its green then gives a consistent DirectX map with the relief upside down. Measured on two vanilla maps the script calls OpenGL, `generalstore_int_003_nohq` and `busstop_pavements_nohq`: their red reads the grout and curb joints, which are recessed, as ridges. Before inverting a channel, check red on a feature of known relief: across a recessed joint that runs along V, red goes bright then dark from left to right.

## How `_nohq` is stored

A shipped `_nohq` is DXT5 with swizzled channels, not an RGB normal sitting in a DXT5 container. Do not read the raw DXT block as (X, Y, Z) in RGB.

- ImageToPAA's rule for `*_nohq.*` is `class normalmap_hq` in `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg`: `format = "DXT5"`, `channelSwizzleA = "1-R"`, `channelSwizzleR = "1-A"`, green and blue kept. So the stored alpha is 1 minus X, and the stored red is 1 minus the source alpha, which is 0 for an opaque source.
- Header scan of the vanilla files (2026-11-17): all 3,865 `_nohq.paa` files under `P:\DZ` are type `0xFF05` (DXT5) and carry the tag `SWIZ` with the bytes `05 04 02 03`, for example `P:\DZ\vehicles\wheeled\hatchback_02\data\hatchback_02_rust_body_nohq.paa`.
- Measured on vanilla vehicle maps and two regenerated mod maps (2026-08-30): the raw mip has red at 0 on every pixel and the X component in the alpha channel. That measurement did not tell X from 1 minus X; the `TexConvert.cfg` rule above does.
- Converting a `_nohq.paa` back with ImageToPAA gives an RGB image (X, Y, Z). Measure amplitude, `mean(sqrt((R-128)^2 + (G-128)^2))`, and relief (the share of pixels with amplitude above 25) on that decoded PNG, never on the raw block.
- Find out how a file is packed from the file itself and from a vanilla `_nohq`, not from its suffix.

## A normal map from albedo brightness

Use this only when there is no baked normal. It cannot tell painted dirt from a real groove, so it is not a bake.

- Take height as the albedo luma, `0.2126 R + 0.7152 G + 0.0722 B`. Dark is low. Build the DayZ normal as `normalize((-s*dx, -s*dy, 1))` after a Sobel filter divided by 8, so Y is already DirectX style.
- Confirm the sign on a known dark seam with a sweep along one line. Entering a groove that the sweep crosses left to right, red is above 128; leaving it, red is below 128. For a sweep down the rows, read green the same way. Two opposing slopes into a height minimum are a valley. The opposite is an inverted mold: a dark seam that comes out as a ridge.
- Recalibrate the gain `s` for each atlas. A gain that landed inside the vanilla range on a 1024 body map overshot on a 512 high contrast detail map. Prefer the lower middle of what vanilla shows; an exaggerated normal looks worse than a weak one.

## SMDI packing

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

On the vanilla `motorbike_02` body the red paint measures a G median of 5, far below the "worn painted metal" row. Calibrate against a vanilla asset of the same family before trusting a row (section below).

What is checked:

- **Painting R white is redundant.** `class specular_diffuseinverse_map` in `TexConvert.cfg` sets `channelSwizzleR = "1"` and `channelSwizzleA = "1"` and keeps G and B. Rechecked 2026-11-17 with DayZ Tools ImageToPAA: a 64 x 64 `x_smdi.png` filled with R = 0, G = 56, B = 200 converts to a `.paa` that decodes back as (255, 56, 200, 255). The earlier test (2026-10-07) found the same for `x_SMDI.png`, so the match ignores case. All 2,696 vanilla `_smdi.paa` files under `P:\DZ` carry the `SWIZ` tag `08 08 02 03`.
- **Measured vanilla files** (2026-09-21): the `_smdi` of the searchlight, battery adapter, a housing and the battery charger decode with R at 255 everywhere; G and B carry the data.
- **The procedural SMDI has no single default.** Counted on `P:\DZ` (2026-11-17): 1,007 procedural `color(r,g,b,a,SMDI)` textures in `.rvmat` files. R is 0 in 566, 1 in 384, between the two in 55, and out of range in 2: `color(100,100,100,1,SMDI)` at `P:\DZ\structures\specific\statues\data\ww2monument_stele_flags.rvmat:59` and in `ww2monument_wall_floor.rvmat`. Of the 928 in Super materials, R is 0 in 545 and 1 in 337. The most common value is `color(0,0,1,1,SMDI)` (297 times, 280 of them in Super materials), for example `P:\DZ\characters\bodies\data\jeans_f_grd.rvmat:59`: green 0, no specular at all. Since Super materials ship R at 0 that often, a white R looks conventional, not required. Which G is neutral for a given material is not something the count can say.

## From a metallic and roughness set to the green channel

A rule that is not verified in game: do not copy a metallic map straight into specular. Metallic is a blend factor between insulator and metal, not a reflectance. Copied as specular, its black (wood, cloth, plastic) becomes zero specular, while real insulators reflect about 4 % at normal incidence (2 to 16 %) and metals 70 to 100 %. Replace the black with `#383838` and keep the bright metal.

- Arithmetic, checked offline: 4 % linear encoded to sRGB is 0.2209, which is 56, `0x38`. Read back as sRGB it is 3.95 %. 56 sits inside the G ranges of the table above for rubber, plastic and wood.
- **Not verified: whether the Super shader decodes `_smdi` green as sRGB.** If it reads green as raw linear, `0x38` is 0.22 of full scale, about 5.6 times the intended 4 %. That green behaves like a physically based F0 at all is not established either. A hint against the sRGB reading: `TexConvert.cfg` comments the color classes (`_co`, `_ca`, macro) as "sRGB color space" and gives `*_smdi.*` no such comment. A second hint: the vanilla motorbike paint below sits at 5, not 56. Treat `0x38` as a sensible starting point, not a calibrated value.
- One ImageMagick recipe composites solid `#383838` over the metallic map using the inverted metallic map as the mask. Worked out from ImageMagick's masked composite rule for opaque inputs, not run: `out = m*m + 0.2196*(1 - m)`, so 0 gives 56, 64 gives 58, 128 gives 92 and 255 gives 255. That is correct for a black and white metallic map and darkens grey or antialiased transitions (m squared where m was meant). Starting point: the textbook form is the linear blend `out = 0.2196 + (1 - 0.2196)*m` (128 gives 156). Pick one on purpose.
- Metal comes out at the metallic value (white is 255), not at the albedo's color. DayZ's green is one number per texel, so that loss comes with the packing.
- The result is a greyscale specular map, usually saved as `<name>_Specular.<ext>` beside the source. That file is the green source of an `_smdi`, not an `_smdi`: pack R = 255, G = this map, B = gloss (inverted roughness).

## Packing the `_smdi` from a specular map and a roughness map

One ImageMagick `-combine` call packs the map: R filled white, G the specular as grey, B the gloss as grey (negated when the source is roughness). That matches the packing table. A batch file can do it by name: given an image named `<base>_Specular`, it looks for `<base>_gloss`, `_glossy`, `_glossiness`, `_rough`, `_roughness` or `_r` with the same extension and writes `<base>_SMDI<ext>`. One such batch file was read, not run. What to check in a packer of that kind:

- **Roughness beats gloss** when the roughness loop runs after the gloss loop and overwrites the match. With both `<base>_gloss` and `<base>_rough` present, B is the inverted roughness.
- **Only exact siblings match**: the same `<base>` and the same extension. A `.png` specular next to a `.tga` roughness gives "Could not find a matching gloss or roughness map". The `_r` suffix means `<base>_r<ext>` only, but a red mask named that way would still be read as roughness.
- The name match ignores case, wherever `_Specular` sits in the name. A path that contains `!` breaks the lookup.
- The output keeps the input's extension: a `.jpg` specular gives a lossy `_SMDI.jpg`. Whether ImageMagick writes the `.tga` compressed is not verified; if it does, ImageToPAA rejects it (`baked-atlas-to-paa.md`).
- The inputs must share a size. How `-combine` handles a mismatch is not verified, so resize first.
- **Write 8 bits per channel.** A 16-bit greyscale PNG fails ImageToPAA (`baked-atlas-to-paa.md`). 16-bit RGB was not tested, so 8 bits is the safe target. The Q8 ImageMagick build is the usual advice; what matters is the depth of the file written, so on a Q16 build force `-depth 8` (not run here). A packer that passes no `-depth` leaves the depth to the build.

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

Procedure (a starting point): decode the shipped `.paa` files of the closest vanilla asset of the same family and of the mod, not the PNG sources. Check that the material constants match. Set G and B per surface class with the vanilla figure beside each, stating the texels and the statistic. Then look in game next to the vanilla asset under the same light.

## The DXT block staircase after a per material change

Seen on a mod motorbike (2026-10-28), with no stored evidence:

- A per material `_smdi` recalibration raised a fuel tank's mirror paint from about G/B 100/190 to 205/237 and gave no class to the logo panel that shares its UV island. The export step used there keeps the old value in every 4 x 4 DXT block that holds texels of another material, so that DXT1 does not mix two islands. That step left 74 % of the mirror texels within 2 px of the logo at G of about 100, and 33 % of those 2 to 4 px away. With the logo given the class of the paint around it, that stale rim measured 0 %.
- In game before the fix: a sawtooth line under the logo seen up close, and a two tone tank with matte bands around the logo and a mirror centre. After it the tank read as one tone from above; the close-up was not looked at again.

What follows from that one case (starting points):

- Give a decal or logo under clear coat the class of the paint around it, not "no class".
- Before accepting a per material change, measure by distance to the border with each neighbour in the same island: the share of border texels that did not change while the interior did. A rim of 2 to 4 texels that kept the old value is the staircase.
- Keeping whole DXT blocks next to a foreign island was that pipeline's tradeoff, not a general rule. DXT1 shares one palette per 4 x 4 block anyway. Check the border of both islands and tell kept values apart from compression artifacts.

## Export and path rules

- Config and `.rvmat` references point at `.paa`, never at `.png`, `.tga`, `.jpg` or `.dds`.
- Use in-game paths such as `dz\...` or `MyMod\...`, never a local disk path.
- Keep source files (`.png`, `.xcf`, `.psd`, `.blend`, `.sbsar`) out of the packed paths, or in a source folder the build leaves out.
- When a tool converts by suffix, still look at the resulting `.paa` and at the item in game.
