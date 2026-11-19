"""check_dayz_winding.py against the MLODs of the inward-winding in-game test, and variants of them.

Run from the repository root:
    python -m pytest -q -p no:cacheprovider skills/dayz-model-tools/scripts/test_check_dayz_winding.py

The fixtures in winding_fixtures/ are the three MLODs of the inward-winding in-game test,
byte for byte (DayZDiag 1.29.163709: b and a solid, c inside-out; a is mirrored), plus b with its
normals negated. make_fixtures.py regenerates them with py3d >= 1.8.0. Each test ties a verdict line to the
measurement it reports - the volume sign and the agreement - so a test cannot pass on a phrase with the
sign turned.

The gate and most tests need the py3d DayZ fork (IS_DAYZ_FORK), which lives at scripts/tools/py3d in this
repo. Without it, or with only a py3d that lacks IS_DAYZ_FORK installed, those tests skip; the three that never read an
MLOD through py3d still run.
"""
import hashlib
import importlib.util
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GATE = HERE / "check_dayz_winding.py"
FIXTURES = HERE / "winding_fixtures"
REPO_PY3D = HERE.parents[2] / "scripts" / "tools" / "py3d"
PY3D_ARGS = ["--py3d", str(REPO_PY3D)] if (REPO_PY3D / "py3d" / "__init__.py").is_file() else []


def _load_fork():
    """The py3d DayZ fork, or None. The repo copy is loaded under a private module name, so it neither takes
    nor is replaced by a py3d another test file imported in the same pytest run (an installed package without IS_DAYZ_FORK)."""
    try:
        if PY3D_ARGS:
            spec = importlib.util.spec_from_file_location("_dayz_characters_py3d_fork",
                                                          REPO_PY3D / "py3d" / "__init__.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            import py3d as module
    except ImportError:
        return None
    return module if getattr(module, "IS_DAYZ_FORK", False) else None


PY3D = _load_fork()
# These never read an MLOD through py3d: a hash, the ODOL signature, and a fake py3d passed with --py3d.
RUN_WITHOUT_THE_FORK = {
    "test_fixtures_are_the_in_game_bytes",
    "test_odol_is_invalid",
    "test_a_py3d_that_is_not_the_fork_is_an_environment_error",
}


@pytest.fixture(autouse=True)
def _skip_without_the_fork(request):
    if PY3D is None and request.node.name not in RUN_WITHOUT_THE_FORK:
        pytest.skip("needs the py3d DayZ fork (scripts/tools/py3d in this repo)")

FIXTURE_SHA256 = {
    "mirror_a.p3d": "b08372a6248d826aad7557827346af030b1d448e4e0d75da3afd0a67a0c16d27",
    "mirror_b.p3d": "f1be491df6304534f2100d053e972a9792b1780e026223408f5c200b465201d7",
    "mirror_c.p3d": "ac5f0f77f6d93db93226e631ed0b02c3492c6e13d815a621bd9ed82e2b4e1da8",
    "mirror_b_normals_out.p3d": "b48a4980844dc1a0be5838fc936c11287fdfd796d0f8403cca869d64301d3c6e",
}
PROXY = "proxy:\\dz\\data\\proxies\\flag.001"

WINDING_RIGHT = ("  winding: RIGHT. 4 of 4 closed shells (48 faces) read a negative signed volume by winding, "
                 "sum -0.1086: the cross product points into the material, the inward MLOD winding order.")
WINDING_INSIDE_OUT = ("  winding: INSIDE-OUT. 4 of 4 closed shells (48 faces) read a positive signed volume by "
                      "winding, sum +0.1086: the cross product points out of the material.")
REVERSE_LOD = ("  fix 1: face.vertices.reverse() on every face of this LOD (the winding first, normals untouched; "
               "never a vertices[1]/[2] swap, which turns a quad into a crossed face).")
NEGATE_POOL = ("negate the normal pool in place: lod.facenormals[j] = (-x, -y, -z) for every j "
               "(not through Vertex.normal).")
PARTS_FIX = ("read the normals shell by shell, never a corner on its own sign: in a shell that reads cleanly, "
             "negate the normals of the faces that read against their winding and keep the rest (a pool entry "
             "that a corner you keep also uses gets a negated copy); leave any other shell as it is, for "
             "inspection (py3d README, \"Winding\", step 3).")
PY3D_COUNT_END = "the count of dayz-p3d-audit's absolute check, over every face of the LOD."
CAVITY = ("  (a closed shell meant to be seen from inside, a cavity, reads positive by design: leave it out of "
          "fix 1)")
PASS_LINE = "DAYZ WINDING/NORMAL CONVENTION: PASS"
FAIL_LINE = "DAYZ WINDING/NORMAL CONVENTION: FAIL (model defect) - do NOT ship"
INVALID_LINE = "DAYZ WINDING/NORMAL CONVENTION: INVALID (not measurable)"


def _import_py3d():
    return PY3D


def run_gate(path):
    result = subprocess.run([sys.executable, "-B", str(GATE), str(path), *PY3D_ARGS],
                            capture_output=True, text=True, encoding="utf-8")
    return result.returncode, result.stdout.splitlines(), result.stdout + result.stderr


def load(m, name):
    with open(FIXTURES / name, "rb") as stream:
        return m.P3D(stream)


def write(p3d, path):
    with open(path, "wb") as stream:
        p3d.write(stream)
    return path


def reverse_faces(lod, faces):
    for face in faces:
        face.vertices.reverse()


def negate_normals_of(lod, faces):
    """Negate the pool entries used by these faces (every entry here belongs to one quad of one box)."""
    for j in sorted({v.normal_index for face in faces for v in face.vertices}):
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])


