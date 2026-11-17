"""P3D to glTF/GLB converter.

Reads MLOD .p3d files via the pack's py3d fork and writes a deterministic
binary glTF (.glb) or JSON .gltf. Geometry buffers are packed little-endian
with the stdlib; there is no numpy or pygltflib dependency.
"""

from __future__ import annotations

import base64
import json
import os
import struct
import sys
from pathlib import Path

from .deps import require_dayz_py3d
from .errors import ViewerError

LOD_VISUAL_0 = 0.0
LOD_VISUAL_1 = 1.0
LOD_VISUAL_2 = 4.0
LOD_VISUAL_3 = 8.0
LOD_GEOMETRY = 1.0e13
LOD_MEMORY = 1.0e15

COMPONENT_FLOAT = 5126
COMPONENT_UINT32 = 5125
TARGET_ARRAY = 34962
TARGET_ELEMENT = 34963


def classify_lod(resolution: float) -> str:
    """Classify a LOD by its resolution value.

    Known gaps (see KNOWN-ISSUES.md): resolutions in (10, 15000) — including
    ViewPilot at 1100 — are labelled ``shadow``. Proxy triangles are not
    filtered here.
    """
    if resolution < 0.5:
        return "visual_0"
    if resolution < 2.0:
        return "visual_1"
    if resolution < 6.0:
        return "visual_2"
    if resolution < 10.0:
        return "visual_3"
    if resolution < 1.5e4:
        return "shadow"
    if abs(resolution - 1.0e13) < 1e11:
        return "geometry"
    if abs(resolution - 2.0e13) < 1e11:
        return "fire_geometry"
    if abs(resolution - 3.0e13) < 1e11:
        return "view_geometry"
    if abs(resolution - 6.0e15) < 1e13:
        return "view_geometry"
    if abs(resolution - 7.0e15) < 1e13:
        return "fire_geometry"
    if resolution > 1.0e14:
        return "memory"
    return "unknown_%s" % resolution


def find_best_visual_lod(p3d_file):
    """Find the highest-detail visual LOD (lowest visual resolution)."""
    best = None
    best_res = float("inf")
    for lod in p3d_file.lods:
        lod_type = classify_lod(lod.resolution)
        if lod_type.startswith("visual") and lod.resolution < best_res:
            best = lod
            best_res = lod.resolution
    return best


def extract_lod_geometry(lod) -> dict:
    """Extract positions, normals, UVs and per-material index groups.

    Every face is exported, including proxy triangles (see KNOWN-ISSUES.md).
    """
    vertex_map = {}
    positions = []
    normals = []
    uvs = []
    material_groups = {}

    for face in lod.faces:
        tex = face.texture if face.texture else ""
        mat = face.material if face.material else ""
        key = (tex, mat)
        material_groups.setdefault(key, [])
        face_indices = []
        for vertex in face.vertices:
            pt_idx = vertex.point_index
            norm_idx = vertex.normal_index
            u, v = vertex.uv if vertex.uv else (0.0, 0.0)
            vert_key = (pt_idx, norm_idx, round(u, 6), round(v, 6))
            if vert_key not in vertex_map:
                vertex_map[vert_key] = len(positions)
                positions.append(tuple(lod.points[pt_idx].coords))
                if norm_idx < len(lod.facenormals):
                    normals.append(tuple(lod.facenormals[norm_idx]))
                else:
                    normals.append((0.0, 1.0, 0.0))
                uvs.append((u, 1.0 - v))
            face_indices.append(vertex_map[vert_key])
        if len(face_indices) == 3:
            material_groups[key].extend(face_indices)
        elif len(face_indices) == 4:
            material_groups[key].extend(
                [
                    face_indices[0],
                    face_indices[1],
                    face_indices[2],
                    face_indices[0],
                    face_indices[2],
                    face_indices[3],
                ]
            )
        elif len(face_indices) > 4:
            for index in range(1, len(face_indices) - 1):
                material_groups[key].extend(
                    [face_indices[0], face_indices[index], face_indices[index + 1]]
                )
    return {
        "positions": positions,
        "normals": normals,
        "uvs": uvs,
        "material_groups": material_groups,
    }


def _pack_f32(values) -> bytes:
    flat = []
    for item in values:
        if isinstance(item, (tuple, list)):
            flat.extend(float(part) for part in item)
        else:
            flat.append(float(item))
    return struct.pack("<%sf" % len(flat), *flat)


