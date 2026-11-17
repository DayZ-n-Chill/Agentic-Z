"""Synthetic MLOD and PAA builders. No game data."""

from __future__ import annotations

import struct

import py3d


def make_triangle_lod(
    points=((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 4.0, 6.0)),
    faces=((0, 1, 2),),
    selections=None,
    resolution=0.0,
    texture="",
    material="",
):
    lod = py3d.LOD()
    lod.resolution = resolution
    for coords in points:
        point = py3d.Point()
        point.coords = tuple(coords)
        lod.points.append(point)
    lod.facenormals.append((0.0, 0.0, 1.0))
    for indices in faces:
        face = py3d.Face(lod.points, lod.facenormals)
        for point_index in indices:
            vertex = py3d.Vertex(lod.points, lod.facenormals)
            vertex.point_index = point_index
            vertex.normal_index = 0
            vertex.uv = (0.0, 0.0)
            face.vertices.append(vertex)
        face.texture = texture
        face.material = material
        lod.faces.append(face)
    for name, membership in (selections or {}).items():
        selection = lod.new_selection(name)
        selection.points = {
            lod.points[index]: 1 for index in membership.get("points", ())
        }
        selection.faces = {
            lod.faces[index]: 1 for index in membership.get("faces", ())
        }
    return lod


def make_memory_lod(name="actionPos", coords=(0.0, 0.5, 0.0), resolution=1.0e15):
    lod = py3d.LOD()
    lod.resolution = resolution
    lod.set_memory_point(name, coords)
    return lod


def save_model(path, lods):
    model = py3d.P3D()
    model.lods.extend(lods)
    model.save(path)
    return path


def lzss_literals(payload: bytes) -> bytes:
    """Encode `payload` as a BI LZSS stream of only literal bytes."""
    out = bytearray()
    offset = 0
    while offset < len(payload):
        chunk = payload[offset : offset + 8]
        out.append(0xFF)
        out.extend(chunk)
        offset += 8
    return bytes(out)


def write_rgba8888_paa(path, pixels, width, height):
    """Write a 4-channel 8-bit PAA. `pixels` is a flat list of (r,g,b,a)."""
    raw = bytearray()
    for red, green, blue, alpha in pixels:
        raw.extend((red, green, blue, alpha))
    compressed = lzss_literals(bytes(raw))
    blob = bytearray()
    blob.extend(struct.pack("<H", 0x8888))
    blob.extend(struct.pack("<H", 0))
    blob.extend(struct.pack("<HH", width, height))
    size = len(compressed)
    blob.extend(bytes((size & 0xFF, (size >> 8) & 0xFF, (size >> 16) & 0xFF)))
    blob.extend(compressed)
    blob.extend(b"\x00" * 6)
    path.write_bytes(bytes(blob))
    return path


def write_dxt1_paa(path, width=4, height=4, color0=0xF800, color1=0x0000):
    """Write a single-block DXT1 PAA (no LZO). Default is solid red-ish."""
    block = struct.pack("<HH", color0, color1) + b"\x00\x00\x00\x00"
    blob = bytearray()
    blob.extend(struct.pack("<H", 0xFF01))
    blob.extend(struct.pack("<H", 0))
    blob.extend(struct.pack("<HH", width, height))
    blob.extend(bytes((8, 0, 0)))
    blob.extend(block)
    blob.extend(b"\x00" * 6)
    path.write_bytes(bytes(blob))
    return path


def parse_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", magic
    assert version == 2
    assert length == len(data)
    json_len, json_type = struct.unpack_from("<I4s", data, 12)
    assert json_type == b"JSON"
    import json

    document = json.loads(data[20 : 20 + json_len].decode("utf-8"))
    return document
