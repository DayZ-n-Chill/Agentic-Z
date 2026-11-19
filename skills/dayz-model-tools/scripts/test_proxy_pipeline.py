#!/usr/bin/env python3
"""End to end test of the batch path: proxy_extract -> proxy_canon -> proxy_apply.

Builds a small MLOD host with one ambiguous (90/45/45) proxy, runs the three
scripts on it and reads the result back.

Run: python -m pytest skills/dayz-model-tools/scripts/test_proxy_pipeline.py, or python test_proxy_pipeline.py.
Needs numpy and the DayZ py3d fork (scripts/tools/py3d); without either the module skips.
"""
import json
import sys
from pathlib import Path

import pytest

if __name__ == "__main__":  # before the skips below, so a script run reports them as skips
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))

np = pytest.importorskip("numpy")  # the CI runner installs pytest only
py3d = pytest.importorskip("py3d")
if not getattr(py3d, "IS_DAYZ_FORK", False):
    pytest.skip("the py3d that imports is not the DayZ fork (scripts/tools/py3d)", allow_module_level=True)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import proxy_apply  # noqa: E402
import proxy_canon  # noqa: E402
import proxy_extract  # noqa: E402

PROXY = "proxy:\\dz\\characters\\proxies\\vest_dz.001"
ANCHOR = (0.0, 1.2, 0.05)
LEG = 0.00136
BODY = [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.0, 1.8, 0.0)]


def _add_face(lod, indices):
    face = py3d.Face(lod.points, lod.facenormals)
    for point_index in indices:
        vertex = py3d.Vertex(lod.points, lod.facenormals)
        vertex.point_index = point_index
        vertex.normal_index = 0
        vertex.uv = (0.0, 0.0)
        face.vertices.append(vertex)
    face.texture = ""
    face.material = ""
    lod.faces.append(face)
    return face


def _host(path, proxy_face_order=(3, 4, 5)):
    """A visual LOD with one body triangle in `zbytek` and one 90/45/45 proxy, plus a Memory LOD.

    Point 3 is the proxy's right-angle corner, the anchor; `proxy_face_order` sets
    which point is face vertex 0."""
    lod = py3d.LOD()
    lod.resolution = 0.0
    proxy_points = [ANCHOR, (ANCHOR[0], ANCHOR[1], ANCHOR[2] + LEG), (ANCHOR[0] + LEG, ANCHOR[1], ANCHOR[2])]
    for coords in BODY + proxy_points:
        point = py3d.Point()
        point.coords = coords
        lod.points.append(point)
    lod.facenormals.append((0.0, 0.0, 1.0))
    body_face = _add_face(lod, (0, 1, 2))
    proxy_face = _add_face(lod, proxy_face_order)
    rest = lod.new_selection("zbytek")
    rest.points = {lod.points[i]: 1 for i in (0, 1, 2)}
    rest.faces = {body_face: 1}
    proxy = lod.new_selection(PROXY)
    proxy.points = {lod.points[i]: 1 for i in (3, 4, 5)}
    proxy.faces = {proxy_face: 1}

    memory = py3d.LOD()
    memory.resolution = 1.0e15
    memory.set_memory_point("pos center", (0.0, 0.0, 0.0))

    model = py3d.P3D()
    model.lods.extend([lod, memory])
    with open(path, "wb") as handle:
        model.write(handle)
    return path


def _read(path):
    with open(path, "rb") as handle:
        return py3d.P3D(handle)


@pytest.fixture
def aligned(tmp_path, monkeypatch):
    src = _host(tmp_path / "host.p3d")
    recipe = tmp_path / "recipe.json"
    edits = tmp_path / "edits.json"
    out = tmp_path / "host_aligned.p3d"
    before = proxy_extract.main(str(src), str(recipe))
    monkeypatch.setattr(sys, "argv", ["proxy_canon.py", str(recipe), str(edits)])
    proxy_canon.main()
    proxy_apply.apply_edits(str(src), str(edits), str(out))
    after = proxy_extract.main(str(out), str(tmp_path / "recipe_after.json"))
    return {"src": src, "out": out, "before": before, "after": after, "edits": json.loads(edits.read_text())}