def _pack_u32(values) -> bytes:
    return struct.pack("<%sI" % len(values), *[int(item) for item in values])


def _pad4(blob: bytearray) -> None:
    while len(blob) % 4:
        blob.append(0)


def _min_max_vec(vectors):
    mins = [min(item[axis] for item in vectors) for axis in range(len(vectors[0]))]
    maxs = [max(item[axis] for item in vectors) for axis in range(len(vectors[0]))]
    return [float(item) for item in mins], [float(item) for item in maxs]


def _dump_json(value) -> bytes:
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return text.encode("utf-8")


def _write_glb(document: dict, bin_data: bytes, output_path: str) -> None:
    json_bytes = _dump_json(document)
    json_padding = (4 - (len(json_bytes) % 4)) % 4
    json_bytes = json_bytes + (b" " * json_padding)
    bin_padding = (4 - (len(bin_data) % 4)) % 4
    bin_bytes = bin_data + (b"\x00" * bin_padding)
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    with open(output_path, "wb") as handle:
        handle.write(struct.pack("<4sII", b"glTF", 2, total))
        handle.write(struct.pack("<I4s", len(json_bytes), b"JSON"))
        handle.write(json_bytes)
        handle.write(struct.pack("<I4s", len(bin_bytes), b"BIN\x00"))
        handle.write(bin_bytes)


def _write_gltf(document: dict, bin_data: bytes, output_path: str) -> None:
    encoded = base64.b64encode(bin_data).decode("ascii")
    document = dict(document)
    buffers = [dict(item) for item in document.get("buffers", [])]
    if buffers:
        buffers[0]["uri"] = "data:application/octet-stream;base64," + encoded
        document["buffers"] = buffers
    payload = _dump_json(document) + b"\n"
    with open(output_path, "wb") as handle:
        handle.write(payload)