def add_quad(m, lod, corners, normal, selection=None):
    """An open sheet: two triangles over four new points, wound so cross . normal > 0."""
    base = len(lod.points)
    for coords in corners:
        point = m.Point()
        point.coords = coords
        point.flags = 0
        lod.points.append(point)
    ni = len(lod.facenormals)
    lod.facenormals.append(normal)
    new = []
    for tri in ((0, 1, 2), (0, 2, 3)):
        face = m.Face(lod.points, lod.facenormals)
        face.flags = 0
        face.texture = ""
        face.material = ""
        for k in tri:
            vertex = m.Vertex(lod.points, lod.facenormals)
            vertex.point_index = base + k
            vertex.normal_index = ni
            face.vertices.append(vertex)
        lod.faces.append(face)
        new.append(face)
    if selection is not None:
        sel = lod.new_selection(selection)
        for face in new:
            sel.faces[face] = 1
        for point in lod.points[base:]:
            sel.points[point] = 1
    return new


# ---- the fixtures are the MLODs the game showed --------------------------------------------------------------

def test_fixtures_are_the_in_game_bytes():
    for name, digest in FIXTURE_SHA256.items():
        assert hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest() == digest, name


def test_generator_rewrites_the_fixtures(tmp_path):
    m = _import_py3d()
    if tuple(map(int, m.__version__.split("."))) < (1, 8, 0):
        pytest.skip("make_fixtures.py needs py3d >= 1.8.0 (blender_to_dayz)")
    subprocess.run([sys.executable, "-B", str(FIXTURES / "make_fixtures.py"), "--out", str(tmp_path),
                    *PY3D_ARGS], check=True, capture_output=True, text=True)
    for name in FIXTURE_SHA256:
        assert (tmp_path / name).read_bytes() == (FIXTURES / name).read_bytes(), name


# ---- the four probe states -------------------------------------------------------------------------------------

def test_rule12_export_passes():
    """b, solid in game with the F reading correctly. The previous gate failed it ("inside-out")."""
    code, lines, out = run_gate(FIXTURES / "mirror_b.p3d")
    assert code == 0, out
    assert WINDING_RIGHT in lines, out
    assert ("  normals: AGREE. 144 of 144 corner normals (100.0 %) agree with their face's winding, above 90 % in "
            "every shell.") in lines, out
    assert "fix 1:" not in out and "not scored" not in out, out
    assert PASS_LINE in lines, out


def test_mirrored_export_passes_and_the_gate_says_it_cannot_see_a_mirror():
    """a, the old det=+1 recipe: solid but mirrored in game. No winding gate can see that."""
    code, lines, out = run_gate(FIXTURES / "mirror_a.p3d")
    assert code == 0, out
    assert WINDING_RIGHT in lines, out
    assert PASS_LINE in lines, out
    assert "cannot see a mirror" in out, out


def test_inside_out_export_fails_reverse_every_face_then_negate():
    """c, inside-out in game: cross product and normals both point out of the material."""
    code, lines, out = run_gate(FIXTURES / "mirror_c.p3d")
    assert code == 1, out
    assert WINDING_INSIDE_OUT in lines, out
    assert REVERSE_LOD in lines, out
    assert CAVITY in lines, out
    assert ("  normals: DISAGREE after fix 1. 0 of 144 corner normals (0.0 %) would agree with their face's winding, "
            "below 10 % in every shell.") in lines, out
    assert "  fix 2: " + NEGATE_POOL in lines, out
    assert FAIL_LINE in lines, out


def test_outward_normals_fail_negate_the_pool_and_keep_the_faces():
    """b with its normals negated: the inward winding with the normals stored outward."""
    code, lines, out = run_gate(FIXTURES / "mirror_b_normals_out.p3d")
    assert code == 1, out
    assert WINDING_RIGHT in lines, out
    assert ("  normals: DISAGREE. 0 of 144 corner normals (0.0 %) agree with their face's winding, below 10 % in "
            "every shell: the stored normals point out of the material (the older outward-normal "
            "convention).") in lines, out
    assert ("  fix 1: " + NEGATE_POOL + " Keep every face as it is: reversing faces on this reading turns the "
            "model inside-out.") in lines, out
    assert "face.vertices.reverse()" not in out, out
    assert FAIL_LINE in lines, out


