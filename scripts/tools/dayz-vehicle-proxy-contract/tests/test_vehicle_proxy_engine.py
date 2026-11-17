from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
import warnings

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from vehicle_proxy.engine import (
    compose_proxy_points,
    find_animation_overlaps,
    find_property_findings,
)
from vehicle_proxy.manifest import load_manifest
from vehicle_proxy.model_cfg import (
    ModelCfgError,
    convert_model_cfg,
    parse_animation_xml_text,
)
from vehicle_proxy_fixtures import (
    make_animated_proxy_host_lod,
    make_complete_cli_fixture,
    make_triangle_lod,
)


class TestEngineResolution(unittest.TestCase):
    def test_canonical_frame_at_origin_is_identity(self):
        points = np.asarray([[1.0, 2.0, 3.0]])
        frame = np.asarray([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], dtype=float)
        result = compose_proxy_points(points, (0, 0, 0), frame, frame)
        np.testing.assert_allclose(points, result)

    def test_composition_uses_frame_delta_then_anchor_without_bbox_recentering(self):
        points = np.asarray(((10.0, 20.0, 30.0), (12.0, 24.0, 36.0)))
        actual = np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
        canonical = np.asarray(((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))
        anchor = np.asarray((3.0, -2.0, 5.0))
        before = points.copy()

        result = compose_proxy_points(points, anchor, actual, canonical)
        expected = points @ (actual @ np.linalg.inv(canonical)).T + anchor

        np.testing.assert_allclose(expected, result)
        np.testing.assert_array_equal(before, points)
        identity_result = compose_proxy_points(points, anchor, np.eye(3), np.eye(3))
        np.testing.assert_allclose(points + anchor, identity_result)

    def test_composition_rejects_invalid_shapes_non_finite_and_singular_frames(self):
        points = np.asarray(((0.0, 0.0, 0.0),))
        non_finite_points = points.copy()
        non_finite_points[0, 1] = np.nan
        non_finite_frame = np.eye(3)
        non_finite_frame[0, 0] = np.inf
        invalid_calls = (
            lambda: compose_proxy_points(
                np.asarray((1.0, 2.0, 3.0)), (0, 0, 0), np.eye(3), np.eye(3)
            ),
            lambda: compose_proxy_points(
                np.zeros((1, 4)), (0, 0, 0), np.eye(3), np.eye(3)
            ),
            lambda: compose_proxy_points(
                non_finite_points, (0, 0, 0), np.eye(3), np.eye(3)
            ),
            lambda: compose_proxy_points(points, (0, 0), np.eye(3), np.eye(3)),
            lambda: compose_proxy_points(points, (0, np.inf, 0), np.eye(3), np.eye(3)),
            lambda: compose_proxy_points(points, (0, 0, 0), np.eye(4), np.eye(3)),
            lambda: compose_proxy_points(
                points, (0, 0, 0), non_finite_frame, np.eye(3)
            ),
            lambda: compose_proxy_points(
                points, (0, 0, 0), np.zeros((3, 3)), np.eye(3)
            ),
            lambda: compose_proxy_points(
                points, (0, 0, 0), np.eye(3), np.zeros((3, 3))
            ),
            lambda: compose_proxy_points(
                points,
                (0, 0, 0),
                np.asarray(((1, 1, 0), (0, 1, 0), (0, 0, 1)), dtype=float),
                np.eye(3),
            ),
            lambda: compose_proxy_points(
                points, (0, 0, 0), np.diag((2.0, 3.0, 4.0)), np.eye(3)
            ),
            lambda: compose_proxy_points(
                points, (0, 0, 0), np.diag((-1.0, 1.0, 1.0)), np.eye(3)
            ),
            lambda: compose_proxy_points(
                points,
                (0, 0, 0),
                np.eye(3),
                np.asarray(((1, 1, 0), (0, 1, 0), (0, 0, 1)), dtype=float),
            ),
            lambda: compose_proxy_points(
                points, (0, 0, 0), np.eye(3), np.diag((2.0, 3.0, 4.0))
            ),
            lambda: compose_proxy_points(
                points, (0, 0, 0), np.eye(3), np.diag((-1.0, 1.0, 1.0))
            ),
        )
        for invalid_call in invalid_calls:
            with self.subTest(call=invalid_call):
                with self.assertRaises(ValueError):
                    invalid_call()

    def test_composition_rejects_finite_inputs_that_overflow_without_warning(self):
        points = np.asarray(((1e308, 0.0, 0.0),))
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with self.assertRaises(ValueError):
                compose_proxy_points(
                    points, (1e308, 0.0, 0.0), np.eye(3), np.eye(3)
                )
        self.assertEqual([], caught)

    def test_missing_autocenter_is_unconfirmed_without_engine_offset_guess(self):
        lod = make_triangle_lod()
        before = np.asarray([point.coords for point in lod.points], dtype=float)
        findings = find_property_findings((lod,), (("autocenter", "0"),))
        self.assertEqual(
            ["ENGINE-AUTOCENTER-UNCONFIRMED"], [finding.code for finding in findings]
        )
        self.assertEqual("autocenter", findings[0].property_name)
        self.assertEqual("0", findings[0].expected_value)
        self.assertIsNone(findings[0].actual_value)
        np.testing.assert_array_equal(
            before, np.asarray([point.coords for point in lod.points], dtype=float)
        )

        lod.properties["autocenter"] = "0"
        self.assertEqual(
            (), find_property_findings((lod,), (("autocenter", "0"),))
        )

    def test_property_findings_cover_each_lod_and_distinguish_other_mismatches(self):
        first = make_triangle_lod()
        first.resolution = 0.0
        first.properties["autocenter"] = "1"
        second = make_triangle_lod()
        second.resolution = 1.0
        second.properties["autocenter"] = "0"
        second.properties["lodnoshadow"] = "0"

        findings = find_property_findings(
            (first, second), (("autocenter", "0"), ("lodnoshadow", "1"))
        )

        self.assertEqual(
            [
                ("ENGINE-AUTOCENTER-UNCONFIRMED", 0.0, "autocenter", "1"),
                ("ENGINE-PROPERTY-MISMATCH", 0.0, "lodnoshadow", None),
                ("ENGINE-PROPERTY-MISMATCH", 1.0, "lodnoshadow", "0"),
            ],
            [
                (
                    finding.code,
                    finding.lod_resolution,
                    finding.property_name,
                    finding.actual_value,
                )
                for finding in findings
            ],
        )

    def test_three_dash_animations_fail_but_authorized_drivewheel_passes(self):
        lod = make_animated_proxy_host_lod()
        animated = {
            "mph": ("Speed",),
            "rpm": ("RPM",),
            "fuel_1": ("Fuel",),
            "drivewheel": ("Steer",),
        }
        findings = find_animation_overlaps(
            lod,
            animated,
            {
                (
                    0.0,
                    "proxy:fixture\\data\\proxy\\mb_steering.002",
                    "drivewheel",
                )
            },
        )
        self.assertEqual(
            ["fuel_1", "mph", "rpm"], sorted(finding.selection for finding in findings)
        )
        self.assertTrue(
            all(finding.code == "ENGINE-ANIMATION-OVERLAP" for finding in findings)
        )
        self.assertTrue(
            all(finding.proxy_basename == "mb_dash" for finding in findings)
        )

    def test_overlap_authorization_requires_exact_host_proxy_and_animation_triple(self):
        lod = make_animated_proxy_host_lod()
        point_only = lod.new_selection("point_only")
        steering_proxy = lod.selections[
            "proxy:FIXTURE\\data\\proxy\\mb_steering.002"
        ]
        point_only.points = dict(steering_proxy.points)
        animated = {
            "drivewheel": ("Steer",),
            "point_only": ("PointOnly",),
            "speed": ("SourceNameOnly",),
        }

        exact_proxy = "proxy:fixture\\data\\proxy\\mb_steering.002"
        for label, authorization in (
            ("wrong-lod", {(1.0, exact_proxy, "drivewheel")}),
            (
                "crossed-proxy",
                {(0.0, "proxy:fixture\\data\\proxy\\mb_dash.001", "drivewheel")},
            ),
            ("proxy-prefix", {(0.0, exact_proxy[:-1], "drivewheel")}),
            ("animation-prefix", {(0.0, exact_proxy, "drive")}),
        ):
            with self.subTest(label=label):
                findings = find_animation_overlaps(lod, animated, authorization)
                self.assertEqual(
                    ["drivewheel"], [finding.selection for finding in findings]
                )

        exact = find_animation_overlaps(
            lod, animated, {(0.0, exact_proxy, "drivewheel")}
        )
        self.assertEqual((), exact)

    def test_missing_or_faceless_reported_proxy_emits_one_invalid_finding(self):
        proxy_name = "proxy:FIXTURE\\data\\proxy\\mb_steering.002"
        proxy = {"name": proxy_name, "path": "FIXTURE\\data\\proxy\\mb_steering"}

        class MissingSelectionLod:
            resolution = 0.0
            selections = {}

            def get_proxies(self):
                return (proxy,)

        absent = find_animation_overlaps(
            MissingSelectionLod(), {"drivewheel": ("Steer",)}, {}
        )
        self.assertEqual(
            [
                (
                    "ENGINE-PROXY-SELECTION-INVALID",
                    "mb_steering",
                    proxy_name,
                )
            ],
            [
                (finding.code, finding.proxy_basename, finding.selection)
                for finding in absent
            ],
        )

        lod = make_animated_proxy_host_lod()
        lod.selections[proxy_name].faces = {}
        faceless = find_animation_overlaps(
            lod, {"drivewheel": ("Steer",)}, {}
        )
        self.assertEqual(
            ["ENGINE-PROXY-SELECTION-INVALID"],
            [finding.code for finding in faceless],
        )
        self.assertEqual(proxy_name, faceless[0].selection)

    def test_reported_proxy_requires_one_triangular_face_matching_its_points(self):
        proxy_name = "proxy:FIXTURE\\data\\proxy\\mb_steering.002"

        multiple_faces = make_animated_proxy_host_lod()
        proxy_selection = multiple_faces.selections[proxy_name]
        dash_face = next(
            iter(
                multiple_faces.selections[
                    "proxy:FIXTURE\\data\\proxy\\mb_dash.001"
                ].faces
            )
        )
        proxy_selection.faces[dash_face] = 1

        non_triangular = make_animated_proxy_host_lod()
        face = next(iter(non_triangular.selections[proxy_name].faces))
        face.vertices.pop()

        mismatched_points = make_animated_proxy_host_lod()
        proxy_selection = mismatched_points.selections[proxy_name]
        proxy_selection.points.pop(next(iter(proxy_selection.points)))
        dash_point = next(
            iter(
                mismatched_points.selections[
                    "proxy:FIXTURE\\data\\proxy\\mb_dash.001"
                ].points
            )
        )
        proxy_selection.points[dash_point] = 1

        for label, lod in (
            ("multiple-faces", multiple_faces),
            ("non-triangular", non_triangular),
            ("point-face-mismatch", mismatched_points),
        ):
            with self.subTest(label=label):
                findings = find_animation_overlaps(
                    lod, {"drivewheel": ("Steer",)}, {}
                )
                invalid = [
                    finding
                    for finding in findings
                    if finding.proxy_basename == "mb_steering"
                ]
                self.assertEqual(
                    ["ENGINE-PROXY-SELECTION-INVALID"],
                    [finding.code for finding in invalid],
                )


class TestModelCfg(unittest.TestCase):
    def test_cfgconvert_multi_root_xml_is_parsed(self):
        xml = (
            '<?xml version="1.0" encoding="iso-8859-1"?>'
            "<CfgSkeletons></CfgSkeletons>"
            "<CfgModels><car><Animations><Speed><selection>mph</selection>"
            "</Speed></Animations></car></CfgModels>"
        )
        self.assertEqual({"mph": ("Speed",)}, parse_animation_xml_text(xml))

    def test_xml_invalid_fails_closed_and_duplicate_selections_keep_source_order(self):
        xml = """\
<?xml version="1.0" encoding="iso-8859-1"?>
<CfgSkeletons></CfgSkeletons>
<CfgModels><car><Animations>
  <Speed><selection> MPH </selection></Speed>
  <BackupSpeed><selection>mph</selection></BackupSpeed>
  <Speed><selection>mph</selection></Speed>
</Animations></car></CfgModels>
"""
        self.assertEqual(
            {"mph": ("Speed", "BackupSpeed", "Speed")},
            parse_animation_xml_text(xml),
        )
        for invalid in ("<CfgModels>", "not xml", "<?xml?><CfgModels></root>"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ModelCfgError):
                    parse_animation_xml_text(invalid)

    def test_xml_requires_cfgmodels_and_rejects_unknown_top_level_roots(self):
        self.assertEqual({}, parse_animation_xml_text("<CfgModels/>"))
        self.assertEqual(
            {},
            parse_animation_xml_text(
                "<CfgSkeletons></CfgSkeletons><CfgModels></CfgModels>"
            ),
        )
        for invalid in (
            "<foo/>",
            "<CfgSkeletons/>",
            "<CfgModels/><foo/>",
            "<foo/><CfgModels/>",
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ModelCfgError):
                    parse_animation_xml_text(invalid)

    def test_convert_model_cfg_invokes_exact_adapter_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            manifest_path, _ = make_complete_cli_fixture(root)
            manifest = load_manifest(manifest_path)
            record = root / "cfgconvert-args.json"
            shim = root / "cfgconvert_shim.py"
            shim.write_text(
                "from pathlib import Path\n"
                "import json\n"
                "import sys\n"
                "args = sys.argv[1:]\n"
                f"Path({str(record)!r}).write_text(json.dumps(args), "
                "encoding='utf-8')\n"
                "dst = Path(args[args.index('-dst') + 1])\n"
                "dst.write_text('<CfgSkeletons></CfgSkeletons><CfgModels><car>"
                "<Animations><Speed><selection>MPH</selection></Speed>"
                "</Animations></car></CfgModels>', encoding='iso-8859-1')\n",
                encoding="utf-8",
            )

            self.assertEqual(
                {"mph": ("Speed",)},
                convert_model_cfg(manifest.model_cfg, manifest.cfgconvert),
            )
            args = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual("-xml", args[0])
            self.assertEqual("-dst", args[1])
            self.assertEqual("model.xml", pathlib.Path(args[2]).name)
            self.assertEqual(str(manifest.model_cfg), args[3])

            with self.assertRaises(ModelCfgError):
                convert_model_cfg(root / "missing-model.cfg", manifest.cfgconvert)
            with self.assertRaises(ModelCfgError):
                convert_model_cfg(manifest.model_cfg, root / "missing-CfgConvert.exe")

            shim.write_text("import sys\nsys.exit(7)\n", encoding="utf-8")
            with self.assertRaisesRegex(ModelCfgError, "exit 7"):
                convert_model_cfg(manifest.model_cfg, manifest.cfgconvert)

            shim.write_text("pass\n", encoding="utf-8")
            with self.assertRaisesRegex(ModelCfgError, "did not create"):
                convert_model_cfg(manifest.model_cfg, manifest.cfgconvert)

            shim.write_text(
                "from pathlib import Path\n"
                "import sys\n"
                "args = sys.argv[1:]\n"
                "Path(args[args.index('-dst') + 1]).write_text("
                "'<CfgModels>', encoding='iso-8859-1')\n",
                encoding="utf-8",
            )
            with self.assertRaises(ModelCfgError):
                convert_model_cfg(manifest.model_cfg, manifest.cfgconvert)


if __name__ == "__main__":
    unittest.main()
