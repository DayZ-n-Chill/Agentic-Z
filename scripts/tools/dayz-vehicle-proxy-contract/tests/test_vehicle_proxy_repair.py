from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
import py3d


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from vehicle_proxy.p3d_graph import ProxyNode, geometry_digest, structural_digest
from vehicle_proxy.repair import (
    RepairOperation,
    RepairRefused,
    plan_repairs,
    stage_one,
    stage_repairs,
)
from vehicle_proxy_fixtures import (
    load_digests,
    load_model,
    make_proxy_file_and_node,
    make_triangle_lod,
)


def _sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_multilod_proxy(root: pathlib.Path):
    addon = root / "addon"
    relative = pathlib.Path("data") / "proxy" / "body.p3d"
    source = addon / relative
    source.parent.mkdir(parents=True)

    visual = make_triangle_lod()
    visual.properties["class"] = "visual"
    visual.facenormals[0] = (0.0, 0.0, 1.0)

    geometry = make_triangle_lod()
    geometry.resolution = 1.0e13
    geometry.properties["class"] = "house"
    geometry.facenormals[0] = (0.0, 1.0, 0.0)
    for point, mass in zip(geometry.points, (10.0, 20.0, 30.0)):
        point.coords = tuple(value + 0.25 for value in point.coords)
        point.mass = mass

    model = py3d.P3D()
    model.lods.extend((visual, geometry))
    model.save(source, verify=True)
    node = ProxyNode(
        piece="body",
        host_lod=0.0,
        host_path=addon / "host.p3d",
        proxy_path=source,
        addon_relative_path=relative,
        proxy_selection="proxy:FIXTURE\\data\\proxy\\body.001",
        proxy_basename="body",
        anchor=(0.0, 0.0, 0.0),
        frame=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        ambiguous=False,
        include_host_direct=False,
        allowed_animated_selections=(),
        repairs=("set-autocenter-zero", "yaw180", "affine-fit"),
        allowed_fit_components=("translation", "rotation", "uniform-scale"),
    )
    return source, node


def _topology(lod) -> tuple[tuple[tuple[int, int], ...], ...]:
    return tuple(
        tuple((int(vertex.point_index), int(vertex.normal_index)) for vertex in face.vertices)
        for face in lod.faces
    )


