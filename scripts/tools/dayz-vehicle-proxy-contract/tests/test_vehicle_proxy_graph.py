from __future__ import annotations

from dataclasses import replace
import pathlib
import sys
import tempfile
import unittest

import numpy as np
import py3d


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from vehicle_proxy.p3d_graph import (
    GraphError,
    direct_host_points,
    geometry_digest,
    resolve_graph,
    structural_digest,
)
from vehicle_proxy_fixtures import make_graph_fixture, make_triangle_lod


class TestVehicleProxyGraph(unittest.TestCase):
    def test_resolves_only_reachable_proxy_and_excludes_proxy_faces_from_direct_shell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest = make_graph_fixture(root)
            nodes = resolve_graph(manifest)
            self.assertEqual(1, len(nodes))
            node = nodes[0]
            self.assertEqual("body", node.piece)
            self.assertEqual("body", node.proxy_basename)
            self.assertEqual((0.0, 0.0, 0.0), node.anchor)
            self.assertEqual(pathlib.Path("data/proxy/body.p3d"), node.addon_relative_path)
            self.assertFalse(node.ambiguous)
            with node.host_path.open("rb") as handle:
                host = py3d.P3D(handle)
            direct = direct_host_points(host.lods[0])
            self.assertEqual((3, 3), direct.shape)
            np.testing.assert_allclose(
                direct,
                np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))),
            )
            for path in (node.host_path, node.proxy_path):
                with path.open("rb") as handle:
                    model = py3d.P3D(handle)
                for lod in model.lods:
                    if 0.0 <= lod.resolution < 1000.0:
                        self.assertTrue(all(point.mass is None for point in lod.points))

    def test_rejects_manifest_variant_that_is_not_reachable_from_host(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_graph_fixture(pathlib.Path(temporary))
            piece = manifest.pieces[0]
            missing = replace(piece.variants[0], expected_proxy_basename="not_present")
            unreachable = replace(manifest, pieces=(replace(piece, variants=(missing,)),))
            with self.assertRaises(GraphError):
                resolve_graph(unreachable)

    def test_rejects_ambiguous_manifest_mapping(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = make_graph_fixture(pathlib.Path(temporary))
            duplicate = replace(manifest.pieces[0], name="body_duplicate")
            ambiguous = replace(
                manifest, pieces=(manifest.pieces[0], duplicate)
            )
            with self.assertRaisesRegex(GraphError, "ambiguous"):
                resolve_graph(ambiguous)

    def test_direct_host_points_returns_empty_matrix_for_proxy_only_lod(self):
        lod = py3d.LOD()
        lod.resolution = 0.0
        lod.add_proxy("FIXTURE\\data\\proxy\\only", index=1)
        direct = direct_host_points(lod)
        self.assertEqual((0, 3), direct.shape)

    def test_direct_host_points_rejects_out_of_range_point_indexes(self):
        for label in ("negative", "upper-bound"):
            with self.subTest(label=label):
                lod = make_triangle_lod()
                point_index = -1 if label == "negative" else len(lod.points)
                lod.faces[0].vertices[0].point_index = point_index
                with self.assertRaisesRegex(GraphError, "invalid point index"):
                    direct_host_points(lod)

    def test_malformed_proxy_selection_cannot_hide_direct_geometry(self):
        lod = make_triangle_lod()
        malformed = lod.new_selection("proxy:malformed")
        malformed.faces = {lod.faces[0]: 1}
        self.assertEqual([], lod.get_proxies())

        direct = direct_host_points(lod)

        self.assertEqual((3, 3), direct.shape)
        np.testing.assert_allclose(
            direct,
            np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))),
        )

    def test_direct_host_points_rejects_inconsistent_recognized_proxy_triangle(self):
        def remove_proxy_face(lod, name):
            lod.selections[name].faces = {}

        def add_fourth_proxy_vertex(lod, name):
            face = next(iter(lod.selections[name].faces))
            face.vertices.append(face.vertices[0])

        def duplicate_proxy_point_reference(lod, name):
            face = next(iter(lod.selections[name].faces))
            face.vertices[1].point_index = face.vertices[0].point_index

        for label, mutate in (
            ("missing-face", remove_proxy_face),
            ("non-triangle-face", add_fourth_proxy_vertex),
            ("mismatched-points", duplicate_proxy_point_reference),
        ):
            with self.subTest(label=label):
                lod = py3d.LOD()
                lod.resolution = 0.0
                name = lod.add_proxy("FIXTURE\\data\\proxy\\only", index=1)
                self.assertEqual([name], [proxy["name"] for proxy in lod.get_proxies()])
                mutate(lod, name)
                with self.assertRaisesRegex(GraphError, "invalid proxy triangle"):
                    direct_host_points(lod)

    def test_structural_digest_ignores_geometric_coordinates(self):
        lod = make_triangle_lod()
        before = structural_digest(lod)
        lod.points[0].coords = (5.0, 0.0, 0.0)
        lod.facenormals[0] = (1.0, 0.0, 0.0)
        self.assertEqual(before, structural_digest(lod))

    def test_structural_digest_covers_required_semantics(self):
        def change_resolution(lod):
            lod.resolution = 1.0

        def change_topology(lod):
            lod.faces[0].vertices[0].point_index = 1

        def change_uv(lod):
            lod.faces[0].vertices[0].uv = (0.5, 0.5)

        def change_texture(lod):
            lod.faces[0].texture = "FIXTURE\\data\\other_co.paa"

        def change_material(lod):
            lod.faces[0].material = "FIXTURE\\data\\other.rvmat"

        def change_membership(lod):
            del lod.selections["zbytek"].points[lod.points[0]]

        for label, mutate in (
            ("resolution", change_resolution),
            ("topology", change_topology),
            ("uv", change_uv),
            ("texture", change_texture),
            ("material", change_material),
            ("selection-membership", change_membership),
        ):
            with self.subTest(label=label):
                lod = make_triangle_lod()
                before = structural_digest(lod)
                mutate(lod)
                self.assertNotEqual(before, structural_digest(lod))

    def test_structural_digest_is_canonical_across_membership_insertion_order(self):
        first = make_triangle_lod()
        second = make_triangle_lod()
        selection = second.selections["zbytek"]
        selection.points = dict(reversed(tuple(selection.points.items())))
        selection.faces = dict(reversed(tuple(selection.faces.items())))
        self.assertEqual(structural_digest(first), structural_digest(second))

    def test_geometry_digest_covers_points_and_face_normal_coordinates(self):
        point_lod = make_triangle_lod()
        before_point = geometry_digest(point_lod)
        point_lod.points[0].coords = (5.0, 0.0, 0.0)
        self.assertNotEqual(before_point, geometry_digest(point_lod))

        normal_lod = make_triangle_lod()
        before_normal = geometry_digest(normal_lod)
        normal_lod.facenormals[0] = (1.0, 0.0, 0.0)
        self.assertNotEqual(before_normal, geometry_digest(normal_lod))

    def test_geometry_digest_ignores_structural_and_property_changes(self):
        lod = make_triangle_lod()
        before = geometry_digest(lod)
        lod.faces[0].vertices[0].uv = (0.5, 0.5)
        lod.faces[0].texture = "FIXTURE\\data\\other_co.paa"
        lod.faces[0].material = "FIXTURE\\data\\other.rvmat"
        lod.properties["autocenter"] = "0"
        del lod.selections["zbytek"].points[lod.points[0]]
        self.assertEqual(before, geometry_digest(lod))


if __name__ == "__main__":
    unittest.main()
