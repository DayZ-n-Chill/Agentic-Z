"""compare_navmesh on synthetic .nm files, route files and terrain NPZ written by the tests.

The terrain cases need numpy and skip without it; everything else is stdlib only.
"""

from __future__ import annotations

import contextlib
import io
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest


TOOL_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import compare_navmesh  # noqa: E402
from nm_fixture import tile_bytes, write_nm  # noqa: E402

try:
    import numpy
except ImportError:  # the terrain cases skip
    numpy = None


W = 12.5  # tile width of every synthetic mesh here: a 4 x 4 grid covering 50 m


def run(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            code = compare_navmesh.main([str(item) for item in argv])
        except SystemExit as exit_:
            code = exit_.code
    return code, stdout.getvalue(), stderr.getvalue()


class _Case(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)
        self.old = write_nm(self.root / "old.nm", 4, 4, W)
        self._outs = 0

    def tearDown(self):
        self._tmp.cleanup()

    def new(self, tiles=None, name="new.nm", **kwargs):
        return write_nm(self.root / name, kwargs.pop("nx", 4), kwargs.pop("nz", 4), kwargs.pop("width", W), tiles, **kwargs)

    def out(self):
        self._outs += 1
        return self.root / f"cmp-{self._outs}.json"

    def compare(self, new, *extra, expect):
        out = self.out()
        code, stdout, stderr = run(["--old-nm", self.old, "--new-nm", new, "--out", out, *extra])
        self.assertEqual(expect, code, stderr)
        report = json.loads(out.read_text(encoding="utf-8"))
        self.assertNotIn("structural", json.loads(stdout))
        return report

    def refused(self, new, *extra, fragment):
        out = self.out()
        code, _, stderr = run(["--old-nm", self.old, "--new-nm", new, "--out", out, *extra])
        self.assertEqual(3, code, stderr)
        self.assertFalse(out.exists(), "a refused comparison must write nothing")
        self.assertTrue(stderr.startswith("error: "), stderr)
        self.assertIn(fragment, stderr)

    def routes(self, text, name="routes.csv", encoding="utf-8"):
        path = self.root / name
        path.write_text(text, encoding=encoding)
        return path


class TestStructure(_Case):
    def test_identical_files(self):
        report = self.compare(self.new(), expect=0)

        self.assertEqual("PASS_NO_STRUCTURE_DELTA", report["status"])
        self.assertEqual([], report["review_reasons"])
        self.assertEqual((0, 0, 16), (report["serialized_changed_tiles"], report["structural_changes"], report["tiles"]))

    def test_serialized_only_change_passes(self):
        # The generator rewrites almost every tile's bytes between runs; the structure is what counts.
        tiles = {(x, z): tile_bytes(x, z, W, payload=b"run-2 %d %d" % (x, z)) for x in range(4) for z in range(4)}

        report = self.compare(self.new(tiles), expect=0)

        self.assertEqual("PASS_NO_STRUCTURE_DELTA", report["status"])
        self.assertEqual(16, report["serialized_changed_tiles"])
        self.assertEqual(0, report["structural_changes"])
        self.assertNotEqual(report["old_nm_sha256"], report["new_nm_sha256"])

    def test_structural_change_without_terrain_is_reviewed(self):
        tiles = {
            (1, 2): tile_bytes(1, 2, W, polygons=5),
            (3, 0): tile_bytes(3, 0, W, vertices=7),
            (0, 3): tile_bytes(0, 3, W, y=(0.0, 10.5)),
            (2, 2): tile_bytes(2, 2, W, payload=b"bytes only"),
        }

        report = self.compare(self.new(tiles), expect=1)

        self.assertEqual("REVIEW", report["status"])
        self.assertEqual(["structure_changed_without_terrain_inputs"], report["review_reasons"])
        self.assertEqual(4, report["serialized_changed_tiles"])
        self.assertEqual(3, report["structural_changes"])
        self.assertEqual([[0, 3], [1, 2], [3, 0]], [item["tile"] for item in report["structural"]])
        first = report["structural"][1]
        self.assertEqual((4, 5), (first["old"]["polygons"], first["new"]["polygons"]))
        self.assertIsNone(first["distance_m"])
        self.assertIsNone(report["changed_terrain_vertices"])
        self.assertIsNone(report["max_structural_tile_distance_m"])

    def test_report_keeps_the_source_fields(self):
        report = self.compare(self.new(), expect=0)

        for key in ("status", "old_nm", "old_nm_sha256", "new_nm", "new_nm_sha256", "old_terrain_sha256",
                    "new_terrain_sha256", "tile_m", "tiles", "serialized_changed_tiles", "structural_changes",
                    "changed_terrain_vertices", "max_structural_tile_distance_m", "local_threshold_m",
                    "structural", "route_tiles_changed", "limits"):
            self.assertIn(key, report)
        self.assertEqual(W, report["tile_m"])
        self.assertFalse(report["layout"]["inside_verified_envelope"])
        self.assertTrue(any("outside the verified envelope" in line for line in report["limits"]))
        self.assertIsNone(report["route_tiles_changed"], "no --routes: not checked, not an empty pass")

    def test_mismatched_tile_sets_are_refused(self):
        self.refused(self.new(nx=5), fragment="tile layouts differ")

    def test_same_grid_of_a_different_tile_width_is_refused(self):
        self.refused(self.new(width=25.0), fragment="tile layouts differ")

    def test_a_malformed_mesh_is_refused(self):
        self.refused(self.new(magic=0), fragment="new.nm")

    def test_missing_mesh_is_refused(self):
        self.refused(self.root / "absent.nm", fragment="absent.nm")

    def test_existing_out_is_refused_and_kept(self):
        out = self.root / "prior.json"
        out.write_text("prior evidence\n", encoding="utf-8")

        code, _, stderr = run(["--old-nm", self.old, "--new-nm", self.new(), "--out", out])

        self.assertEqual(3, code)
        self.assertIn("already exists", stderr)
        self.assertEqual("prior evidence\n", out.read_text(encoding="utf-8"))


class TestRoutes(_Case):
    def test_compare_uses_the_module_route_margin(self):
        # Tile (0, 0) is [0, 12.5]; a point at (30, 30) meets it only with the 25 m margin.
        new = self.new({(0, 0): tile_bytes(0, 0, W, polygons=5)})
        routes = self.routes("pt;30 0 30;30 0 30\n")

        report = self.compare(new, "--routes", routes, expect=1)

        self.assertEqual({"pt": [[0, 0]]}, report["route_tiles_changed"])
        self.assertIn("route_tile_changed", report["review_reasons"])

    def test_route_over_a_changed_tile(self):
        new = self.new({(1, 2): tile_bytes(1, 2, W, polygons=5)})
        # The 25 m margin puts "near" over tile (1, 2); "far" covers x from 35 m, tiles 2 and up.
        routes = self.routes("near;14 3 30;20 3 31\n\nfar;60 0 60;70 0 70\n")

        report = self.compare(new, "--routes", routes, expect=1)

        self.assertEqual({"near": [[1, 2]], "far": []}, report["route_tiles_changed"])
        self.assertEqual(
            ["structure_changed_without_terrain_inputs", "route_tile_changed"], report["review_reasons"]
        )

    def test_routes_read_with_a_byte_order_mark(self):
        routes = self.routes("only;1 0 1;2 0 2\n", encoding="utf-8-sig")

        report = self.compare(self.new(), "--routes", routes, expect=0)

        self.assertEqual({"only": []}, report["route_tiles_changed"])

    def test_route_cover_is_the_widened_rectangle(self):
        # 25 m around (30, 30) is x and z in [5, 55]: tiles 0 to 4 on each axis.
        cover = compare_navmesh.route_cover((30.0, 30.0), (30.0, 30.0), W, 25.0)
        self.assertEqual({(x, z) for x in range(5) for z in range(5)}, cover)
        # A tile edge on the widened border counts: [12.5, 37.5] meets tiles 0 to 3.
        self.assertEqual({(x, 0) for x in range(4)}, {k for k in compare_navmesh.route_cover((37.5, 0.0), (12.5, 0.0), W, 0.0) if k[1] == 0})
        # With the grid, only its tiles: (30, 30) widened by 25 m on a 4 x 4 grid.
        clipped = compare_navmesh.route_cover((30.0, 30.0), (30.0, 30.0), W, 25.0, (4, 4))
        self.assertEqual({(x, z) for x in range(4) for z in range(4)}, clipped)

    def test_a_route_far_off_the_map_covers_only_the_grid(self):
        # Unclipped, this rectangle would be some 1.6e11 tiles on a side.
        new = self.new({(1, 2): tile_bytes(1, 2, W, polygons=5)})
        routes = self.routes("wide;-1e12 0 -1e12;1e12 0 1e12\noff;1e12 0 1e12;2e12 0 2e12\n")

        report = self.compare(new, "--routes", routes, expect=1)

        self.assertEqual({"wide": [[1, 2]], "off": []}, report["route_tiles_changed"])

    def test_malformed_route_files_are_refused(self):
        for label, text in (
            ("two fields", "r1;1 2 3\n"),
            ("two coordinates", "r1;1 2;3 4 5\n"),
            ("not a number", "r1;1 x 3;4 5 6\n"),
            ("non-finite", "r1;1 2 nan;4 5 6\n"),
            ("empty id", ";1 2 3;4 5 6\n"),
            ("duplicate id", "r1;1 2 3;4 5 6\nr1;1 2 3;4 5 6\n"),
            ("no routes", "\n  \n"),
        ):
            with self.subTest(case=label):
                self.refused(self.new(), "--routes", self.routes(text, name=f"{label}.csv"), fragment="routes")

    def test_route_errors_name_the_line(self):
        self.refused(self.new(), "--routes", self.routes("ok;1 2 3;4 5 6\nbad;1 2 3\n"), fragment="line 2")


class TestUsage(_Case):
    def test_usage_errors_exit_2(self):
        npz = self.root / "t.npz"
        npz.write_bytes(b"")
        for label, extra in (
            ("cell without terrain", ["--cell-m", "6"]),
            ("local without terrain", ["--local-m", "10"]),
            ("one terrain", ["--old-terrain", npz, "--cell-m", "6"]),
            ("terrain without cell", ["--old-terrain", npz, "--new-terrain", npz]),
            ("zero cell", ["--old-terrain", npz, "--new-terrain", npz, "--cell-m", "0"]),
            ("negative local", ["--old-terrain", npz, "--new-terrain", npz, "--cell-m", "6", "--local-m", "-1"]),
            ("nan cell", ["--old-terrain", npz, "--new-terrain", npz, "--cell-m", "nan"]),
        ):
            with self.subTest(case=label):
                out = self.out()
                code, _, _ = run(["--old-nm", self.old, "--new-nm", self.new(), "--out", out, *extra])
                self.assertEqual(2, code)
                self.assertFalse(out.exists())


class TestNumpyOnlyForTerrain(_Case):
    """The comparator imports numpy only when terrain inputs are given (run with numpy blocked)."""

    def blocked(self, *argv):
        script = textwrap.dedent(
            """
            import sys
            sys.modules["numpy"] = None
            sys.path.insert(0, sys.argv[1])
            import compare_navmesh
            raise SystemExit(compare_navmesh.main(sys.argv[2:]))
            """
        )
        return subprocess.run(
            [sys.executable, "-c", script, str(TOOL_ROOT), *[str(item) for item in argv]],
            capture_output=True,
            text=True,
            cwd=str(self.root),
        )

    def test_without_terrain_numpy_is_not_needed(self):
        out = self.out()

        result = self.blocked("--old-nm", self.old, "--new-nm", self.new(), "--out", out,
                              "--routes", self.routes("r;1 0 1;2 0 2\n"))

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("PASS_NO_STRUCTURE_DELTA", json.loads(out.read_text(encoding="utf-8"))["status"])

    def test_terrain_without_numpy_is_refused(self):
        npz = self.root / "t.npz"
        npz.write_bytes(b"not read")
        out = self.out()

        result = self.blocked("--old-nm", self.old, "--new-nm", self.new(), "--out", out,
                              "--old-terrain", npz, "--new-terrain", npz, "--cell-m", "6.25")

        self.assertEqual(3, result.returncode)
        self.assertIn("numpy", result.stderr)
        self.assertFalse(out.exists())


@unittest.skipIf(numpy is None, "numpy is not installed: the terrain locality cases need it")
class TestTerrain(_Case):
    # An 8 x 8 height grid at 6.25 m covers the same 50 m as the 4 x 4 tiles of 12.5 m.
    # Vertex (row, col) is at x = col * cell, z = (rows - 1 - row) * cell: row 0 is the largest z.
    CELL = 6.25

    def terrain(self, name, changes=(), shape=(8, 8), key="heights", value=None):
        heights = numpy.zeros(shape) if value is None else value
        for row, col in changes:
            heights[row, col] = 1.5
        path = self.root / name
        with path.open("wb") as handle:
            numpy.savez(handle, **{key: heights})
        return path

    def args(self, old_t, new_t, *extra):
        return ["--old-terrain", old_t, "--new-terrain", new_t, "--cell-m", self.CELL, *extra]

    def test_local_change_passes(self):
        # The vertex at col 2, row 3 is at (12.5, 25.0), a corner of tile (1, 2).
        new = self.new({(1, 2): tile_bytes(1, 2, W, polygons=5)})

        report = self.compare(new, *self.args(self.terrain("o.npz"), self.terrain("n.npz", [(3, 2)])), expect=0)

        self.assertEqual("PASS_LOCAL_STRUCTURE_DELTA", report["status"])
        self.assertEqual(1, report["changed_terrain_vertices"])
        self.assertEqual(0.0, report["structural"][0]["distance_m"])
        self.assertEqual(0.0, report["max_structural_tile_distance_m"])
        self.assertEqual(100.0, report["local_threshold_m"])
        self.assertEqual(self.CELL, report["cell_m"])
        self.assertEqual([50.0, 50.0], report["terrain_extent_m"])

    def test_change_beyond_local_m_is_reviewed(self):
        # Tile (3, 3) is [37.5, 50] on both axes: 25 m in x and 12.5 m in z from (12.5, 25.0).
        new = self.new({(3, 3): tile_bytes(3, 3, W, vertices=9)})

        report = self.compare(
            new, *self.args(self.terrain("o.npz"), self.terrain("n.npz", [(3, 2)]), "--local-m", "20"), expect=1
        )

        self.assertEqual(["structure_farther_than_local_m"], report["review_reasons"])
        self.assertEqual(round(math.hypot(25.0, 12.5), 1), report["structural"][0]["distance_m"])
        self.assertEqual(20.0, report["local_threshold_m"])

    def test_row_zero_is_the_largest_z(self):
        # Row 0, col 7 is (43.75, 43.75), inside tile (3, 3).
        new = self.new({(3, 3): tile_bytes(3, 3, W, vertices=9)})

        report = self.compare(
            new, *self.args(self.terrain("o.npz"), self.terrain("n.npz", [(0, 7)]), "--local-m", "0"), expect=0
        )

        self.assertEqual(0.0, report["structural"][0]["distance_m"])

    def test_terrain_change_without_structure_change_is_reviewed(self):
        # A terrain edit the mesh does not show at all: a stale mesh, or an edit too small to matter.
        report = self.compare(self.new(), *self.args(self.terrain("o.npz"), self.terrain("n.npz", [(3, 2)])), expect=1)

        self.assertEqual("REVIEW", report["status"])
        self.assertEqual(["terrain_changed_without_structure_change"], report["review_reasons"])

    def test_same_terrain_and_structure_passes(self):
        report = self.compare(self.new(), *self.args(self.terrain("o.npz"), self.terrain("n.npz")), expect=0)

        self.assertEqual("PASS_NO_STRUCTURE_DELTA", report["status"])
        self.assertEqual(0, report["changed_terrain_vertices"])

    def test_structure_change_with_no_terrain_change_is_reviewed(self):
        new = self.new({(1, 1): tile_bytes(1, 1, W, polygons=1)})

        report = self.compare(new, *self.args(self.terrain("o.npz"), self.terrain("n.npz")), expect=1)

        self.assertEqual(["structure_farther_than_local_m"], report["review_reasons"])
        self.assertIsNone(report["structural"][0]["distance_m"])

    def test_route_on_a_local_change_is_reviewed(self):
        new = self.new({(1, 2): tile_bytes(1, 2, W, polygons=5)})

        report = self.compare(
            new,
            *self.args(self.terrain("o.npz"), self.terrain("n.npz", [(3, 2)])),
            "--routes",
            self.routes("road;16 0 26;18 0 27\n"),
            expect=1,
        )

        self.assertEqual(["route_tile_changed"], report["review_reasons"])
        self.assertEqual({"road": [[1, 2]]}, report["route_tiles_changed"])

    def test_a_cell_so_large_that_distances_overflow_is_refused(self):
        new = self.new({(1, 2): tile_bytes(1, 2, W, polygons=5)})
        args = ["--old-terrain", self.terrain("o.npz"), "--new-terrain", self.terrain("n.npz", [(3, 7)]),
                "--cell-m", "1e308"]

        with numpy.errstate(over="ignore", invalid="ignore"):
            self.refused(new, *args, fragment="non-finite")

    def test_bad_terrain_inputs_are_refused(self):
        old_t = self.terrain("o.npz")
        npy = self.root / "plain.npy"
        numpy.save(npy, numpy.zeros((8, 8)))
        garbage = self.root / "garbage.npz"
        garbage.write_bytes(b"not an archive")
        for label, new_t, fragment in (
            ("shape", self.terrain("shape.npz", shape=(8, 9)), "shape"),
            ("key", self.terrain("key.npz", key="elevation"), "heights"),
            ("npy", npy, "NPZ"),
            ("garbage", garbage, "NPZ"),
            ("1-D", self.terrain("flat.npz", value=numpy.zeros(64)), "2-D"),
            ("non-finite", self.terrain("nan.npz", value=numpy.full((8, 8), numpy.nan)), "finite"),
        ):
            with self.subTest(case=label):
                self.refused(self.new(), *self.args(old_t, new_t), fragment=fragment)


if __name__ == "__main__":
    unittest.main()