class TestRepair(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.tempdir = pathlib.Path(self._temporary.name)
        self.addon = self.tempdir / "addon"

    def tearDown(self):
        self._temporary.cleanup()

    def test_property_operation_preserves_geometry(self):
        src, node = make_proxy_file_and_node(
            self.addon, repairs=("set-autocenter-zero",)
        )
        before = load_digests(src)
        dst = stage_one(node, "set-autocenter-zero", self.tempdir / "stage")
        after = load_digests(dst)
        self.assertEqual(before.geometry, after.geometry)
        self.assertEqual(before.structural, after.structural)
        self.assertEqual({"autocenter": "0"}, after.properties)

    def test_yaw180_changes_only_points_and_normals(self):
        src, node = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        before = load_model(src)
        dst = stage_one(node, "yaw180", self.tempdir / "stage")
        after = load_model(dst)
        self.assertEqual(
            structural_digest(before.lods[0]), structural_digest(after.lods[0])
        )
        for old, new in zip(before.lods[0].points, after.lods[0].points):
            self.assertEqual((-old.coords[0], old.coords[1], -old.coords[2]), new.coords)
            self.assertIs(old.mass, new.mass)
        for old, new in zip(before.lods[0].facenormals, after.lods[0].facenormals):
            self.assertEqual((-old[0], old[1], -old[2]), new)
        self.assertEqual(_topology(before.lods[0]), _topology(after.lods[0]))
        self.assertEqual(dict(before.lods[0].properties), dict(after.lods[0].properties))

    def test_unauthorized_operation_is_rejected(self):
        _, node = make_proxy_file_and_node(self.addon, repairs=())
        with self.assertRaises(RepairRefused):
            stage_one(node, "yaw180", self.tempdir / "stage")

    def test_affine_translation_requires_component_authorization(self):
        matrix = np.eye(4)
        matrix[:3, 3] = (0.25, -0.10, 0.05)
        _, denied = make_proxy_file_and_node(
            self.addon / "denied-addon",
            repairs=("affine-fit",),
            allowed_fit_components=(),
        )
        with self.assertRaises(RepairRefused):
            stage_one(
                denied,
                "affine-fit",
                self.tempdir / "denied-stage",
                fit_matrix=matrix,
            )
        src, allowed = make_proxy_file_and_node(
            self.addon / "allowed-addon",
            repairs=("affine-fit",),
            allowed_fit_components=("translation",),
        )
        dst = stage_one(
            allowed,
            "affine-fit",
            self.tempdir / "allowed-stage",
            fit_matrix=matrix,
        )
        before = np.asarray(load_model(src).lods[0].points[0].coords)
        after = np.asarray(load_model(dst).lods[0].points[0].coords)
        np.testing.assert_allclose(after, before + matrix[:3, 3])

    def test_plan_filters_sorts_and_freezes_measured_matrices(self):
        _, base = make_proxy_file_and_node(
            self.addon,
            repairs=("affine-fit",),
            allowed_fit_components=("translation",),
        )
        matrix = np.eye(4)
        matrix[0, 3] = 0.25
        late = replace(base, piece="z-piece", host_lod=2.0)
        early = replace(base, piece="a-piece", host_lod=1.0)
        skipped = replace(base, piece="skip", host_lod=0.0, repairs=())
        plan = plan_repairs(
            (late, skipped, early),
            "affine-fit",
            {
                (late.piece, late.host_lod): matrix,
                (early.piece, early.host_lod): matrix,
            },
        )
        self.assertEqual((early, late), tuple(item.node for item in plan))
        matrix[0, 3] = 99.0
        self.assertEqual(0.25, plan[0].fit_matrix[0][3])
        with self.assertRaises(TypeError):
            plan[0].fit_matrix[0][3] = 1.0
        with self.assertRaises(FrozenInstanceError):
            plan[0].operation = "yaw180"

    def test_plan_fails_without_authorized_nodes_or_required_matrix(self):
        _, node = make_proxy_file_and_node(self.addon, repairs=())
        with self.assertRaises(RepairRefused):
            plan_repairs((node,), "yaw180")
        affine = replace(node, repairs=("affine-fit",))
        with self.assertRaises(RepairRefused):
            plan_repairs((affine,), "affine-fit", {})

    def test_batch_planning_and_staging_is_deterministic(self):
        source, body = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        dash_relative = pathlib.Path("data") / "proxy" / "dash.p3d"
        dash_source = self.addon / dash_relative
        dash_source.write_bytes(source.read_bytes())
        dash = replace(
            body,
            piece="dash",
            host_lod=1.0,
            proxy_path=dash_source,
            addon_relative_path=dash_relative,
            proxy_basename="dash",
        )
        plan = plan_repairs((dash, body), "yaw180")
        outputs = stage_repairs(plan, self.tempdir / "stage")
        self.assertEqual(
            (
                self.tempdir / "stage" / body.addon_relative_path,
                self.tempdir / "stage" / dash.addon_relative_path,
            ),
            outputs,
        )
        self.assertTrue(all(path.is_file() for path in outputs))

    def test_paths_reject_escape_absolute_inconsistency_and_addon_tree(self):
        _, node = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        cases = (
            (replace(node, addon_relative_path=pathlib.Path("..") / "escape.p3d"), self.tempdir / "stage"),
            (replace(node, addon_relative_path=(self.tempdir / "absolute.p3d")), self.tempdir / "stage"),
            (replace(node, addon_relative_path=pathlib.Path("data") / "other.p3d"), self.tempdir / "stage"),
            (node, self.addon / "stage"),
        )
        for invalid, staging in cases:
            with self.subTest(relative=invalid.addon_relative_path, staging=staging):
                with self.assertRaises(RepairRefused):
                    stage_one(invalid, "yaw180", staging)

    def test_batch_rejects_duplicate_destination_and_source_alias(self):
        _, first = make_proxy_file_and_node(
            self.tempdir / "addon-a", repairs=("yaw180",)
        )
        _, second = make_proxy_file_and_node(
            self.tempdir / "addon-b", repairs=("yaw180",)
        )
        duplicate = (
            RepairOperation(first, "yaw180"),
            RepairOperation(second, "yaw180"),
        )
        with self.assertRaises(RepairRefused):
            stage_repairs(duplicate, self.tempdir / "stage")
        with self.assertRaises(RepairRefused):
            stage_repairs(duplicate, self.tempdir / "addon-b")

    def test_source_hash_is_unchanged_by_staging(self):
        source, node = make_proxy_file_and_node(
            self.addon, repairs=("set-autocenter-zero",)
        )
        before = _sha256(source)
        destination = stage_one(
            node, "set-autocenter-zero", self.tempdir / "stage"
        )
        self.assertNotEqual(source.resolve(), destination.resolve())
        self.assertEqual(before, _sha256(source))

    def test_preexisting_destination_is_refused_and_unchanged(self):
        _, node = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        staging = self.tempdir / "stage"
        destination = staging / node.addon_relative_path
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"preexisting-staging-sentinel")
        before = _sha256(destination)

        with self.assertRaises(RepairRefused):
            stage_one(node, "yaw180", staging)

        self.assertEqual(before, _sha256(destination))
        self.assertEqual(b"preexisting-staging-sentinel", destination.read_bytes())

    def test_second_operation_failure_leaves_no_visible_outputs(self):
        source, first = make_proxy_file_and_node(
            self.addon, repairs=("yaw180",)
        )
        second_relative = pathlib.Path("data") / "proxy" / "broken.p3d"
        second_source = self.addon / second_relative
        second_source.write_bytes(b"not-an-mlod-p3d")
        second = replace(
            first,
            piece="broken",
            host_lod=1.0,
            proxy_path=second_source,
            addon_relative_path=second_relative,
            proxy_basename="broken",
        )
        staging = self.tempdir / "stage"
        plan = (
            RepairOperation(first, "yaw180"),
            RepairOperation(second, "yaw180"),
        )

        with self.assertRaises(RepairRefused):
            stage_repairs(plan, staging)

        self.assertEqual([], list(staging.rglob("*.p3d")))
        self.assertTrue(source.is_file())
        self.assertTrue(second_source.is_file())

    def test_concurrent_source_mutation_leaves_no_visible_output(self):
        source, node = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        staging = self.tempdir / "stage"
        destination = staging / node.addon_relative_path
        original_save = py3d.P3D.save
        mutated = False

        def save_then_mutate(model, path, verify=True, backup_dir=None):
            nonlocal mutated
            result = original_save(
                model, path, verify=verify, backup_dir=backup_dir
            )
            if not mutated:
                source.write_bytes(source.read_bytes() + b"concurrent-mutation")
                mutated = True
            return result

        with mock.patch.object(py3d.P3D, "save", new=save_then_mutate), mock.patch(
            "vehicle_proxy.repair.os.rename", wraps=os.rename
        ) as commit:
            with self.assertRaises(RepairRefused):
                stage_one(node, "yaw180", staging)

        self.assertTrue(mutated)
        commit.assert_not_called()
        self.assertFalse(destination.exists())
        self.assertEqual([], list(staging.rglob("*.p3d")))

    def test_existing_or_raced_staging_root_is_refused_unchanged(self):
        _, node = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        existing = self.tempdir / "existing-stage"
        existing.mkdir()
        existing_sentinel = existing / "sentinel.txt"
        existing_sentinel.write_bytes(b"existing-stage-owner")

        with self.assertRaises(RepairRefused):
            stage_one(node, "yaw180", existing)

        self.assertEqual(b"existing-stage-owner", existing_sentinel.read_bytes())
        self.assertEqual([], list(existing.rglob("*.p3d")))

        raced = self.tempdir / "raced-stage"
        raced_sentinel = raced / "race-owner.txt"
        real_rename = os.rename

        def create_destination_then_rename(source, destination):
            destination = pathlib.Path(destination)
            destination.mkdir()
            (destination / raced_sentinel.name).write_bytes(b"raced-stage-owner")
            return real_rename(source, destination)

        with mock.patch(
            "vehicle_proxy.repair.os.rename", new=create_destination_then_rename
        ):
            with self.assertRaises(RepairRefused):
                stage_one(node, "yaw180", raced)

        self.assertEqual(b"raced-stage-owner", raced_sentinel.read_bytes())
        self.assertEqual([], list(raced.rglob("*.p3d")))
        self.assertEqual(
            [], list(self.tempdir.glob(f".{raced.name}.vehicle-proxy-repair-*"))
        )

    def test_directory_rename_failure_cleans_private_sibling_and_output(self):
        _, node = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        staging = self.tempdir / "stage"

        with mock.patch(
            "vehicle_proxy.repair.os.rename",
            side_effect=PermissionError("injected directory rename failure"),
        ):
            with self.assertRaises(RepairRefused):
                stage_one(node, "yaw180", staging)

        self.assertFalse(staging.exists())
        self.assertEqual(
            [], list(self.tempdir.glob(f".{staging.name}.vehicle-proxy-repair-*"))
        )

    def test_successful_batch_uses_one_complete_directory_rename_only(self):
        source, body = make_proxy_file_and_node(self.addon, repairs=("yaw180",))
        dash_relative = pathlib.Path("data") / "proxy" / "dash-atomic.p3d"
        dash_source = self.addon / dash_relative
        dash_source.write_bytes(source.read_bytes())
        dash = replace(
            body,
            piece="dash-atomic",
            host_lod=1.0,
            proxy_path=dash_source,
            addon_relative_path=dash_relative,
            proxy_basename="dash-atomic",
        )
        staging = self.tempdir / "stage"
        plan = (
            RepairOperation(body, "yaw180"),
            RepairOperation(dash, "yaw180"),
        )
        rename_calls = []
        link_calls = []
        real_rename = os.rename
        real_link = os.link

        def observe_complete_tree(source_tree, destination):
            source_tree = pathlib.Path(source_tree)
            destination = pathlib.Path(destination)
            self.assertEqual(staging.parent, source_tree.parent)
            self.assertEqual(staging, destination)
            self.assertFalse(destination.exists())
            self.assertTrue((source_tree / body.addon_relative_path).is_file())
            self.assertTrue((source_tree / dash.addon_relative_path).is_file())
            rename_calls.append((source_tree, destination))
            return real_rename(source_tree, destination)

        def observe_link(source_path, destination_path):
            link_calls.append((source_path, destination_path))
            return real_link(source_path, destination_path)

        with mock.patch(
            "vehicle_proxy.repair.os.rename", new=observe_complete_tree
        ), mock.patch("vehicle_proxy.repair.os.link", new=observe_link):
            outputs = stage_repairs(plan, staging)

        self.assertEqual(1, len(rename_calls))
        self.assertEqual([], link_calls)
        self.assertEqual(
            (
                staging / body.addon_relative_path,
                staging / dash.addon_relative_path,
            ),
            outputs,
        )
        self.assertTrue(all(path.is_file() for path in outputs))

    def test_affine_rejects_reflection_shear_and_nonuniform_scale(self):
        _, node = make_proxy_file_and_node(
            self.addon,
            repairs=("affine-fit",),
            allowed_fit_components=(
                "translation",
                "rotation",
                "reflection",
                "uniform-scale",
            ),
        )
        reflection = np.diag((-1.0, 1.0, 1.0, 1.0))
        shear = np.eye(4)
        shear[0, 1] = 0.25
        nonuniform = np.diag((2.0, 1.0, 1.0, 1.0))
        for label, matrix in (
            ("reflection", reflection),
            ("shear", shear),
            ("nonuniform", nonuniform),
        ):
            with self.subTest(label=label):
                with self.assertRaises(RepairRefused):
                    stage_one(
                        node,
                        "affine-fit",
                        self.tempdir / label,
                        fit_matrix=matrix,
                    )

    def test_affine_transforms_all_lods_normals_and_preserves_mass_and_winding(self):
        source, node = _make_multilod_proxy(self.tempdir)
        angle = np.deg2rad(90.0)
        rotation = np.asarray(
            (
                (np.cos(angle), -np.sin(angle), 0.0),
                (np.sin(angle), np.cos(angle), 0.0),
                (0.0, 0.0, 1.0),
            )
        )
        matrix = np.eye(4)
        matrix[:3, :3] = 1.5 * rotation
        matrix[:3, 3] = (0.25, -0.5, 0.75)
        before = load_model(source)
        destination = stage_one(
            node,
            "affine-fit",
            self.tempdir / "stage",
            fit_matrix=matrix,
        )
        after = load_model(destination)
        self.assertEqual(len(before.lods), len(after.lods))
        for old_lod, new_lod in zip(before.lods, after.lods):
            self.assertEqual(structural_digest(old_lod), structural_digest(new_lod))
            self.assertEqual(dict(old_lod.properties), dict(new_lod.properties))
            self.assertEqual(_topology(old_lod), _topology(new_lod))
            self.assertEqual(
                tuple(point.mass for point in old_lod.points),
                tuple(point.mass for point in new_lod.points),
            )
            for old, new in zip(old_lod.points, new_lod.points):
                expected = matrix[:3, :3] @ np.asarray(old.coords) + matrix[:3, 3]
                np.testing.assert_allclose(new.coords, expected, rtol=1e-6, atol=1e-6)
            for old, new in zip(old_lod.facenormals, new_lod.facenormals):
                expected = rotation @ np.asarray(old)
                np.testing.assert_allclose(new, expected, rtol=1e-6, atol=1e-6)
        self.assertTrue(all(point.mass is None for point in after.lods[0].points))
        self.assertEqual((10.0, 20.0, 30.0), tuple(p.mass for p in after.lods[1].points))


if __name__ == "__main__":
    unittest.main()