def test_faces_reversed_after_export_fail_reverse_and_keep_the_normals(tmp_path):
    """b with every face reversed afterwards: inside-out, and the normals are right once the faces are."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    reverse_faces(p3d.lods[0], p3d.lods[0].faces)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_faces_reversed.p3d"))
    assert code == 1, out
    assert WINDING_INSIDE_OUT in lines, out
    assert REVERSE_LOD in lines, out
    assert ("  normals: AGREE after fix 1. 144 of 144 corner normals (100.0 %) would agree with their face's "
            "winding, above 90 % in every shell: keep the normals.") in lines, out
    assert "fix 2:" not in out, out


def first_corner_line(lines):
    hits = [line for line in lines if line.startswith("  py3d first-corner count")]
    assert len(hits) == 1, lines
    return hits[0]


def test_the_gate_prints_the_count_py3d_reads(tmp_path):
    """The first-corner count the gate prints is py3d _pct_normal_agreement's (dayz-p3d-audit's absolute
    check): on each fixture as it is, and on c also after the reversal the gate asks for."""
    m = _import_py3d()
    for name in FIXTURE_SHA256:
        p3d = load(m, name)
        now = m._pct_normal_agreement(p3d.lods[0])
        code, lines, out = run_gate(FIXTURES / name)
        line = first_corner_line(lines)
        assert line.startswith(f"  py3d first-corner count: {round(now * 48 / 100)} of 48 faces ({now:.1f} %)"), (name, out)
        if name == "mirror_c.p3d":
            reverse_faces(p3d.lods[0], p3d.lods[0].faces)
            later = m._pct_normal_agreement(p3d.lods[0])
            assert f"as the model is, {round(later * 48 / 100)} of 48 ({later:.1f} %) after fix 1;" in line, out
        else:
            assert "after fix" not in line, (name, out)


def test_after_a_reversal_the_count_is_the_one_the_reversed_model_reads(tmp_path):
    """c with every face's first corner pointing inward and its other corners outward. Reversing
    the faces makes another corner first, so the reading after fix 1 is not the complement of the reading
    before; the gate reads the order the reversal leaves, and its count matches py3d on the reversed model."""
    m = _import_py3d()
    p3d = load(m, "mirror_c.p3d")
    lod = p3d.lods[0]
    for face in lod.faces:
        n = face.vertices[0].normal
        lod.facenormals.append((-n[0], -n[1], -n[2]))
        face.vertices[0].normal_index = len(lod.facenormals) - 1
    path = write(p3d, tmp_path / "c_first_corners_inward.p3d")
    code, lines, out = run_gate(path)
    assert code == 1, out
    assert WINDING_INSIDE_OUT in lines, out
    assert ("  normals: MIXED after fix 1. 48 of 144 corner normals (33.3 %) would agree with their face's winding; "
            "these shells do not reach 90 %:") in lines, out
    assert "keep the normals" not in out, out
    reverse_faces(lod, lod.faces)
    pct = m._pct_normal_agreement(lod)
    assert pct == 0.0
    assert first_corner_line(lines) == ("  py3d first-corner count: 0 of 48 faces (0.0 %) as the model is, 0 of 48 "
                                        "(0.0 %) after fix 1; " + PY3D_COUNT_END), out


def test_a_right_part_among_outward_normals_is_not_negated_with_the_pool(tmp_path):
    """b_normals_out with one quad's normals put back inward reads 4.2 % at the first corner. The
    pool fix would turn that quad outward; the gate lists the shells instead, and the pool fix applied anyway
    still fails."""
    m = _import_py3d()
    p3d = load(m, "mirror_b_normals_out.p3d")
    lod = p3d.lods[0]
    negate_normals_of(lod, lod.faces[0:2])
    code, lines, out = run_gate(write(p3d, tmp_path / "b_out_one_quad_in.p3d"))
    assert code == 1, out
    assert ("  normals: MIXED. 6 of 144 corner normals (4.2 %) agree with their face's winding; these shells do not "
            "reach 90 %:") in lines, out
    assert "    shell at lod.faces 0-11: 6 of 36 corners agree" in lines, out
    assert "  fix 1: " + PARTS_FIX in lines, out
    assert NEGATE_POOL not in out, out
    for j in range(len(lod.facenormals)):
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])
    code, lines, out = run_gate(write(p3d, tmp_path / "b_out_one_quad_in_pool_negated.p3d"))
    assert code == 1, out
    assert "    shell at lod.faces 0-11: 30 of 36 corners agree" in lines, out


def test_normals_wrong_only_at_corners_py3d_does_not_read(tmp_path):
    """Every face's second and third corners outward, first corners inward. py3d
    reads 100 %; the gate reads every corner."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    for face in lod.faces:
        for v in face.vertices[1:]:
            n = v.normal
            lod.facenormals.append((-n[0], -n[1], -n[2]))
            v.normal_index = len(lod.facenormals) - 1
    assert m._pct_normal_agreement(lod) == 100.0
    code, lines, out = run_gate(write(p3d, tmp_path / "b_later_corners_out.p3d"))
    assert code == 1, out
    assert ("  normals: MIXED. 48 of 144 corner normals (33.3 %) agree with their face's winding; these shells do "
            "not reach 90 %:") in lines, out
    assert first_corner_line(lines) == "  py3d first-corner count: 48 of 48 faces (100.0 %), " + PY3D_COUNT_END, out


def test_a_shell_without_first_corner_normals_is_still_read(tmp_path):
    """The stem's first corners have a zero normal and its other corners point outward."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    for face in lod.faces[12:24]:
        lod.facenormals.append((0.0, 0.0, 0.0))
        face.vertices[0].normal_index = len(lod.facenormals) - 1
        for v in face.vertices[1:]:
            n = v.normal
            lod.facenormals.append((-n[0], -n[1], -n[2]))
            v.normal_index = len(lod.facenormals) - 1
    code, lines, out = run_gate(write(p3d, tmp_path / "b_stem_zero_first_corners.p3d"))
    assert code == 1, out
    assert "    shell at lod.faces 12-23: 0 of 24 corners agree" in lines, out
    assert "  12 corners with a zero normal, not read." in lines, out


def test_a_shell_with_no_normal_at_all_is_not_measurable(tmp_path):
    """Every normal of the stem is zero, so none of its corners has a sign. The
    other shells agree; the stem cannot pass on their votes."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    lod.facenormals.append((0.0, 0.0, 0.0))
    for face in lod.faces[12:24]:
        for v in face.vertices:
            v.normal_index = len(lod.facenormals) - 1
    code, lines, out = run_gate(write(p3d, tmp_path / "b_stem_no_normals.p3d"))
    assert code == 2, out
    assert "  normals: no corner with a clear sign in 12 faces of 1 shell: not measurable there." in lines, out
    assert "  36 corners with a zero normal, not read." in lines, out
    assert INVALID_LINE in lines, out


