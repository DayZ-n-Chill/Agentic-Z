"""Tests for the /dayz-clothing scripts and templates.

The math and file handling are tested with small stand-in objects, so they run
with only pytest installed. The round trip through real .p3d files runs when the
DayZ fork of py3d is importable (scripts/tools/py3d, or on the path) and skips
otherwise; the template check against vanilla skips when P:\\ is not mounted.
"""
import importlib.util
import json
import math
import re
import struct
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"


def _load(name):
    spec = importlib.util.spec_from_file_location("dayz_clothing_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


extract = _load("alignment_viewer_extract")
build = _load("alignment_viewer_build")
apply_json = _load("apply_alignment_json")
export_fbx = _load("export_clothing_fbx")


# ------------------------------------------------------------------ stand-ins

class Pt:
    def __init__(self, x, y, z):
        self.coords = (x, y, z)


class Vert:
    def __init__(self, point_index):
        self.point_index = point_index
        self.uv = (0.0, 0.0)


class Face:
    def __init__(self, indices):
        self.vertices = [Vert(i) for i in indices]


class Sel:
    def __init__(self, points):
        self.points = points


class Lod:
    def __init__(self, points, faces=(), selections=None):
        self.points = list(points)
        self.faces = list(faces)
        self.selections = selections or {}


class Model:
    def __init__(self, lods):
        self.lods = lods
        self.saved = []

    def save(self, path, verify=True):
        self.saved.append((path, verify))


def column(n):
    """n points on a vertical line at x = 1, heights 0 .. n-1."""
    return [Pt(1.0, float(i), 0.0) for i in range(n)]


# ------------------------------------------------------------------ extract

def test_mesh_arrays_fans_polygons_into_triangles():
    lod = Lod([Pt(0, 0, 0), Pt(1, 0, 0), Pt(1, 1, 0), Pt(0, 1, 0)], [Face([0, 1, 2, 3])])
    positions, indices = extract.mesh_arrays(lod)
    assert positions == [0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0]
    assert indices == [0, 1, 2, 0, 2, 3]


def test_selection_weights_ignore_case_and_read_none_as_zero():
    pts = column(3)
    lod = Lod(pts, selections={"LeftArm": Sel({pts[0]: 1, pts[1]: 0.25, pts[2]: None})})
    assert extract.selection_weights(lod, "leftarm") == [1.0, 0.25, 0.0]
    assert extract.selection_weights(lod, "rightarm") == [0.0, 0.0, 0.0]


def test_combo_region_adds_parts_and_caps_at_one():
    pts = column(3)
    lod = Lod(pts, selections={
        "pelvis": Sel({pts[0]: 0.7, pts[1]: 0.4}),
        "spine": Sel({pts[0]: 0.6, pts[2]: 0.3}),
        "leftarm": Sel({pts[2]: 1}),
    })
    names, weights = extract.region_weights(lod, ["leftarm"], {"abdomen": ["pelvis", "spine"]})
    assert names == ["leftarm", "abdomen"]
    assert weights == [[0.0, 0.0, 1.0], [1.0, 0.4, 0.3]]


def test_pivot_is_the_top_of_a_region_and_the_whole_of_a_combo():
    pts = column(10)
    everything = Sel({p: 1 for p in pts})
    lod = Lod(pts, selections={"leftarm": everything, "pelvis": everything})
    combos = {"abdomen": ["pelvis"]}
    names, weights = extract.region_weights(lod, ["leftarm", "rightarm"], combos)
    pivots = extract.region_pivots(lod, names, weights, combos)
    assert pivots["leftarm"] == [1.0, 8.5, 0.0]   # the two highest of ten points
    assert pivots["abdomen"] == [1.0, 4.5, 0.0]   # all ten
    assert "rightarm" not in pivots               # no weighted point, no pivot


def test_parse_combos():
    assert extract.parse_combos(["Abdomen=pelvis+Spine"]) == {"abdomen": ["pelvis", "spine"]}
    with pytest.raises(SystemExit):
        extract.parse_combos(["abdomen"])


def _fake_py3d(model):
    return types.SimpleNamespace(P3D=lambda f: model)


def test_extract_writes_the_data_file(tmp_path, monkeypatch, capsys):
    pts = [Pt(0, 0, 0), Pt(1, 0, 0), Pt(1, 1, 0), Pt(0, 1, 0)]
    lod = Lod(pts, [Face([0, 1, 2, 3])], {"leftarm": Sel({pts[2]: 1, pts[3]: 1})})
    monkeypatch.setattr(extract, "load_py3d", lambda: _fake_py3d(Model([lod])))
    p3d = tmp_path / "garment_m.p3d"
    p3d.write_bytes(b"MLOD")
    out = tmp_path / "work"

    assert extract.main([str(p3d), "--out", str(out), "--regions", "leftarm,rightarm", "--combo", "abdomen=pelvis+spine"]) == 0

    data = json.loads((out / "align_data.json").read_text(encoding="utf-8"))
    assert data["armor"]["regions"] == ["leftarm", "rightarm", "abdomen"]
    assert data["armor"]["indices"] == [0, 1, 2, 0, 2, 3]
    assert data["armor"]["weights"][0] == [0.0, 0.0, 1.0, 1.0]
    assert data["armor"]["pivots"] == {"leftarm": [0.5, 1.0, 0.0]}
    assert data["ghost"] == {"positions": [], "indices": []}
    assert "[WARN]  no weighted points for: rightarm, abdomen" in capsys.readouterr().out


def test_extract_refuses_a_lod_index_out_of_range(tmp_path, monkeypatch):
    monkeypatch.setattr(extract, "load_py3d", lambda: _fake_py3d(Model([Lod(column(2))])))
    p3d = tmp_path / "garment_m.p3d"
    p3d.write_bytes(b"MLOD")
    with pytest.raises(SystemExit) as exc:
        extract.main([str(p3d), "--out", str(tmp_path), "--lod", "3"])
    assert "out of range" in str(exc.value)


def test_ghost_mlod_is_read_with_py3d(tmp_path):
    ghost = tmp_path / "ghost.p3d"
    ghost.write_bytes(b"MLOD....")
    lod = Lod([Pt(0, 0, 0), Pt(1, 0, 0), Pt(0, 1, 0)], [Face([0, 1, 2])])
    positions, indices = extract.read_ghost(str(ghost), _fake_py3d(Model([lod])), None)
    assert (len(positions), indices) == (9, [0, 1, 2])


def test_ghost_odol_needs_a_backend(tmp_path, monkeypatch):
    ghost = tmp_path / "chainmail_m.p3d"
    ghost.write_bytes(b"ODOL....")
    monkeypatch.delenv("DAYZ_ODOL_BACKEND_ROOT", raising=False)
    with pytest.raises(SystemExit) as exc:
        extract.read_ghost(str(ghost), None, None)
    assert "--odol-backend" in str(exc.value)

    other = tmp_path / "notes.p3d"
    other.write_bytes(b"nope")
    with pytest.raises(SystemExit) as exc:
        extract.read_ghost(str(other), None, None)
    assert "neither an MLOD nor an ODOL" in str(exc.value)


def test_ghost_odol_is_read_through_the_backend_folder(tmp_path, monkeypatch):
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / "odol_reader.py").write_text(
        "class _V:\n"
        "    def __init__(self, x, y, z):\n"
        "        self.x, self.y, self.z = x, y, z\n"
        "class _F:\n"
        "    vertex_indices = [0, 1, 2, 3]\n"
        "class _L:\n"
        "    vertices = [_V(0, 0, 0), _V(1, 0, 0), _V(1, 1, 0), _V(0, 1, 0)]\n"
        "    faces = [_F()]\n"
        "class ODOL:\n"
        "    lods = [_L()]\n"
        "    @classmethod\n"
        "    def from_file(cls, path):\n"
        "        return cls()\n",
        encoding="utf-8",
    )
    ghost = tmp_path / "chainmail_m.p3d"
    ghost.write_bytes(b"ODOL....")
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.delitem(sys.modules, "odol_reader", raising=False)
    positions, indices = extract.read_ghost(str(ghost), None, str(backend))
    sys.modules.pop("odol_reader", None)
    assert len(positions) == 12
    assert indices == [0, 1, 2, 0, 2, 3]