def test_extract_reports_the_isosceles_proxy_as_ambiguous(aligned):
    (proxy,) = aligned["before"]["proxies"]
    assert proxy["name"] == PROXY
    assert proxy["slot"] == "Vest"
    assert proxy["ref_model"] == "\\dz\\characters\\proxies\\vest_dz"
    assert proxy["ambiguous"] is True
    assert proxy["point_indices"] == [3, 4, 5]


def test_body_mesh_in_the_recipe_leaves_the_proxy_triangle_out(aligned):
    assert aligned["before"]["body"]["faces"] == [[0, 1, 2]]


def test_canon_writes_one_edit_for_the_same_three_points(aligned):
    (edit,) = aligned["edits"]["edits"]
    assert edit["name"] == PROXY
    assert edit["point_indices"] == [3, 4, 5]
    assert len(edit["new_triangle"]) == 3


def test_applied_proxy_is_unambiguous_identity_at_the_same_anchor(aligned):
    (proxy,) = aligned["after"]["proxies"]
    assert proxy["ambiguous"] is False
    assert np.allclose(proxy["frame"], np.eye(3), atol=1e-3)  # coordinates are stored as float32
    assert np.allclose(proxy["origin"], ANCHOR, atol=1e-6)
    assert abs(proxy["angles_deg"][0] - 90) < 0.5 and abs(proxy["angles_deg"][2] - 26.57) < 0.5


def test_origin_is_the_derived_anchor_when_face_vertex_0_is_not_the_right_angle(tmp_path, monkeypatch):
    src = _host(tmp_path / "host.p3d", proxy_face_order=(4, 5, 3))
    recipe = tmp_path / "recipe.json"
    edits = tmp_path / "edits.json"
    (proxy,) = proxy_extract.main(str(src), str(recipe))["proxies"]
    assert proxy["point_indices"][0] != 3
    assert np.allclose(proxy["origin"], ANCHOR, atol=1e-6)
    monkeypatch.setattr(sys, "argv", ["proxy_canon.py", str(recipe), str(edits)])
    proxy_canon.main()
    (edit,) = json.loads(edits.read_text())["edits"]
    assert np.allclose(edit["new_triangle"][0], ANCHOR, atol=1e-6)


def test_worn_overlay_accepts_a_full_path_outside_dz(tmp_path, monkeypatch):
    """A --map value that is a full .p3d path may sit on another drive than --dz."""
    import worn_overlay

    src = _host(tmp_path / "host.p3d")
    recipe = tmp_path / "recipe.json"
    out = tmp_path / "worn.json"
    proxy_extract.main(str(src), str(recipe))
    dz = str(Path(__file__).resolve().parent)  # on Windows usually another drive than tmp_path
    monkeypatch.setattr(sys, "argv", ["worn_overlay.py", str(recipe), str(out), "--dz", dz,
                                      "--no-defaults", "--map", "Vest=%s" % src])
    worn_overlay.main()
    (proxy,) = json.loads(out.read_text())["proxies"]
    assert Path(dz, proxy["worn"]["source"]).resolve() == Path(src).resolve()
    assert proxy["worn"]["faces"]


def test_apply_changes_nothing_but_the_proxy_points(aligned):
    before, after = _read(aligned["src"]), _read(aligned["out"])
    assert len(after.lods) == len(before.lods) == 2
    lod_before, lod_after = before.lods[0], after.lods[0]
    assert [p.coords for p in lod_after.points[:3]] == [p.coords for p in lod_before.points[:3]]
    assert list(lod_after.selections) == list(lod_before.selections) == ["zbytek", PROXY]
    assert len(lod_after.faces) == len(lod_before.faces) == 2
    assert [p.coords for p in after.lods[1].points] == [p.coords for p in before.lods[1].points]
