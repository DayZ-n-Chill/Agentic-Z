"""PAA to PNG converter.

Reads Bohemia Interactive .paa/.pac texture files and converts to PNG.
Supports: DXT1, DXT5, DXT3, RGBA4444, RGBA5551, RGBA8888, LuminanceAlpha.
Based on the BI Community Wiki PAA File Format specification.

LZSS decompression follows the BI variant documented on that wiki
(ring buffer 4096, init 0x20, match-length offset +2).
"""

from __future__ import annotations

import io
import os
import struct
import sys

from .deps import require_pillow
from .errors import MissingDependencyError, ViewerError

try:
    import lzo

    HAS_LZO = True
except ImportError:
    lzo = None
    HAS_LZO = False

PAA_DXT1 = 0xFF01
PAA_DXT2 = 0xFF02
PAA_DXT3 = 0xFF03
PAA_DXT4 = 0xFF04
PAA_DXT5 = 0xFF05
PAA_RGBA5551 = 0x1555
PAA_RGBA4444 = 0x4444
PAA_LUMALPHA = 0x8080
PAA_RGBA8888 = 0x8888
PAA_INDEX_PAL = 0x4747

PAA_TYPE_NAMES = {
    PAA_DXT1: "DXT1",
    PAA_DXT2: "DXT2",
    PAA_DXT3: "DXT3",
    PAA_DXT4: "DXT4",
    PAA_DXT5: "DXT5",
    PAA_RGBA5551: "RGBA5551",
    PAA_RGBA4444: "RGBA4444",
    PAA_LUMALPHA: "LuminanceAlpha",
    PAA_RGBA8888: "RGBA8888",
    PAA_INDEX_PAL: "IndexPalette",
}

IS_DXT = {PAA_DXT1, PAA_DXT2, PAA_DXT3, PAA_DXT4, PAA_DXT5}


def lzss_decode(data_in: bytes, expected_out_size: int) -> bytes:
    """LZSS decompression as used by BI for non-DXT PAA mipmaps.

    BI variant: ring buffer size 4096 (0x1000), init with 0x20 (space),
    match length offset +2. Documented on the BI Community Wiki; the
    algorithm is a standard LZSS variant and is reimplemented here.
    """
    buf = bytearray(b"\x20" * 0x100F)
    out = bytearray()
    r = 0
    pi = 0
    flags = 0
    sz_in = len(data_in)

    while pi < sz_in and len(out) < expected_out_size:
        flags >>= 1
        if (flags & 256) == 0:
            if pi >= sz_in:
                break
            flags = data_in[pi] | 0xFF00
            pi += 1

        if flags & 1:
            if pi >= sz_in or len(out) >= expected_out_size:
                break
            c = data_in[pi]
            pi += 1
            out.append(c)
            buf[r] = c
            r = (r + 1) & 0xFFF
        else:
            if pi + 1 >= sz_in:
                break
            i = data_in[pi]
            j = data_in[pi + 1]
            pi += 2
            i |= (j & 0xF0) << 4
            j = (j & 0x0F) + 2
            pr = r
            for k in range(j + 1):
                c = buf[(pr - i + k) & 0xFFF]
                if len(out) >= expected_out_size:
                    break
                out.append(c)
                buf[r] = c
                r = (r + 1) & 0xFFF

    return bytes(out)


def _make_dds_header(width: int, height: int, dxt_type: int) -> bytes:
    """Build a minimal DDS header so Pillow's DdsImagePlugin can decode."""
    magic = b"DDS "
    header_size = 124
    flags = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000
    pitch_or_linear = 0
    depth = 0
    mip_count = 1
    reserved = b"\x00" * 44

    pf_size = 32
    pf_flags = 0x4

    if dxt_type == PAA_DXT1:
        fourcc = b"DXT1"
        pitch_or_linear = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 8
    elif dxt_type == PAA_DXT3:
        fourcc = b"DXT3"
        pitch_or_linear = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 16
    elif dxt_type == PAA_DXT5:
        fourcc = b"DXT5"
        pitch_or_linear = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 16
    else:
        fourcc = b"DXT1"
        pitch_or_linear = max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 8

    header = struct.pack(
        "<4sI I I I I I I",
        magic,
        header_size,
        flags,
        height,
        width,
        pitch_or_linear,
        depth,
        mip_count,
    )
    header += reserved
    header += struct.pack(
        "<I I 4s I I I I I",
        pf_size,
        pf_flags,
        fourcc,
        0,
        0,
        0,
        0,
        0,
    )
    header += struct.pack("<I I I I I", 0x1000, 0, 0, 0, 0)
    return header