# ------------------------------------------------------------------ apply: the math

# The adjustments and the points the live viewer computed for them on the armor this
# skill was first used on. They pin the three.js "XYZ" Euler convention.
ARMOR_ADJUST = {
    "leftarm":      {"pivot": [0.2067, 1.5152, 0.0092],  "rot_deg": [-8.5, -5, 12],   "offset": [-0.01, -0.025, 0]},
    "rightarm":     {"pivot": [-0.2064, 1.5154, 0.0094], "rot_deg": [-8.5, 5, -12],   "offset": [0.01, -0.025, 0]},
    "leftforearm":  {"pivot": [0.3762, 1.221, 0.0122],   "rot_deg": [-14.5, -42, -7], "offset": [0.12, -0.05, 0.08]},
    "rightforearm": {"pivot": [-0.376, 1.2213, 0.0123],  "rot_deg": [-14.5, 42, 7],   "offset": [-0.12, -0.05, 0.08]},
}
ARMOR_SAMPLES = {
    "leftarm":      {"before": [0.26471, 1.47306, -0.05007],  "after": [0.26712021231651306, 1.4534785747528076, -0.039239734411239624]},
    "rightarm":     {"before": [-0.26471, 1.47306, -0.05007], "after": [-0.26717138290405273, 1.453521728515625, -0.0391882099211216]},
    "leftforearm":  {"before": [0.47052, 1.12833, -0.13453],  "after": [0.6555596590042114, 1.057312250137329, 0.06586986780166626]},
    "rightforearm": {"before": [-0.47052, 1.12833, -0.13453], "after": [-0.6555469632148743, 1.0573089122772217, 0.06608349084854126]},
}


