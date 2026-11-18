# The `.paa` file layout

How a DayZ `.paa` file is laid out byte by byte: the format magic, the tagged header, the mip headers, the terminator, and how a DXT1 block stores 16 pixels. Read it to inspect a `.paa` or to write one without DayZ Tools; the writer itself is in `png-to-paa-encoding.md`.

ImageToPAA (`/dayz-pack-texture`) is the normal way to make a `.paa`, and which format it picks per suffix is in `suffixes-and-sizes.md`.

## The parts of the file

The vanilla sedan interior `P:\DZ\vehicles\wheeled\civiliansedan\data\civiliansedan_int1_co.paa` shows every part:

| Part | Size | In the sedan file |
|---|---|---|
| Format magic, a little endian `uint16` | 2 bytes | `01 FF`, which is `0xFF01`, DXT1 |
| Tagged blocks | 12 bytes plus each block's data | `AVGC`, then `MAXC`, then `OFFS` |
| Palette size | 2 bytes | `00 00`, no palette |
| Mips, largest first | 7 byte header plus data each | the top mip at offset 112 |
| Terminator | 6 bytes | six zero bytes at the end of the file |

A DXT5 file starts with `05 FF` instead, as the windscreen normal map `P:\DZ\vehicles\wheeled\civiliansedan\data\gazglass_nohq.paa` does. A `_nohq` is DXT5 (`suffixes-and-sizes.md`), so a DXT1 writer's output is never a valid `_nohq`.

## Tagged blocks

Each block is a 4 byte marker, a 4 byte name, a `uint32` length and the data:

```text
[4 bytes] "GGAT", the word TAGG written backwards
[4 bytes] the tag name backwards: "CGVA" for AVGC, "CXAM" for MAXC, "SFFO" for OFFS
[4 bytes] length, uint32 little endian
[length bytes] data
```

| Tag | Length | Holds |
|---|---|---|
| `AVGC` | 4 | The average color of the image, as BGRA |
| `MAXC` | 4 | The largest pixel value, as BGRA |
| `OFFS` | 64 | Sixteen `uint32` offsets from the start of the file to each mip header, zero for unused slots |

In the sedan file `AVGC` is `49 4A 4B FF`, `MAXC` is `FF FF FF FF`, and the first `OFFS` entry is 112, the offset of its top mip. Unverified (not tested in game): which tags the engine needs before it loads a file, and whether it streams mips from `OFFS`. Write all three, in this order, as vanilla does.

## Mip headers

Each mip starts with a 7 byte header, then its data:

```text
[2 bytes] width, uint16 little endian
[2 bytes] height, uint16 little endian
[3 bytes] data length, a 24-bit little endian integer
[data length bytes] the DXT blocks
```

The top bit of the width marks a mip whose data is LZO compressed. The sedan's top mip has a width of `0x8800`, which is 2048 with that bit set, a height of 2048 and 1,663,790 bytes of data, where raw DXT1 at that size would be 2,097,152. An uncompressed mip leaves the bit clear, and its data length is exactly (width / 4) x (height / 4) x 8 bytes for DXT1.

## A DXT1 block

DXT1 (BC1) stores each 4 x 4 block of RGB pixels in 8 bytes:

```text
[2 bytes] color0 as R5G6B5
[2 bytes] color1 as R5G6B5
[4 bytes] sixteen 2-bit indexes, pixel 0 in the lowest 2 bits
```

When `color0` is greater than `color1` as a `uint16`, the block has four colors: `c0`, `c1`, `2c0/3 + c1/3` and `c0/3 + 2c1/3`. When `color0` is less than or equal to `color1`, it has three colors and transparent black, which is meant for one bit alpha. An opaque writer always keeps `color0` greater, including on a flat block where both colors are equal.

DXT5 adds an 8 byte alpha block in front of the same color block, 16 bytes per 4 x 4 tile.

## Mistakes that break a file

- The magic written as `b"\xFF\x01"`. The value is a little endian `uint16`, so `0xFF01` is the bytes `01 FF`.
- A 4 byte mip data length. It is 3 bytes; a decoder that reports a length in the tens of megabytes for a 1024 mip means 4 bytes were written.
- No 6 byte terminator. Vanilla files end with it; without it a reader runs past the last mip.
- An image size that is not a multiple of 4. DXT blocks are 4 x 4, so pad the edge before encoding.
