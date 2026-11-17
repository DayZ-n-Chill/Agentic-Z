"""Needle triangles in the collision components: check_collision_needle_triangles in audit_p3d.py.

No test needs an installed py3d. Most run the check on stand-in LODs that carry the
attributes it reads from py3d's classes: LOD.resolution, .points, .faces and .selections,
Point.coords, Face.vertices, Vertex.point, and Selection.faces and .points. The Wiring test
runs main() on a 16-byte file (the MLOD signature audit_p3d() checks, then twelve zero bytes)
with load_py3d() returning a stand-in whose P3D() gives the model. The SerializedModels tests
load the DayZ fork of py3d from scripts/tools/py3d by its file path, write MLODs with it, read
them back and run main() or the check on them; they skip where that folder is missing.

The hulls are closed and convex, wound outward as Qhull's simplices come (the check reads no
winding; the written models reverse them to the MLOD's inward winding): a box 0.5 m wide and
0.25 m high, 1 m long unless a test says otherwise; the box with a point just outside the
middle of its top front edge, whose top face is triangulated with a needle (the shape a
Qhull hull produced in the measured project); and the box with one corner cut by a 1 mm face.
"""
import contextlib
import importlib.util
import io
import math
import re
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent / "audit_p3d.py"
REPO_PY3D = Path(__file__).resolve().parents[3] / "scripts" / "tools" / "py3d" / "py3d" / "__init__.py"
PEN = r"dz\data\data\penetration\wood_desk.rvmat"


def _load_audit():
    spec = importlib.util.spec_from_file_location("dayz_audit_p3d_needles", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = _load_audit()

L, W, H = 1.0, 0.5, 0.25


def box(length=L):
    return [(0, 0, 0), (length, 0, 0), (length, W, 0), (0, W, 0),
            (0, 0, H), (length, 0, H), (length, W, H), (0, W, H)]


BOX = box()
BOX_TRIANGLES = [(0, 2, 1), (0, 3, 2), (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3),
                 (1, 2, 6), (1, 6, 5), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4)]
BOX_QUADS = [(0, 3, 2, 1), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5), (4, 5, 6, 7), (0, 1, 5, 4)]
NEEDLE_TRIANGLES = [(0, 2, 1), (0, 3, 2), (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3),
                    (4, 8, 5), (4, 5, 6), (4, 6, 7), (1, 2, 6), (1, 6, 5),
                    (0, 1, 8), (0, 8, 4), (1, 5, 8)]
NEEDLE_FACE = 6
CHAMFER_FACE = 13
# The measured needle, area 3e-8 m^2 and ratio 4.6e-7: on an edge sqrt(3e-8 / 4.6e-7) = 0.2554 m
# long, at 2 * 3e-8 / 0.2554 = 2.35e-7 m from it.
MEASURED_LENGTH = math.sqrt(3e-8 / 4.6e-7)
MEASURED_OFFSET = 2 * 3e-8 / MEASURED_LENGTH
# The finding on needle_box(2e-5) as Component01 of a Geometry LOD of its own.
NEEDLE_HEAD = ("LOD[0] Geometry, Component01, face 6: needle triangle (points 4, 8, 5), area "
               "1.00e-05 m^2, area/longest edge^2 1.00e-05 (this check fails a triangle under "
               "1e-06 m^2 or 1e-04).")


def needle_box(offset, length=L):
    """The box `length` long and point 8 at `offset` outside the middle of its top front edge
    (4-5), in the plane of the top face. That face is triangulated with the needle (4, 8, 5) at
    position NEEDLE_FACE: its longest edge is 4-5, so its area is offset * length / 2 and its
    ratio offset / (2 * length), both offset / 2 when the box is 1 m long."""
    return box(length) + [(length / 2, -offset, H)], list(NEEDLE_TRIANGLES)


