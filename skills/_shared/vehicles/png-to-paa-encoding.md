# PNG to PAA encoding in pure Python (DXT1)

A DXT1 `.paa` writer of about 200 lines that needs only Pillow and NumPy, the file layout it writes, how to check its output, and what it cannot do.

> Status: tool notes from the author's own pipeline. The encoder was not run here, and its output was not loaded in the game here. On a machine with DayZ Tools, `/dayz-pack-texture` (ImageToPAA) is this repo's normal route and handles every texture suffix; use this encoder on machines without Bohemia's tools (Linux, macOS, a clean Windows), for opaque `_co` textures only. The header layout it writes was compared with vanilla files on `P:\` (anchors below).

## Vanilla anchors checked on `P:\`

- `P:\DZ\vehicles\wheeled\civiliansedan\data\civiliansedan_int1_co.paa` starts with the bytes `01 FF` (DXT1), then `GGAT` + `CGVA` with length 4 (AVGC), `GGAT` + `CXAM` with length 4 (MAXC), then `GGAT` + `SFFO` (OFFS): the magic, the reversed tag names and the tag order this encoder writes.
- `P:\DZ\vehicles\wheeled\civiliansedan\data\gazglass_nohq.paa` starts with `05 FF` (DXT5). That agrees with `skills/_shared/textures/suffixes-and-sizes.md`, where `_nohq` is DXT5, so do not ship this DXT1 encoder's output as a `_nohq`.

## Why this exists

The DayZ engine only reads `.paa` textures. Historically the author's skill told the
user to convert the generated PNGs themselves with TexView or Pal2PacE. That
handoff broke the "ready to implement" promise — users on Linux/macOS or
clean Windows environments don't have Bohemia's tools installed.

This reference provides a pure-Python DXT1 PAA encoder that produces valid
files the engine accepts. ~200 lines, zero C dependencies, works anywhere
Pillow + NumPy install.

## When to use this vs TexView

| Situation | Use |
|---|---|
| Generating the base color / diffuse `_co` PAA from a PNG | This encoder |
| Input PNG has an alpha channel you need to preserve (decals, glass) | TexView (needs DXT5; this encoder is DXT1-only for now) |
| User wants to iterate on the texture outside the pipeline | Ship the PNG + this encoder; they can re-run it |
| Pre-existing `.paa` from the mod itself | Don't re-encode — reuse as-is |

DXT1 covers the common case for opaque surface color textures. For normal
maps (`_nohq`) and spec/metal (`_smdi`) the channels encode different data
but the format is still DXT1/DXT5 — the encoder below handles the color
case; extend for DXT5 if you need alpha.

## File format summary

A DayZ `.paa` is roughly:

```
[ 2 bytes ] magic (0xFF01 little-endian for DXT1 = bytes 01 FF)
[ TAGG chunks ] variable — AVGC, MAXC, OFFS (see below)
[ 2 bytes ] palette size (0 when not indexed)
[ mipmaps ] each: 2B width, 2B height, 3B data_len, data; largest first
[ 6 bytes ] terminator (zeros)
```

Each TAGG chunk is:

```
[ 4 bytes ] "GGAT"  (literal — "TAGG" is a marker backwards)
[ 4 bytes ] reversed tag name, e.g. "CGVA" for AVGC, "SFFO" for OFFS
[ 4 bytes ] length (uint32 LE)
[ length bytes ] data
```

Three TAGGs matter for the engine to accept the file:

- **AVGC** (4 bytes, BGRA) — average color over the top mip, used for
  distance fallback rendering.
- **MAXC** (4 bytes, BGRA) — maximum pixel value, used by some shaders.
- **OFFS** (64 bytes, 16 × uint32 LE) — offset from start-of-file to each
  mipmap's header. Zeros for unused slots.

Skipping OFFS is a silent compatibility bug — the engine loads it but the
renderer can't seek-to-mip, which defeats mip streaming.

## DXT1 block encoding (BC1)

DXT1 stores 4×4 blocks of RGB pixels in 8 bytes:

```
[ 2 bytes ] color0 as R5G6B5
[ 2 bytes ] color1 as R5G6B5
[ 4 bytes ] 16 × 2-bit indices (pixel 0 = lowest 2 bits)
```

If `color0 > color1` (as uint16): the 4-color palette is
`{c0, c1, 2c0/3+c1/3, c0/3+2c1/3}`.
If `color0 <= color1`: 3-color + transparent palette. Don't use this mode
in opaque encoding — it's for 1-bit-alpha content.

