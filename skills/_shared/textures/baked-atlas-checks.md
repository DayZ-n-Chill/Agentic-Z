# Baked and borrowed textures

What to check between a baked or borrowed texture and a working `.paa`: an ambient shadow map you made, the baked maps a borrowed vanilla material drags in, whether the atlas is the right one at all, converting a `.paa` back, and what changes on Linux.

The conversion itself is `/dayz-pack-texture`. The suffix rules, how ImageToPAA stores an `_as`, and the images ImageToPAA refuses are in `suffixes-and-sizes.md`.

## Checking an `_as` you made

An `_as` keeps its shadow in the green channel only (`suffixes-and-sizes.md`). Check it one channel at a time, never as greyscale.

- The vanilla planks map `P:\DZ\gear\consumables\data\pile_of_planks_as.paa` decodes with green from 0 up, a green mean of 53.1 and 74 % of its pixels under 48, while red, blue and alpha sit at 255 everywhere. A luminance conversion of the same file reads as a bright image of about 185 and hides exactly the shadows the shader uses. Five vanilla vehicle `_as` files decode the same way.
- A starting check for your own `_as`: decode the `.paa` and require the largest green error against the source to be 8 of 255 or less, with red, blue and alpha at 255.
- Never require a channel by channel RGB match against a grey PNG. The only way to pass such a check is to route the file through an in-between `_dxt1` suffix, which ships a grey `_as` with R, G and B equal.
- Name the source plainly, `<name>_as.png`, with no in-between suffix.

## What a borrowed vanilla material brings along

Copying a vanilla `.rvmat` also copies the maps baked for the vanilla model it belongs to.

- Its Stage4 `_as` can paint that model's dark patches onto yours, which looks like broken lighting or broken normals. Its Stage5 `_smdi` carries the same risk.
- Check which UV set each stage reads. The planks material reads its `_as` with `uvSource="tex1"` (`P:\DZ\gear\consumables\data\pile_of_planks.rvmat:47` and `:48`), a second UV set many mod models do not have. Measuring the map over your first UV set does not show what the shader samples. What the engine does when the second set is missing is not checked.
- To drop the borrowed shadow, use the neutral stage vanilla itself writes, `texture="#(argb,8,8,3)color(1,1,1,1,AS)";`. It appears 4,779 times in the `.rvmat` files under `P:\DZ`, for example at `P:\DZ\vehicles\parts\data\aircraft_battery.rvmat:47`.
- For real depth, bake an `_as` for your own mesh and read it with `uvSource="tex"`.
- A preview renderer that skips Stage4 cannot show this fault. Before trusting a preview, make sure a material you know is bad shows up as bad in it. The test that settles it is in game, one change at a time: the borrowed `_as`, the neutral `_as`, then self shadowing off.

Before copying any vanilla `.rvmat`, measure its `_as` per channel and read Stage4, Stage5 and every `uvSource`.

## Is it the right atlas

Rule out the wrong atlas before blaming mirrored UVs, face winding or the V direction:

1. Decode the atlas to PNG and look at it. Pillow opens DXT1 and DXT5 DDS files directly.
2. Draw the UV polygons of the faces in question over that image, with `image_y = (1 - v) * H`.
3. Only then look at mapping conventions or geometry.

It takes two minutes and catches the expensive case where the atlas belongs to another asset. It matters most when converting a model from another game:

- Some games name materials `*_[PRIMARY]` or `*_[SECONDARY]` and give them no color atlas on purpose, because their color comes from that game's paint palette. Use a flat paint texture or paint a `_co`; never bind whichever atlas is largest.
- Aircraft atlases can hold a mirrored copy of one side so the markings read correctly on both sides. Mirrored text alone does not justify flipping U for the whole model.

## Converting a `.paa` back

- ImageToPAA converts in the other direction from the command line: `ImageToPAA in.paa out.png` and `ImageToPAA in.paa out.tga` both exit 0, and the TGA comes out uncompressed (**tool knowledge**).
- An `_smdi` PNG written by Pillow from the start has always converted cleanly (**tool knowledge**).
- Read any Explorer right click entry (`.reg` file) that wraps these conversions before you install it. A `.paa` entry written as `cmd /c "for %%i in ("%1") do ImageToPAA ..."` uses the doubled `%%i` of a batch file; handed to `cmd /c` it stops with "%%i was unexpected at this time" before ImageToPAA runs, while the same loop with a single `%i` runs. Whether Explorer turns `%%` into `%` first is not checked, so do not count on such an entry until it has been tried. A TGA entry written as `magick "%1" -compress none "%1"` overwrites the file in place with no backup.

## On Linux

The Proton setup and which tools run there (ImageToPAA, `dayzmake img2paa` and `paa2img`, TexView) are in `_shared/linux-proton.md`. For texture work:

- The suffix rules apply as on Windows; a `_ca` PNG becomes DXT5.
- Workbench starts under Proton, but the `.edds` and `.emat` import of `matpbr-emat.md` is not checked there.
- `P:\` paths inside a `.rvmat` are paths under the folder `dayz-proton.sh init` maps.