def chamfered_box(cut):
    """The box with corner 6 cut at `cut` along its three edges: the cut face (6, 8, 9), at
    position CHAMFER_FACE, is equilateral, of side cut * sqrt(2), area sqrt(3) / 2 * cut^2 and
    ratio sqrt(3) / 4. The faces beside it are pentagons, triangulated."""
    points = list(BOX)
    points[6] = (L - cut, W, H)
    points += [(L, W - cut, H), (L, W, H - cut)]
    faces = [(0, 2, 1), (0, 3, 2), (3, 7, 6), (3, 6, 9), (3, 9, 2), (0, 4, 7), (0, 7, 3),
             (1, 2, 9), (1, 9, 8), (1, 8, 5), (4, 5, 8), (4, 8, 6), (4, 6, 7),
             (6, 8, 9), (0, 1, 5), (0, 5, 4)]
    return points, faces


class Point:
    def __init__(self, coords):
        self.coords = tuple(float(x) for x in coords)


class Vertex:
    def __init__(self, points, point_index):
        self.point = points[point_index]
        self.point_index = point_index
        self.normal_index = 0
        self.uv = (0.0, 0.0)


class Face:
    def __init__(self, points, corners):
        self.vertices = [Vertex(points, k) for k in corners]
        self.texture = ""
        self.material = PEN


class Selection:
    def __init__(self, faces, points=()):
        self.points = {point: 1 for point in points}
        self.faces = {face: 1 for face in faces}


class LOD:
    """selections maps a name to the positions of its faces in faces, and selection_points
    a name to the positions of its points in points (none when it is not there). A selection
    without selection_points holds every point its faces use, as Object Builder writes it."""

    def __init__(self, resolution, points=(), faces=(), selections=None, selection_points=None):
        self.resolution = resolution
        self.points = [Point(coords) for coords in points]
        self.faces = [Face(self.points, corners) for corners in faces]
        self.facenormals = [(0.0, 0.0, 1.0)]
        self.properties = {}
        self.mass = 10.0 if resolution == 1e13 else None
        held = selection_points or {}
        self.selections = {}
        for name, members in (selections or {}).items():
            members = [self.faces[n] for n in members]
            if name in held:
                points_of = [self.points[k] for k in held[name]]
            else:
                points_of = list({id(v.point): v.point for face in members for v in face.vertices}.values())
            self.selections[name] = Selection(members, points_of)

    @property
    def num_vertices(self):
        return sum(len(face.vertices) for face in self.faces)


class Model:
    def __init__(self, lods):
        self.lods = lods


def two_hulls(second, name="Component02"):
    """A collision LOD's points, faces and selections: the box as Component01 (points 0-7,
    faces 0-11) and the hull `second`, (points, faces), after it as `name`."""
    points, faces = second
    base = len(BOX)
    first = len(BOX_TRIANGLES)
    all_faces = BOX_TRIANGLES + [tuple(base + k for k in face) for face in faces]
    return BOX + points, all_faces, {"Component01": range(first), name: range(first, len(all_faces))}


def needle_lod(selections, selection_points=None):
    """A Geometry LOD of needle_box(2e-5) alone, with these selections."""
    points, faces = needle_box(2e-5)
    return LOD(1e13, points, faces, selections, selection_points)


def tiny_triangle_model(selections=None, selection_points=None):
    """A Geometry LOD: the box and a 1 mm triangle (face 12, points 8 to 10, area 5e-7 m^2),
    all in Component01, and these selections besides."""
    points = BOX + [(5, 5, 5), (5.001, 5, 5), (5, 5.001, 5)]
    faces = BOX_TRIANGLES + [(8, 9, 10)]
    held = {"Component01": range(13)}
    held.update(selections or {})
    return Model([LOD(1e13, points, faces, held, selection_points)])


class TriangleArithmetic(unittest.TestCase):
    def test_area_and_ratio_of_known_triangles(self):
        cases = [
            (((0, 0, 0), (1, 0, 0), (0, 1, 0)), 0.5, 0.25),
            (((0, 0, 0), (2, 0, 0), (1, math.sqrt(3), 0)), math.sqrt(3), math.sqrt(3) / 4),
            (((0, 0, 0), (1, 0, 0), (2, 0, 0)), 0.0, 0.0),
            (((1, 1, 1), (1, 1, 1), (1, 1, 1)), 0.0, 0.0),
        ]
        for corners, area, ratio in cases:
            got = audit.triangle_area_ratio(*corners)
            self.assertAlmostEqual(got[0], area, places=12, msg=corners)
            self.assertAlmostEqual(got[1], ratio, places=12, msg=corners)


