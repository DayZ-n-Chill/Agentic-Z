from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
from typing import Mapping, Sequence

import py3d

from vehicle_proxy.manifest import load_manifest


_IDENTITY_FRAME = (
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
)


@dataclass(frozen=True)
class LoadedDigests:
    structural: str
    geometry: str
    properties: dict[str, str]


def _require_under(root: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"fixture output escapes temporary root: {path}") from error


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_verified_model(root: Path, path: Path, model: py3d.P3D) -> py3d.P3D:
    _require_under(root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    model.save(path, verify=True)
    with path.open("rb") as handle:
        reread = py3d.P3D(handle)
    errors = [finding for finding in reread.validate() if finding.severity == "ERROR"]
    if errors:
        raise AssertionError(f"fixture P3D validation failed: {errors}")
    for lod in reread.lods:
        if 0.0 <= lod.resolution < 1000.0:
            if any(point.mass is not None for point in lod.points):
                raise AssertionError("temporary visual LOD must keep point.mass=None")
    return reread


def make_triangle_lod() -> py3d.LOD:
    lod = py3d.LOD()
    lod.resolution = 0.0
    for coords in ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        point = py3d.Point()
        point.coords = coords
        point.flags = 0
        point.mass = None
        lod.points.append(point)
    lod.facenormals.append((0.0, 0.0, 1.0))
    face = py3d.Face(lod.points, lod.facenormals)
    face.flags = 0
    face.texture = "FIXTURE\\data\\triangle_co.paa"
    face.material = "FIXTURE\\data\\triangle.rvmat"
    for point_index, uv in enumerate(((0.0, 0.0), (1.0, 0.0), (0.0, 1.0))):
        vertex = py3d.Vertex(lod.points, lod.facenormals)
        vertex.point_index = point_index
        vertex.normal_index = 0
        vertex.uv = uv
        face.vertices.append(vertex)
    lod.faces.append(face)
    selection = lod.new_selection("zbytek")
    selection.points = {point: 1 for point in lod.points}
    selection.faces = {face: 1}
    return lod


def _make_proxy_model(*, autocenter: bool = False) -> py3d.P3D:
    model = py3d.P3D()
    lod = make_triangle_lod()
    if autocenter:
        lod.properties["autocenter"] = "0"
    model.lods.append(lod)
    return model


def _write_manifest(root: Path, payload: dict) -> Path:
    path = root / "manifest.json"
    _require_under(root, path)
    path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return path


def make_graph_fixture(root: Path):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    proxy_path = root / "data" / "proxy" / "body.p3d"
    _write_verified_model(root, proxy_path, _make_proxy_model())

    host = py3d.P3D()
    host_lod = make_triangle_lod()
    host_lod.add_proxy("FIXTURE\\data\\proxy\\body", index=1)
    host_lod.add_proxy("FIXTURE\\data\\proxy\\unlisted", index=2)
    host.lods.append(host_lod)
    host_path = root / "host.p3d"
    _write_verified_model(root, host_path, host)

    source_obj = root / "body.obj"
    source_obj.write_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl CORE_PAINT\nf 1 2 3\n",
        encoding="utf-8",
    )
    scene = root / "scene.gltf"
    scene.write_text("{}", encoding="utf-8")
    model_cfg = root / "model.cfg"
    model_cfg.write_text("class CfgModels {};\n", encoding="utf-8")
    cfgconvert = root / "CfgConvert.exe"
    cfgconvert.write_bytes(b"fixture")

    payload = {
        "schema_version": 1,
        "vehicle": "fixture",
        "addon_root": str(root.resolve()),
        "host_p3d": str(host_path.resolve()),
        "model_cfg": str(model_cfg.resolve()),
        "cfgconvert": str(cfgconvert.resolve()),
        "deployed_pbo": str((root / "fixture.pbo").resolve()),
        "pbo_prefix": "FIXTURE",
        "source": {
            "scene": str(scene.resolve()),
            "scene_sha256": _sha256(scene),
            "dependencies": [],
            "matrix": [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ],
        },
        "canonical_proxy_frame": [list(row) for row in _IDENTITY_FRAME],
        "required_properties": {},
        "thresholds": {
            "translation_m": 0.01,
            "rotation_deg": 0.1,
            "scale_error": 0.005,
            "p95_m": 0.05,
        },
        "pieces": [
            {
                "name": "body",
                "source_obj": str(source_obj.resolve()),
                "source_sha256": _sha256(source_obj),
                "include_host_direct": True,
                "host_direct_material_prefixes": ["CORE_"],
                "host_direct_material_exact": [],
                "allowed_animated_selections": [],
                "variants": [
                    {
                        "host_lod": 0.0,
                        "expected_proxy_basename": "body",
                        "repairs": ["set-autocenter-zero"],
                        "allowed_fit_components": [],
                    }
                ],
            }
        ],
    }
    return load_manifest(_write_manifest(root, payload))


