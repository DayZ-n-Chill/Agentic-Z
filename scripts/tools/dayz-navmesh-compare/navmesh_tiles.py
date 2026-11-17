"""Fail-closed reader for the tile table of a DayZ navmesh (.nm) file.

Read-only, and not a general .nm decoder: it reads the file header, the offset
table and the 100-byte header of every tile, and checks each of them against
the file before it trusts it. Nothing is skipped or repaired; a file that fails
a check raises NavmeshFormatError naming the file and the check.

File header (48 bytes): magic b"TESM", version 6, tile count, tiles along x,
tiles along z (5 x uint32 LE); origin x y z, tile width, tile depth (5 x
float32 LE); 8 bytes not read. Then the offset table, one uint32 per tile,
relative to the end of the table. Each tile: a 16-byte prefix whose uint32 at
byte 8 is the size of the tile after the prefix and is checked (measured on
two Baltic 12.5 m .nm files of 966 289 tiles each, two Baltic 50 m .nm files of
60 025 tiles each, and the three vanilla navmesh.nm files of Chernarus+,
Livonia and Sakhal, 94 249, 65 536 and 94 249 tiles: 2 306 662 tiles; in all of
them that field equals the bytes from the end of the prefix to the next tile
or the end of the file). The uint64 at byte 0 and the uint32 at byte 12 are
not interpreted. Then a header laid out as Detour's dtMeshHeader (magic b"VAND", version 11,
the tile's grid x and y, which are x and z here, layer, user id, polygon
count, vertex count, seven more int fields; walkable height, radius and climb,
bmin x y z, bmax x y z, bv quantisation factor), then the tile data. Upstream
recastnavigation writes version 7 at the same place (Detour/Include/
DetourNavMesh.h, dtMeshHeader); the files measured carry 11.

A tile's hash covers its header and data, not the prefix. The layout is read
from the header and checked: count = tiles x * tiles z, origin (0, 0, 0), square
finite positive tiles, a sorted offset table inside the file, one tile per grid
cell, and horizontal bounds within 1 mm of the cell. Only one family of files was
measured (see README.md): NavmeshLayout.inside_verified_envelope says whether a
layout is that one.
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass
from pathlib import Path


TESM_MAGIC = 0x4D534554  # b"TESM" as the file's first four bytes
TESM_VERSION = 6
DNAV_MAGIC = 0x444E4156  # b"VAND" as the first four bytes of each tile header
DNAV_VERSION = 11

FILE_HEADER_BYTES = 48
TILE_PREFIX_BYTES = 16
TILE_PREFIX_SIZE_OFFSET = 8  # uint32 LE: bytes after the prefix to the next tile
TILE_HEADER_BYTES = 100  # 15 x uint32 then 10 x float32
BOUNDS_TOLERANCE_M = 0.001

# The one family of files measured: a 12 288 m world at these tile widths.
VERIFIED_WORLD_M = 12288.0
VERIFIED_TILE_WIDTHS_M = (12.5, 25.0, 50.0)


class NavmeshFormatError(ValueError):
    """A file the reader refuses; the message names the file and the failed check."""


@dataclass(frozen=True)
class NavmeshLayout:
    """The tile grid of one file, as its header gives it."""

    tiles_x: int
    tiles_z: int
    tile_m: float

    @property
    def inside_verified_envelope(self) -> bool:
        """True only for a square grid covering the measured 12 288 m world at a measured width."""
        if self.tile_m not in VERIFIED_TILE_WIDTHS_M:
            return False
        side = int(VERIFIED_WORLD_M // self.tile_m)
        return self.tiles_x == side and self.tiles_z == side

    def to_json(self) -> dict:
        return {
            "tiles_x": self.tiles_x,
            "tiles_z": self.tiles_z,
            "tile_m": self.tile_m,
            "tiles": self.tiles_x * self.tiles_z,
            "covered_x_m": self.tiles_x * self.tile_m,
            "covered_z_m": self.tiles_z * self.tile_m,
            "tesm_version": TESM_VERSION,
            "dnav_version": DNAV_VERSION,
            "inside_verified_envelope": self.inside_verified_envelope,
        }


@dataclass(frozen=True, slots=True)
class TileRecord:
    """What the comparison keeps of one tile: its place, size, hash and structure fields."""

    x: int
    z: int
    size: int  # bytes from the tile header to the next tile
    sha256: bytes  # raw digest of those bytes
    polygons: int
    vertices: int
    y_min: float
    y_max: float

    def structure(self) -> tuple[int, int, float, float]:
        """The fields a structural change is judged on."""
        return (self.polygons, self.vertices, self.y_min, self.y_max)

    def to_json(self) -> dict:
        return {
            "tile": [self.x, self.z],
            "bytes": self.size,
            "sha256": self.sha256.hex(),
            "polygons": self.polygons,
            "vertices": self.vertices,
            "y_bounds": [self.y_min, self.y_max],
        }


@dataclass(frozen=True)
class Navmesh:
    """One read file: its SHA-256, layout and tiles in grid order (index z * tiles_x + x)."""

    path: Path
    sha256: str
    layout: NavmeshLayout
    tiles: tuple[TileRecord, ...]

    def tile(self, x: int, z: int) -> TileRecord:
        if not (0 <= x < self.layout.tiles_x and 0 <= z < self.layout.tiles_z):
            raise KeyError((x, z))
        return self.tiles[z * self.layout.tiles_x + x]


def _error(path: Path, message: str) -> NavmeshFormatError:
    return NavmeshFormatError(f"{path}: {message}")


def read_navmesh(path: Path | str) -> Navmesh:
    """Read and check one .nm file. OSError if it cannot be read, NavmeshFormatError if refused."""
    path = Path(path)
    data = path.read_bytes()
    return _parse(path, data)


def _parse(path: Path, data: bytes) -> Navmesh:
    if len(data) < FILE_HEADER_BYTES:
        raise _error(path, f"{len(data)} bytes, shorter than the {FILE_HEADER_BYTES}-byte file header")
    magic, version, count, tiles_x, tiles_z = struct.unpack_from("<5I", data, 0)
    if magic != TESM_MAGIC:
        raise _error(path, f"magic {magic:#010x} is not TESM ({TESM_MAGIC:#010x})")
    if version != TESM_VERSION:
        raise _error(path, f"version {version}, expected {TESM_VERSION}")
    if tiles_x < 1 or tiles_z < 1:
        raise _error(path, f"empty tile grid {tiles_x} x {tiles_z}")
    if count != tiles_x * tiles_z:
        raise _error(path, f"tile count {count} is not {tiles_x} x {tiles_z} = {tiles_x * tiles_z}")
    origin_x, origin_y, origin_z, width, depth = struct.unpack_from("<5f", data, 20)
    if (origin_x, origin_y, origin_z) != (0.0, 0.0, 0.0):
        raise _error(path, f"origin ({origin_x}, {origin_y}, {origin_z}) is not (0, 0, 0)")
    if not (math.isfinite(width) and width > 0.0 and width == depth):
        raise _error(path, f"tile size {width} x {depth} m is not one finite positive square")

    table_end = FILE_HEADER_BYTES + 4 * count
    if len(data) < table_end:
        raise _error(path, f"offset table of {count} entries runs past the end of the file ({len(data)} bytes)")
    offsets = struct.unpack_from(f"<{count}I", data, FILE_HEADER_BYTES)
    if offsets[0] != 0:
        raise _error(path, f"first offset is {offsets[0]}, expected 0")
    for index in range(1, count):
        if offsets[index] <= offsets[index - 1]:
            raise _error(
                path,
                f"offsets are not strictly increasing at table entry {index} "
                f"({offsets[index - 1]} then {offsets[index]})",
            )

    view = memoryview(data)
    tiles: list[TileRecord | None] = [None] * count
    for index, offset in enumerate(offsets):
        start = table_end + offset
        end = table_end + offsets[index + 1] if index + 1 < count else len(data)
        if end > len(data) or start >= end:
            raise _error(path, f"table entry {index}: the tile at offset {offset} runs past the end of the file")
        if end - start >= TILE_PREFIX_BYTES:
            declared = struct.unpack_from("<I", data, start + TILE_PREFIX_SIZE_OFFSET)[0]
            if start + TILE_PREFIX_BYTES + declared != end:
                raise _error(
                    path,
                    f"table entry {index}: prefix size {declared} does not match the "
                    f"{end - start - TILE_PREFIX_BYTES} bytes to the next tile or the end of the file",
                )
        header = start + TILE_PREFIX_BYTES
        if end - header <= TILE_HEADER_BYTES:
            raise _error(
                path,
                f"table entry {index}: {end - start} bytes, no data after the {TILE_PREFIX_BYTES}-byte "
                f"prefix and the {TILE_HEADER_BYTES}-byte tile header",
            )
        ints = struct.unpack_from("<15I", data, header)
        floats = struct.unpack_from("<10f", data, header + 60)
        if ints[0] != DNAV_MAGIC:
            raise _error(path, f"table entry {index}: tile magic {ints[0]:#010x} is not DNAV ({DNAV_MAGIC:#010x})")
        if ints[1] != DNAV_VERSION:
            raise _error(path, f"table entry {index}: tile version {ints[1]}, expected {DNAV_VERSION}")
        x, z = ints[2], ints[3]
        if x >= tiles_x or z >= tiles_z:
            raise _error(path, f"table entry {index}: tile ({x}, {z}) is outside the {tiles_x} x {tiles_z} grid")
        slot = z * tiles_x + x
        if tiles[slot] is not None:
            raise _error(path, f"table entry {index}: duplicate tile ({x}, {z})")
        bounds = floats[3:9]
        if not all(math.isfinite(value) for value in bounds):
            raise _error(path, f"table entry {index}: tile ({x}, {z}) has non-finite bounds {bounds}")
        actual = (floats[3], floats[5], floats[6], floats[8])
        expected = (width * x, width * z, width * (x + 1), width * (z + 1))
        if any(abs(got - want) > BOUNDS_TOLERANCE_M for got, want in zip(actual, expected)):
            raise _error(
                path,
                f"table entry {index}: bounds x [{floats[3]}, {floats[6]}] z [{floats[5]}, {floats[8]}] "
                f"do not match tile ({x}, {z}) at {width} m",
            )
        tiles[slot] = TileRecord(
            x=x,
            z=z,
            size=end - header,
            sha256=hashlib.sha256(view[header:end]).digest(),
            polygons=ints[6],
            vertices=ints[7],
            y_min=floats[4],
            y_max=floats[7],
        )

    # count == tiles_x * tiles_z, every tile in range and none twice: every cell is filled.
    return Navmesh(
        path=path,
        sha256=hashlib.sha256(data).hexdigest(),
        layout=NavmeshLayout(tiles_x=tiles_x, tiles_z=tiles_z, tile_m=width),
        tiles=tuple(tiles),  # type: ignore[arg-type]
    )
