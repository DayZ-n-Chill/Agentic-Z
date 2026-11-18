# From a baked or borrowed texture to a working `.paa`

The checks between a baked or borrowed texture and a working `.paa`: checking an ambient shadow map you produced, the baked data a borrowed vanilla material brings with it, making sure the atlas is the right one before blaming the UVs, converting a `.paa` back, and what changes on Linux.

How to read it: a `P:\` citation was checked on the vanilla files. "Measured" blocks carry their date. The conversion itself is `/dayz-pack-texture`; the suffix rules, how ImageToPAA stores an `_as`, and the images ImageToPAA refuses are in `suffixes-and-sizes.md`.

## Contents

- [Checking an `_as` you produced](#checking-an-_as-you-produced)
- [A borrowed vanilla material brings baked data](#a-borrowed-vanilla-material-brings-baked-data)
- [Atlas identity before any mapping diagnosis](#atlas-identity-before-any-mapping-diagnosis)
- [Converting a `.paa` back, and Explorer entries](#converting-a-paa-back-and-explorer-entries)
- [On Linux](#on-linux)

## Checking an `_as` you produced

An `_as` keeps its shadow in green only (`suffixes-and-sizes.md`), so audit it one channel at a time, never as greyscale.

- Measured on the vanilla `P:\DZ\gear\consumables\data\pile_of_planks_as.paa` (2026-08-31): green has a minimum of 0 and a mean of 53.1, with 74 % of the pixels under 48, while red, blue and alpha are a constant 255. A luminance conversion reports a bright image of about 185 and hides the very shadows the shader reads. Decoding five vanilla vehicle `_as` files (2026-09-14) showed the same layout.
- A check for an `_as` you produced (a starting point): decode the `.paa` and require the largest green error against the source to be at most 8 of 255, with red, blue and alpha at 255. Never require a per channel RGB match against a grey PNG. Such a rule can only be met by dodging the swizzle through an in-between `_dxt1` suffix, which ships grey `_as` maps with R = G = B.
- Keep the source name plain, `<name>_as.png`, with no in-between suffix.

## A borrowed vanilla material brings baked data

Borrowing a vanilla `.rvmat` also borrows textures baked for the donor mesh.

- Its Stage4 `_as` can paint the donor's dark patches onto your model and look like broken lighting or broken normals. Its Stage5 `_smdi` carries the same risk.
- Check which UV set the stage reads. The planks material names `pile_of_planks_as.paa` with `uvSource="tex1"` (`P:\DZ\gear\consumables\data\pile_of_planks.rvmat:47-48`): a second UV set that many mod models do not have. Measuring the map over your model's first UV set does not show what the shader samples. What the engine does when the second set is missing is not verified.
- To remove the donor's shadow, use the neutral stage vanilla itself writes, `texture="#(argb,8,8,3)color(1,1,1,1,AS)";`. It appears 4,388 times in the `.rvmat` files under `P:\DZ`, for example at `P:\DZ\vehicles\parts\data\aircraft_battery.rvmat:47`.
- For real depth, bake an `_as` for your own mesh and read it with `uvSource="tex"`.
- A preview renderer that leaves Stage4 out cannot show this fault. Before trusting a visual test bench, prove that a material known to be bad turns it red. What settles it is a test in game with one variable changed at a time: the donor `_as`, the neutral `_as`, and self shadowing off (done that way on 2026-08-31).

Before borrowing any vanilla `.rvmat`: measure its `_as` per channel, and check Stage4, Stage5 and every `uvSource`.

## Atlas identity before any mapping diagnosis

Before blaming mirrored UVs, face winding or the V direction:

1. Decode the atlas to PNG and look at it. Pillow opens DXT1 and DXT5 DDS files directly.
2. Draw the UV polygons of the affected faces over that image, with `image_y = (1 - v) * H`.
3. Only then look into mapping conventions or geometry.

This two minute check catches the costly case where the chosen atlas belongs to another asset. It also stops a material resolver for a source game from inventing color data:

- In one source game's files, materials named `*_[PRIMARY]` or `*_[SECONDARY]` have no color atlas on purpose, because their color comes from that game's paint palette. Use a flat paint texture or author a `_co`. Never bind "the largest atlas available".
- Aircraft atlases can hold a mirrored copy of one side so that markings read correctly on both sides. Mirrored text on both sides does not by itself justify flipping U for the whole model.

## Converting a `.paa` back, and Explorer entries

- The other direction works from the command line: `ImageToPAA in.paa out.png` and `ImageToPAA in.paa out.tga` both exit 0, and the TGA comes out uncompressed (measured 2026-10-07; the PNG direction rechecked 2026-11-17).
- An `_smdi` PNG written by Pillow from the start never failed.
- Explorer right-click entries (`.reg` files) that wrap these conversions need a look before use; the following was read, not installed. A `.paa` entry of the form `cmd /c "for %%i in ("%1") do ImageToPAA ..."` uses a doubled `%%i`, which is batch file syntax; given to `cmd /c` it stops before ImageToPAA runs ("%%i was unexpected at this time"), while the same loop with a single `%i` runs. Whether Explorer turns `%%` into `%` first is not verified, so do not count on such an entry until it is tried. A TGA entry of the form `magick "%1" -compress none "%1"` rewrites the file in place with no backup.

## On Linux

The Proton setup and the measured tool matrix (ImageToPAA, `dayzmake img2paa` and `paa2img`, TexView) are in `_shared/linux-proton.md`. What it means for texture work:

- The suffix rules apply as on Windows; a `_ca` PNG became DXT5.
- Workbench (the `.edds` and `.emat` import of `matpbr-emat.md`) starts under Proton; the import steps were not verified there.
- `P:\` paths in a `.rvmat` are paths under the folder that `dayz-proton.sh init` maps.
