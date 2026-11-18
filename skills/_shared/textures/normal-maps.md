# Normal maps

Which way a DayZ normal map points, how to measure the convention of a source map before it is packed, what a packed `_nohq` holds, and how to build a normal map from albedo brightness when there is no bake.

How to read it: a `P:\` citation was checked on the vanilla files. "Measured" blocks carry their date. The suffix rules, and how ImageToPAA swizzles a `_nohq` (the `SWIZ` tag and the header scan), are in `suffixes-and-sizes.md`; this file does not repeat them. Baking a normal map in Blender is `normal-bake.md`.

## Contents

- [The convention](#the-convention)
- [Measuring a source map's convention](#measuring-a-source-maps-convention)
- [What a raking light render confirms](#what-a-raking-light-render-confirms)
- [Measured results](#measured-results)
- [Known limits of the measurement](#known-limits-of-the-measurement)
- [Reading a packed `_nohq`](#reading-a-packed-_nohq)
- [A normal map from albedo brightness](#a-normal-map-from-albedo-brightness)

## The convention

- DayZ `_nohq` is tangent space, DirectX style: X+ and Y-, green pointing down (**tool knowledge**). 3ds Max and Unreal use the same convention by default.
- Blender, Cycles and many bakers write OpenGL style, Y+, by default. Invert the green channel of such a source before the final export.
- Do not guess the convention of a source from where it came from. `normal_convention.py` proposes a candidate, and the candidate is then confirmed another way (below).
- About 3 % of vanilla `_nohq` files are consistent with OpenGL by their own features (at least 25 of 848 measured, see below). Do not take a vanilla file as a sign reference without checking it.

## Measuring a source map's convention

The script ships with `/dayz-pack-texture`. It needs numpy and Pillow (`python -m pip install -r "<skill-dir>\scripts\requirements.txt"`, where `<skill-dir>` is that skill's folder):

```cmd
python "<skill-dir>\scripts\normal_convention.py" --normal <normal.png> --albedo <albedo.png> [--json]
```

It needs the normal map and the albedo of the same UV layout, at the same size, as PNG. Decode a `.paa` with DayZ Tools ImageToPAA first. It takes two independent readings and proposes a convention only when they agree.

- **Albedo reading.** A high-pass of the albedo marks the hollows (a pixel darker than its blurred surroundings). Across a hollow, d(nx)/dx and d(ny)/dy have the same sign in DirectX and opposite signs in OpenGL. The red channel calibrates the sign, so an albedo that is darker on the ridges than in the hollows gives the same answer. No answer when a correlation is under 0.02 or undefined (a flat or clean albedo).
- **Curl reading.** With p = -nx/nz and q = ny/nz, the slopes of a height field satisfy d(p)/d(row) = d(q)/d(col) under OpenGL and d(p)/d(row) = -d(q)/d(col) under DirectX. The convention whose median residual is under 0.8 of the other's wins, provided the two medians differ by more than one 8-bit step of the normal (2/255); otherwise no answer. That floor is a heuristic, not a bound on rounding noise. Where the normals are nearly flat (nz close to 1), rounding to 8 bits moves p and q by up to about half a step and the residual by up to about one step; where they tilt, dividing by a smaller nz amplifies the error (one unit normal with nz = 0.4 already moves p by about 4 half steps). The floor was added after a vanilla map whose residuals sat half a step apart read OpenGL.
- **Block stability.** When the two readings agree, the map is cut into a 6 x 6 grid of blocks and each block gets each reading from its own pixels, with the derivatives, masks and thresholds of the whole map. Among the blocks that name a convention, at most 1 in 10 may name the other one for the curl reading and 1 in 3 for the albedo reading, and at least one must name the candidate; otherwise no answer. A convention that is really inverted inverts a reading wherever there is relief. The albedo reading gets more room because it can flip legitimately where the surface curves opposite ways along x and y. The check was added after a flat brick decal (`decal_bricks_01_nohq`) and a cloth bag (`bagpack_nohq`), both DirectX by their own features, read OpenGL with readings that agreed on the whole map; block by block, the decal's curl reading and the bag's albedo reading split.

Exit code 0 means a candidate, `DirectX` or `OpenGL`. Exit code 2 is `INCONCLUSIVE` or bad arguments (for example no `--albedo`). Exit code 1 is bad input, including numpy or Pillow not being installed. With `--json` the block counts are `curl_blocks_agree`, `curl_blocks_opposed`, `albedo_blocks_agree`, `albedo_blocks_opposed` and `blocks_stable` (null when the readings do not agree).

**A candidate is not proof.** A review built maps of known DirectX convention that both readings call OpenGL: a valid tangent space bake on a sphere patch (the curved frame turns the slopes the readings assume into something else) and undersampled tileable detail. The block check cannot see an error that is the same in every block: the tileable detail still reads OpenGL in all 36 blocks. Confirm a candidate before inverting a channel, with the baker's export setting or with a render under a raking light in which a known groove reads as a groove.

## What a raking light render confirms

Inverting the green channel changes the shading only through the light's V component (n.L moves by 2 x ny x Ly). So the render confirms a convention only when all three hold:

- The light crosses V: it comes from the top or the bottom of the texture, or diagonally, not only from a side. A light parallel to U renders the map and its inverted green copy identically: maximum difference 0.0 on a tileable fixture against 0.51 with the light along V (0.0 against 0.92 on vanilla `P:\DZ\animals\bos_taurus\data\bull_brown_nohq.paa`).
- The known groove has relief along V: it runs along U, so its walls face the top and the bottom of the image. A groove that runs along V renders the same with either green under any light.
- The same render with the green inverted reads that groove as a ridge.

When the two renders look the same, the check is inconclusive, not a confirmation. On a mesh, U and V are the texture's axes as the UV island lies on the surface, so a rotated island changes which light in the scene crosses V.

## Measured results

- A downloaded heater model that did not state its convention: candidate DirectX both ways. Albedo reading red -0.130 and green -0.085 over 491,775 of 1,048,576 pixels (2026-09-21); curl residuals 0.013 under DirectX against 0.024 under OpenGL (2026-10-03). With the block check it stays DirectX: curl 19 blocks for and 0 against, albedo 29 for and 2 against. Not confirmed another way and not checked in game.
- Vanilla `_nohq` and `_co` pairs decoded with ImageToPAA (2026-10-04):
  - On 284 pairs never used to design the block check (every tenth pair under `P:\DZ`, offset 2) the script gave 157 `DirectX`, 119 `INCONCLUSIVE` (41.9 %) and 8 `OpenGL`.
  - Each of the 8 `OpenGL` answers is consistent with OpenGL by its own features: ring targets, knobs, perforation holes, pores. None was a wrong candidate (0 of 165).
  - The `DirectX` answers are presumed right, not checked one by one.
  - On the two samples used to design the check, 1 of the 18 `OpenGL` answers is wrong: `kancel_008_nohq` (below).
  - Over the three samples (848 valid pairs, 502 candidates): 1 wrong candidate, and `INCONCLUSIVE` on about 41 % of the pairs.

## Known limits of the measurement

- **A map that mixes the two conventions inside every block.** The block check only sees a convention that changes from one region to another. A map whose features disagree a few pixels apart, the same way in every block, passes it and can get a wrong candidate. Vanilla `P:\DZ\structures\industrial\cementworks\data\kancel_008_nohq.paa` is a door whose glass panes read DirectX by their own edges (7 of 7 that count), while its hinge bolts and the outer step of its windows read OpenGL. The script calls it OpenGL with stable blocks (curl 28 for and 0 against, albedo 27 for and 4 against). Before inverting a channel, check features of known relief of more than one kind (a recessed panel and a raised bolt, for example).
- **Each reading alone.** The albedo reading is wrong, with strong correlations, on a surface that curves one way along x and the other along y (ribs whose amplitude grows down the image), and the two readings then disagree. The curl reading has no signal on a surface that is a sum of one function of x and one of y. Painted dark marks with no relief dilute the albedo reading. Each limit has a fixture in `test_normal_convention.py`, next to the script.
- **An inverted green rerun is no control.** It flips both readings, so it cannot disagree with the first run. The controls are the fixtures of known convention in the test file.
- **Which channel is off.** Both readings compare the sign of the green channel with the red one, so they cannot tell which of the two disagrees with the real relief. A map whose red is inverted against the relief (X-, Y-) reads `OpenGL` like a map whose green is inverted, and inverting its green then gives a consistent DirectX map with the relief upside down. Measured on two vanilla maps the script calls OpenGL, `generalstore_int_003_nohq` and `busstop_pavements_nohq`: their red reads the grout and curb joints, which are recessed, as ridges. Before inverting a channel, check red on a feature of known relief: across a recessed joint that runs along V, red goes bright then dark from left to right.

## Reading a packed `_nohq`

A shipped `_nohq` is DXT5 with swizzled channels (`suffixes-and-sizes.md`), so do not read the raw DXT block as (X, Y, Z) in RGB.

- Measured on vanilla vehicle maps and two regenerated mod maps (2026-08-30): the raw mip has red at 0 on every pixel and the X component in the alpha channel. That measurement did not tell X from 1 minus X; the `TexConvert.cfg` rule does.
- Converting a `_nohq.paa` back with ImageToPAA gives an RGB image (X, Y, Z). Measure amplitude, `mean(sqrt((R-128)^2 + (G-128)^2))`, and relief (the share of pixels with amplitude above 25) on that decoded PNG, never on the raw block.
- Find out how a file is packed from the file itself and from a vanilla `_nohq`, not from its suffix.

## A normal map from albedo brightness

Use this only when there is no baked normal. It cannot tell painted dirt from a real groove, so it is not a bake.

- Take height as the albedo luma, `0.2126 R + 0.7152 G + 0.0722 B`. Dark is low. Build the DayZ normal as `normalize((-s*dx, -s*dy, 1))` after a Sobel filter divided by 8, so Y is already DirectX style.
- Confirm the sign on a known dark seam with a sweep along one line. Entering a groove that the sweep crosses left to right, red is above 128; leaving it, red is below 128. For a sweep down the rows, read green the same way. Two opposing slopes into a height minimum are a valley. The opposite is an inverted mold: a dark seam that comes out as a ridge.
- Recalibrate the gain `s` for each atlas. A gain that landed inside the vanilla range on a 1024 body map overshot on a 512 high contrast detail map. Prefer the lower middle of what vanilla shows; an exaggerated normal looks worse than a weak one.
