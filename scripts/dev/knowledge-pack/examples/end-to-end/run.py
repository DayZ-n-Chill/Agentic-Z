#!/usr/bin/env python3
"""Run steps 1-3 of the synthetic end-to-end model-tool example.

Creates a one-triangle MLOD, gates it with dayz-model-preflight, and
converts it with dayz-3d-viewer. Exits 0 only if every check matches.
Does not launch DayZ.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Agentic-Z repository root; the tools live under scripts/tools/.
REPO_ROOT = Path(__file__).resolve().parents[5]
WORK = Path(__file__).resolve().parent / "work"

for relative in (
    "scripts/tools/py3d",
    "scripts/tools/dayz-model-preflight",
    "scripts/tools/dayz-3d-viewer",
):
    value = str(REPO_ROOT / relative)
    if value not in sys.path:
        sys.path.insert(0, value)


IDENTITY = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
]


def fail(message: str) -> None:
    raise SystemExit("FAIL: %s" % message)


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def step1_py3d(work: Path) -> Path:
    import py3d

    if getattr(py3d, "IS_DAYZ_FORK", False) is not True:
        fail("py3d is not the DayZ fork")
    visual = py3d.LOD()
    visual.resolution = 0.0
    for coords in ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 4.0, 6.0)):
        point = py3d.Point()
        point.coords = coords
        visual.points.append(point)
    visual.facenormals.append((0.0, 0.0, 1.0))
    face = py3d.Face(visual.points, visual.facenormals)
    for index in (0, 1, 2):
        vertex = py3d.Vertex(visual.points, visual.facenormals)
        vertex.point_index = index
        vertex.normal_index = 0
        vertex.uv = (0.0, 0.0)
        face.vertices.append(vertex)
    visual.faces.append(face)
    selection = visual.new_selection("Component01")
    selection.points = {point: 1 for point in visual.points}
    selection.faces = {face: 1}

    memory = py3d.LOD()
    memory.resolution = 1.0e15
    memory.set_memory_point("actionPos", (0.0, 0.5, 0.0))

    model = py3d.P3D()
    model.lods.extend([visual, memory])
    target = work / "target.p3d"
    source = work / "source.p3d"
    model.save(target)
    source.write_bytes(target.read_bytes())
    if target.stat().st_size < 32:
        fail("target.p3d is too small to be an MLOD")
    return target


def step2_preflight(work: Path, target: Path) -> None:
    from dayz_model_preflight import run_preflight

    contract = {
        "schema_version": "dayz-model-preflight-v1",
        "scale": {
            "lod_index": 0,
            "expected_dimensions_m": [2.0, 4.0, 6.0],
            "tolerance_m": [0.01, 0.01, 0.01],
        },
        "bones": {
            "requirements": [{"lod_index": 0, "selections": ["Component01"]}]
        },
        "winding": {
            "source_model": "source.p3d",
            "transform": IDENTITY,
            "position_tolerance_m": 1e-5,
            "faces": [
                {
                    "source": {"lod_index": 0, "face_index": 0},
                    "target": {"lod_index": 0, "face_index": 0},
                }
            ],
        },
    }
    contract_path = work / "preflight.json"
    write_json(contract_path, contract)
    result = run_preflight(str(target), str(contract_path))
    write_json(work / "preflight-result.json", result)
    if result.get("verdict") != "PASS":
        fail("preflight verdict is %s: %s" % (result.get("verdict"), result.get("findings")))


def step3_viewer(work: Path, target: Path) -> None:
    from dayz_3d_viewer import p3d_to_glb, run_pipeline

    out = work / "viewer"
    results = run_pipeline(
        str(target),
        output_dir=str(out),
        model_name="synthetic",
        mode="embedded",
        generate_viewer=True,
    )
    if results["errors"]:
        fail("viewer pipeline errors: %s" % results["errors"])
    glb = out / "synthetic.glb"
    html = out / "synthetic_viewer.html"
    if not glb.is_file():
        # run_pipeline records the basename only; write via p3d_to_glb if needed
        p3d_to_glb(str(target), str(glb))
    if not glb.is_file() or not html.is_file():
        fail("missing glb or html: %s" % results)
    document = _parse_glb(glb)
    positions = [item for item in document["accessors"] if item["type"] == "VEC3"]
    scalars = [item for item in document["accessors"] if item["type"] == "SCALAR"]
    if positions[0]["count"] != 3 or scalars[0]["count"] != 3:
        fail("unexpected glb counts: %s" % document["accessors"])
    text = html.read_text(encoding="utf-8")
    if "const M=" not in text and "synthetic.glb" not in text:
        fail("html does not embed or link the model")
    host = str(work)
    if host in text or host.replace("\\", "/") in text:
        fail("html contains a host path")
    if "C:\\Users" in text or "C:/Users" in text:
        fail("html contains a user profile path")


def _parse_glb(path: Path) -> dict:
    import struct

    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        fail("glb header is not glTF 2")
    json_len, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        fail("glb JSON chunk missing")
    return json.loads(data[20 : 20 + json_len].decode("utf-8"))


def main() -> int:
    work = WORK
    if work.exists():
        for child in sorted(work.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
    work.mkdir(parents=True, exist_ok=True)
    target = step1_py3d(work)
    print("1. wrote %s (%s bytes)" % (target.name, target.stat().st_size))
    step2_preflight(work, target)
    print("2. preflight PASS")
    step3_viewer(work, target)
    print("3. viewer wrote synthetic.glb + synthetic_viewer.html")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
