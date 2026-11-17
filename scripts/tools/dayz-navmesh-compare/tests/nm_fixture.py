"""Synthetic .nm files in the layout navmesh_tiles.py reads. No game data.

File: magic, version, tile count, tiles x, tiles z (5 x uint32), origin x y z,
tile width, tile depth (5 x float32), 8 bytes the reader skips, an offset table
(count x uint32, relative to its end), then the tiles. Tile: a 16-byte prefix
(uint64 unused, uint32 size of the header plus payload, uint32 unused), a
dtMeshHeader (15 x uint32, 10 x float32) and a payload.
"""

from __future__ import annotations

import struct


TESM = 0x4D534554
DNAV = 0x444E4156


def tile_bytes(
    x,
    z,
    width,
    *,
    polygons=4,
    vertices=6,
    y=(0.0, 10.0),
    payload=b"\x01\x02\x03\x04",
    magic=DNAV,
    version=11,
    coords=None,
    bmin=None,
    bmax=None,
    prefix_size=None,
):
    cx, cz = (x, z) if coords is None else coords
    low = (width * x, y[0], width * z) if bmin is None else bmin
    high = (width * (x + 1), y[1], width * (z + 1)) if bmax is None else bmax
    ints = (magic, version, cx, cz, 0, 0, polygons, vertices, 0, 0, 0, 0, 0, 0, 0)
    floats = (2.0, 0.6, 0.9, *low, *high, 0.5)
    body = struct.pack("<15I", *ints) + struct.pack("<10f", *floats) + payload
    size = len(body) if prefix_size is None else prefix_size
    return struct.pack("<QII", 0x1111111111111111, size, 0x22222222) + body


def grid(nx, nz):
    return [(x, z) for z in range(nz) for x in range(nx)]


def nm_bytes(
    nx,
    nz,
    width,
    tiles=None,
    *,
    order=None,
    magic=TESM,
    version=6,
    count=None,
    origin=(0.0, 0.0, 0.0),
    depth=None,
    offsets=None,
    truncate=None,
):
    """A whole .nm; tiles maps (x, z) to tile bytes, missing ones get tile_bytes()."""
    tiles = tiles or {}
    order = grid(nx, nz) if order is None else order
    blobs = [tiles[key] if key in tiles else tile_bytes(*key, width) for key in order]
    if offsets is None:
        offsets, at = [], 0
        for blob in blobs:
            offsets.append(at)
            at += len(blob)
    count = len(offsets) if count is None else count
    depth = width if depth is None else depth
    header = struct.pack("<5I", magic, version, count, nx, nz)
    header += struct.pack("<5f", *origin, width, depth)
    header += struct.pack("<2I", count, 64)
    data = header + struct.pack(f"<{len(offsets)}I", *offsets) + b"".join(blobs)
    return data if truncate is None else data[:truncate]


def write_nm(path, *args, **kwargs):
    path.write_bytes(nm_bytes(*args, **kwargs))
    return path