def own_normal(lod, vertex, normal):
    """Give one corner its own pool entry, so changing it touches no other corner."""
    lod.facenormals.append(tuple(float(c) for c in normal))
    vertex.normal_index = len(lod.facenormals) - 1


def test_the_pool_fix_says_what_else_it_turns(tmp_path):
    """One corner of b_normals_out put back inward by hand. Every shell stays below 10 %, so
    the gate gives the pool fix, and says it also turns that corner; applied anyway, the corner ends against
    its face and the model passes: the 90 % per shell is a tolerance, which the healthy smooth-shaded
    giant infected build needs (219 corners against their face)."""
    m = _import_py3d()
    p3d = load(m, "mirror_b_normals_out.p3d")
    lod = p3d.lods[0]
    corner = lod.faces[0].vertices[0]
    n = corner.normal
    own_normal(lod, corner, (-n[0], -n[1], -n[2]))
    code, lines, out = run_gate(write(p3d, tmp_path / "b_out_one_corner_in.p3d"))
    assert code == 1, out
    assert ("  normals: DISAGREE. 1 of 144 corner normals (0.7 %) agree with their face's winding, below 10 % in "
            "every shell: the stored normals point out of the material (the older outward-normal "
            "convention).") in lines, out
    assert ("It also turns 1 corner that agrees now: right for an export that stored every normal the other way, "
            "whose odd corners go back to how they were authored (the giant infected inward-winding build has 219 against "
            "their face); to keep them, read the shells part by part instead, never a corner on its own sign "
            "(py3d README, \"Winding\", step 3).") in out, out
    assert "negate only the corners" not in out, out
    for j in range(len(lod.facenormals)):
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])
    code, lines, out = run_gate(write(p3d, tmp_path / "b_out_one_corner_in_pool_negated.p3d"))
    assert code == 0, out
    assert ("  normals: AGREE. 143 of 144 corner normals (99.3 %) agree with their face's winding, above 90 % in "
            "every shell.") in lines, out


def test_the_tolerance_is_ninety_percent_per_shell(tmp_path):
    """One corner of the plate against its face (35 of 36) passes; four (32 of 36) do not."""
    m = _import_py3d()
    for count, code_expected in ((1, 0), (4, 1)):
        p3d = load(m, "mirror_b.p3d")
        lod = p3d.lods[0]
        for face in lod.faces[0:count]:
            n = face.vertices[0].normal
            own_normal(lod, face.vertices[0], (-n[0], -n[1], -n[2]))
        code, lines, out = run_gate(write(p3d, tmp_path / ("b_plate_%d_corners_out.p3d" % count)))
        assert code == code_expected, (count, out)
        if count == 4:
            assert "    shell at lod.faces 0-11: 32 of 36 corners agree" in lines, out


def test_no_pool_fix_when_part_of_the_lod_is_not_read(tmp_path):
    """b_normals_out with one plate face turned: the plate is incoherent and not read, so the pool fix would
    reach normals this reading never saw."""
    m = _import_py3d()
    p3d = load(m, "mirror_b_normals_out.p3d")
    lod = p3d.lods[0]
    reverse_faces(lod, lod.faces[0:1])
    code, lines, out = run_gate(write(p3d, tmp_path / "b_out_plate_incoherent.p3d"))
    assert code == 1, out
    assert ("  fix 2: " + PARTS_FIX + " Not the whole pool: part of this LOD is not read.") in lines, out
    assert NEGATE_POOL not in out, out


def dart_prism(m, start):
    """A closed prism whose two caps are planar dart quads (reflex corner at (x, z) = (1, 1)), every face wound
    with its vector area into the material and every corner normal along it: an inward-winding model. *start* rotates
    the cap's corner list, which moves the reflex corner to a different index."""
    dart = [(0.0, 0.0), (2.0, 1.0), (0.0, 4.0), (1.0, 1.0)]
    dart = dart[start:] + dart[:start]
    p3d = m.P3D()
    lod = m.LOD()
    lod.resolution = 0.0
    for y in (0.0, 1.0):
        for x, z in dart:
            point = m.Point()
            point.coords = (x, y, z)
            point.flags = 0
            lod.points.append(point)

    def area(idx):
        pts = [lod.points[i].coords for i in idx]
        s = [0.0, 0.0, 0.0]
        for k in range(1, len(pts) - 1):
            a = [pts[k][i] - pts[0][i] for i in range(3)]
            b = [pts[k + 1][i] - pts[0][i] for i in range(3)]
            c = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
            s = [s[i] + c[i] for i in range(3)]
        return s

    bottom = [0, 1, 2, 3] if area([0, 1, 2, 3])[1] < 0 else [3, 2, 1, 0]   # outward on the bottom is -y
    faces = [bottom] + [[bottom[(k + 1) % 4], bottom[k], bottom[k] + 4, bottom[(k + 1) % 4] + 4] for k in range(4)]
    faces.append([i + 4 for i in bottom[::-1]])
    for idx in (f[::-1] for f in faces):                                     # outward -> inward (inward winding)
        a = area(idx)
        length = sum(c * c for c in a) ** 0.5
        lod.facenormals.append(tuple(c / length for c in a))
        face = m.Face(lod.points, lod.facenormals)
        face.flags, face.texture, face.material = 0, "", ""
        for i in idx:
            vertex = m.Vertex(lod.points, lod.facenormals)
            vertex.point_index = i
            vertex.normal_index = len(lod.facenormals) - 1
            face.vertices.append(vertex)
        lod.faces.append(face)
    p3d.lods.append(lod)
    return p3d