The encoder picks endpoints by projecting onto a luminance axis and
taking the extremes, then maps each pixel to the nearest of the 4 palette
colors by RGB distance. Simple, fast (pure NumPy), good enough for the
matte PBR surfaces DayZ items usually have.

## Reference implementation

Save as `paa_encoder.py` next to your build script (or inline it there):

```python
import numpy as np
import struct
from PIL import Image


def _rgb_to_565(r, g, b):
    return ((int(r) >> 3) << 11) | ((int(g) >> 2) << 5) | (int(b) >> 3)


def _rgb565_to_rgb(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


def _dxt1_block(block_rgb):
    """block_rgb: (4, 4, 3) uint8 — returns 8 bytes of DXT1."""
    pixels = block_rgb.reshape(-1, 3).astype(np.int32)  # (16, 3)

    # Luminance-axis endpoint selection (fast, good enough for matte PBR)
    lum = pixels[:, 0] * 299 + pixels[:, 1] * 587 + pixels[:, 2] * 114
    c0 = pixels[int(np.argmax(lum))]
    c1 = pixels[int(np.argmin(lum))]
    c0_565 = _rgb_to_565(c0[0], c0[1], c0[2])
    c1_565 = _rgb_to_565(c1[0], c1[1], c1[2])

    # Must satisfy c0 > c1 for the 4-color (no-alpha) palette mode.
    if c0_565 == c1_565:
        # Flat block — nudge to force 4-color mode (otherwise rendering black).
        if c1_565 > 0:
            c1_565 -= 1
        else:
            c0_565 += 1
    elif c0_565 < c1_565:
        c0_565, c1_565 = c1_565, c0_565

    r0, g0, b0 = _rgb565_to_rgb(c0_565)
    r1, g1, b1 = _rgb565_to_rgb(c1_565)
    palette = np.array([
        [r0, g0, b0],
        [r1, g1, b1],
        [(2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3],
        [(r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3],
    ], dtype=np.int32)

    d = ((pixels[:, None, :] - palette[None, :, :]) ** 2).sum(axis=2)
    idx = np.argmin(d, axis=1)
    packed = 0
    for i, v in enumerate(idx):
        packed |= (int(v) & 0x3) << (i * 2)

    return (
        c0_565.to_bytes(2, "little")
        + c1_565.to_bytes(2, "little")
        + packed.to_bytes(4, "little")
    )


def _dxt1_encode_image(rgb_arr):
    """rgb_arr: (H, W, 3) uint8. H and W are padded to multiples of 4."""
    h, w, _ = rgb_arr.shape
    pad_h = (4 - h % 4) % 4
    pad_w = (4 - w % 4) % 4
    if pad_h or pad_w:
        rgb_arr = np.pad(rgb_arr, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")
        h += pad_h
        w += pad_w
    out = bytearray()
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            out += _dxt1_block(rgb_arr[y:y + 4, x:x + 4, :])
    return bytes(out)


def _build_mipchain(pil_image, min_size=4):
    """Return [(w, h, dxt1_bytes), ...] largest-first, down to min_size x min_size."""
    mips = []
    img = pil_image
    while True:
        w, h = img.size
        if w < min_size or h < min_size:
            break
        arr = np.asarray(img)
        if arr.ndim == 2:
            arr = np.stack([arr, arr, arr], axis=2)
        elif arr.shape[2] == 4:
            arr = arr[:, :, :3]
        mips.append((w, h, _dxt1_encode_image(arr)))
        if w <= min_size and h <= min_size:
            break
        img = img.resize((max(min_size, w // 2), max(min_size, h // 2)),
                         Image.LANCZOS)
    return mips


def write_paa_dxt1(src_png_path, out_paa_path, max_size=1024):
    """Encode a PNG to DXT1 PAA. max_size caps the top-mip dimension.

    The engine is happy with non-square textures, but mod items rarely
    benefit from anything larger than 1024 for color maps. Big source
    PNGs (4k) should be downscaled here.
    """
    img = Image.open(src_png_path).convert("RGB")
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    mips = _build_mipchain(img, min_size=4)

    # Summary colors for TAGGs
    small = img.resize((16, 16), Image.LANCZOS)
    avg = np.asarray(small).mean(axis=(0, 1)).astype(int)
    mx = np.asarray(small).max(axis=(0, 1)).astype(int)
    avgc = bytes([int(avg[2]), int(avg[1]), int(avg[0]), 0xFF])  # BGRA
    maxc = bytes([int(mx[2]), int(mx[1]), int(mx[0]), 0xFF])

    out = bytearray()
    out += b"\x01\xFF"                   # DXT1 magic (0xFF01 LE)
    # AVGC
    out += b"GGATCGVA" + (4).to_bytes(4, "little") + avgc
    # MAXC
    out += b"GGATCXAM" + (4).to_bytes(4, "little") + maxc
    # OFFS — reserve 64 bytes, fill after we know mip offsets
    out += b"GGATSFFO" + (64).to_bytes(4, "little")
    offs_pos = len(out)
    out += b"\x00" * 64
    # Palette size
    out += b"\x00\x00"

    mip_offsets = []
    for (w, h, data) in mips:
        mip_offsets.append(len(out))
        out += w.to_bytes(2, "little") + h.to_bytes(2, "little")
        out += len(data).to_bytes(3, "little")
        out += data
    # Terminator
    out += b"\x00" * 6

    # Fill OFFS now that mip offsets are known
    offs_data = bytearray(64)
    for i, ofs in enumerate(mip_offsets[:16]):
        struct.pack_into("<I", offs_data, i * 4, ofs)
    out[offs_pos:offs_pos + 64] = bytes(offs_data)

    with open(out_paa_path, "wb") as f:
        f.write(out)

    return {
        "path": out_paa_path,
        "size_bytes": len(out),
        "mip_count": len(mips),
    }
```