def p3d_to_glb(
    p3d_path: str,
    output_path: str | None = None,
    texture_dir: str | None = None,
    texture_map: dict | None = None,
    rvmat_data: dict | None = None,
    verbose: bool = False,
) -> str:
    """Convert a .p3d (MLOD) file to .glb (binary glTF).

    Returns the path to the generated file. The same input produces the
    same bytes: no timestamps, no host paths.
    """
    py3d = require_dayz_py3d()
    if output_path is None:
        output_path = os.path.splitext(p3d_path)[0] + ".glb"
    if verbose:
        print("Reading: %s" % p3d_path)
    with open(p3d_path, "rb") as handle:
        p3d_file = py3d.P3D(handle)
    if verbose:
        print("LODs found: %s" % len(p3d_file.lods))
        for lod in p3d_file.lods:
            print(
                "  %s: %s points, %s faces"
                % (classify_lod(lod.resolution), len(lod.points), len(lod.faces))
            )
    lod = find_best_visual_lod(p3d_file)
    if lod is None:
        raise ViewerError("No visual LOD found in P3D file")
    if verbose:
        print(
            "Using LOD: resolution=%s, %s points, %s faces"
            % (lod.resolution, len(lod.points), len(lod.faces))
        )
    geo = extract_lod_geometry(lod)
    positions = geo["positions"]
    normals_list = geo["normals"]
    uvs = geo["uvs"]
    material_groups = geo["material_groups"]
    if verbose:
        print(
            "Extracted: %s vertices, %s material group(s)"
            % (len(positions), len(material_groups))
        )
        for (tex, mat), indices in material_groups.items():
            print(
                "  [%s] [%s]: %s triangles"
                % (tex or "no_tex", mat or "no_mat", len(indices) // 3)
            )
    if not positions:
        raise ViewerError("No geometry found in visual LOD")

    bin_data = bytearray()
    buffer_views = []
    accessors = []

    def add_buffer_view(data_bytes: bytes, target=None) -> int:
        _pad4(bin_data)
        offset = len(bin_data)
        bin_data.extend(data_bytes)
        view = {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(data_bytes),
        }
        if target is not None:
            view["target"] = target
        buffer_views.append(view)
        return len(buffer_views) - 1

    def add_accessor(view_index, component_type, count, acc_type, min_vals=None, max_vals=None):
        accessor = {
            "bufferView": view_index,
            "byteOffset": 0,
            "componentType": component_type,
            "count": count,
            "type": acc_type,
        }
        if min_vals is not None:
            accessor["min"] = min_vals
        if max_vals is not None:
            accessor["max"] = max_vals
        accessors.append(accessor)
        return len(accessors) - 1

    pos_min, pos_max = _min_max_vec(positions)
    pos_acc = add_accessor(
        add_buffer_view(_pack_f32(positions), TARGET_ARRAY),
        COMPONENT_FLOAT,
        len(positions),
        "VEC3",
        pos_min,
        pos_max,
    )
    norm_acc = add_accessor(
        add_buffer_view(_pack_f32(normals_list), TARGET_ARRAY),
        COMPONENT_FLOAT,
        len(normals_list),
        "VEC3",
    )
    uv_acc = add_accessor(
        add_buffer_view(_pack_f32(uvs), TARGET_ARRAY),
        COMPONENT_FLOAT,
        len(uvs),
        "VEC2",
    )

    gltf_materials = []
    gltf_textures = []
    gltf_images = []
    tex_to_material_idx = {}
    if texture_map is None:
        texture_map = {}
    if texture_dir:
        for png_file in sorted(Path(texture_dir).glob("*.png")):
            texture_map[png_file.stem.lower()] = str(png_file)

    def resolve_texture(paa_path: str):
        if not paa_path:
            return None
        normalized = paa_path.replace("\\", "/")
        basename = os.path.basename(normalized).lower()
        stem = os.path.splitext(basename)[0]
        if stem in texture_map:
            return texture_map[stem]
        for variant in (stem, stem.replace("_co", ""), stem + "_co"):
            if variant in texture_map:
                return texture_map[variant]
        return None

    def get_or_create_material(tex_path: str, mat_path: str) -> int:
        key = (tex_path, mat_path)
        if key in tex_to_material_idx:
            return tex_to_material_idx[key]
        mat_name = os.path.basename(mat_path.replace("\\", "/")) if mat_path else (
            os.path.basename(tex_path.replace("\\", "/")) if tex_path else "default"
        )
        base_color = [0.6, 0.6, 0.6, 1.0]
        metallic = 0.1
        roughness = 0.8
        emissive_factor = [0.0, 0.0, 0.0]
        is_emissive = False
        if rvmat_data and mat_path:
            mat_stem = os.path.splitext(os.path.basename(mat_path.replace("\\", "/")))[0].lower()
            rvmat = rvmat_data.get(mat_stem)
            if rvmat:
                diff = rvmat.get("colors", {}).get("diffuse")
                if diff and len(diff) >= 3:
                    base_color = [diff[0], diff[1], diff[2], 1.0]
                forced = rvmat.get("colors", {}).get("forceddiffuse")
                if forced and len(forced) >= 3 and any(value > 0.01 for value in forced[:3]):
                    base_color = [forced[0], forced[1], forced[2], 1.0]
                spec = rvmat.get("colors", {}).get("specular")
                spec_power = rvmat.get("specular_power")
                if spec and len(spec) >= 3:
                    metallic = min(1.0, sum(spec[:3]) / 3.0 * 2.0)
                if spec_power:
                    roughness = max(0.1, 1.0 - (spec_power / 100.0))
                emm = rvmat.get("colors", {}).get(
                    "emmisive", rvmat.get("colors", {}).get("emissive")
                )
                if emm and len(emm) >= 3 and any(value > 0.1 for value in emm[:3]):
                    is_emissive = True
                    max_e = max(emm[0], emm[1], emm[2], 1.0)
                    emissive_factor = [
                        min(1.0, emm[0] / max_e),
                        min(1.0, emm[1] / max_e),
                        min(1.0, emm[2] / max_e),
                    ]
                    base_color = [
                        emissive_factor[0],
                        emissive_factor[1],
                        emissive_factor[2],
                        1.0,
                    ]
                if verbose:
                    print(
                        "    RVMAT '%s': color=%s, metal=%.2f, rough=%.2f, emissive=%s"
                        % (mat_stem, base_color[:3], metallic, roughness, emissive_factor)
                    )
        material = {
            "name": mat_name,
            "pbrMetallicRoughness": {
                "baseColorFactor": [float(item) for item in base_color],
                "metallicFactor": float(metallic),
                "roughnessFactor": float(roughness),
            },
            "doubleSided": True,
        }
        if is_emissive:
            material["emissiveFactor"] = [float(item) for item in emissive_factor]
        png_path = resolve_texture(tex_path)
        if png_path and os.path.exists(png_path):
            with open(png_path, "rb") as handle:
                png_data = handle.read()
            data_uri = "data:image/png;base64," + base64.b64encode(png_data).decode("ascii")
            gltf_images.append(
                {
                    "uri": data_uri,
                    "mimeType": "image/png",
                    "name": os.path.basename(png_path),
                }
            )
            gltf_textures.append({"source": len(gltf_images) - 1})
            material["pbrMetallicRoughness"]["baseColorTexture"] = {
                "index": len(gltf_textures) - 1
            }
            material["pbrMetallicRoughness"]["baseColorFactor"] = [1.0, 1.0, 1.0, 1.0]
        gltf_materials.append(material)
        tex_to_material_idx[key] = len(gltf_materials) - 1
        return tex_to_material_idx[key]

    primitives = []
    for (tex, mat), indices in material_groups.items():
        if not indices:
            continue
        idx_min = int(min(indices))
        idx_max = int(max(indices))
        idx_acc = add_accessor(
            add_buffer_view(_pack_u32(indices), TARGET_ELEMENT),
            COMPONENT_UINT32,
            len(indices),
            "SCALAR",
            [idx_min],
            [idx_max],
        )
        primitives.append(
            {
                "attributes": {
                    "POSITION": pos_acc,
                    "NORMAL": norm_acc,
                    "TEXCOORD_0": uv_acc,
                },
                "indices": idx_acc,
                "material": get_or_create_material(tex, mat),
            }
        )

    stem = Path(p3d_path).stem
    document = {
        "asset": {"generator": "dayz-3d-viewer", "version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": stem}],
        "meshes": [{"primitives": primitives, "name": stem}],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_data)}],
    }
    if gltf_materials:
        document["materials"] = gltf_materials
    if gltf_textures:
        document["textures"] = gltf_textures
    if gltf_images:
        document["images"] = gltf_images

    if output_path.endswith(".gltf"):
        _write_gltf(document, bytes(bin_data), output_path)
    else:
        _write_glb(document, bytes(bin_data), output_path)

    if verbose:
        print("Saved: %s" % output_path)
        print("  Size: %s bytes" % os.path.getsize(output_path))
        print("  Primitives: %s" % len(primitives))
        print("  Materials: %s" % len(gltf_materials))
        print("  Textures embedded: %s" % len(gltf_images))
    return output_path