def test_a_non_convex_quad_is_read_by_its_vector_area(tmp_path):
    """In a dart quad the first three corners can point against the face. The prism is right
    in every rotation of its caps; with the reflex corner at index 1 of a cap, py3d's first-corner count
    reads that cap as disagreeing, and the gate does not."""
    m = _import_py3d()
    against = 0
    for start in range(4):
        p3d = dart_prism(m, start)
        if m._pct_normal_agreement(p3d.lods[0]) < 100.0:
            against += 1
        code, lines, out = run_gate(write(p3d, tmp_path / ("dart_%d.p3d" % start)))
        assert code == 0, (start, out)
        assert ("  normals: AGREE. 24 of 24 corner normals (100.0 %) agree with their face's winding, above 90 % in "
                "every shell.") in lines, (start, out)
    assert against == 2
    p3d = dart_prism(m, 1)
    lod = p3d.lods[0]
    for j in range(len(lod.facenormals)):
        n = lod.facenormals[j]
        lod.facenormals[j] = (-n[0], -n[1], -n[2])
    code, lines, out = run_gate(write(p3d, tmp_path / "dart_1_normals_out.p3d"))
    assert code == 1, out
    assert any(line.startswith("  normals: DISAGREE. 0 of 24 corner normals (0.0 %)") for line in lines), out


def test_a_corner_normal_in_its_face_plane_has_no_sign(tmp_path):
    """A corner normal lying in its face's plane, tipped by +-1e-8, is read the same both ways:
    no clear sign, not a vote, so it neither fails the model nor gets flipped."""
    m = _import_py3d()
    for tip in (-1e-8, 0.0, 1e-8):
        p3d = load(m, "mirror_b.p3d")
        lod = p3d.lods[0]
        face = lod.faces[0]
        n = face.vertices[0].normal                       # the face's own unit normal (axis-aligned box)
        in_plane = (n[1], n[2], n[0])                     # an axis-aligned vector at 90 degrees to it
        own_normal(lod, face.vertices[0], tuple(in_plane[i] + tip * n[i] for i in range(3)))
        code, lines, out = run_gate(write(p3d, tmp_path / ("b_corner_in_plane_%g.p3d" % tip)))
        assert code == 0, (tip, out)
        assert ("  1 corner normal within 5 degrees of the face plane: no clear sign, not read (inspect them if "
                "their shading matters).") in lines, (tip, out)


def test_the_printed_py3d_count_covers_every_face(tmp_path):
    """The py3d count the gate prints is py3d's over the whole LOD, proxies and incoherent
    shells included, even though the gate's own reading leaves them out."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    add_quad(m, p3d.lods[0], [(0.0, 2.0, 0.0), (0.1, 2.0, 0.0), (0.1, 2.2, 0.0), (0.0, 2.2, 0.0)],
             (0.0, 0.0, -1.0), selection=PROXY)
    path = write(p3d, tmp_path / "b_plus_disagreeing_proxy.p3d")
    with open(path, "rb") as stream:
        pct = m._pct_normal_agreement(m.P3D(stream).lods[0])
    code, lines, out = run_gate(path)
    assert first_corner_line(lines) == ("  py3d first-corner count: 48 of 50 faces (%.1f %%), " % pct) + PY3D_COUNT_END, out
    p3d = load(m, "mirror_b.p3d")
    reverse_faces(p3d.lods[0], p3d.lods[0].faces[0:1])
    pct = m._pct_normal_agreement(p3d.lods[0])
    code, lines, out = run_gate(write(p3d, tmp_path / "b_one_face_turned_count.p3d"))
    assert first_corner_line(lines) == ("  py3d first-corner count: 47 of 48 faces (%.1f %%), " % pct) + PY3D_COUNT_END, out


def add_box(m, lod, lo, hi):
    """A closed box wound OUTWARD with outward normals: cross product and normals out of the material, the
    inside-out state."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    base = len(lod.points)
    for coords in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]:
        point = m.Point()
        point.coords = coords
        point.flags = 0
        lod.points.append(point)
    for quad, normal in (((0, 3, 2, 1), (0, 0, -1)), ((4, 5, 6, 7), (0, 0, 1)), ((0, 1, 5, 4), (0, -1, 0)),
                         ((2, 3, 7, 6), (0, 1, 0)), ((3, 0, 4, 7), (-1, 0, 0)), ((1, 2, 6, 5), (1, 0, 0))):
        lod.facenormals.append(tuple(float(c) for c in normal))
        for tri in ((0, 1, 2), (0, 2, 3)):
            face = m.Face(lod.points, lod.facenormals)
            face.flags, face.texture, face.material = 0, "", ""
            for k in tri:
                vertex = m.Vertex(lod.points, lod.facenormals)
                vertex.point_index = base + quad[k]
                vertex.normal_index = len(lod.facenormals) - 1
                face.vertices.append(vertex)
            lod.faces.append(face)


