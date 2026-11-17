# UI textures: loading screens, menu backgrounds, map images

Two rules for full screen UI textures, each with what was measured behind it: do not change the tone curve from an offline model, and ship a `.paa` made by ImageToPAA, not a hand written `.edds`. It also records the `.edds` layout that was decoded while finding that out.

How to read it: all of this is measured on one production mod and its tools (2026-08-21), not on vanilla files, so nothing here cites `P:\`. Lines marked "hypothesis" fit the observations and are not proven.

## Rule 1: measure the engine's tone curve before changing a texture's

Never change the tone curve of a UI texture on the strength of an offline model. Take a screenshot first.

- **What happened.** A mod in production applied a full sRGB to linear decode to its loading screen source. An offline model, built from a note that said "1.29 washes UI by +35 % luma, contrast 76 to 58" (Bohemia ticket T198202), called that about four times too strong, and the decode was replaced by a gentle photographic curve. In game the result was much brighter than before. That report from the user is the only real observation in the whole exercise.
- **Hypothesis.** Working backwards, linear to sRGB applied to the old texture predicts a render of 132.31 against a source median of 132.51: an exact cancellation. So the engine plausibly treats a UI `.paa` as linear data and encodes it for display, which would make the sRGB to linear decode on the source the correct inverse and the "+35 %" model wrong, or measured on something else. This fits one report and arithmetic, not a measurement. Do not act on it either.
- **What ends the guessing.** Take a screenshot of the UI texture on screen, compare it pixel by pixel with the known texture that produced it, and derive the real curve. One screenshot settles it.
- **A second trap.** Storing linear data in an 8-bit DXT1 texture starves the shadows, and the engine's expansion then amplifies exactly that rounding. Measured on the production mod: the raw DXT1 error averaged 2.64 of 255, but in display space it reached a mean of 7.46 and a maximum of 77 in the darkest 18 % of the image: blotchy, banded shadows that read as "the picture looks a bit off" while the overall tone is right. If linear storage is the right route, the fix is precision (an uncompressed or higher bit depth `.paa`, or dithering before the encode), not a tone change.
- **Check.** Decode the shipped `.paa` and compare its luma median with the source. A build script that "ran fine" proves nothing about the curve it applied. An offline round trip never predicts the render: look at it in game.

### The power of two limit belongs to ImageToPAA

`ImageToPAA.exe` rejects 2048 x 1152 and 1920 x 1080 with `Error (Img is not of power of 2 size)`; 2048 x 1024 is accepted and 1536 x 1024 is rejected. That project reports that `.paa` files of other sizes still load at run time: the loading screen mask its mods ship is 1920 x 1080. That is a third party report. Vanilla ships no such file: all 30,094 `.paa` files under `P:\DZ` have power of two sides (header scan of 2026-11-17), so keep to powers of two unless you test the other case yourself.

Forcing a 16:9 source into 2048 x 1024 costs about 12.5 % of vertical stretch. Plan a crop, or another encoder, before promising 16:9.

## Rule 2: ship a `.paa` from ImageToPAA, not a hand written `.edds`

- **What failed.** An `.edds` written by a Python script did not render: not as self contained LZ4, not as a structural clone of a production file with the same tags, and not as `COPY` blocks. `LoadImageFile` returned `true` every time, so the log does not catch it. A Python round trip with a maximum difference of 0 does not predict the render.
- **What worked.** A `.paa` from DayZ Tools `ImageToPAA.exe`, referenced from script, on the first try. About 1 MB against about 14 MB for the `.edds`.
- **Use a decoder to inspect someone else's `.edds`, not to write one.** Six production files decoded with a maximum difference of 0 on mip 0 against their source PNG. DayZ Tools has no command line `.edds` writer; production files come from a Workbench PNG import, which the `.meta` file records.

### The `.edds` layout that was decoded

- A 128-byte DDS header. The loading screen backgrounds were uncompressed BGRA8: pixel format flags `0x41`, red mask `0x00FF0000`, alpha mask `0xFF000000`. The mip count is floor(log2(max(width, height))) + 1.
- From offset 128, 8 bytes per mip: a 4-byte tag and a `uint32` size. The tag is `COPY` (raw) or `LZ4 `. The smallest mip comes first. The payloads follow in the same order.
- An `LZ4 ` payload is a `uint32` holding the uncompressed mip size, then slices of 65,536 bytes, each prefixed by its compressed size, with `0x80000000` set on the last one.
- **The slices are linked blocks.** Slice 0 decompresses alone. Later slices fail with "corrupt input or insufficient space" unless the previous slice is passed as the dictionary (`lz4.block.decompress(data, uncompressed_size=n, dict=prev)`). That error reads like a size bug and is not one.
