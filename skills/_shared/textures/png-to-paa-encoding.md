# A `.paa` writer in Python

Covers a DXT1 `.paa` writer of about 150 lines that needs only Pillow and numpy: when to use it, the code, how to check its output, and what it cannot do. The byte layout it writes is explained in `paa-file-layout.md`.

On a machine with DayZ Tools, `/dayz-pack-texture` (ImageToPAA) is the normal route and handles every suffix. Use this writer on a machine without Bohemia's tools (Linux, macOS, a clean Windows) and for opaque `_co` textures only. Its output reads back cleanly in this repo's PAA decoder; how the game shows it is not checked in game.

## When to use it

| Situation | Use |
|---|---|
| An opaque `_co` made from a PNG, no DayZ Tools on the machine | This writer |
| A texture with alpha that must survive (decals, glass) | ImageToPAA through `/dayz-pack-texture`; alpha needs DXT5 and this writer is DXT1 only |
| A `_nohq`, `_smdi` or any suffix ImageToPAA swizzles | ImageToPAA; a `_nohq` is DXT5 (`P:\DZ\vehicles\wheeled\civiliansedan\data\gazglass_nohq.paa` starts with `05 FF`) |
| A user who wants to keep changing the texture | Ship the PNG and the writer so they can run it again |
| A `.paa` the mod already has | Reuse it as it is; never encode it again |

The writer picks the two block colors at the brightest and darkest pixel by luminance, then maps each pixel to the nearest of the four colors. It is fast in numpy and good enough for the matte surfaces most DayZ items have.

## The writer

Save it as `paa_encoder.py` beside your build script, or paste it in:

```python
import struct

import numpy as np
from PIL import Image

def _rgb_to_565(r, g, b):
    return ((int(r) >> 3) << 11) | ((int(g) >> 2) << 5) | (int(b) >> 3)

def _rgb565_to_rgb(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))

def _dxt1_block(block_rgb):
    """block_rgb: (4, 4, 3) uint8. Returns the 8 bytes of one DXT1 block."""
    pixels = block_rgb.reshape(-1, 3).astype(np.int32)

    # End colors at the brightest and darkest pixel by luminance.
    lum = pixels[:, 0] * 299 + pixels[:, 1] * 587 + pixels[:, 2] * 114
    c0 = pixels[int(np.argmax(lum))]
    c1 = pixels[int(np.argmin(lum))]
    c0_565 = _rgb_to_565(c0[0], c0[1], c0[2])
    c1_565 = _rgb_to_565(c1[0], c1[1], c1[2])

    # Four color mode needs c0 > c1; a flat block is nudged, or it renders black.
    if c0_565 == c1_565:
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

    return c0_565.to_bytes(2, "little") + c1_565.to_bytes(2, "little") + packed.to_bytes(4, "little")

def _dxt1_encode_image(rgb_arr):
    """rgb_arr: (H, W, 3) uint8. Pads H and W to multiples of 4."""
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
    """Returns [(w, h, dxt1_bytes), ...], largest first, down to min_size."""
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
        img = img.resize((max(min_size, w // 2), max(min_size, h // 2)), Image.LANCZOS)
    return mips

def write_paa_dxt1(src_png_path, out_paa_path, max_size=1024):
    """Encodes a PNG as a DXT1 .paa. max_size caps the top mip's longer side."""
    img = Image.open(src_png_path).convert("RGB")
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    mips = _build_mipchain(img, min_size=4)

    small = img.resize((16, 16), Image.LANCZOS)
    avg = np.asarray(small).mean(axis=(0, 1)).astype(int)
    mx = np.asarray(small).max(axis=(0, 1)).astype(int)
    avgc = bytes([int(avg[2]), int(avg[1]), int(avg[0]), 0xFF])  # BGRA
    maxc = bytes([int(mx[2]), int(mx[1]), int(mx[0]), 0xFF])

    out = bytearray()
    out += b"\x01\xFF"  # DXT1 magic, 0xFF01 little endian
    out += b"GGATCGVA" + (4).to_bytes(4, "little") + avgc
    out += b"GGATCXAM" + (4).to_bytes(4, "little") + maxc
    out += b"GGATSFFO" + (64).to_bytes(4, "little")
    offs_pos = len(out)
    out += b"\x00" * 64  # OFFS, filled in once the mip offsets are known
    out += b"\x00\x00"  # palette size

    mip_offsets = []
    for (w, h, data) in mips:
        mip_offsets.append(len(out))
        out += w.to_bytes(2, "little") + h.to_bytes(2, "little")
        out += len(data).to_bytes(3, "little")
        out += data
    out += b"\x00" * 6  # terminator

    offs_data = bytearray(64)
    for i, ofs in enumerate(mip_offsets[:16]):
        struct.pack_into("<I", offs_data, i * 4, ofs)
    out[offs_pos:offs_pos + 64] = bytes(offs_data)

    with open(out_paa_path, "wb") as f:
        f.write(out)

    return {"path": out_paa_path, "size_bytes": len(out), "mip_count": len(mips)}
```

`max_size` defaults to 1024 because a mod item's color map rarely gains from more; scale a 4K source down here. Non-square images are fine.

Calling it:

```python
from paa_encoder import write_paa_dxt1

info = write_paa_dxt1(
    src_png_path="generated/lamp_diffuse.png",
    out_paa_path="mod/data/lamp/lamp_co.paa",
    max_size=1024,
)
print(info)  # {'path': ..., 'size_bytes': 699229, 'mip_count': 9}
```

## Checking the output

Read the file back with the PAA decoder of the 3D viewer tool, `scripts/tools/dayz-3d-viewer/dayz_3d_viewer/paa_to_png.py`, run from the repo root:

```python
import sys
sys.path.insert(0, "scripts/tools/dayz-3d-viewer")
from dayz_3d_viewer.paa_to_png import convert_paa_to_png
convert_paa_to_png("mod/data/lamp/lamp_co.paa", "verify.png", verbose=True)
```

A good file prints:

```text
PAA Type: DXT1 (0xFF01)
Tags: ['AVGC', 'MAXC', 'OFFS']
Mipmaps: 9
  [0] 1024x1024 (524288 bytes, LZO=False)
  ... (each mip half the size of the one before)
```

`LZO=False` on every mip is expected: this writer never compresses mips, while ImageToPAA does (`paa-file-layout.md`, "Mip headers"). Then look at the texture in game; the read back proves the layout, not how the engine draws it.

## What it cannot do

- **No alpha.** Textures with real alpha need DXT5, which adds an 8 byte alpha block in front of each color block.
- **No LZO.** Files come out larger than ImageToPAA's; vanilla's top mip in `paa-file-layout.md` is about a fifth smaller than raw DXT1. That is usually fine for a mod item. Adding LZO needs `python-lzo`, which builds against the liblzo2 headers, or the slower pure Python `lzokay`. If the mod gets too large, convert the biggest textures with ImageToPAA instead.
- **Weak on saturated colors.** Choosing end colors by luminance can pick near grey colors when a block varies in hue rather than brightness. Weathered metal, dirt and stone come out well; vivid signs or logos can show color banding in small areas.

These are the price of a writer with no native dependencies. Prefer Bohemia's tools wherever they are installed.
