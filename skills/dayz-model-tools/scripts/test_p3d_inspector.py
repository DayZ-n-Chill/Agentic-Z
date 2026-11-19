#!/usr/bin/env python3
"""Tests for the three inspector scripts: extract, viewer and build.

Run: python -m pytest skills/dayz-model-tools/scripts/test_p3d_inspector.py. Only pytest is needed.
The round-trip tests skip when no py3d can be loaded, the auto-fix test skips
without numpy, and the real page test skips when viewer_core.py is not in the
checkout (it ships with the 3D viewer tool under scripts/tools/dayz-3d-viewer).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p3d_inspector_build as build  # noqa: E402
import p3d_inspector_extract as extract  # noqa: E402
import p3d_inspector_viewer as viewer  # noqa: E402

REPO = Path(__file__).resolve().parents[3]

FAKE_CORE = '''VIEWER_CORE_CONTRACT = "dayz-viewer-core/1"
THREE_VERSION = "{version}"
def importmap_script(): return "IMPORTMAP"
def module_imports(addons=(), three_alias="THREE"): return "IMPORTS " + three_alias
def boot_js(**kwargs): return "BOOT " + kwargs["post_controls_hook"]
def loop_js(**kwargs): return "LOOP"
'''


def _py3d_or_skip():
    try:
        return extract.load_py3d()
    except ImportError:
        pytest.skip("no py3d: scripts/tools/py3d is not in this checkout and none is installed")


def _round_trip(tmp_path, recipe, **kwargs):
    _py3d_or_skip()
    out = tmp_path / "model.p3d"
    result = build.build_p3d(recipe, str(out), **kwargs)
    return result, extract.extract_recipe(str(out))


# ---------------------------------------------------------------- extractor

@pytest.mark.parametrize("resolution, lod_type", [
    (0.0, "visual_0"),
    (1.0, "visual_1"),
    (4.0, "visual_2"),
    (8.0, "visual_3"),
    (16.0, "visual_3"),
    (999.0, "visual_3"),
    (1.0e4, "shadow"),
    (1.1e4, "shadow"),
    (1.0e13, "geometry"),
    (1.0e15, "memory"),
    (2.0e15, "landcontact"),
    (3.0e15, "roadway"),
    (4.0e15, "paths"),
    (5.0e15, "hitpoints"),
    (6.0e15, "view_geometry"),
    (7.0e15, "fire_geometry"),
])
def test_classify_lod_knows_every_dayz_resolution(resolution, lod_type):
    assert extract.classify_lod(resolution) == lod_type


def test_classify_lod_does_not_fold_the_1e15_family_into_memory():
    # The fault of an earlier version: everything over 1e14 read as "memory".
    types = {extract.classify_lod(n * 1.0e15) for n in range(1, 8)}
    assert len(types) == 7


def test_classify_lod_reports_geophys_and_arma_values_as_unknown():
    for resolution in (2.0e13, 3.0e13, 4.0e13):
        assert extract.classify_lod(resolution).startswith("unknown_")


def test_classify_lod_does_not_call_the_values_between_visual_and_shadow_a_shadow():
    # Visual is 0 to 999 and a shadow volume 10000 to 19999 (_shared/models/lods.md).
    for resolution in (1000.0, 1100.0, 9999.0, 2.0e4):
        assert extract.classify_lod(resolution).startswith("unknown_")


@pytest.mark.parametrize("selections, category", [
    (["door_axis"], "axis"),
    (["pos center"], "center"),
    (["ce_center"], "center"),
    (["actionPos"], "interaction"),
    (["box_placing_min"], "placing"),
    (["port_input"], "port"),
    (["proxy_wheel"], "proxy"),
    (["something"], "other"),
    ([], "other"),
])
def test_classify_memory_point(selections, category):
    assert extract.classify_memory_point(selections) == category


def test_demo_recipe_has_the_documented_shape():
    recipe = extract.generate_demo_recipe()
    assert set(recipe) >= {"meta", "lods", "memory_points", "axes", "bounding_box", "referenced_paths"}
    assert [lod["type"] for lod in recipe["lods"]] == ["visual_0", "geometry", "memory"]
    assert recipe["meta"]["mode"] == "demo"
    json.dumps(recipe)  # must be plain JSON


def test_load_py3d_without_fork_or_install_names_what_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(extract, "REPO_FORK", tmp_path / "py3d" / "__init__.py")
    monkeypatch.setitem(sys.modules, "py3d", None)  # makes `import py3d` raise ImportError
    with pytest.raises(ImportError, match="pip install py3d"):
        extract.load_py3d()


def test_scripts_look_for_the_fork_in_scripts_tools():
    expected = REPO / "scripts" / "tools" / "py3d" / "py3d" / "__init__.py"
    assert extract.REPO_FORK == expected
    assert build.REPO_FORK == expected


# ------------------------------------------------------------------ builder

def test_guess_density_reads_material_words_from_the_referenced_paths():
    assert build.guess_density({"referenced_paths": {"textures": ["data\\steel_co.paa"]}}) == 7800
    assert build.guess_density({"referenced_paths": {"materials": ["data\\wood.rvmat"]}}) == 600
    assert build.guess_density({}) == build.DENSITY_DEFAULT


def test_dedup_normals_shares_equal_normals():
    pool, index_map = build.dedup_normals([[0, 1, 0], [0, 1, 0], [1, 0, 0]])
    assert pool == [(0.0, 1.0, 0.0), (1.0, 0.0, 0.0)]
    assert index_map == [0, 0, 1]


def test_extractor_and_builder_agree_on_every_lod_resolution():
    for lod_type, resolution in build.LOD_RESOLUTION.items():
        if lod_type in ("shadow_close", "shadow_far"):
            continue
        assert extract.classify_lod(resolution) == lod_type
        # The builder's own classifier, used for its verbose output, has one name for all visual LODs.
        expected = "visual" if lod_type.startswith("visual") else lod_type
        assert build.classify_lod_res(resolution) == expected


def test_round_trip_keeps_lods_selections_and_properties(tmp_path):
    demo = extract.generate_demo_recipe()
    result, back = _round_trip(tmp_path, demo, auto_fix_enabled=False)

    assert result["lods_written"] == 3
    assert result["warnings"] == [] and result["fixes_applied"] == []
    assert [lod["type"] for lod in back["lods"]] == ["visual_0", "geometry", "memory"]
    for before, after in zip(demo["lods"][:2], back["lods"][:2]):
        assert after["num_points"] == before["num_points"]
        assert after["num_faces"] == before["num_faces"]
        counts = {name: (sel["vertex_count"], sel["face_count"]) for name, sel in after["selections"].items()}
        assert counts == {
            name: (sel["vertex_count"], sel["face_count"]) for name, sel in before["selections"].items()
        }
    assert back["referenced_paths"] == demo["referenced_paths"]
    # Defaults the builder adds to a Geometry LOD that has no class.
    assert back["lods"][1]["properties"] == {"autocenter": "0", "class": "house"}


def test_round_trip_keeps_memory_point_membership(tmp_path):
    # Compare membership counts, not only names (skills/_shared/models/tools-p3d-inspector-round-trip.md).
    demo = extract.generate_demo_recipe()
    _, back = _round_trip(tmp_path, demo, auto_fix_enabled=False)

    assert [(mp["index"], mp["selections"]) for mp in back["memory_points"]] == [
        (mp["index"], mp["selections"]) for mp in demo["memory_points"]
    ]
    memory_lod = back["lods"][2]
    assert memory_lod["selections"]["button_axis"]["vertex_count"] == 2
    assert all(sel["vertex_count"] >= 1 for sel in memory_lod["selections"].values())
    axis = back["axes"]["button_axis"]
    assert axis["point_indices"] == [5, 6]
    assert axis["direction"] == pytest.approx([0.0, 1.0, 0.0])
    assert axis["length"] == pytest.approx(0.015)


def test_round_trip_keeps_every_lod_at_its_own_resolution(tmp_path):
    # Fails if the builder writes each LOD at its type's usual resolution: levels 2,
    # 3 and 5 would all become 4, and both shadow volumes 10000.
    demo = extract.generate_demo_recipe()
    visual = demo["lods"][0]
    for resolution in (2.0, 3.0, 5.0, 16.0):
        demo["lods"].append(dict(visual, resolution=resolution, type=extract.classify_lod(resolution)))
    for resolution in (1.0e4, 1.1e4):
        demo["lods"].append(dict(demo["lods"][1], resolution=resolution, type="shadow"))
    _, back = _round_trip(tmp_path, demo, auto_fix_enabled=False)
    assert [(lod["type"], lod["resolution"]) for lod in back["lods"] if lod["resolution"] < 1.0e12] == [
        ("visual_0", 0.0), ("visual_2", 2.0), ("visual_2", 3.0), ("visual_2", 5.0),
        ("visual_3", 16.0), ("shadow", 1.0e4), ("shadow", 1.1e4),
    ]


def test_builder_uses_the_usual_resolution_when_the_recipe_records_none(tmp_path):
    demo = extract.generate_demo_recipe()
    for lod in demo["lods"]:
        del lod["resolution"]
    _, back = _round_trip(tmp_path, demo, auto_fix_enabled=False)
    assert [lod["type"] for lod in back["lods"]] == ["visual_0", "geometry", "memory"]


def test_round_trip_keeps_visual_selections_on_the_same_geometry(tmp_path):
    # A real visual LOD has quads and points used with more than one UV, so the
    # Recipe's entries and triangles are not the LOD's points and faces. Fails if a
    # selection's point and face indices are applied to the rebuilt arrays as they are.
    py3d = _py3d_or_skip()
    lod = py3d.LOD()
    lod.resolution = 0.0
    for coords in ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (2, 0, 0), (2, 1, 0)):
        point = py3d.Point()
        point.coords = coords
        point.flags = 0
        lod.points.append(point)
    lod.facenormals = [(0, 0, 1)]

    def add_face(point_indices, uvs):
        face = py3d.Face(lod.points, lod.facenormals)
        face.flags = 0
        face.texture = "a.paa"
        face.material = ""
        for point_index, uv in zip(point_indices, uvs):
            vertex = py3d.Vertex(lod.points, lod.facenormals)
            vertex.point_index = point_index
            vertex.normal_index = 0
            vertex.uv = uv
            face.vertices.append(vertex)
        lod.faces.append(face)

    add_face([0, 1, 2, 3], [(0, 0), (1, 0), (1, 1), (0, 1)])  # a quad
    add_face([1, 4, 5], [(0, 0), (0.5, 0), (0.5, 1)])         # point 1 again, other UV
    add_face([1, 5, 2], [(0, 0), (0.5, 1), (0, 1)])
    right = py3d.Selection(lod.points, lod.faces)
    right.points[lod.points[4]] = 1
    right.points[lod.points[5]] = 1
    right.faces[lod.faces[1]] = 1
    lod.selections["right"] = right
    model = py3d.P3D()
    model.lods.append(lod)
    source = tmp_path / "source.p3d"
    with open(source, "wb") as f:
        model.write(f)

    rebuilt = tmp_path / "rebuilt.p3d"
    build.build_p3d(extract.extract_recipe(str(source)), str(rebuilt), auto_fix_enabled=False)
    with open(rebuilt, "rb") as f:
        back = py3d.P3D(f).lods[0]
    selection = back.selections["right"]
    assert {tuple(point.coords) for point in selection.points} == {(2.0, 0.0, 0.0), (2.0, 1.0, 0.0)}
    assert [
        [tuple(back.points[vertex.point_index].coords) for vertex in face.vertices]
        for face in selection.faces
    ] == [[(1.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.0, 0.0)]]


def test_builder_ignores_the_selections_of_a_memory_lod_entry(tmp_path):
    # Known limit: membership that is only in lods[memory].selections is lost.
    demo = extract.generate_demo_recipe()
    demo["lods"][2]["selections"] = {"only_here": {"vertices": [0, 1], "faces": []}}
    _, back = _round_trip(tmp_path, demo, auto_fix_enabled=False)
    assert "only_here" not in back["lods"][2]["selections"]


def test_builder_writes_mass_on_geometry_points_and_honours_the_override(tmp_path):
    py3d = _py3d_or_skip()
    demo = extract.generate_demo_recipe()
    demo["meta"]["point_mass_default"] = 2.5
    out = tmp_path / "model.p3d"
    build.build_p3d(demo, str(out), auto_fix_enabled=False)
    with open(out, "rb") as f:
        model = py3d.P3D(f)
    by_type = {extract.classify_lod(lod.resolution): lod for lod in model.lods}
    assert {point.mass for point in by_type["geometry"].points} == {2.5}
    assert {point.mass for point in by_type["visual_0"].points} == {None}


def test_builder_writes_no_mass_on_the_fire_geometry_lod(tmp_path):
    # Mass belongs to the Geometry LOD alone; on Fire Geometry the audit reports it.
    py3d = _py3d_or_skip()
    demo = extract.generate_demo_recipe()
    demo["lods"].append(dict(demo["lods"][1], type="fire_geometry", resolution=7.0e15))
    out = tmp_path / "model.p3d"
    build.build_p3d(demo, str(out), auto_fix_enabled=False)
    with open(out, "rb") as f:
        model = py3d.P3D(f)
    by_type = {extract.classify_lod(lod.resolution): lod for lod in model.lods}
    assert {point.mass for point in by_type["fire_geometry"].points} == {None}
    assert None not in {point.mass for point in by_type["geometry"].points}


def test_builder_skips_an_unknown_lod_type_with_a_warning(tmp_path):
    demo = extract.generate_demo_recipe()
    demo["lods"].append({"type": "unknown_40000000000000", "resolution": 4.0e13})
    result, back = _round_trip(tmp_path, demo, auto_fix_enabled=False)
    assert result["warnings"] == ["skipped unknown LOD type: unknown_40000000000000"]
    assert len(back["lods"]) == 3


def test_auto_fix_reverses_every_lod_when_most_normals_oppose_the_winding(tmp_path):
    pytest.importorskip("numpy")
    # The demo's stored normals point against the winding of most of its faces.
    result, _ = _round_trip(tmp_path, extract.generate_demo_recipe(), auto_fix_enabled=True)
    assert len(result["fixes_applied"]) == 1
    assert "reversed winding on all faces" in result["fixes_applied"][0]


def test_auto_fix_checks_a_first_visual_lod_numbered_one(tmp_path):
    # Vanilla models often number their first visual LOD 1.0, not 0.0.
    pytest.importorskip("numpy")
    demo = extract.generate_demo_recipe()
    demo["lods"][0]["resolution"] = 1.0
    result, _ = _round_trip(tmp_path, demo, auto_fix_enabled=True)
    assert len(result["fixes_applied"]) == 1


def test_fanned_polygon_leaves_later_faces_their_own_normal(tmp_path):
    # A hexagon in the XZ plane, then a triangle in the YZ plane. Fails if the
    # triangle is written with a normal of the hexagon's fan.
    py3d = _py3d_or_skip()
    hexagon = [(1, 0, 0), (0.5, 0, 0.87), (-0.5, 0, 0.87), (-1, 0, 0), (-0.5, 0, -0.87), (0.5, 0, -0.87)]
    triangle = [(0, 0, 0), (0, 1, 0), (0, 0, 1)]
    demo = extract.generate_demo_recipe()
    geometry = demo["lods"][1]
    geometry["wireframe"] = {
        "positions": [list(p) for p in hexagon + triangle],
        "faces": [[0, 1, 2, 3, 4, 5], [6, 7, 8]],
    }
    geometry["selections"] = {}
    out = tmp_path / "model.p3d"
    build.build_p3d(demo, str(out), auto_fix_enabled=False)
    with open(out, "rb") as f:
        model = py3d.P3D(f)
    lod = {extract.classify_lod(lod.resolution): lod for lod in model.lods}["geometry"]
    tri = [face for face in lod.faces if {v.point_index for v in face.vertices} == {6, 7, 8}]
    assert len(tri) == 1
    stored = lod.facenormals[tri[0].vertices[0].normal_index]
    assert [round(c, 6) for c in stored] == [1.0, 0.0, 0.0]


# ------------------------------------------------------------------- viewer

def test_repo_paths_name_the_tool_copy_first():
    assert viewer.VIEWER_CORE_PATHS[0] == (
        REPO / "scripts" / "tools" / "dayz-3d-viewer" / "dayz_3d_viewer" / "viewer_core.py"
    )


def test_missing_viewer_core_names_the_paths_it_tried(tmp_path):
    missing = tmp_path / "viewer_core.py"
    with pytest.raises(ImportError, match="viewer_core.py") as caught:
        viewer.load_viewer_core((missing,))
    assert str(missing) in str(caught.value)


def test_viewer_core_with_another_three_version_is_refused(tmp_path):
    stale = tmp_path / "viewer_core.py"
    stale.write_text(FAKE_CORE.format(version="0.147.0"), encoding="utf-8")
    with pytest.raises(ImportError):
        viewer.load_viewer_core((stale,))


def test_page_embeds_the_recipe_and_fills_every_scaffold_slot(tmp_path, monkeypatch):
    core_file = tmp_path / "viewer_core.py"
    core_file.write_text(FAKE_CORE.format(version=viewer.THREE_VERSION), encoding="utf-8")
    core = viewer.load_viewer_core((core_file,))
    monkeypatch.setattr(viewer, "load_viewer_core", lambda: core)
    recipe = extract.generate_demo_recipe()
    out = tmp_path / "inspector.html"

    html = viewer.generate_inspector_html(recipe, output_path=str(out))

    assert out.read_text(encoding="utf-8") == html
    assert "<title>P3D Inspector — demo_switch.p3d</title>" in html
    assert json.dumps(recipe["memory_points"]) in html
    assert json.dumps(recipe["axes"]) in html
    for filled in ("IMPORTMAP", "IMPORTS T", "BOOT __vcFrame"):
        assert filled in html, filled
    for placeholder in ("__VC_IMPORTMAP__", "__VC_IMPORTS__", "__VC_BOOT__"):
        assert placeholder not in html, placeholder
    for label in ("Export Recipe", "Memory Pts", "Fire Geo", "LandContact", "HitPoints"):
        assert label in html, label


def test_page_with_the_real_viewer_core_pins_three(tmp_path):
    if not any(path.is_file() for path in viewer.VIEWER_CORE_PATHS):
        pytest.skip("viewer_core.py is not in this checkout (scripts/tools/dayz-3d-viewer)")
    html = viewer.generate_inspector_html(extract.generate_demo_recipe())
    assert "three@" + viewer.THREE_VERSION in html
    assert "OrbitControls" in html
    for placeholder in ("__VC_IMPORTMAP__", "__VC_IMPORTS__", "__VC_BOOT__"):
        assert placeholder not in html, placeholder


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