def test_a_thin_closed_part_is_read_not_called_flat(tmp_path):
    """A closed part of 1 x 0.05 x 30 mm, inside-out, was called flat at a 0.1 mm cut-off and
    passed. Twins welded at 5 decimals stay under 2e-5 m; this part is not flat, and it fails."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    add_box(m, p3d.lods[0], (1.0, 0.0, 0.0), (1.001, 0.00005, 0.03))
    code, lines, out = run_gate(write(p3d, tmp_path / "b_plus_thin_part.p3d"))
    assert code == 1, out
    assert any(line.startswith("    shell at lod.faces 48-59: 12 faces, volume +1.5e-09") for line in lines), out
    assert "not scored" not in out, out


def test_a_py3d_that_is_not_the_fork_is_an_environment_error(tmp_path):
    """No IS_DAYZ_FORK, or an unreadable __version__, exits 2 instead of raising."""
    for body in ("", "IS_DAYZ_FORK = True\n__version__ = 'not-a-version'\n"):
        root = tmp_path / ("fake%d" % len(body))
        (root / "py3d").mkdir(parents=True)
        (root / "py3d" / "__init__.py").write_text(body, encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(GATE), str(FIXTURES / "mirror_b.p3d"), "--py3d", str(root)],
                                capture_output=True, text=True, encoding="utf-8")
        assert result.returncode == 2, result.stdout + result.stderr
        assert result.stdout.startswith("invalid environment:"), result.stdout + result.stderr


# ---- per closed shell, never the sum over the LOD ------------------------------------------------------------------

def test_one_inverted_box_is_named_and_the_lod_sum_does_not_hide_it(tmp_path):
    """The stem box (lod.faces 12-23) turned, faces and normals: the LOD sum stays negative (-0.0822)."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    stem = lod.faces[12:24]
    reverse_faces(lod, stem)
    negate_normals_of(lod, stem)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_stem_inverted.p3d"))
    assert code == 1, out
    assert ("  winding: INSIDE-OUT. 1 of 4 closed shells (12 faces) read a positive signed volume by winding, "
            "sum +0.0132; the other 3 (36 faces) read negative, sum -0.0954. The sum over all of them, -0.0822, "
            "hides it.") in lines, out
    assert any(line.startswith("    shell at lod.faces 12-23: 12 faces, volume +0.0132") for line in lines), out
    assert ("  fix 1: face.vertices.reverse() on every face of the listed shells, and only those (the winding "
            "first, normals untouched): the other shells are right, and reversing the whole LOD would move the "
            "inversion onto them.") in lines, out
    assert ("  normals: MIXED after fix 1. 108 of 144 corner normals (75.0 %) would agree with their face's "
            "winding; these shells do not reach 90 %:") in lines, out
    assert "    shell at lod.faces 12-23: 0 of 36 corners would agree" in lines, out
    assert "  fix 2: " + PARTS_FIX in lines, out


def test_a_face_turned_against_its_neighbours_is_made_coherent_before_any_volume(tmp_path):
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    reverse_faces(lod, lod.faces[0:1])
    code, lines, out = run_gate(write(p3d, tmp_path / "b_one_face_turned.p3d"))
    assert code == 1, out
    assert ("  winding: INCOHERENT. 1 closed shell has faces wound against their neighbours, so its volume is "
            "not read:") in lines, out
    assert ("    shell at lod.faces 0-11: 12 faces, 3 edges run the same way by both of their faces; orientation "
            "groups of 11 and 1 faces") in lines, out
    assert any(line.startswith("  fix 1: make each listed shell coherent") for line in lines), out
    assert FAIL_LINE in lines, out


def test_most_boxes_inverted_the_lod_sum_would_turn_the_right_one(tmp_path):
    """c with its stem box put right: the sum over the shells is positive, and reversing by it is wrong."""
    m = _import_py3d()
    p3d = load(m, "mirror_c.p3d")
    lod = p3d.lods[0]
    reverse_faces(lod, lod.faces[12:24])
    negate_normals_of(lod, lod.faces[12:24])
    code, lines, out = run_gate(write(p3d, tmp_path / "c_stem_right.p3d"))
    assert code == 1, out
    assert ("  winding: INSIDE-OUT. 3 of 4 closed shells (36 faces) read a positive signed volume by winding, "
            "sum +0.0954; the other 1 (12 faces) read negative, sum -0.0132. The sum over all of them, +0.0822, "
            "would turn the right ones too.") in lines, out
    assert "    shell at lod.faces 12-23" not in out, out


def test_one_part_with_outward_normals_is_listed_without_any_reversal(tmp_path):
    """b with the stem's normals negated only: winding right everywhere, one part to negate."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    negate_normals_of(lod, lod.faces[12:24])
    code, lines, out = run_gate(write(p3d, tmp_path / "b_stem_normals_out.p3d"))
    assert code == 1, out
    assert WINDING_RIGHT in lines, out
    assert ("  normals: MIXED. 108 of 144 corner normals (75.0 %) agree with their face's winding; these shells do "
            "not reach 90 %:") in lines, out
    assert "    shell at lod.faces 12-23: 0 of 36 corners agree" in lines, out
    assert "  fix 1: " + PARTS_FIX in lines, out
    assert "face.vertices.reverse()" not in out, out


def add_tetra(m, lod, centre, size):
    """A closed tetrahedron wound inward (negative volume) with its normals stored OUTWARD: 4 faces that
    all disagree with their winding."""
    cx, cy, cz = centre
    base = len(lod.points)
    for dx, dy, dz in ((0, 0, 0), (size, 0, 0), (0, size, 0), (0, 0, size)):
        point = m.Point()
        point.coords = (cx + dx, cy + dy, cz + dz)
        point.flags = 0
        lod.points.append(point)
    # each triple's cross product points into the tetrahedron ((0,1,2): +z on its z=cz face); each normal out
    for tri, normal in (((0, 1, 2), (0.0, 0.0, -1.0)), ((0, 3, 1), (0.0, -1.0, 0.0)),
                        ((0, 2, 3), (-1.0, 0.0, 0.0)), ((1, 3, 2), (0.577, 0.577, 0.577))):
        lod.facenormals.append(normal)
        face = m.Face(lod.points, lod.facenormals)
        face.flags, face.texture, face.material = 0, "", ""
        for k in tri:
            vertex = m.Vertex(lod.points, lod.facenormals)
            vertex.point_index = base + k
            vertex.normal_index = len(lod.facenormals) - 1
            face.vertices.append(vertex)
        lod.faces.append(face)


def test_a_small_part_with_outward_normals_fails_under_an_agreeing_lod(tmp_path):
    """48 of 52 faces agree (92.3 %, above 90 %), but one closed part has every normal against its faces."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    add_tetra(m, p3d.lods[0], (1.0, 0.0, 1.0), 0.1)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_plus_tetra_normals_out.p3d"))
    assert code == 1, out
    assert ("  winding: RIGHT. 5 of 5 closed shells (52 faces) read a negative signed volume by winding, "
            "sum -0.1088: the cross product points into the material, the inward MLOD winding order.") in lines, out
    assert ("  normals: MIXED. 144 of 156 corner normals (92.3 %) agree with their face's winding; these shells "
            "do not reach 90 %:") in lines, out
    assert "    shell at lod.faces 48-51: 0 of 12 corners agree" in lines, out