def make_animated_proxy_host_lod() -> py3d.LOD:
    lod = py3d.LOD()
    lod.resolution = 0.0
    dash_proxy = lod.add_proxy("FIXTURE\\data\\proxy\\mb_dash", index=1)
    steering_proxy = lod.add_proxy(
        "FIXTURE\\data\\proxy\\mb_steering", index=2
    )
    for name in ("mph", "rpm", "fuel_1"):
        selection = lod.new_selection(name)
        selection.points = dict(lod.selections[dash_proxy].points)
        selection.faces = dict(lod.selections[dash_proxy].faces)
    drivewheel = lod.new_selection("drivewheel")
    drivewheel.points = dict(lod.selections[steering_proxy].points)
    drivewheel.faces = dict(lod.selections[steering_proxy].faces)
    return lod


def make_proxy_file_and_node(
    root: Path,
    repairs: Sequence[str],
    allowed_fit_components: Sequence[str] = (),
):
    from vehicle_proxy.p3d_graph import ProxyNode

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    proxy_path = root / "data" / "proxy" / "body.p3d"
    _write_verified_model(root, proxy_path, _make_proxy_model())
    node = ProxyNode(
        piece="body",
        host_lod=0.0,
        host_path=root / "host.p3d",
        proxy_path=proxy_path,
        addon_relative_path=Path("data") / "proxy" / "body.p3d",
        proxy_selection="proxy:FIXTURE\\data\\proxy\\body.001",
        proxy_basename="body",
        anchor=(0.0, 0.0, 0.0),
        frame=_IDENTITY_FRAME,
        ambiguous=False,
        include_host_direct=False,
        allowed_animated_selections=(),
        repairs=tuple(repairs),
        allowed_fit_components=tuple(allowed_fit_components),
    )
    return proxy_path, node


def load_model(path: Path) -> py3d.P3D:
    with Path(path).open("rb") as handle:
        return py3d.P3D(handle)


def load_digests(path: Path) -> LoadedDigests:
    from vehicle_proxy.p3d_graph import geometry_digest, structural_digest

    model = load_model(path)
    if len(model.lods) != 1:
        raise ValueError("load_digests fixture expects exactly one LOD")
    lod = model.lods[0]
    return LoadedDigests(
        structural=structural_digest(lod),
        geometry=geometry_digest(lod),
        properties=dict(lod.properties),
    )


def write_test_pbo(path: Path, entries: Mapping[str, bytes]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(entries.items(), key=lambda item: item[0].replace("/", "\\").lower())
    header = bytearray()
    payload = bytearray()
    for raw_name, raw_data in ordered:
        name = raw_name.replace("/", "\\")
        data = bytes(raw_data)
        encoded = name.encode("ascii")
        if not name or b"\x00" in encoded:
            raise ValueError(f"invalid PBO fixture entry name: {raw_name!r}")
        header.extend(encoded)
        header.append(0)
        header.extend(struct.pack("<5I", 0, len(data), 0, 0, len(data)))
        payload.extend(data)
    header.extend(b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0))
    path.write_bytes(bytes(header + payload))


