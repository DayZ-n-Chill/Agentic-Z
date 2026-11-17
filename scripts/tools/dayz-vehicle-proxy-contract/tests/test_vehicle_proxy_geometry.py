from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from vehicle_proxy.geometry import (
    GeometryError,
    apply_matrix,
    classify_fit,
    fit_surface,
    load_obj_geometry,
    select_source_points,
)
from vehicle_proxy.manifest import Thresholds


class TestSurfaceFit(unittest.TestCase):
    def setUp(self):
        self.reference = np.asarray(
            (
                (0.0, 0.0, 0.0),
                (2.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, 3.0),
                (1.0, 2.0, 3.0),
            ),
            dtype=float,
        )
        self.identity = np.eye(4)
        self.yaw180 = np.asarray(
            (
                (-1.0, 0.0, 0.0, 0.0),
                (0.0, 1.0, 0.0, 0.0),
                (0.0, 0.0, -1.0, 0.0),
                (0.0, 0.0, 0.0, 1.0),
            )
        )
        self.thresholds = Thresholds(0.01, 0.1, 0.005, 0.05)

    def test_candidate_to_reference_identity_and_translation_classification(self):
        identity_metrics = fit_surface(
            self.reference, self.reference.copy(), {"identity": self.identity}
        )
        identity_classification = classify_fit(identity_metrics, self.thresholds)
        self.assertTrue(identity_classification.passes)
        self.assertFalse(identity_classification.repairable)
        np.testing.assert_allclose(identity_metrics.matrix, self.identity, atol=1e-8)

        offset = np.asarray((0.4, -0.2, 0.1))
        candidate = self.reference + offset
        metrics = fit_surface(
            self.reference, candidate, {"identity": self.identity}
        )

        np.testing.assert_allclose(metrics.translation, -offset, atol=1e-5)
        np.testing.assert_allclose(
            apply_matrix(candidate, np.asarray(metrics.matrix)),
            self.reference,
            atol=1e-5,
        )
        self.assertLess(metrics.symmetric_p95_m, 1e-5)
        classification = classify_fit(metrics, self.thresholds)
        self.assertFalse(classification.passes)
        self.assertTrue(classification.repairable)

    def test_yaw180_seed_wins_and_invalid_seeds_fail_closed(self):
        candidate = apply_matrix(self.reference, self.yaw180)
        metrics = fit_surface(
            self.reference,
            candidate,
            {"identity": self.identity, "yaw180": self.yaw180},
        )
        self.assertEqual("yaw180", metrics.seed)
        self.assertLess(metrics.symmetric_p95_m, 1e-5)
        np.testing.assert_allclose(
            apply_matrix(candidate, np.asarray(metrics.matrix)),
            self.reference,
            atol=1e-5,
        )

        non_finite_seed = np.eye(4)
        non_finite_seed[0, 0] = np.inf
        invalid_seeds = (
            ("empty", {}),
            ("wrong-shape", {"bad": np.eye(3)}),
            ("non-finite", {"bad": non_finite_seed}),
            ("singular", {"bad": np.zeros((4, 4))}),
            ("non-affine", {"bad": np.diag((1.0, 1.0, 1.0, 2.0))}),
        )
        for label, seeds in invalid_seeds:
            with self.subTest(label=label):
                with self.assertRaises(GeometryError):
                    fit_surface(self.reference, self.reference, seeds)

        anisotropic = np.diag((2.0, 0.5, 1.0, 1.0))
        shear = np.eye(4)
        shear[0, 1] = 0.8
        translated_shear = shear.copy()
        translated_shear[:3, 3] = (0.4, -0.2, 0.1)
        for label, seed in (
            ("anisotropic-det-one", anisotropic),
            ("shear-det-one", shear),
            ("translated-shear-det-one", translated_shear),
        ):
            with self.subTest(label=label):
                candidate = apply_matrix(self.reference, np.linalg.inv(seed))
                try:
                    invalid_metrics = fit_surface(
                        self.reference, candidate, {label: seed}
                    )
                except GeometryError:
                    continue
                invalid_classification = classify_fit(
                    invalid_metrics, self.thresholds
                )
                self.fail(
                    f"non-similarity seed accepted: "
                    f"passes={invalid_classification.passes}, "
                    f"repairable={invalid_classification.repairable}"
                )

    def test_scale_distortion_and_reflection_are_never_repairable(self):
        uniform_candidate = self.reference * 1.2
        uniform_seed = np.diag((1.0 / 1.2, 1.0 / 1.2, 1.0 / 1.2, 1.0))
        uniform_metrics = fit_surface(
            self.reference, uniform_candidate, {"uniform": uniform_seed}
        )
        self.assertLess(uniform_metrics.symmetric_p95_m, 1e-5)
        self.assertGreater(
            abs(uniform_metrics.uniform_scale - 1.0), self.thresholds.scale_error
        )
        uniform_classification = classify_fit(uniform_metrics, self.thresholds)
        self.assertFalse(uniform_classification.passes)
        self.assertFalse(uniform_classification.repairable)

        distorted_candidate = self.reference * np.asarray((1.2, 1.0, 0.8))
        distorted_metrics = fit_surface(
            self.reference, distorted_candidate, {"identity": self.identity}
        )
        self.assertGreater(
            distorted_metrics.symmetric_p95_m, self.thresholds.p95_m
        )
        distorted_classification = classify_fit(
            distorted_metrics, self.thresholds
        )
        self.assertFalse(distorted_classification.passes)
        self.assertFalse(distorted_classification.repairable)

        reflection = np.diag((-1.0, 1.0, 1.0, 1.0))
        reflected_candidate = apply_matrix(self.reference, reflection)
        reflected_metrics = fit_surface(
            self.reference, reflected_candidate, {"reflection": reflection}
        )
        self.assertLess(reflected_metrics.symmetric_p95_m, 1e-5)
        self.assertLess(reflected_metrics.determinant, 0.0)
        reflected_classification = classify_fit(
            reflected_metrics, self.thresholds
        )
        self.assertFalse(reflected_classification.passes)
        self.assertFalse(reflected_classification.repairable)
        self.assertIn("reflection detected", reflected_classification.reasons)

    def test_obj_face_partition_and_invalid_geometry_fail_closed(self):
        obj_text = """\
v 0 0 0
v 1 0 0
v 0 1 0
v 0 0 1
usemtl CORE_PAINT
f 1 2 3
usemtl DETAIL
f 1 3 4
"""
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "source.obj"
            path.write_text(obj_text, encoding="utf-8")
            geometry = load_obj_geometry(path)

        direct = select_source_points(geometry, ("CORE_",), (), complement=False)
        proxy = select_source_points(geometry, ("CORE_",), (), complement=True)
        self.assertEqual(
            {(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)},
            set(map(tuple, direct)),
        )
        self.assertEqual(
            {(0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)},
            set(map(tuple, proxy)),
        )
        self.assertEqual(
            {(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)},
            set(map(tuple, direct)) & set(map(tuple, proxy)),
        )

        invalid_clouds = (
            ("shape", np.asarray((0.0, 1.0, 2.0))),
            ("empty", np.empty((0, 3))),
            ("non-finite", np.asarray(((0.0, 0.0, np.nan),) * 3)),
        )
        for label, cloud in invalid_clouds:
            with self.subTest(label=label):
                with self.assertRaises(GeometryError):
                    fit_surface(cloud, self.reference, {"identity": self.identity})


if __name__ == "__main__":
    unittest.main()