def test_math_matches_the_points_the_viewer_computed():
    assert apply_json.cross_check(ARMOR_ADJUST, ARMOR_SAMPLES) < apply_json.SAMPLE_TOLERANCE


def test_cross_check_sees_a_wrong_euler_order():
    wrong = {"leftforearm": dict(ARMOR_ADJUST["leftforearm"], rot_deg=[-7, -42, -14.5])}  # z and x swapped
    assert apply_json.cross_check(wrong, ARMOR_SAMPLES) >= apply_json.SAMPLE_TOLERANCE


def test_euler_matrix_is_a_rotation_and_identity_at_zero():
    assert apply_json.euler_xyz_matrix(0, 0, 0) == ((1.0, -0.0, 0.0), (0.0, 1.0, -0.0), (0.0, 0.0, 1.0))
    m = apply_json.euler_xyz_matrix(-14.5, -42, -7)
    det = (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
           - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
           + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))
    assert math.isclose(det, 1.0, abs_tol=1e-12)


def test_weight_blends_between_the_original_and_the_target():
    adj = {"pivot": [0, 0, 0], "rot_deg": [0, 0, 90], "offset": [0, 0, 0]}
    base = (1.0, 0.0, 0.0)
    full = apply_json.apply_region(base, base, 1.0, adj)
    half = apply_json.apply_region(base, base, 0.5, adj)
    assert full == pytest.approx((0.0, 1.0, 0.0), abs=1e-12)
    assert half == pytest.approx((0.5, 0.5, 0.0), abs=1e-12)


def test_a_point_in_two_regions_moves_as_it_does_in_the_viewer():
    # The page computes each region's target from the ORIGINAL position and blends the live
    # position toward it, region after region. A point weighted to two regions shows the difference.
    point = Pt(0.3, 1.3, 0.0)
    lod = Lod([point], selections={"leftarm": Sel({point: 0.6}), "leftforearm": Sel({point: 0.4})})
    adjust = {"leftarm": ARMOR_ADJUST["leftarm"], "leftforearm": ARMOR_ADJUST["leftforearm"]}
    base = point.coords

    assert apply_json.adjust_lod(lod, adjust, {}) == 1

    t1 = apply_json.region_target(base, adjust["leftarm"])
    live = tuple(base[i] + 0.6 * (t1[i] - base[i]) for i in range(3))
    t2 = apply_json.region_target(base, adjust["leftforearm"])
    live = tuple(live[i] + 0.4 * (t2[i] - live[i]) for i in range(3))
    assert point.coords == pytest.approx(live, abs=1e-12)


def test_combined_region_and_untouched_points():
    a, b, c = Pt(0, 1, 0), Pt(0, 1, 0), Pt(0, 1, 0)
    lod = Lod([a, b, c], selections={"Pelvis": Sel({a: 0.7}), "spine": Sel({a: 0.6, b: 0.5}), "neck": Sel({c: 1})})
    adjust = {"abdomen": {"pivot": [0, 0, 0], "rot_deg": [0, 0, 0], "offset": [0.1, 0, 0]}}
    assert apply_json.adjust_lod(lod, adjust, {"abdomen": ["pelvis", "spine"]}) == 2
    assert a.coords == pytest.approx((0.1, 1, 0))    # 0.7 + 0.6 capped at 1.0
    assert b.coords == pytest.approx((0.05, 1, 0))
    assert c.coords == (0, 1, 0)
    assert apply_json.weighted_centroid(lod, "abdomen", {"abdomen": ["pelvis", "spine"]}) == pytest.approx((0.125 / 1.5, 1, 0))
    assert apply_json.weighted_centroid(lod, "leftarm", {}) is None