def decode_dxt_mipmap(data: bytes, width: int, height: int, dxt_type: int):
    """Decode DXT compressed data using Pillow's DDS support."""
    image_cls = require_pillow()
    dds_bytes = _make_dds_header(width, height, dxt_type) + data
    img = image_cls.open(io.BytesIO(dds_bytes))
    img.load()
    return img.convert("RGBA")


def decode_rgba4444(data: bytes, width: int, height: int):
    image_cls = require_pillow()
    img = image_cls.new("RGBA", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 2
            if idx + 1 >= len(data):
                break
            val = struct.unpack_from("<H", data, idx)[0]
            r = ((val >> 12) & 0xF) * 17
            g = ((val >> 8) & 0xF) * 17
            b = ((val >> 4) & 0xF) * 17
            a = (val & 0xF) * 17
            pixels[x, y] = (r, g, b, a)
    return img


def decode_rgba5551(data: bytes, width: int, height: int):
    image_cls = require_pillow()
    img = image_cls.new("RGBA", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 2
            if idx + 1 >= len(data):
                break
            val = struct.unpack_from("<H", data, idx)[0]
            a = (val & 0x8000) >> 15
            r = ((val >> 10) & 0x1F) << 3
            g = ((val >> 5) & 0x1F) << 3
            b = (val & 0x1F) << 3
            pixels[x, y] = (r, g, b, 255 if a else 0)
    return img


def decode_lumalpha(data: bytes, width: int, height: int):
    image_cls = require_pillow()
    img = image_cls.new("RGBA", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 2
            if idx + 1 >= len(data):
                break
            lum = data[idx]
            alpha = data[idx + 1]
            pixels[x, y] = (lum, lum, lum, alpha)
    return img


def decode_rgba8888(data: bytes, width: int, height: int):
    image_cls = require_pillow()
    img = image_cls.new("RGBA", (width, height))
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            idx = (y * width + x) * 4
            if idx + 3 >= len(data):
                break
            pixels[x, y] = (data[idx], data[idx + 1], data[idx + 2], data[idx + 3])
    return img


def expected_raw_size(paa_type: int, width: int, height: int) -> int:
    if paa_type == PAA_DXT1:
        return max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 8
    if paa_type in (PAA_DXT3, PAA_DXT5):
        return max(1, (width + 3) // 4) * max(1, (height + 3) // 4) * 16
    if paa_type in (PAA_RGBA4444, PAA_RGBA5551, PAA_LUMALPHA):
        return width * height * 2
    if paa_type == PAA_RGBA8888:
        return width * height * 4
    return width * height * 2


def _require_lzo():
    if not HAS_LZO:
        raise MissingDependencyError(
            "LZO-compressed PAA files need python-lzo or the lzokay shim. "
            "Install with: pip install 'dayz-3d-viewer[lzo]' "
            "then python -m dayz_3d_viewer install-lzo-shim"
        )
    return lzo


class PAAFile:
    """Parser for BI .paa/.pac texture files."""

    def __init__(self, filepath: str | None = None, fileobj=None):
        self.paa_type = 0
        self.type_name = "Unknown"
        self.tags = {}
        self.mipmaps = []

        if filepath:
            with open(filepath, "rb") as handle:
                self._parse(handle)
        elif fileobj:
            self._parse(fileobj)
        else:
            raise ViewerError("PAAFile requires filepath or fileobj")

    def _parse(self, handle):
        self.paa_type = struct.unpack("<H", handle.read(2))[0]
        self.type_name = PAA_TYPE_NAMES.get(
            self.paa_type, "Unknown(0x%04X)" % self.paa_type
        )
        if self.paa_type == PAA_INDEX_PAL:
            raise ViewerError("Index palette PAA (0x4747) is not supported")
        self._read_tags(handle)
        self._read_mipmaps(handle)

    def _read_tags(self, handle):
        while True:
            marker = handle.read(2)
            if len(marker) < 2:
                break
            val = struct.unpack("<H", marker)[0]
            if val == 0:
                break
            handle.seek(-2, 1)
            sig = handle.read(8)
            if sig[:4] != b"GGAT":
                handle.seek(-8, 1)
                handle.read(2)
                break
            tag_name_raw = sig[4:8]
            tag_name = tag_name_raw[::-1].decode("ascii", errors="replace").strip("\x00")
            tag_size = struct.unpack("<I", handle.read(4))[0]
            tag_data = handle.read(tag_size)
            self.tags[tag_name] = tag_data

    def _read_mipmaps(self, handle):
        while True:
            header = handle.read(4)
            if len(header) < 4:
                break
            width, height = struct.unpack("<HH", header)
            if width == 0 and height == 0:
                break
            size_bytes = handle.read(3)
            if len(size_bytes) < 3:
                break
            data_size = size_bytes[0] | (size_bytes[1] << 8) | (size_bytes[2] << 16)
            if data_size == 0:
                break
            raw_data = handle.read(data_size)
            lzo_compressed = False
            real_width = width
            if self.paa_type in IS_DXT and (width & 0x8000):
                lzo_compressed = True
                real_width = width & 0x7FFF
            self.mipmaps.append(
                {
                    "width": real_width,
                    "height": height,
                    "data": raw_data,
                    "data_size": data_size,
                    "lzo": lzo_compressed,
                }
            )

    def get_largest_mipmap(self) -> dict:
        if not self.mipmaps:
            raise ViewerError("No mipmaps found in PAA file")
        return self.mipmaps[0]

    def decode_mipmap(self, mip_index: int = 0):
        mip = self.mipmaps[mip_index]
        width, height = mip["width"], mip["height"]
        data = mip["data"]

        if self.paa_type in IS_DXT:
            exp_size = expected_raw_size(self.paa_type, width, height)
            if mip["lzo"]:
                codec = _require_lzo()
                data = codec.decompress(data, False, exp_size)
            elif len(data) != exp_size and len(data) > 0 and HAS_LZO:
                try:
                    data = lzo.decompress(data, False, exp_size)
                except Exception:
                    pass
            if len(data) < exp_size:
                data = data + b"\x00" * (exp_size - len(data))
            return decode_dxt_mipmap(data, width, height, self.paa_type)

        exp_size = expected_raw_size(self.paa_type, width, height)
        try:
            decompressed = lzss_decode(data, exp_size)
        except Exception:
            decompressed = data
        if self.paa_type == PAA_RGBA4444:
            return decode_rgba4444(decompressed, width, height)
        if self.paa_type == PAA_RGBA5551:
            return decode_rgba5551(decompressed, width, height)
        if self.paa_type == PAA_LUMALPHA:
            return decode_lumalpha(decompressed, width, height)
        if self.paa_type == PAA_RGBA8888:
            return decode_rgba8888(decompressed, width, height)
        raise ViewerError("Unsupported PAA type: 0x%04X" % self.paa_type)

    def to_png(self, output_path: str, mip_index: int = 0):
        img = self.decode_mipmap(mip_index)
        img.save(output_path, "PNG")
        return img

    def info(self) -> dict:
        return {
            "type": self.type_name,
            "type_hex": "0x%04X" % self.paa_type,
            "num_mipmaps": len(self.mipmaps),
            "tags": list(self.tags.keys()),
            "mipmaps": [
                {
                    "width": item["width"],
                    "height": item["height"],
                    "data_size": item["data_size"],
                    "lzo": item["lzo"],
                }
                for item in self.mipmaps
            ],
        }


def convert_paa_to_png(
    input_path: str, output_path: str | None = None, verbose: bool = False
) -> str:
    """Convert a .paa file to .png. Returns the output path."""
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".png"
    paa = PAAFile(input_path)
    if verbose:
        info = paa.info()
        print("PAA Type: %s (%s)" % (info["type"], info["type_hex"]))
        print("Tags: %s" % info["tags"])
        print("Mipmaps: %s" % info["num_mipmaps"])
        for index, mip in enumerate(info["mipmaps"]):
            print(
                "  [%s] %sx%s (%s bytes, LZO=%s)"
                % (index, mip["width"], mip["height"], mip["data_size"], mip["lzo"])
            )
    paa.to_png(output_path)
    if verbose:
        print("Saved: %s" % output_path)
    return output_path


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("Usage: python -m dayz_3d_viewer paa-to-png <input.paa> [output.png] [-v]")
        return 2
    verbose = "-v" in args
    positional = [item for item in args if item != "-v"]
    convert_paa_to_png(
        positional[0],
        positional[1] if len(positional) > 1 else None,
        verbose,
    )
    return 0
