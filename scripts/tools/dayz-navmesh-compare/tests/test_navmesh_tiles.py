"""navmesh_tiles.read_navmesh on synthetic .nm files written by the tests."""

from __future__ import annotations

import hashlib
import math
import pathlib
import random
import struct
import sys
import tempfile
import unittest


TOOL_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOL_ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import navmesh_tiles  # noqa: E402
from navmesh_tiles import NavmeshFormatError, NavmeshLayout, read_navmesh  # noqa: E402
from nm_fixture import DNAV, grid, nm_bytes, tile_bytes, write_nm  # noqa: E402


class _Case(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def nm(self, *args, **kwargs):
        return write_nm(self.root / "a.nm", *args, **kwargs)

    def refused(self, fragment, *args, **kwargs):
        path = self.nm(*args, **kwargs)
        with self.assertRaises(NavmeshFormatError) as raised:
            read_navmesh(path)
        self.assertIn(fragment, str(raised.exception))
        return raised.exception


class TestRead(_Case):
    def test_prefix_size_matches_bytes_to_the_next_tile(self):
        mesh = read_navmesh(self.nm(3, 2, 12.5))

        self.assertEqual(6, len(mesh.tiles))

    def test_layout_and_records(self):
        special = tile_bytes(2, 1, 12.5, polygons=9, vertices=17, y=(-3.5, 42.25), payload=b"payload")
        path = self.nm(3, 2, 12.5, {(2, 1): special})

        mesh = read_navmesh(path)

        self.assertEqual(NavmeshLayout(tiles_x=3, tiles_z=2, tile_m=12.5), mesh.layout)
        self.assertEqual(6, len(mesh.tiles))
        record = mesh.tile(2, 1)
        self.assertEqual((2, 1), (record.x, record.z))
        self.assertEqual((9, 17), (record.polygons, record.vertices))
        self.assertEqual((-3.5, 42.25), (record.y_min, record.y_max))
        self.assertEqual(len(special) - 16, record.size)
        self.assertEqual(hashlib.sha256(special[16:]).digest(), record.sha256)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), mesh.sha256)

    def test_tile_order_in_the_file_does_not_matter(self):
        order = grid(4, 3)
        random.Random(9821).shuffle(order)

        mesh = read_navmesh(self.nm(4, 3, 25.0, order=order))

        self.assertEqual([(x, z) for z in range(3) for x in range(4)], [(t.x, t.z) for t in mesh.tiles])

    def test_record_json_has_the_source_fields(self):
        mesh = read_navmesh(self.nm(1, 1, 50.0))

        self.assertEqual(
            {"tile": [0, 0], "bytes": 104, "sha256": mesh.tile(0, 0).sha256.hex(), "polygons": 4,
             "vertices": 6, "y_bounds": [0.0, 10.0]},
            mesh.tile(0, 0).to_json(),
        )


class TestEnvelope(unittest.TestCase):
    def test_measured_layouts_are_inside(self):
        for width, side in ((12.5, 983), (25.0, 491), (50.0, 245)):
            with self.subTest(width=width):
                self.assertTrue(NavmeshLayout(side, side, width).inside_verified_envelope)

    def test_anything_else_is_outside(self):
        for nx, nz, width in ((244, 245, 50.0), (246, 246, 50.0), (307, 307, 40.0), (3, 2, 12.5), (983, 982, 12.5)):
            with self.subTest(layout=(nx, nz, width)):
                self.assertFalse(NavmeshLayout(nx, nz, width).inside_verified_envelope)

    def test_layout_json(self):
        self.assertEqual(
            {"tiles_x": 245, "tiles_z": 245, "tile_m": 50.0, "tiles": 60025, "covered_x_m": 12250.0,
             "covered_z_m": 12250.0, "tesm_version": 6, "dnav_version": 11, "inside_verified_envelope": True},
            NavmeshLayout(245, 245, 50.0).to_json(),
        )


