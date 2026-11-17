from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import py3d

from .manifest import VehicleManifest


class GraphError(ValueError):
    """The reachable host-to-proxy graph violates the manifest contract."""


@dataclass(frozen=True)
class ProxyNode:
    piece: str
    host_lod: float
    host_path: Path
    proxy_path: Path
    addon_relative_path: Path
    proxy_selection: str
    proxy_basename: str
    anchor: tuple[float, float, float]
    frame: tuple[tuple[float, float, float], ...]
    ambiguous: bool
    include_host_direct: bool
    allowed_animated_selections: tuple[str, ...]
    repairs: tuple[str, ...]
    allowed_fit_components: tuple[str, ...]


def _normal_coordinates(normal: Any) -> list[float]:
    coordinates = normal.coords if hasattr(normal, "coords") else normal
    return [float(value) for value in coordinates]


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _selection_memberships(lod) -> list[dict[str, object]]:
    point_indexes = {id(point): index for index, point in enumerate(lod.points)}
    face_indexes = {id(face): index for index, face in enumerate(lod.faces)}
    memberships = []
    for name, selection in sorted(lod.selections.items(), key=lambda item: item[0]):
        try:
            points = sorted(
                (point_indexes[id(point)], float(weight))
                for point, weight in selection.points.items()
            )
            faces = sorted(
                (face_indexes[id(face)], float(weight))
                for face, weight in selection.faces.items()
            )
        except KeyError as error:
            raise GraphError(f"selection {name!r} contains stale membership") from error
        memberships.append({"name": name, "points": points, "faces": faces})
    return memberships


def structural_digest(lod) -> str:
    """Hash non-geometric LOD semantics using canonical JSON."""
    faces = []
    for face in lod.faces:
        faces.append(
            {
                "flags": int(face.flags),
                "texture": face.texture,
                "material": face.material,
                "vertices": [
                    {
                        "point_index": int(vertex.point_index),
                        "normal_index": int(vertex.normal_index),
                        "uv": [float(value) for value in vertex.uv],
                    }
                    for vertex in face.vertices
                ],
            }
        )
    payload = {
        "resolution": float(lod.resolution),
        "point_count": len(lod.points),
        "point_flags": [int(point.flags) for point in lod.points],
        "facenormal_count": len(lod.facenormals),
        "faces": faces,
        "selections": _selection_memberships(lod),
    }
    return _canonical_sha256(payload)


def geometry_digest(lod) -> str:
    """Hash only point and face-normal coordinates using canonical JSON."""
    payload = {
        "points": [
            [float(value) for value in point.coords] for point in lod.points
        ],
        "facenormals": [
            _normal_coordinates(normal) for normal in lod.facenormals
        ],
    }
    return _canonical_sha256(payload)


def direct_host_points(lod) -> np.ndarray:
    lod_face_ids = {id(face) for face in lod.faces}
    proxy_face_ids = set()
    for proxy in lod.get_proxies():
        name = proxy["name"]
        selection = lod.selections.get(name)
        selected_points = tuple(selection.points) if selection is not None else ()
        selected_faces = tuple(selection.faces) if selection is not None else ()
        if len(selected_points) != 3 or len(selected_faces) != 1:
            raise GraphError(f"invalid proxy triangle for selection {name!r}")
        face = selected_faces[0]
        if id(face) not in lod_face_ids or len(face.vertices) != 3:
            raise GraphError(f"invalid proxy triangle for selection {name!r}")
        referenced_point_ids = set()
        for vertex in face.vertices:
            point_index = int(vertex.point_index)
            if point_index < 0 or point_index >= len(lod.points):
                raise GraphError(f"invalid proxy triangle for selection {name!r}")
            referenced_point_ids.add(id(lod.points[point_index]))
        if referenced_point_ids != {id(point) for point in selected_points}:
            raise GraphError(f"invalid proxy triangle for selection {name!r}")
        proxy_face_ids.add(id(face))

    point_indexes = set()
    for face in lod.faces:
        if id(face) in proxy_face_ids:
            continue
        for vertex in face.vertices:
            point_index = int(vertex.point_index)
            if point_index < 0 or point_index >= len(lod.points):
                raise GraphError("direct host face references an invalid point index")
            point_indexes.add(point_index)
    if not point_indexes:
        return np.empty((0, 3), dtype=float)
    coordinates = [lod.points[index].coords for index in sorted(point_indexes)]
    result = np.asarray(coordinates, dtype=float)
    if result.ndim != 2 or result.shape[1] != 3:
        raise GraphError("direct host points must have three coordinates")
    return result