# ------------------------------------------------------------------ apply: the files

def _apply_setup(tmp_path, monkeypatch):
    point = Pt(*ARMOR_SAMPLES["leftarm"]["before"])
    model = Model([Lod([point], selections={"leftarm": Sel({point: 1})}), Lod([])])
    monkeypatch.setattr(apply_json, "load_py3d", lambda: _fake_py3d(model))
    p3d = tmp_path / "garment_m.p3d"
    p3d.write_bytes(b"original")
    adjust = tmp_path / "adjust.json"
    adjust.write_text(json.dumps({"leftarm": ARMOR_ADJUST["leftarm"]}), encoding="utf-8")
    return point, model, p3d, adjust


def test_apply_backs_up_moves_and_saves(tmp_path, monkeypatch, capsys):
    point, model, p3d, adjust = _apply_setup(tmp_path, monkeypatch)
    samples = tmp_path / "samples.json"
    samples.write_text(json.dumps({"leftarm": ARMOR_SAMPLES["leftarm"]}), encoding="utf-8")

    assert apply_json.main(["--adjust", str(adjust), "--samples", str(samples), str(p3d)]) == 0

    backups = list((tmp_path / "_backups").iterdir())
    assert len(backups) == 1 and backups[0].read_bytes() == b"original"
    assert re.fullmatch(r"garment_m\.p3d\.bak_pre_alignment_\d{8}", backups[0].name)
    assert point.coords == pytest.approx(ARMOR_SAMPLES["leftarm"]["after"], abs=1e-4)
    assert model.saved == [(str(p3d), True)]
    out = capsys.readouterr().out
    assert "CROSS-CHECK PASS" in out
    assert "garment_m.p3d: applied to 1 points, saved and verified." in out


def test_apply_stops_before_touching_files_when_the_samples_disagree(tmp_path, monkeypatch, capsys):
    point, model, p3d, adjust = _apply_setup(tmp_path, monkeypatch)
    before = point.coords
    samples = tmp_path / "samples.json"
    samples.write_text(json.dumps({"leftarm": {"before": [0.2, 1.4, 0.0], "after": [0.9, 0.9, 0.9]}}), encoding="utf-8")

    assert apply_json.main(["--adjust", str(adjust), "--samples", str(samples), str(p3d)]) == 1

    assert point.coords == before and model.saved == []
    assert not (tmp_path / "_backups").exists()
    assert "Euler convention mismatch" in capsys.readouterr().err


def test_apply_warns_about_a_region_with_no_selection(tmp_path, monkeypatch, capsys):
    _point, _model, p3d, adjust = _apply_setup(tmp_path, monkeypatch)
    adjust.write_text(json.dumps({"rightarm": ARMOR_ADJUST["rightarm"]}), encoding="utf-8")
    assert apply_json.main(["--adjust", str(adjust), "--backup-dir", str(tmp_path / "bk"), str(p3d)]) == 0
    assert (tmp_path / "bk").is_dir()
    assert "[WARN]  rightarm: no weighted selection" in capsys.readouterr().out


# ------------------------------------------------------------------ viewer page

VIEWER_CORE_STUB = '''
VIEWER_CORE_CONTRACT = "%s"
THREE_VERSION = "%s"
def importmap_script(): return "<script type=\\"importmap\\">{}</script>"
def module_imports(three_alias="THREE"): return "import * as %%s from 'three';" %% three_alias
def boot_js(**kw): return "/*boot %%s*/" %% kw["canvas_expr"]
def resize_js(**kw): return "/*resize %%s*/" %% kw["fn"]
def loop_js(**kw): return "/*loop*/"
'''


def _stub_core(tmp_path, contract=build.VIEWER_CORE_CONTRACT, three=build.THREE_VERSION):
    path = tmp_path / "viewer_core.py"
    path.write_text(VIEWER_CORE_STUB % (contract, three), encoding="utf-8")
    return path


DATA = {"armor": {"positions": [0, 0, 0], "indices": [], "regions": ["leftarm", "abdomen"], "weights": [[1], [0]], "pivots": {"leftarm": [0, 0, 0]}},
        "ghost": {"positions": [], "indices": []}}