class TestRefusals(_Case):
    def test_bad_file_magic(self):
        self.refused("magic", 2, 2, 12.5, magic=0x4D534554 ^ 0xFF)

    def test_bad_file_version(self):
        self.refused("version 7", 2, 2, 12.5, version=7)

    def test_shorter_than_the_header(self):
        self.refused("header", 2, 2, 12.5, truncate=40)

    def test_count_must_be_tiles_x_times_tiles_z(self):
        self.refused("tile count", 2, 2, 12.5, order=grid(2, 2)[:3])

    def test_origin_must_be_zero(self):
        self.refused("origin", 2, 2, 12.5, origin=(0.0, 0.0, 6.0))

    def test_square_finite_positive_tiles(self):
        for depth_or_width in ({"depth": 25.0}, {"width": 0.0}, {"width": math.nan}, {"width": -12.5}):
            with self.subTest(case=depth_or_width):
                width = depth_or_width.get("width", 12.5)
                depth = depth_or_width.get("depth")
                self.refused("tile size", 2, 2, width, depth=depth)

    def test_truncated_offset_table(self):
        self.refused("offset table", 2, 2, 12.5, truncate=48 + 8)

    def test_first_offset_must_be_zero(self):
        size = len(tile_bytes(0, 0, 12.5))
        self.refused("first offset", 2, 1, 12.5, offsets=[4, 4 + size])

    def test_unsorted_offsets(self):
        size = len(tile_bytes(0, 0, 12.5))
        self.refused("increasing", 3, 1, 12.5, offsets=[0, 2 * size, size])

    def test_duplicate_offsets(self):
        self.refused("increasing", 2, 1, 12.5, offsets=[0, 0])

    def test_tile_past_the_end_of_the_file(self):
        size = len(tile_bytes(0, 0, 12.5))
        self.refused("past the end", 2, 1, 12.5, offsets=[0, 10 * size])

    def test_extra_bytes_after_the_last_tile(self):
        path = self.nm(1, 1, 12.5)
        path.write_bytes(path.read_bytes() + b"EXTRA")
        with self.assertRaises(NavmeshFormatError) as raised:
            read_navmesh(path)
        self.assertIn("table entry 0", str(raised.exception))

    def test_last_tile_payload_three_bytes_short(self):
        path = self.nm(1, 1, 12.5)
        path.write_bytes(path.read_bytes()[:-3])
        with self.assertRaises(NavmeshFormatError) as raised:
            read_navmesh(path)
        self.assertIn("table entry 0", str(raised.exception))

    def test_middle_tile_prefix_size_does_not_match(self):
        self.refused("table entry 1", 3, 1, 12.5, {(1, 0): tile_bytes(1, 0, 12.5, prefix_size=50)})

    def test_tile_with_no_data_after_its_header(self):
        self.refused("no data after", 1, 1, 12.5, {(0, 0): tile_bytes(0, 0, 12.5, payload=b"")})

    def test_bad_tile_magic(self):
        self.refused("tile magic", 2, 1, 12.5, {(1, 0): tile_bytes(1, 0, 12.5, magic=DNAV ^ 1)})

    def test_bad_tile_version(self):
        self.refused("tile version 7", 2, 1, 12.5, {(1, 0): tile_bytes(1, 0, 12.5, version=7)})

    def test_tile_coordinate_out_of_the_grid(self):
        tile = tile_bytes(1, 0, 12.5, coords=(2, 0), bmin=(25.0, 0.0, 0.0), bmax=(37.5, 1.0, 12.5))
        self.refused("outside the 2 x 1 grid", 2, 1, 12.5, {(1, 0): tile})

    def test_duplicate_tile(self):
        self.refused("duplicate tile (0, 0)", 2, 1, 12.5, {(1, 0): tile_bytes(0, 0, 12.5)})

    def test_bounds_must_match_the_coordinate(self):
        for label, kwargs in (
            ("bmin x", {"bmin": (12.0, 0.0, 0.0)}),
            ("bmin z", {"bmin": (12.5, 0.0, 0.5)}),
            ("bmax x", {"bmax": (25.5, 1.0, 12.5)}),
            ("bmax z", {"bmax": (25.0, 1.0, 13.0)}),
        ):
            with self.subTest(bound=label):
                self.refused("do not match tile (1, 0)", 2, 1, 12.5, {(1, 0): tile_bytes(1, 0, 12.5, **kwargs)})

    def test_bounds_within_the_tolerance_are_read(self):
        tile = tile_bytes(1, 0, 12.5, bmin=(12.5005, 0.0, 0.0))
        self.assertEqual(2, len(read_navmesh(self.nm(2, 1, 12.5, {(1, 0): tile})).tiles))

    def test_non_finite_bounds(self):
        # A NaN would also pass a check written as abs(a - b) > tolerance.
        for label, kwargs in (
            ("nan x", {"bmin": (math.nan, 0.0, 0.0)}),
            ("inf y", {"y": (0.0, math.inf)}),
            ("nan y", {"y": (math.nan, 1.0)}),
        ):
            with self.subTest(bound=label):
                self.refused("non-finite", 2, 1, 12.5, {(1, 0): tile_bytes(1, 0, 12.5, **kwargs)})

    def test_unreadable_file_is_an_os_error(self):
        with self.assertRaises(OSError):
            read_navmesh(self.root / "absent.nm")

    def test_errors_name_the_file(self):
        error = self.refused("magic", 1, 1, 12.5, magic=0)
        self.assertIn("a.nm", str(error))


class TestConstants(unittest.TestCase):
    def test_magics_spell_the_bytes_the_files_start_with(self):
        self.assertEqual(b"TESM", struct.pack("<I", navmesh_tiles.TESM_MAGIC))
        self.assertEqual(b"VAND", struct.pack("<I", navmesh_tiles.DNAV_MAGIC))
        self.assertEqual(b"TESM", nm_bytes(1, 1, 12.5)[:4])


if __name__ == "__main__":
    unittest.main()