def _proxy_basename(proxy_path: str) -> str:
    return Path(proxy_path.replace("\\", "/")).name.lower()


def _resolve_proxy_path(addon_root: Path, prefix: str, proxy_path: str) -> Path:
    parts = proxy_path.replace("/", "\\").split("\\")
    if not parts or not parts[0] or parts[0].lower() != prefix.lower():
        raise GraphError(f"proxy outside prefix {prefix}: {proxy_path}")
    relative_parts = parts[1:]
    if not relative_parts or any(part in ("", ".", "..") for part in relative_parts):
        raise GraphError(f"invalid proxy path: {proxy_path}")
    root = addon_root.resolve()
    candidate = (addon_root / Path(*relative_parts)).with_suffix(".p3d").resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise GraphError(f"proxy outside addon root: {proxy_path}") from error
    return candidate


def resolve_graph(manifest: VehicleManifest) -> tuple[ProxyNode, ...]:
    with manifest.host_p3d.open("rb") as handle:
        host = py3d.P3D(handle)

    expected: dict[
        tuple[float, str],
        list[tuple[int, int, object, object]],
    ] = {}
    cardinality: dict[tuple[int, int], int] = {}
    for piece_index, piece in enumerate(manifest.pieces):
        for variant_index, variant in enumerate(piece.variants):
            key = (variant.host_lod, variant.expected_proxy_basename)
            expected.setdefault(key, []).append(
                (piece_index, variant_index, piece, variant)
            )
            cardinality[(piece_index, variant_index)] = 0

    nodes = []
    for lod in host.lods:
        for proxy in lod.get_proxies():
            basename = _proxy_basename(proxy["path"])
            matches = expected.get((lod.resolution, basename), [])
            if not matches:
                continue
            if len(matches) != 1:
                raise GraphError(
                    f"ambiguous manifest mapping for {basename} at LOD {lod.resolution}"
                )
            piece_index, variant_index, piece, variant = matches[0]
            cardinality_key = (piece_index, variant_index)
            cardinality[cardinality_key] += 1
            if cardinality[cardinality_key] != 1:
                raise GraphError(
                    f"reachable proxy cardinality for {piece.name}/{basename} "
                    f"at LOD {lod.resolution} is greater than one"
                )
            path = _resolve_proxy_path(
                manifest.addon_root, manifest.pbo_prefix, proxy["path"]
            )
            if not path.is_file():
                raise GraphError(f"missing proxy P3D: {path}")
            try:
                addon_relative_path = path.relative_to(manifest.addon_root.resolve())
            except ValueError as error:
                raise GraphError(f"proxy outside addon root: {path}") from error
            nodes.append(
                ProxyNode(
                    piece=piece.name,
                    host_lod=float(lod.resolution),
                    host_path=manifest.host_p3d,
                    proxy_path=path,
                    addon_relative_path=addon_relative_path,
                    proxy_selection=str(proxy["name"]),
                    proxy_basename=basename,
                    anchor=tuple(float(value) for value in proxy["anchor"]),
                    frame=tuple(
                        tuple(float(value) for value in row)
                        for row in proxy["frame"]
                    ),
                    ambiguous=bool(proxy["ambiguous"]),
                    include_host_direct=piece.include_host_direct,
                    allowed_animated_selections=piece.allowed_animated_selections,
                    repairs=variant.repairs,
                    allowed_fit_components=variant.allowed_fit_components,
                )
            )

    missing = [
        f"{manifest.pieces[piece_index].name}/"
        f"{manifest.pieces[piece_index].variants[variant_index].expected_proxy_basename}"
        f"@{manifest.pieces[piece_index].variants[variant_index].host_lod}"
        for (piece_index, variant_index), count in cardinality.items()
        if count == 0
    ]
    if missing:
        raise GraphError(f"unreachable manifest proxy variants: {missing}")
    expected_count = sum(len(piece.variants) for piece in manifest.pieces)
    if len(nodes) != expected_count:
        raise GraphError(
            f"reachable manifest nodes {len(nodes)} != expected {expected_count}"
        )
    return tuple(nodes)