def test_viewer_page_is_built_in_english_with_the_data_inside(tmp_path, capsys):
    data = tmp_path / "align_data.json"
    data.write_text(json.dumps(DATA, separators=(",", ":")), encoding="utf-8")

    assert build.main(["--data", str(data), "--viewer-core", str(_stub_core(tmp_path)), "--title", "Vest <fit>"]) == 0

    page = (tmp_path / "alignment_viewer.html").read_text(encoding="utf-8")
    assert "<title>Vest &lt;fit&gt;</title>" in page
    assert "const DATA = " + json.dumps(DATA, separators=(",", ":")) + ";" in page
    assert "import * as THREE from 'three';" in page and '/*boot document.getElementById("c")*/' in page
    assert "/*resize doResize*/" in page and "/*loop*/" in page
    assert "Generate adjustments JSON" in page and "Mirror left / right adjustments" in page
    for spanish in ("Alineador", "Frente", "Espalda", "Mostrar", "Espejar", "Generar", "Copiar", "mover", "Hombro", "Antebrazo"):
        assert spanish not in page
    assert "__" not in page.replace("__proto__", "")
    assert "viewer written:" in capsys.readouterr().out


def test_viewer_core_of_another_version_is_refused(tmp_path, capsys):
    data = tmp_path / "align_data.json"
    data.write_text("{}", encoding="utf-8")
    core = _stub_core(tmp_path, three="0.1.0")
    assert build.main(["--data", str(data), "--viewer-core", str(core)]) == 2
    assert "viewer_core.py" in capsys.readouterr().err
    assert not (tmp_path / "alignment_viewer.html").exists()
    with pytest.raises(ImportError):
        build.load_viewer_core(str(tmp_path / "missing.py"))


def test_viewer_page_builds_with_the_repo_viewer_core(tmp_path):
    if not any(c.is_file() for c in build.VIEWER_CORE_CANDIDATES):
        pytest.skip("viewer_core.py is not in this checkout")
    page = build.build_html(json.dumps(DATA), "Fit", build.load_viewer_core())
    assert "three" in page and 'id="controls"' in page


# ------------------------------------------------------------------ FBX export helpers

