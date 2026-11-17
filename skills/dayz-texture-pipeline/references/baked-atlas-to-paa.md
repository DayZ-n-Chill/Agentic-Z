# From a baked atlas to `.paa`: what to check on the way

The checks between a baked or borrowed texture and a working `.paa`: reading an ambient shadow map per channel, the baked data a borrowed vanilla material brings with it, making sure the atlas is the right one before blaming the UVs, the images ImageToPAA refuses, and the Linux notes.

How to read it: a `P:\` citation was checked on the vanilla files. "Rechecked" lines were run again on 2026-11-17 with DayZ Tools ImageToPAA. "Measured" blocks name their project and date. The conversion itself is `/dayz-pack-texture`; this file covers what goes wrong before and after it.

## Contents

- [Ambient shadow maps: read them per channel](#ambient-shadow-maps-read-them-per-channel)
- [A borrowed vanilla material brings baked data](#a-borrowed-vanilla-material-brings-baked-data)
- [Atlas identity before any mapping diagnosis](#atlas-identity-before-any-mapping-diagnosis)
- [Images ImageToPAA refuses](#images-imagetopaa-refuses)
- [The source file name decides the treatment](#the-source-file-name-decides-the-treatment)
- [Blender saves a relative path somewhere else](#blender-saves-a-relative-path-somewhere-else)
- [On Linux](#on-linux)

## Ambient shadow maps: read them per channel

Audit an `_as` file one channel at a time, never as greyscale.

- ImageToPAA's rule for `*_as.*` is `class ambient_shadow` in `<DayZ Tools>\Bin\ImageToPAA\TexConvert.cfg`: DXT1 with `channelSwizzleR = "1"`, `channelSwizzleG = "G"`, `channelSwizzleB = "1"` and `channelSwizzleA = "1"`. The shadow stays in green; red, blue and alpha are forced to 255. All 1,114 vanilla `_as.paa` files under `P:\DZ` carry the matching `SWIZ` tag, `08 08 02 08` (header scan of 2026-11-17).
- Measured on the vanilla `P:\DZ\gear\consumables\data\pile_of_planks_as.paa` (2026-08-31): green has a minimum of 0 and a mean of 53.1, with 74 % of the pixels under 48, while red, blue and alpha are a constant 255. A luminance conversion reports a bright image of about 185 and hides the very shadows the shader reads. Decoding five vanilla vehicle `_as` files (2026-09-14) showed the same layout.
- A check for an `_as` you produced (a starting point): decode the `.paa` and require the largest green error against the source to be at most 8 of 255, with red, blue and alpha at 255. Never require a per channel RGB match against a grey PNG. In one project (LFQuad3) that rule pushed a worker to dodge the swizzle through an in-between `_dxt1` suffix and ship grey `_as` maps with R = G = B.
- Keep the source name plain, `<name>_as.png`, with no in-between suffix.

## A borrowed vanilla material brings baked data

Borrowing a vanilla `.rvmat` also borrows textures baked for the donor mesh.

- Its Stage4 `_as` can paint the donor's dark patches onto your model and look like broken lighting or broken normals. Its Stage5 `_smdi` carries the same risk.
- Check which UV set the stage reads. The planks material names `pile_of_planks_as.paa` with `uvSource="tex1"` (`P:\DZ\gear\consumables\data\pile_of_planks.rvmat:47-48`): a second UV set that many mod models do not have. Measuring the map over your model's first UV set does not show what the shader samples. What the engine does when the second set is missing is not verified.
- To remove the donor's shadow, use the neutral stage vanilla itself writes, `texture="#(argb,8,8,3)color(1,1,1,1,AS)";`. It appears 4,388 times in the `.rvmat` files under `P:\DZ`, for example at `P:\DZ\vehicles\parts\data\aircraft_battery.rvmat:47`.
- For real depth, bake an `_as` for your own mesh and read it with `uvSource="tex"`.
- A preview renderer that leaves Stage4 out cannot show this fault. Before trusting a visual test bench, prove that a material known to be bad turns it red. In the project that found this (2026-08-31), what settled it was a test in game with one variable changed at a time: the donor `_as`, the neutral `_as`, and self shadowing off.

Before borrowing any vanilla `.rvmat`: measure its `_as` per channel, and check Stage4, Stage5 and every `uvSource`.

## Atlas identity before any mapping diagnosis

Before blaming mirrored UVs, face winding or the V direction:

1. Decode the atlas to PNG and look at it. Pillow opens DXT1 and DXT5 DDS files directly.
2. Draw the UV polygons of the affected faces over that image, with `image_y = (1 - v) * H`.
3. Only then look into mapping conventions or geometry.

This two minute check catches the costly case where the chosen atlas belongs to another asset. It also stops a material resolver for a source game from inventing color data:

- In one source game's files, materials named `*_[PRIMARY]` or `*_[SECONDARY]` have no color atlas on purpose, because their color comes from that game's paint palette. Use a flat paint texture or author a `_co`. Never bind "the largest atlas available".
- Aircraft atlases can hold a mirrored copy of one side so that markings read correctly on both sides. Mirrored text on both sides does not by itself justify flipping U for the whole model.

Before changing UV orientation or winding, do this check first.

## Images ImageToPAA refuses

`/dayz-pack-texture` checks the suffix, the extension and the size before it calls ImageToPAA. These inputs get past a header check and still fail in the tool, with `Error (Loading of img failed)` and nothing more, unless noted:

| Input | Result | Fix |
|---|---|---|
| A PNG written by Blender | Fails. The file carries EXIF, gamma and chromaticity chunks. Measured (LFQuad, 2026-09-02): a 23.95 MB file from Blender failed; the same pixels saved again came to 6.96 MB and converted to a 7.39 MB `.paa`. | Save it again with Pillow: `Image.open(src).convert("RGB").save(dst)` |
| A TGA with RLE compression (image type 10) | Fails. Rechecked: a 64 x 64 RLE TGA gives exit code 1 and no `.paa`; the same pixels as an uncompressed TGA (type 2) convert. Photopea is reported to offer no uncompressed TGA. | Save it uncompressed (Pillow's `save()` with no `compression`; `magick in.tga -compress none out.tga` was not run here) |
| A PNG with 16 bits per channel | Fails. Rechecked with a 16-bit greyscale PNG: exit code 1 and no `.paa`. 16-bit RGB was not tested. | Export 8 bits per channel (with ImageMagick, the Q8 build or `-depth 8`; not run here) |
| A size that is not a power of two | Fails with `Error (Img is not of power of 2 size)`. Rechecked with a 96 x 64 PNG: exit code 1 and no `.paa`. | Resize or crop; see the size rule in `_shared/textures/suffixes-and-sizes.md` |

- The other direction works from the command line: `ImageToPAA in.paa out.png` and `ImageToPAA in.paa out.tga` both exit 0, and the TGA comes out uncompressed (measured 2026-10-07; the PNG direction rechecked).
- An `_smdi` PNG written by Pillow from the start never failed.
- Third party Explorer menu entries (Strykar's `.reg` files, DayZ Modders Discord, 2026-10-07) were read, not installed. The two `.paa` entries run `cmd /c "for %%i in ("%1") do ImageToPAA ..."`. A doubled `%%i` is batch file syntax; given to `cmd /c` it stops before ImageToPAA runs ("%%i was unexpected at this time"), while the same loop with a single `%i` runs. Whether Explorer turns `%%` into `%` first is not verified, so do not count on those two entries until one is tried. Their TGA entry (`magick "%1" -compress none "%1"`) rewrites the file in place with no backup.

## The source file name decides the treatment

ImageToPAA picks the treatment from the end of the file name. A normal map source must be named `*_nohq.png`. A file named `*_nohq_DX.png` is converted like a plain texture, with no normal map handling (measured, LFQuad, 2026-09-02). Rename the source before converting; `/dayz-pack-texture` refuses a name with no known suffix and never renames for you.

## Blender saves a relative path somewhere else

`img.filepath_raw = "folder\file.png"` resolves against the open `.blend` file, not against the working folder, and `save()` raises nothing. In one project a whole bake was reported as written and was nowhere to be found. Use an absolute path and check `os.path.isfile()` before reporting a file as written.

## On Linux

Everything above is the Windows workflow. On Linux, the Proton setup, the measured tool matrix and the pitfalls are in the shared Linux notes (`_shared/linux-proton.md`). What changes for this skill, as measured there:

- PNG or TGA to `.paa`: `dayzmake img2paa` natively, or Bohemia's converter under Proton with `dayz-proton.sh tool ImageToPAA <in.png> <out.paa>` (the script is `skills/_shared/scripts/dayz-proton.sh`). The suffix rules apply as on Windows; a `_ca` PNG became DXT5. `.paa` to PNG: `dayzmake paa2img`.
- TexView: `dayz-proton.sh gui TexView <paa>` opened a DXT5 `.paa` and showed its format, size and average color.
- Workbench (the `.edds` and `.emat` import of `matpbr-emat-pipeline.md`) starts under Proton; the import steps were not verified there.
- `P:\` paths in a `.rvmat` are paths under the folder that `dayz-proton.sh init` maps.