class NeedleTriangles(unittest.TestCase):
    """needle_triangles() on points and faces."""

    def test_a_healthy_hull_passes(self):
        self.assertEqual(audit.needle_triangles(BOX, BOX_TRIANGLES), [])
        # It is read: its four thinnest triangles (legs 1 and 0.25 m, ratio 0.118) fail at 0.12.
        thinnest = audit.needle_triangles(BOX, BOX_TRIANGLES, min_ratio=0.12)
        self.assertEqual([face for face, _, _, _ in thinnest], [2, 3, 10, 11])

    def test_a_quad_reads_as_two_triangles_and_a_box_of_quads_passes(self):
        self.assertEqual(audit.needle_triangles(BOX, BOX_QUADS), [])
        # At a ratio no triangle reaches every triangle is listed: (a, b, c) and (a, c, d) per quad.
        every = audit.needle_triangles(BOX, BOX_QUADS, min_ratio=1.0)
        self.assertEqual([(face, corners) for face, corners, _, _ in every],
                         [(n, t) for n, (a, b, c, d) in enumerate(BOX_QUADS) for t in ((a, b, c), (a, c, d))])

    def test_a_large_thin_triangle_above_the_ratio_passes(self):
        # 2 m long and 0.476 mm high: area 4.76e-4 m^2 and ratio 1.19e-4, the lowest ratio that
        # took rays in the measured runs.
        points = [(0, 0, 0), (2, 0, 0), (1, 4.76e-4, 0)]
        self.assertEqual(audit.needle_triangles(points, [(0, 1, 2)]), [])
        (needle,) = audit.needle_triangles(points, [(0, 1, 2)], min_ratio=1.2e-4)
        self.assertAlmostEqual(needle[2], 4.76e-4, delta=1e-12)
        self.assertAlmostEqual(needle[3], 1.19e-4, delta=1e-12)

    def test_a_triangle_on_the_ratio_threshold_passes(self):
        # 1 m long and 0.2 mm high: area 1e-4 m^2 over a longest edge of 1 m, a ratio of 1e-4,
        # both exactly in floating point. The check fails a ratio under 1e-4, not at it.
        points = [(0, 0, 0), (1, 0, 0), (0.5, 0.0002, 0)]
        self.assertEqual(audit.triangle_area_ratio(*points), (1e-4, 1e-4))
        self.assertEqual(audit.needle_triangles(points, [(0, 1, 2)]), [])

    def test_a_triangle_on_the_area_threshold_passes(self):
        # Legs of 2 mm and 1 mm: area 1e-6 m^2 exactly in floating point, and ratio 0.2. The
        # check fails an area under 1e-6 m^2, not at it.
        points = [(0, 0, 0), (0.002, 0, 0), (0, 0.001, 0)]
        self.assertEqual(audit.triangle_area_ratio(*points), (1e-6, 0.2))
        self.assertEqual(audit.needle_triangles(points, [(0, 1, 2)]), [])

    def test_a_needle_between_the_two_ratios_fails(self):
        # Ratio 5e-5: under the check's 1e-4 and over 1e-5, the ratio of the next test.
        points = [(0, 0, 0), (1, 0, 0), (0.5, 0.0001, 0)]
        self.assertEqual(audit.needle_triangles(points, [(0, 1, 2)]), [(0, (0, 1, 2), 5e-05, 5e-05)])

    def test_a_needle_by_ratio_fails_and_is_named(self):
        points, faces = needle_box(2e-5)
        (needle,) = audit.needle_triangles(points, faces)
        face, corners, area, ratio = needle
        self.assertEqual((face, corners), (NEEDLE_FACE, (4, 8, 5)))
        self.assertAlmostEqual(area, 1e-5, delta=1e-15)
        self.assertAlmostEqual(ratio, 1e-5, delta=1e-15)
        self.assertGreater(area, audit.NEEDLE_MIN_AREA)

    def test_a_small_triangle_fails_by_area_and_is_named(self):
        points, faces = chamfered_box(1e-3)
        (needle,) = audit.needle_triangles(points, faces)
        face, corners, area, ratio = needle
        self.assertEqual((face, corners), (CHAMFER_FACE, (6, 8, 9)))
        self.assertAlmostEqual(area, math.sqrt(3) / 2 * 1e-6, delta=1e-15)
        self.assertAlmostEqual(ratio, math.sqrt(3) / 4, delta=1e-9)

    def test_a_needle_of_the_measured_size_fails_and_is_named(self):
        # The measured needle: area 3e-8 m^2 and ratio 4.6e-7, on a box 0.2554 m long.
        points, faces = needle_box(MEASURED_OFFSET, MEASURED_LENGTH)
        (needle,) = audit.needle_triangles(points, faces)
        face, corners, area, ratio = needle
        self.assertEqual((face, corners), (NEEDLE_FACE, (4, 8, 5)))
        self.assertAlmostEqual(area, 3e-8, delta=1e-20)
        self.assertAlmostEqual(ratio, 4.6e-7, delta=1e-19)