def test_axis_map_is_its_own_inverse_and_flips_handedness():
    for c in ((1.0, 2.0, 3.0), (-0.34, 1.5, -0.045)):
        assert export_fbx.dayz_to_blender(export_fbx.dayz_to_blender(c)) == c
    x, y, z = (export_fbx.dayz_to_blender(axis) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    det = (x[0] * (y[1] * z[2] - y[2] * z[1]) - x[1] * (y[0] * z[2] - y[2] * z[0]) + x[2] * (y[0] * z[1] - y[1] * z[0]))
    assert det == -1
    # DayZ front (-Z) lands on Blender front (-Y); the anatomical left stays on +X.
    assert export_fbx.dayz_to_blender((0.3, 1.5, -0.1)) == (0.3, -0.1, 1.5)


def test_script_args_are_what_follows_the_double_dash():
    argv = ["blender", "-b", "--python", "export_clothing_fbx.py", "--", "--out", "pkg", "a_m.p3d"]
    assert export_fbx.script_args(argv) == ["--out", "pkg", "a_m.p3d"]
    assert export_fbx.script_args(["export_clothing_fbx.py", "--out", "pkg"]) == ["--out", "pkg"]
    assert len(export_fbx.DEFAULT_BONES) == 10


# ------------------------------------------------------------------ templates

def _template_bone_pairs():
    text = (TEMPLATES / "model.cfg.template").read_text(encoding="utf-8")
    block = text.split("skeletonBones[]=", 1)[1].split("};", 1)[0]
    names = re.findall(r'"([^"]*)"', block)
    return text, list(zip(names[0::2], names[1::2]))


def test_model_cfg_template_declares_the_clothing_skeleton():
    text, pairs = _template_bone_pairs()
    assert "class DayzTemporarySkeleton" in text and "isDiscrete=0;" in text
    assert "OFP2_ManSkeleton" not in text
    assert len(pairs) == 159
    assert pairs[0] == ("pelvis", "") and pairs[-1] == ("righthand_dummy", "")
    bones = [bone for bone, _ in pairs]
    assert len(set(bones)) == 159
    assert all(parent == "" or parent in bones[:i] for i, (_, parent) in enumerate(pairs)), "a parent must come before its child"
    assert text.count('skeletonName="DayzTemporarySkeleton"') == 2   # the _m and _f classes; the ground model has none
    assert "armorhneck" not in text.lower()


VANILLA_WORN = Path("P:/DZ/characters/tops/chainmail_m.p3d")


@pytest.mark.skipif(not VANILLA_WORN.is_file(), reason="P:\\ is not mounted with vanilla data")
def test_model_cfg_template_matches_the_vanilla_worn_skeleton():
    data = VANILLA_WORN.read_bytes()
    assert data[:4] == b"ODOL"
    start = data.index(b"DayzTemporarySkeleton\0") + len(b"DayzTemporarySkeleton\0")
    count = struct.unpack_from("<I", data, start + 1)[0]   # one flag byte, then the bone count
    pos = start + 5
    vanilla = []
    for _ in range(count):
        end = data.index(b"\0", pos)
        bone = data[pos:end].decode("latin1")
        pos = end + 1
        end = data.index(b"\0", pos)
        vanilla.append((bone.lower(), data[pos:end].decode("latin1").lower()))
        pos = end + 1
    assert vanilla == _template_bone_pairs()[1]


def test_artist_readme_template_is_english_with_placeholders():
    text = (TEMPLATES / "README-ARTIST.template.md").read_text(encoding="utf-8")
    assert "## Contents" in text and "## Optional improvement" in text and "## Return workflow" in text
    assert "Contenido" not in text and "Mejora" not in text
    assert "<garment>_m.fbx" in text and "DayzTemporarySkeleton" in text


# ------------------------------------------------------------------ real .p3d round trip

def _fork():
    if apply_json.PY3D_DIR.is_dir() and str(apply_json.PY3D_DIR) not in sys.path:
        sys.path.insert(0, str(apply_json.PY3D_DIR))
    py3d = pytest.importorskip("py3d")
    if not getattr(py3d, "IS_DAYZ_FORK", False):
        pytest.skip("the installed py3d is not the DayZ fork")
    return py3d


def test_extract_and_apply_on_a_real_p3d(tmp_path, capsys):
    py3d = _fork()
    lod = py3d.LOD()
    for coords in ((0.2, 1.5, 0.0), (0.4, 1.5, 0.0), (0.4, 1.2, 0.0), (0.2, 1.2, 0.0)):
        point = py3d.Point()
        point.coords = coords
        lod.points.append(point)
    lod.facenormals.append((0.0, 0.0, -1.0))
    face = py3d.Face(lod.points, lod.facenormals)
    for i in range(4):
        vertex = py3d.Vertex(lod.points, lod.facenormals)
        vertex.point_index, vertex.normal_index, vertex.uv = i, 0, (0.0, 0.0)
        face.vertices.append(vertex)
    lod.faces.append(face)
    lod.set_selection("LeftArm", point_idx=[0, 1], weight=1)
    model = py3d.P3D()
    model.lods.append(lod)
    p3d = tmp_path / "garment_m.p3d"
    model.save(str(p3d))

    assert extract.main([str(p3d), "--out", str(tmp_path), "--regions", "leftarm"]) == 0
    data = json.loads((tmp_path / "align_data.json").read_text(encoding="utf-8"))
    assert data["armor"]["regions"] == ["leftarm", "abdomen"]   # abdomen is the default combined region
    assert data["armor"]["weights"] == [[1.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]]
    assert data["armor"]["indices"] == [0, 1, 2, 0, 2, 3]

    adjust = tmp_path / "adjust.json"
    adjust.write_text(json.dumps({"leftarm": {"pivot": data["armor"]["pivots"]["leftarm"], "rot_deg": [0, 0, 0], "offset": [0.05, -0.02, 0]}}), encoding="utf-8")
    assert apply_json.main(["--adjust", str(adjust), str(p3d)]) == 0

    with open(p3d, "rb") as f:
        moved = [point.coords for point in py3d.P3D(f).lods[0].points]
    assert moved[0] == pytest.approx((0.25, 1.48, 0.0), abs=1e-6)
    assert moved[1] == pytest.approx((0.45, 1.48, 0.0), abs=1e-6)
    assert moved[2] == pytest.approx((0.4, 1.2, 0.0), abs=1e-6) and moved[3] == pytest.approx((0.2, 1.2, 0.0), abs=1e-6)
    assert len(list((tmp_path / "_backups").iterdir())) == 1
    assert "centroid X 0.300 -> 0.350" in capsys.readouterr().out
