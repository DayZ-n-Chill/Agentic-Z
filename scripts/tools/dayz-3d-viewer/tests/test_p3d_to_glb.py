from dayz_3d_viewer import classify_lod, p3d_info, p3d_to_glb
from dayz_3d_viewer.p3d_to_gltf import extract_lod_geometry, find_best_visual_lod

from _support import (
    make_memory_lod,
    make_triangle_lod,
    parse_glb,
    save_model,
)
import py3d


def test_triangle_round_trip_has_expected_counts(tmp_path):
    model = save_model(
        tmp_path / "tri.p3d",
        [
            make_triangle_lod(selections={"Component01": {"points": [0, 1, 2], "faces": [0]}}),
            make_memory_lod(),
        ],
    )
    glb = tmp_path / "tri.glb"
    p3d_to_glb(str(model), str(glb))
    document = parse_glb(glb)
    positions = [item for item in document["accessors"] if item["type"] == "VEC3"]
    assert positions[0]["count"] == 3
    scalars = [item for item in document["accessors"] if item["type"] == "SCALAR"]
    assert scalars[0]["count"] == 3
    primitives = document["meshes"][0]["primitives"]
    assert len(primitives) == 1
    info = p3d_info(str(model))
    assert info["file"] == "tri.p3d"
    assert info["num_lods"] == 2
    assert info["lods"][0]["type"] == "visual_0"
    assert info["lods"][1]["type"] == "memory"
    assert "Component01" in info["lods"][0]["selections"]


def test_no_host_paths_in_glb(tmp_path):
    model = save_model(tmp_path / "tri.p3d", [make_triangle_lod()])
    glb = tmp_path / "tri.glb"
    p3d_to_glb(str(model), str(glb))
    payload = glb.read_bytes()
    assert str(tmp_path).encode("ascii", "ignore") not in payload
    assert b"C:\\Users" not in payload
    assert b"asset" in payload
    document = parse_glb(glb)
    assert document["asset"]["generator"] == "dayz-3d-viewer"


def test_classify_lod_res1100_is_shadow_not_visual():
    assert classify_lod(1100.0) == "shadow"
    assert not classify_lod(1100.0).startswith("visual")
    assert classify_lod(0.0) == "visual_0"


def test_proxy_faces_are_exported_as_geometry(tmp_path):
    visual = make_triangle_lod(
        points=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            (5.0, 0.0, 0.0),
            (5.1, 0.0, 0.0),
            (5.0, 0.1, 0.0),
        ),
        faces=((0, 1, 2), (3, 4, 5)),
        selections={
            "zbytek": {"points": [0, 1, 2], "faces": [0]},
            "proxy:something.001": {"points": [3, 4, 5], "faces": [1]},
        },
    )
    path = save_model(tmp_path / "proxy.p3d", [visual])
    with path.open("rb") as handle:
        model = py3d.P3D(handle)
    geo = extract_lod_geometry(find_best_visual_lod(model))
    triangle_count = sum(len(indices) // 3 for indices in geo["material_groups"].values())
    assert triangle_count == 2
    assert len(geo["positions"]) == 6