class CollisionComponents(unittest.TestCase):
    """check_collision_needle_triangles() on a stand-in model."""

    def test_the_finding_names_the_lod_the_component_the_face_and_both_numbers(self):
        points, faces, selections = two_hulls(needle_box(2e-5))
        lower = {name.lower(): members for name, members in selections.items()}
        model = Model([
            LOD(0.0, points, faces, selections),
            LOD(1e13, points, faces, selections),
            LOD(1e15, [(0, 0, 0)]),
            LOD(6e15, points, faces, lower),
            LOD(7e15, points, faces, selections),
        ])
        issues = audit.check_collision_needle_triangles(model)
        face = len(BOX_TRIANGLES) + NEEDLE_FACE
        heads = ["LOD[1] Geometry, Component02, face %d: " % face,
                 "LOD[3] ViewGeo, component02, face %d: " % face,
                 "LOD[4] FireGeo, Component02, face %d: " % face]
        self.assertEqual([severity for severity, _ in issues], ["CRITICAL"] * len(heads), issues)
        for (_, message), head in zip(issues, heads):
            self.assertTrue(message.startswith(
                head + "needle triangle (points 12, 16, 13), area 1.00e-05 m^2, "
                "area/longest edge^2 1.00e-05 (this check fails a triangle under 1e-06 m^2 or "
                "1e-04)."), message)
            self.assertIn("without point 16, the corner opposite the longest edge", message)

    def test_a_geophys_lod_is_not_read(self):
        # The measured runs covered the Geometry, View and Fire LODs only.
        points, faces, selections = two_hulls(needle_box(2e-5))
        self.assertEqual(audit.check_collision_needle_triangles(Model([LOD(4e13, points, faces, selections)])), [])

    def test_a_proxy_triangle_in_a_component_is_not_read(self):
        # The 1 mm triangle, once as a proxy triangle: the one face of a selection named
        # proxy:<path>.<index> whose points are its three corners.
        (issue,) = audit.check_collision_needle_triangles(tiny_triangle_model())
        self.assertTrue(issue[1].startswith("LOD[0] Geometry, Component01, face 12: "), issue)
        proxy = "proxy:\\dz\\vehicles\\parts\\battery_car.001"
        held = tiny_triangle_model({proxy: [12]}, {proxy: (8, 9, 10)})
        self.assertEqual(audit.check_collision_needle_triangles(held), [])

    def test_a_proxy_named_in_capitals_is_not_read(self):
        (issue,) = audit.check_collision_needle_triangles(tiny_triangle_model())
        self.assertTrue(issue[1].startswith("LOD[0] Geometry, Component01, face 12: "), issue)
        proxy = "PROXY:\\demo\\asset.001"
        held = tiny_triangle_model({proxy: [12]}, {proxy: (8, 9, 10)})
        self.assertEqual(audit.check_collision_needle_triangles(held), [])

    def test_a_selection_under_a_proxy_name_that_is_not_a_proxy_triangle_is_read(self):
        # Each selection holds the needle and is not a proxy triangle by py3d's rule, so the
        # needle is reported: (name, its faces, its points).
        every = range(len(NEEDLE_TRIANGLES))
        corners = NEEDLE_TRIANGLES[NEEDLE_FACE]
        cases = [
            ("proxy:fake.001", [NEEDLE_FACE], ()),             # no points
            ("PROXY:fake.001", [NEEDLE_FACE], ()),             # no points, in capitals
            ("proxy:fake", [NEEDLE_FACE], corners),            # no index
            ("notproxy:fake.001", [NEEDLE_FACE], corners),     # not proxy:
            ("proxy:fake.001", [NEEDLE_FACE], (0, 1, 2)),      # three points, not its corners
            ("proxy:fake.001", [NEEDLE_FACE, 7], corners),     # two faces
        ]
        for name, faces, points in cases:
            with self.subTest(name=name, faces=faces, points=points):
                model = Model([needle_lod({"Component01": every, name: faces}, {name: points})])
                (issue,) = audit.check_collision_needle_triangles(model)
                self.assertEqual(issue[0], "CRITICAL")
                self.assertTrue(issue[1].startswith(NEEDLE_HEAD), issue)

    def test_a_face_in_no_component_is_not_read(self):
        points, faces = needle_box(2e-5)
        rest = [n for n in range(len(faces)) if n != NEEDLE_FACE]
        covered = Model([LOD(1e13, points, faces, {"Component01": range(len(faces))})])
        outside = Model([LOD(1e13, points, faces, {"Component01": rest, "lid": [NEEDLE_FACE]})])
        (issue,) = audit.check_collision_needle_triangles(covered)
        self.assertTrue(issue[1].startswith("LOD[0] Geometry, Component01, face 6: "), issue)
        self.assertEqual(audit.check_collision_needle_triangles(outside), [])

    def test_a_face_at_weight_zero_is_not_read(self):
        # A weight of 0 is no membership: py3d does not write it.
        lod = needle_lod({"Component01": range(len(NEEDLE_TRIANGLES))})
        (issue,) = audit.check_collision_needle_triangles(Model([lod]))
        self.assertTrue(issue[1].startswith(NEEDLE_HEAD), issue)
        lod.selections["Component01"].faces[lod.faces[NEEDLE_FACE]] = 0
        self.assertEqual(audit.check_collision_needle_triangles(Model([lod])), [])

    def test_a_name_that_only_begins_like_a_component_is_not_read(self):
        every = range(len(NEEDLE_TRIANGLES))
        (issue,) = audit.check_collision_needle_triangles(Model([needle_lod({"Component01": every})]))
        self.assertTrue(issue[1].startswith(NEEDLE_HEAD), issue)
        self.assertEqual(audit.check_collision_needle_triangles(Model([needle_lod({"Component01a": every})])), [])