def test_inside_out_with_proxies_reverses_everything_but_the_proxies(tmp_path):
    m = _import_py3d()
    p3d = load(m, "mirror_c.p3d")
    lod = p3d.lods[0]
    add_quad(m, lod, [(0.0, 2.0, 0.0), (0.1, 2.0, 0.0), (0.1, 2.2, 0.0), (0.0, 2.2, 0.0)], (0.0, 0.0, 1.0),
             selection=PROXY)
    code, lines, out = run_gate(write(p3d, tmp_path / "c_plus_proxy.p3d"))
    assert code == 1, out
    assert WINDING_INSIDE_OUT in lines, out
    assert ("  fix 1: face.vertices.reverse() on every face of this LOD except its proxy:* triangles (the winding "
            "first, normals untouched; never a vertices[1]/[2] swap, which turns a quad into a crossed "
            "face).") in lines, out


def test_inside_out_with_open_parts_says_what_it_cannot_check(tmp_path):
    m = _import_py3d()
    p3d = load(m, "mirror_c.p3d")
    add_quad(m, p3d.lods[0], [(-0.5, 0.2, 0.2), (0.5, 0.2, 0.2), (0.5, 1.2, 0.2), (-0.5, 1.2, 0.2)],
             (0.0, 0.0, 1.0))
    code, lines, out = run_gate(write(p3d, tmp_path / "c_plus_open_sheet.p3d"))
    assert code == 1, out
    assert WINDING_INSIDE_OUT in lines, out
    assert ("  fix 1: face.vertices.reverse() on every face of these closed shells (the winding first, normals "
            "untouched). The faces not scored below are not covered: check them with the visibility battery "
            "before turning any of them.") in lines, out
    assert "same export call" not in out, out
    assert any(line.startswith("  not scored: 2 of 50 faces (4.0 %) in 1 open shell;") for line in lines), out