def make_complete_cli_fixture(root: Path):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)

    proxy_path = root / "data" / "proxy" / "body.p3d"
    _write_verified_model(root, proxy_path, _make_proxy_model(autocenter=True))

    host = py3d.P3D()
    host_lod = py3d.LOD()
    host_lod.resolution = 0.0
    host_lod.add_proxy("FIXTURE\\data\\proxy\\body", index=1)
    host.lods.append(host_lod)
    host_path = root / "data" / "host.p3d"
    _write_verified_model(root, host_path, host)

    source_obj = root / "body.obj"
    source_obj.write_text(
        "v 0 0 0\nv 1 0 0\nv 0 1 0\nusemtl BODY\nf 1 2 3\n",
        encoding="utf-8",
    )
    scene = root / "scene.gltf"
    scene.write_text('{"asset":{"version":"2.0"}}', encoding="utf-8")
    dependency = root / "scene.bin"
    dependency.write_bytes(b"fixture-scene")
    model_cfg = root / "model.cfg"
    model_cfg.write_text(
        "class CfgSkeletons {};\nclass CfgModels {};\n", encoding="utf-8"
    )

    cfgconvert_python = root / "cfgconvert_shim.py"
    cfgconvert_python.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "dst = Path(args[args.index('-dst') + 1])\n"
        "dst.write_text('<CfgSkeletons></CfgSkeletons><CfgModels></CfgModels>', "
        "encoding='iso-8859-1')\n",
        encoding="utf-8",
    )
    cfgconvert = root / "CfgConvert.cmd"
    cfgconvert.write_text(
        '@echo off\r\npython "%~dp0cfgconvert_shim.py" %*\r\n', encoding="ascii"
    )

    deployed_pbo = root / "fixture.pbo"
    write_test_pbo(
        deployed_pbo,
        {
            "data\\host.p3d": host_path.read_bytes(),
            "data\\proxy\\body.p3d": proxy_path.read_bytes(),
        },
    )

    payload = {
        "schema_version": 1,
        "vehicle": "fixture",
        "addon_root": str(root.resolve()),
        "host_p3d": str(host_path.resolve()),
        "model_cfg": str(model_cfg.resolve()),
        "cfgconvert": str(cfgconvert.resolve()),
        "deployed_pbo": str(deployed_pbo.resolve()),
        "pbo_prefix": "FIXTURE",
        "source": {
            "scene": str(scene.resolve()),
            "scene_sha256": _sha256(scene),
            "dependencies": [
                {"path": str(dependency.resolve()), "sha256": _sha256(dependency)}
            ],
            "matrix": [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ],
        },
        "canonical_proxy_frame": [list(row) for row in _IDENTITY_FRAME],
        "required_properties": {"autocenter": "0"},
        "thresholds": {
            "translation_m": 0.01,
            "rotation_deg": 0.1,
            "scale_error": 0.005,
            "p95_m": 0.05,
        },
        "pieces": [
            {
                "name": "body",
                "source_obj": str(source_obj.resolve()),
                "source_sha256": _sha256(source_obj),
                "include_host_direct": False,
                "host_direct_material_prefixes": [],
                "host_direct_material_exact": [],
                "allowed_animated_selections": [],
                "variants": [
                    {
                        "host_lod": 0.0,
                        "expected_proxy_basename": "body",
                        "repairs": [],
                        "allowed_fit_components": [],
                    }
                ],
            }
        ],
    }
    manifest_path = _write_manifest(root, payload)
    load_manifest(manifest_path)
    outdir = root / "out"
    outdir.mkdir(parents=True, exist_ok=True)
    return manifest_path, outdir