def _run_main(py3d, data):
    """main() on a .p3d holding data, with load_py3d() giving py3d and the preflight gate off."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "model.p3d"
        path.write_bytes(data)
        out = io.StringIO()
        with mock.patch.object(audit, "load_py3d", lambda: py3d), \
                mock.patch.object(audit.h, "gate_on_preflight", lambda: None), \
                contextlib.redirect_stdout(out):
            try:
                audit.main([str(path)])
            except SystemExit as stop:
                return stop.code, out.getvalue()
    raise AssertionError("main() did not exit")


class Wiring(unittest.TestCase):
    """main() runs the check on a .p3d and exits 1 on a needle."""

    def run_main(self, model):
        stand_in = types.SimpleNamespace(P3D=lambda stream: model)
        return _run_main(stand_in, b"MLOD" + bytes(12))  # the signature audit_p3d() reads

    def model(self, second):
        points, faces, selections = two_hulls(second)
        box_only = {"Component01": range(len(BOX_TRIANGLES))}
        return Model([
            LOD(0.0, BOX, BOX_TRIANGLES),
            LOD(1e13, points, faces, selections),
            LOD(1e15, [(0, 0, 0)]),
            LOD(6e15, BOX, BOX_TRIANGLES, box_only),
            LOD(7e15, BOX, BOX_TRIANGLES, box_only),
        ])

    def test_main_exits_1_on_a_needle_and_0_without_one(self):
        code, out = self.run_main(self.model((BOX, BOX_QUADS)))
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: ALL CHECKS PASSED", out)
        code, out = self.run_main(self.model(needle_box(2e-5)))
        self.assertEqual(code, 1, out)
        self.assertIn("  CRITICAL: LOD[1] Geometry, Component02, face 18: needle triangle", out)
        self.assertIn("RESULT: 1 CRITICAL, 0 WARNING, 1 NOTE", out)  # the note is the Geometry mass


@unittest.skipUnless(REPO_PY3D.is_file(), "the DayZ fork of py3d is not at scripts/tools/py3d")
class SerializedModels(unittest.TestCase):
    """MLODs written and read back with the DayZ fork of py3d, then main() or the check on them."""

    # The three findings on the measured needle as Component01 of the Geometry, View and Fire
    # LODs: the hull is written wound inward, so the needle (4, 8, 5) reads (5, 8, 4).
    NEEDLE_LINES = ["  CRITICAL: LOD[%d] %s, Component01, face 6: needle triangle (points 5, 8, 4), area "
                    "3.00e-08 m^2, area/longest edge^2 4.60e-07 (this check fails a triangle under 1e-06 "
                    "m^2 or 1e-04)." % (n, kind) for n, kind in ((1, "Geometry"), (3, "ViewGeo"), (4, "FireGeo"))]

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("py3d_dayz_fork_under_test", REPO_PY3D)
        cls.py3d = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.py3d)

    def add_hull(self, lod, points, faces, component=None):
        """points and faces into lod, each face in reverse (the MLOD's inward winding), with its
        normal and a penetration material; component names a selection that holds them all,
        faces and points. Returns the faces."""
        m = self.py3d
        base = len(lod.points)
        for coords in points:
            point = m.Point()
            point.coords = tuple(float(x) for x in coords)
            point.flags = 0
            lod.points.append(point)
        made = []
        for corners in faces:
            corners = [base + k for k in reversed(corners)]
            a, b, c = (lod.points[k].coords for k in corners)
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            size = math.sqrt(sum(x * x for x in normal))
            lod.facenormals.append(tuple(x / size for x in normal))
            face = m.Face(lod.points, lod.facenormals)
            face.flags, face.texture, face.material = 0, "", PEN
            for k in corners:
                vertex = m.Vertex(lod.points, lod.facenormals)
                vertex.point_index = k
                vertex.normal_index = len(lod.facenormals) - 1
                vertex.uv = (0.0, 0.0)
                face.vertices.append(vertex)
            lod.faces.append(face)
            made.append(face)
        if component:
            sel = lod.new_selection(component)
            sel.faces = {face: 1 for face in made}
            sel.points = {lod.points[base + k]: 1 for k in range(len(points))}
        return made

    def written(self, hull, each_collision_lod=None):
        """The bytes of an MLOD of hull, (points, faces): it is the Visual LOD and Component01 of
        the Geometry (10 kg), View and Fire LODs, with a Memory LOD; each_collision_lod(lod)
        runs on each of those three before it is written."""
        m = self.py3d
        model = m.P3D()
        for resolution in (0.0, 1e13, 1e15, 6e15, 7e15):
            lod = m.LOD()
            lod.resolution = resolution
            if resolution == 1e15:
                lod.set_memory_point("pos center", (0.1, 0.25, 0.125))
            else:
                self.add_hull(lod, *hull, component=None if resolution == 0.0 else "Component01")
            if resolution in (1e13, 6e15, 7e15) and each_collision_lod:
                each_collision_lod(lod)
            if resolution == 1e13:
                lod.set_total_mass(10.0)
                lod.properties["autocenter"] = "0"
            model.lods.append(lod)
        stream = io.BytesIO()
        model.write(stream)
        return stream.getvalue()

    def read(self, data):
        return self.py3d.P3D(io.BytesIO(data))

    def run_main(self, data):
        return _run_main(self.py3d, data)

    def assert_needle_findings(self, code, out):
        self.assertEqual(code, 1, out)
        found = [line for line in out.splitlines() if line.startswith("  CRITICAL: ")]
        self.assertEqual(len(found), 3, out)
        for line, head in zip(found, self.NEEDLE_LINES):
            self.assertTrue(line.startswith(head), line)
            self.assertIn("without point 8, the corner opposite the longest edge", line)
        self.assertIn("RESULT: 3 CRITICAL, 0 WARNING, 1 NOTE", out)  # the note is the Geometry mass

    def test_a_needle_written_and_read_back_fails_in_the_three_collision_lods(self):
        data = self.written(needle_box(MEASURED_OFFSET, MEASURED_LENGTH))
        self.assertEqual(self.read(data).validate(), [])
        self.assert_needle_findings(*self.run_main(data))

    def test_a_proxy_name_does_not_hide_a_needle_in_a_written_model(self):
        hull = needle_box(MEASURED_OFFSET, MEASURED_LENGTH)

        def under(name, with_corners):
            def add(lod):
                needle = lod.faces[NEEDLE_FACE]
                sel = lod.new_selection(name)
                sel.faces = {needle: 1}
                sel.points = {vertex.point: 1 for vertex in needle.vertices} if with_corners else {}
            return add

        for name, with_corners in (("proxy:fake.001", False), ("proxy:fake", True)):
            with self.subTest(name=name, corners=with_corners):
                data = self.written(hull, under(name, with_corners))
                back = self.read(data)
                self.assertEqual(back.validate(), [])
                held = back.lods[1].selections[name]
                self.assertEqual((len(held.faces), len(held.points)), (1, 3 if with_corners else 0))
                self.assert_needle_findings(*self.run_main(data))
        # The same face under proxy:<path>.<index> with its three corners as its points is a proxy
        # triangle by py3d's rule, and the check leaves it out as py3d's own checks do.
        code, out = self.run_main(self.written(hull, under("proxy:fake.001", True)))
        self.assertEqual(code, 0, out)
        self.assertIn("RESULT: ALL CHECKS PASSED", out)

    def test_the_proxy_rule_is_py3d_s_on_a_lod_py3d_wrote_and_read_back(self):
        m = self.py3d
        lod = m.LOD()
        lod.resolution = 1e13
        self.add_hull(lod, BOX, BOX_TRIANGLES, component="Component01")
        component = lod.selections["Component01"]
        real = lod.add_proxy("\\dz\\demo\\asset", 1, origin=(2.0, 0.0, 0.0), scale=5e-4)   # face 12
        # A triangle with legs of 0.5 mm (area 1.25e-7 m^2) under each name, faces 13 to 18:
        # (name, its points, its faces).
        cases = [
            ("PROXY:\\demo\\asset.002", "corners", 1),
            ("proxy:fake.003", "none", 1),
            ("proxy:fake", "corners", 1),
            ("notproxy:fake.004", "corners", 1),
            ("proxy:fake.005", "box", 1),
            ("proxy:fake.006", "corners", 2),
        ]
        for n, (name, points, faces) in enumerate(cases):
            x = 3.0 + n
            (face,) = self.add_hull(lod, [(x, 0, 0), (x + 5e-4, 0, 0), (x, 5e-4, 0)], [(0, 1, 2)])
            sel = lod.new_selection(name)
            sel.faces = {face: 1}
            if faces == 2:
                sel.faces[lod.faces[0]] = 1
            corners = [vertex.point for vertex in face.vertices]
            sel.points = {point: 1 for point in {"corners": corners, "none": [], "box": lod.points[:3]}[points]}
        for face in lod.faces[12:]:   # every small triangle is in the component too
            component.faces[face] = 1
            for vertex in face.vertices:
                component.points[vertex.point] = 1
        model = m.P3D()
        model.lods.append(lod)
        stream = io.BytesIO()
        model.write(stream)
        back = self.read(stream.getvalue())
        geo = back.lods[0]
        shapes = {name: (len(sel.faces), len(sel.points)) for name, sel in geo.selections.items()}
        self.assertEqual(shapes, {
            "Component01": (19, 29), real: (1, 3), "PROXY:\\demo\\asset.002": (1, 3),
            "proxy:fake.003": (1, 0), "proxy:fake": (1, 3), "notproxy:fake.004": (1, 3),
            "proxy:fake.005": (1, 3), "proxy:fake.006": (2, 3),
        })
        proxies = audit.proxy_triangles(geo)
        self.assertEqual(proxies, m._proxy_triangle_faces(geo))
        self.assertEqual({n for n, fa in enumerate(geo.faces) if id(fa) in proxies}, {12, 13})
        issues = audit.check_collision_needle_triangles(back)
        self.assertEqual([int(re.search(r", face (\d+): ", message).group(1)) for _, message in issues],
                         [14, 15, 16, 17, 18])
        for _, message in issues:
            self.assertIn("area 1.25e-07 m^2, area/longest edge^2 2.50e-01", message)


if __name__ == "__main__":
    unittest.main()