def test_a_non_orientable_shell_is_named(tmp_path):
    """The five-triangle Moebius band: every inner edge run the same way, and no grouping fixes it."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    base = len(lod.points)
    for k in range(5):
        point = m.Point()
        angle = 2 * 3.141592653589793 * k / 5
        point.coords = (2.0 + 0.5 * __import__("math").cos(angle), 0.1 * k, 0.5 * __import__("math").sin(angle))
        point.flags = 0
        lod.points.append(point)
    lod.facenormals.append((0.0, 1.0, 0.0))
    for k in range(5):
        face = m.Face(lod.points, lod.facenormals)
        face.flags, face.texture, face.material = 0, "", ""
        for j in (k, (k + 1) % 5, (k + 2) % 5):
            vertex = m.Vertex(lod.points, lod.facenormals)
            vertex.point_index = base + j
            vertex.normal_index = len(lod.facenormals) - 1
            face.vertices.append(vertex)
        lod.faces.append(face)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_plus_moebius.p3d"))
    assert code == 1, out
    assert "  winding: INCOHERENT. 1 shell has faces wound against their neighbours, so its volume is not read:" \
        in lines, out
    shell = [line for line in lines if line.startswith("    shell at lod.faces 48-52: 5 faces, 5 edges")]
    assert len(shell) == 1 and "(an open shell)" in shell[0] and "not orientable" in shell[0], out
    assert WINDING_RIGHT in lines, out


# ---- what the volume cannot score ----------------------------------------------------------------------------------

def test_open_parts_are_reported_not_scored(tmp_path):
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    # an open sheet behind the plate, cross product and normal toward +z
    add_quad(m, lod, [(-0.5, 0.2, 0.2), (0.5, 0.2, 0.2), (0.5, 1.2, 0.2), (-0.5, 1.2, 0.2)], (0.0, 0.0, 1.0))
    code, lines, out = run_gate(write(p3d, tmp_path / "b_plus_open_sheet.p3d"))
    assert code == 0, out
    assert WINDING_RIGHT in lines, out
    assert ("  not scored: 2 of 50 faces (4.0 %) in 1 open shell; no volume sign decides an open or flat part: "
            "check them with the visibility battery (dayz-p3d-audit references/winding-diagnostics.md, "
            "\"From Check B to fix\").") in lines, out
    assert PASS_LINE in lines, out
    assert ("  The winding of 2 of 50 faces (4.0 %), in open or flat parts, was not scored: this PASS covers the "
            "closed shells' winding only.") in lines, out


def test_only_open_parts_are_not_measurable(tmp_path):
    m = _import_py3d()
    p3d = m.P3D()
    lod = m.LOD()
    lod.resolution = 0.0
    add_quad(m, lod, [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 1.0, 0.0), (-0.5, 1.0, 0.0)], (0.0, 0.0, 1.0))
    p3d.lods.append(lod)
    code, lines, out = run_gate(write(p3d, tmp_path / "open_sheet.p3d"))
    assert code == 2, out
    assert ("  winding: UNSCORED. No closed shell to read: the volume sign means nothing on an open or flat "
            "part.") in lines, out
    assert INVALID_LINE in lines, out


def test_open_parts_whose_normals_disagree_fail_without_a_side(tmp_path):
    m = _import_py3d()
    p3d = m.P3D()
    lod = m.LOD()
    lod.resolution = 0.0
    faces = add_quad(m, lod, [(-0.5, 0.0, 0.0), (0.5, 0.0, 0.0), (0.5, 1.0, 0.0), (-0.5, 1.0, 0.0)],
                     (0.0, 0.0, 1.0))
    negate_normals_of(lod, faces)
    p3d.lods.append(lod)
    code, lines, out = run_gate(write(p3d, tmp_path / "open_sheet_disagrees.p3d"))
    assert code == 1, out
    assert ("  normals: DISAGREE. 0 of 6 corner normals (0.0 %) agree with their face's winding; with no closed "
            "shell this gate cannot say which of the two is wrong.") in lines, out
    assert "fix 1:" not in out, out


def test_no_normal_to_read_is_not_measurable(tmp_path):
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    for j in range(len(lod.facenormals)):
        lod.facenormals[j] = (0.0, 0.0, 0.0)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_zero_normals.p3d"))
    assert code == 2, out
    assert WINDING_RIGHT in lines, out
    assert "  normals: UNSCORED. No corner normal has a clear sign against its face." in lines, out
    assert "  144 corners with a zero normal, not read." in lines, out
    assert INVALID_LINE in lines, out


def test_welded_twins_are_flat_and_not_scored(tmp_path):
    """A face and its reversed twin on the same points close a shell of zero volume: no sign. The quad's
    diagonal is shared by four faces, so each triangle closes a shell with its own twin: two shells."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    front = add_quad(m, lod, [(-0.5, 0.2, 0.2), (0.5, 0.2, 0.2), (0.5, 1.2, 0.2), (-0.5, 1.2, 0.2)],
                     (0.0, 0.0, 1.0))
    for face in front:
        twin = m.Face(lod.points, lod.facenormals)
        twin.flags, twin.texture, twin.material = 0, "", ""
        lod.facenormals.append((0.0, 0.0, -1.0))
        for v in reversed(face.vertices):
            vertex = m.Vertex(lod.points, lod.facenormals)
            vertex.point_index = v.point_index
            vertex.normal_index = len(lod.facenormals) - 1
            twin.vertices.append(vertex)
        lod.faces.append(twin)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_plus_twins.p3d"))
    assert code == 0, out
    assert WINDING_RIGHT in lines, out
    assert ("  not scored: 4 of 52 faces (7.7 %) in 2 flat closed shells; no volume sign decides an open or "
            "flat part: check them with the visibility battery (dayz-p3d-audit "
            "references/winding-diagnostics.md, \"From Check B to fix\").") in lines, out


def test_proxy_triangles_stay_out(tmp_path):
    """A proxy triangle's vertex order encodes its frame: it is neither scored nor voted."""
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    lod = p3d.lods[0]
    add_quad(m, lod, [(0.0, 2.0, 0.0), (0.1, 2.0, 0.0), (0.1, 2.2, 0.0), (0.0, 2.2, 0.0)], (0.0, 0.0, -1.0),
             selection=PROXY)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_plus_proxy.p3d"))
    assert code == 0, out
    assert "[PASS] LOD 0 res=0.0: 48 faces, 2 proxy faces left out" in lines, out
    assert WINDING_RIGHT in lines, out


# ---- LODs, inputs, exit codes --------------------------------------------------------------------------------------

def test_every_visual_lod_is_read_and_collision_lods_are_not(tmp_path):
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    for resolution, name in ((20.0, "mirror_c.p3d"), (1e13, "mirror_c.p3d")):
        extra = load(m, name).lods[0]
        extra.resolution = resolution
        p3d.lods.append(extra)
    code, lines, out = run_gate(write(p3d, tmp_path / "b_with_c_lods.p3d"))
    assert code == 1, out
    assert any(line.startswith("[PASS] LOD 0 res=0.0:") for line in lines), out
    assert any(line.startswith("[FAIL] LOD 1 res=20.0:") for line in lines), out
    assert not any(line.startswith("[") and " LOD 2 " in line for line in lines), out


def test_odol_is_invalid(tmp_path):
    path = tmp_path / "odol.p3d"
    path.write_bytes(b"ODOL" + bytes(64))
    code, lines, out = run_gate(path)
    assert code == 2, out
    assert "this file is ODOL" in out, out


def test_truncated_mlod_is_invalid(tmp_path):
    path = tmp_path / "truncated.p3d"
    path.write_bytes((FIXTURES / "mirror_b.p3d").read_bytes()[:200])
    code, lines, out = run_gate(path)
    assert code == 2, out
    assert out.startswith("invalid input:"), out


def test_no_visual_lod_is_invalid(tmp_path):
    m = _import_py3d()
    p3d = load(m, "mirror_b.p3d")
    p3d.lods[0].resolution = 1e13
    code, lines, out = run_gate(write(p3d, tmp_path / "geometry_only.p3d"))
    assert code == 2, out
    assert "no visual LOD" in out, out