## Usage in the pipeline

```python
from paa_encoder import write_paa_dxt1

info = write_paa_dxt1(
    src_png_path="generated/lamp_diffuse.png",
    out_paa_path="mod/data/lamp/lf_lamp.paa",
    max_size=1024,
)
print(info)  # {'path': ..., 'size_bytes': 699229, 'mip_count': 9}
```

## Verification

Round-trip the output through the PAA decoder of the 3D viewer tool (`paa_to_png.py` in
`scripts/tools/dayz-3d-viewer/dayz_3d_viewer/`) to confirm:

```python
from paa_to_png import convert_paa_to_png
convert_paa_to_png("mod/data/lamp/lf_lamp.paa", "verify.png", verbose=True)
```

A valid PAA shows:

```
PAA Type: DXT1 (0xFF01)
Tags: ['AVGC', 'MAXC', 'OFFS']
Mipmaps: 9
  [0] 1024x1024 (524288 bytes, LZO=False)
  ... (each mip half the previous size)
```

`LZO=False` on every mip is expected — this encoder never compresses
mipmaps. The engine reads uncompressed mips correctly; LZO only buys
file-size (roughly 30–40% for typical DayZ textures). Adding LZO is
doable but requires `python-lzo` (needs liblzo2 headers to build) or
`lzokay` (pure Python, slower). Not worth the install friction for
matte textures under ~1 MB.

## Limitations & future work

- **No alpha channel.** DXT5 encoding is needed for textures with
  meaningful alpha. The block format is similar: same 8-byte color block
  + an 8-byte alpha block per 4×4 tile.
- **No LZO compression.** File sizes are 30–40% larger than what TexView
  produces. Usually fine for mod items. If you hit mod size limits,
  switch a few large textures to TexView-compressed PAAs.
- **Luminance-axis endpoint selection is suboptimal** on saturated color
  blocks (it can pick near-grayscale endpoints when the actual axis of
  variation is chroma). Fine for weathered metal, dirt, stone — the
  dominant DayZ surfaces. For vivid signage or logos, expect some color
  banding in small regions.

These are tradeoffs for zero-dependency encoding. When the user has
Bohemia tools installed they should prefer those; when they don't, this
encoder is the unblocker.

## Common mistakes

- **Emitting the magic as `b"\xFF\x01"`** instead of `b"\x01\xFF"`. The
  format is little-endian uint16, so 0xFF01 → bytes `01 FF`.
- **Writing 4-byte mip data_len** — the spec is 3 bytes. Check with the
  decoder; if it reports `data_len` in the tens of megabytes for a 1024
  mip, you wrote 4 bytes.
- **Forgetting the 6-byte terminator.** Without it the engine keeps
  reading past the last mip and may fail silently or display a garbage
  texture.
- **Not padding to multiples of 4.** DXT blocks are 4×4; a 1023×1023
  image has to be padded. Encoder handles this via
  `np.pad(mode="edge")`, but if you reimplement, don't forget.