def p3d_info(p3d_path: str) -> dict:
    """Return LOD anatomy without converting."""
    py3d = require_dayz_py3d()
    with open(p3d_path, "rb") as handle:
        p3d_file = py3d.P3D(handle)
    lods_info = []
    for lod in p3d_file.lods:
        textures = set()
        materials = set()
        for face in lod.faces:
            if face.texture:
                textures.add(face.texture.replace("\\", "/"))
            if face.material:
                materials.add(face.material.replace("\\", "/"))
        selections = []
        if hasattr(lod, "selections"):
            selections = list(lod.selections.keys())
        lods_info.append(
            {
                "type": classify_lod(lod.resolution),
                "resolution": lod.resolution,
                "points": len(lod.points),
                "faces": len(lod.faces),
                "selections": selections,
                "textures": sorted(textures),
                "materials": sorted(materials),
            }
        )
    return {
        "file": Path(p3d_path).name,
        "num_lods": len(p3d_file.lods),
        "lods": lods_info,
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(
            "Usage: python -m dayz_3d_viewer p3d-to-glb <input.p3d> "
            "[output.glb] [--textures DIR] [--info] [-v]"
        )
        return 2
    verbose = "-v" in args
    info_only = "--info" in args
    positional = [item for item in args if item not in ("-v", "--info")]
    tex_dir = None
    if "--textures" in positional:
        index = positional.index("--textures")
        tex_dir = positional[index + 1]
        positional = positional[:index] + positional[index + 2 :]
    if not positional:
        print("Missing input .p3d")
        return 2
    if info_only:
        print(json.dumps(p3d_info(positional[0]), indent=2, sort_keys=True))
        return 0
    p3d_to_glb(
        positional[0],
        positional[1] if len(positional) > 1 else None,
        texture_dir=tex_dir,
        verbose=verbose,
    )
    return 0
