# UI textures

Covers full screen UI textures (loading screens, menu backgrounds, map images): measure the engine's tone curve before changing a texture's, ship a `.paa` from ImageToPAA rather than a hand written `.edds`, and size a screen image for ImageToPAA.

The one vanilla fact here is the image call itself: `ImageWidget.LoadImageFile(int num, string name, bool noCache = false)` returns a `bool` (`P:\scripts\1_core\proto\enwidgets.c:257`), and that `bool` says nothing about whether the image draws. The rest was measured on a production mod and its tools, not on vanilla files. How a loading screen picks and shows its backgrounds is in `_shared/ui/cameras-seats-loading-screens.md`.

## Measure the tone curve before changing it

Never change a UI texture's tone curve because an offline model says so. Take a screenshot first.

- An offline model of the engine is not the engine. A production mod applied a full sRGB to linear decode to its loading screen source. A model built on the claim that "1.29 washes UI by +35 % luma, contrast 76 to 58" called that about four times too strong, so the decode was swapped for a gentle photographic curve, and in game the screen came out much brighter than before.
- Unverified: working backwards, linear to sRGB applied to the old texture predicts a render of 132.31 against a source median of 132.51, an exact cancellation. That fits the engine treating a UI `.paa` as linear data and encoding it for display, which would make the sRGB to linear decode the right inverse and the "+35 %" model wrong. It rests on one report and arithmetic, so do not act on it either.
- What settles it: screenshot the UI texture on screen, compare it pixel by pixel with the texture that produced it, and derive the real curve.
- Storing linear data in an 8-bit DXT1 texture starves the shadows, and the engine's expansion then magnifies that rounding. On the production mod the raw DXT1 error averaged 2.64 of 255, but in display space it reached a mean of 7.46 and a maximum of 77 in the darkest 18 % of the image: blotchy, banded shadows that make the picture look a bit off while the overall tone is right. If linear storage is the right route, fix it with precision (an uncompressed or higher bit depth `.paa`, or dithering before the encode), not with a tone change.
- Decode the shipped `.paa` and compare its luma median with the source. A build script that ran without errors proves nothing about the curve it applied, and an offline round trip never predicts the render; look at it in game.

## Screen sized images

The power of two rule and the vanilla scan behind it are in `suffixes-and-sizes.md`. For a screen sized image it means `ImageToPAA.exe` rejects 2048 x 1152 and 1920 x 1080 with `Error (Img is not of power of 2 size)`, accepts 2048 x 1024, and rejects 1536 x 1024. A `.paa` of another size can still load at run time: one mod ships a 1920 x 1080 loading screen mask (third-party mod behaviour, not vanilla).

Squeezing a 16:9 source into 2048 x 1024 stretches it about 12.5 % vertically. Plan a crop, or another encoder, before promising 16:9.

## Ship a `.paa`, not a hand written `.edds`

- An `.edds` written by a Python script does not render: not as self contained LZ4, not as a structural copy of a production file with the same tags, and not as `COPY` blocks. `LoadImageFile` returns `true` every time, so the log does not catch it, and a Python round trip with a largest difference of 0 does not predict the render.
- A `.paa` from DayZ Tools `ImageToPAA.exe` (`/dayz-pack-texture`), named from script, renders on the first try, at about 1 MB against about 14 MB for the `.edds`.
- Use a decoder to inspect someone else's `.edds`, never to write one. Six production files decode with a largest difference of 0 on the top mip against their source PNG. DayZ Tools has no command line `.edds` writer; production files come from a Workbench PNG import, which the `.meta` file records.

## The `.edds` layout

- A 128-byte DDS header. The loading screen backgrounds are uncompressed BGRA8: pixel format flags `0x41`, red mask `0x00FF0000`, alpha mask `0xFF000000`. The mip count is floor(log2(max(width, height))) + 1.
- From offset 128, 8 bytes per mip: a 4-byte tag and a `uint32` size. The tag is `COPY` (raw) or `LZ4 `. The smallest mip comes first, and the payloads follow in the same order.
- An `LZ4 ` payload is a `uint32` holding the mip's uncompressed size, then slices of 65,536 bytes, each prefixed by its compressed size, with `0x80000000` set on the last one.
- The slices are linked blocks. Slice 0 decompresses alone; later slices fail with "corrupt input or insufficient space" unless the previous slice is passed as the dictionary (`lz4.block.decompress(data, uncompressed_size=n, dict=prev)`). That error looks like a size bug and is not one.
