# Normal maps

Which way a DayZ normal map points, how to measure the convention of a source map before packing it, what a packed `_nohq` holds, and how to build a normal map from albedo brightness when there is no bake.

The suffix rules, and how ImageToPAA swizzles a `_nohq` (the `SWIZ` tag and the header scan), are in `suffixes-and-sizes.md`. Baking a normal map in Blender is `normal-bake.md`.

## Contents

- [The convention](#the-convention)
- [Measuring a source map](#measuring-a-source-map)
- [Confirming with a raking light](#confirming-with-a-raking-light)
- [How the script does on vanilla maps](#how-the-script-does-on-vanilla-maps)
- [Where the measurement goes wrong](#where-the-measurement-goes-wrong)
- [Reading a packed `_nohq`](#reading-a-packed-_nohq)
- [A normal map from albedo brightness](#a-normal-map-from-albedo-brightness)

## The convention

- A DayZ `_nohq` is tangent space, DirectX style: X+ and Y-, green pointing down (**tool knowledge**). 3ds Max and Unreal use the same convention by default.
- Blender, Cycles and many bakers write OpenGL style, Y+, by default. Invert the green channel of such a map before the final export.
- Never guess a map's convention from where it came from. `normal_convention.py` proposes one, and you confirm it another way (below).
- About 3 % of vanilla `_nohq` files look OpenGL by their own features (at least 25 of 848 measured). Check a vanilla map before using it as a sign reference.

## Measuring a source map

The script ships with `/dayz-pack-texture` and needs numpy and Pillow (`python -m pip install -r "<skill-dir>\scripts\requirements.txt"`, where `<skill-dir>` is that skill's folder):

```cmd
python "<skill-dir>\scripts\normal_convention.py" --normal <normal.png> --albedo <albedo.png> [--json]
```

Give it the normal map and the albedo of the same UV layout, same size, as PNG; decode a `.paa` with ImageToPAA first. It takes two independent readings and proposes a convention only when they agree.

- **Albedo reading.** A high pass of the albedo marks the hollows, pixels darker than their blurred surroundings. Across a hollow, d(nx)/dx and d(ny)/dy share a sign under DirectX and have opposite signs under OpenGL. The red channel calibrates the sign, so an albedo darker on the ridges than in the hollows gives the same answer. It gives no answer when a correlation is under 0.02 or undefined (a flat or clean albedo).
- **Curl reading.** With p = -nx/nz and q = ny/nz, the slopes of a height field satisfy d(p)/d(row) = d(q)/d(col) under OpenGL and d(p)/d(row) = -d(q)/d(col) under DirectX. The convention whose median residual is under 0.8 of the other's wins, as long as the two medians differ by more than one 8-bit step of the normal (2/255); otherwise no answer. That floor is a rule of thumb, not a bound on rounding noise: where normals are nearly flat (nz close to 1), 8-bit rounding moves p and q by up to about half a step and the residual by up to about one step, and where they tilt a smaller nz magnifies the error (at nz = 0.4, p already moves by about 4 half steps). Without the floor, a vanilla map whose residuals sit half a step apart reads OpenGL.
- **Block stability.** When the two readings agree, the map is cut into a 6 x 6 grid and each block gets both readings from its own pixels, with the whole map's derivatives, masks and thresholds. Among the blocks that name a convention, at most 1 in 10 may name the other for the curl reading and 1 in 3 for the albedo reading, and at least one must name the candidate; otherwise no answer. A map that is really inverted inverts a reading wherever there is relief. The albedo reading gets more room because it can flip legitimately where the surface curves opposite ways along x and y. Without this check, a flat brick decal (`decal_bricks_01_nohq`) and a cloth bag (`bagpack_nohq`), both DirectX by their own features, read OpenGL with readings that agree over the whole map; block by block, the decal's curl reading and the bag's albedo reading split.

Exit code 0 means a candidate, `DirectX` or `OpenGL`. Exit code 2 means `INCONCLUSIVE` or bad arguments, such as no `--albedo`. Exit code 1 means bad input, including numpy or Pillow missing. With `--json` the block counts are `curl_blocks_agree`, `curl_blocks_opposed`, `albedo_blocks_agree`, `albedo_blocks_opposed` and `blocks_stable` (null when the readings disagree).

A candidate is not proof. Maps of known DirectX convention exist that both readings call OpenGL: a valid tangent space bake on a sphere patch, where the curved frame turns the slopes the readings assume into something else, and undersampled tileable detail. The block check cannot see an error that is the same in every block; the tileable detail reads OpenGL in all 36 blocks. Confirm a candidate before inverting a channel, from the baker's export setting or with a raking light render in which a known groove reads as a groove.

## Confirming with a raking light

Inverting green changes the shading only through the light's V component (n.L moves by 2 x ny x Ly). A render confirms the convention only when all three hold:

- The light crosses V: it comes from the top or bottom of the texture, or diagonally, not only from one side. A light along U renders a map and its green inverted copy identically: largest difference 0.0 on a tileable test map against 0.51 with the light along V, and 0.0 against 0.92 on vanilla `P:\DZ\animals\bos_taurus\data\bull_brown_nohq.paa`.
- The known groove has relief along V: it runs along U, so its walls face the top and bottom of the image. A groove that runs along V renders the same with either green under any light.
- The same render with green inverted reads that groove as a ridge.

If the two renders look the same, the check is inconclusive, not a pass. On a mesh, U and V are the texture's axes as the UV island lies on the surface, so a rotated island changes which scene light crosses V.

## How the script does on vanilla maps

- A downloaded heater model with no stated convention: DirectX by both readings. Albedo reading red -0.130 and green -0.085 over 491,775 of 1,048,576 pixels; curl residuals 0.013 under DirectX against 0.024 under OpenGL; blocks curl 19 for and 0 against, albedo 29 for and 2 against. Not confirmed another way and not checked in game.
- Vanilla `_nohq` and `_co` pairs decoded with ImageToPAA:
  - On 284 pairs not used to design the block check (every tenth pair under `P:\DZ`, offset 2) the script gives 157 `DirectX`, 119 `INCONCLUSIVE` (41.9 %) and 8 `OpenGL`.
  - Each of the 8 `OpenGL` answers is OpenGL by its own features: ring targets, knobs, perforation holes, pores. None of the 165 candidates is wrong.
  - The `DirectX` answers are presumed right, not checked one by one.
  - On the two samples used to design the check, 1 of 18 `OpenGL` answers is wrong: `kancel_008_nohq` (below).
  - Over all three samples (848 valid pairs, 502 candidates): 1 wrong candidate, and `INCONCLUSIVE` on about 41 % of pairs.

## Where the measurement goes wrong

- **A map that mixes both conventions inside every block.** The block check only sees a convention that changes from region to region. A map whose features disagree a few pixels apart, the same way in every block, passes it and can get a wrong candidate. Vanilla `P:\DZ\structures\industrial\cementworks\data\kancel_008_nohq.paa` is a door whose glass panes read DirectX by their own edges (7 of 7 that count), while its hinge bolts and the outer step of its windows read OpenGL. The script calls it OpenGL with stable blocks (curl 28 for and 0 against, albedo 27 for and 4 against). Before inverting a channel, check features of known relief of more than one kind, such as a recessed panel and a raised bolt.
- **Each reading alone.** The albedo reading is wrong, with strong correlations, on a surface that curves one way along x and the other along y (ribs whose height grows down the image), and the two readings then disagree. The curl reading has no signal on a surface that is a sum of one function of x and one of y. Painted dark marks with no relief dilute the albedo reading. Each case has a test map in `test_normal_convention.py`, next to the script.
- **A green inverted rerun is no control.** It flips both readings, so it cannot disagree with the first run. The controls are the test maps of known convention in the test file.
- **Which channel is off.** Both readings compare green's sign with red's, so they cannot tell which of the two disagrees with the real relief. A map whose red is inverted against the relief (X-, Y-) reads `OpenGL` just like one whose green is inverted, and inverting its green then gives a consistent DirectX map with the relief upside down. Two vanilla maps the script calls OpenGL, `generalstore_int_003_nohq` and `busstop_pavements_nohq`, read their recessed grout and curb joints as ridges in red. Before inverting a channel, check red on a feature of known relief: across a recessed joint that runs along V, red goes bright then dark from left to right.

## Reading a packed `_nohq`

A shipped `_nohq` is DXT5 with swizzled channels (`suffixes-and-sizes.md`), so never read the raw DXT block as (X, Y, Z) in RGB.

- On vanilla vehicle maps and on mod maps regenerated the same way, the raw top mip has red at 0 on every pixel and the X component in alpha. That alone does not tell X from 1 minus X; the `TexConvert.cfg` rule does.
- Converting a `_nohq.paa` back with ImageToPAA gives an RGB image of (X, Y, Z). Measure amplitude, `mean(sqrt((R-128)^2 + (G-128)^2))`, and relief, the share of pixels with amplitude above 25, on that decoded PNG, never on the raw block.
- Find out how a file is packed from the file itself and from a vanilla `_nohq`, not from its suffix.

## A normal map from albedo brightness

Use this only when there is no baked normal. It cannot tell painted dirt from a real groove, so it is not a bake.

- Take height as the albedo luma, `0.2126 R + 0.7152 G + 0.0722 B`, dark being low. Build the DayZ normal as `normalize((-s*dx, -s*dy, 1))` after a Sobel filter divided by 8, so Y already points the DirectX way.
- Confirm the sign on a known dark seam with a sweep along one line. Entering a groove that the sweep crosses left to right, red is above 128; leaving it, red is below 128. For a sweep down the rows, read green the same way. Two slopes facing each other into a height minimum are a valley; the opposite is an inverted mold, a dark seam that comes out as a ridge.
- Tune the gain `s` for each atlas. A gain that lands inside the vanilla range on a 1024 body map overshoots on a 512 high contrast detail map. Prefer the lower middle of what vanilla shows; an exaggerated normal looks worse than a weak one.
