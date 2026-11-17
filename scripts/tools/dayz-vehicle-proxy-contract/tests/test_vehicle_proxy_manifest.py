import copy
from dataclasses import FrozenInstanceError
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import vehicle_proxy.manifest as manifest_module
from vehicle_proxy.manifest import ManifestError, load_manifest


def _payload(root):
    return {
        "schema_version": 1,
        "vehicle": "fixture",
        "addon_root": str(root),
        "host_p3d": str(root / "host.p3d"),
        "model_cfg": str(root / "model.cfg"),
        "cfgconvert": str(root / "CfgConvert.exe"),
        "deployed_pbo": str(root / "fixture.pbo"),
        "pbo_prefix": "FIXTURE",
        "source": {
            "scene": str(root / "scene.gltf"),
            "scene_sha256": "a" * 64,
            "dependencies": [
                {"path": str(root / "scene.bin"), "sha256": "c" * 64}
            ],
            "matrix": [
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ],
        },
        "canonical_proxy_frame": [[-1, 0, 0], [0, 0, 1], [0, 1, 0]],
        "required_properties": {"autocenter": "0"},
        "thresholds": {
            "translation_m": 0.01,
            "rotation_deg": 0.1,
            "scale_error": 0.005,
            "p95_m": 0.05,
        },
        "pieces": [
            {
                "name": "body",
                "source_obj": str(root / "body.obj"),
                "source_sha256": "b" * 64,
                "include_host_direct": True,
                "allowed_animated_selections": [],
                "host_direct_material_prefixes": ["CORE_"],
                "host_direct_material_exact": [],
                "variants": [
                    {
                        "host_lod": 0.0,
                        "expected_proxy_basename": "body",
                        "repairs": ["set-autocenter-zero"],
                    }
                ],
            }
        ],
    }


class TestVehicleProxyManifest(unittest.TestCase):
    def _load_payload(self, root, payload):
        path = root / "manifest.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return load_manifest(path)

    def test_loads_absolute_paths_and_variant_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            payload = _payload(root)
            manifest = self._load_payload(root, payload)
            stored_paths = (
                manifest.addon_root,
                manifest.host_p3d,
                manifest.model_cfg,
                manifest.cfgconvert,
                manifest.deployed_pbo,
                manifest.source_scene,
                manifest.source_dependencies[0].path,
                manifest.pieces[0].source_obj,
            )
            self.assertTrue(
                all(isinstance(value, pathlib.Path) and value.is_absolute() for value in stored_paths)
            )
            self.assertEqual("A" * 64, manifest.source_scene_sha256)
            self.assertEqual("B" * 64, manifest.pieces[0].source_sha256)
            payload["pieces"][0]["variants"][0]["repairs"] = ["warp"]
            with self.assertRaises(ManifestError):
                self._load_payload(root, payload)
        self.assertEqual("fixture", manifest.vehicle)
        self.assertEqual(
            ("set-autocenter-zero",), manifest.pieces[0].variants[0].repairs
        )

    def test_contract_models_are_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            manifest = self._load_payload(root, _payload(root))
            cases = (
                (manifest, "vehicle", "changed"),
                (manifest.pieces[0], "name", "changed"),
                (manifest.pieces[0].variants[0], "host_lod", 1.0),
                (manifest.thresholds, "translation_m", 1.0),
            )
            for value, field, replacement in cases:
                with self.subTest(type=type(value).__name__, field=field):
                    with self.assertRaises(FrozenInstanceError):
                        setattr(value, field, replacement)

    def test_allowed_host_animation_overlaps_are_optional_normalized_and_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            payload = _payload(root)
            manifest = self._load_payload(root, payload)
            self.assertEqual((), manifest.allowed_host_animation_overlaps)

            payload["allowed_host_animation_overlaps"] = [
                {
                    "host_lod": 2,
                    "proxy_selection_name": " Proxy:FIXTURE\\data\\proxy\\Wheel_1_1.001 ",
                    "animated_selection": " Wheel_1_1 ",
                }
            ]
            manifest = self._load_payload(root, payload)
            allowance = manifest.allowed_host_animation_overlaps[0]
            self.assertEqual(2.0, allowance.host_lod)
            self.assertEqual(
                "proxy:fixture\\data\\proxy\\wheel_1_1.001",
                allowance.proxy_selection_name,
            )
            self.assertEqual("wheel_1_1", allowance.animated_selection)
            with self.assertRaises(FrozenInstanceError):
                allowance.animated_selection = "changed"
            with self.assertRaises(TypeError):
                manifest.allowed_host_animation_overlaps[0] = allowance

    def test_rejects_invalid_or_duplicate_host_animation_allowances(self):
        valid = {
            "host_lod": 0,
            "proxy_selection_name": "proxy:fixture\\data\\proxy\\wheel_1_1.001",
            "animated_selection": "wheel_1_1",
        }
        invalid = (
            None,
            {},
            {**valid, "host_lod": True},
            {**valid, "host_lod": float("inf")},
            {**valid, "proxy_selection_name": ""},
            {**valid, "proxy_selection_name": 1},
            {**valid, "animated_selection": "   "},
            {**valid, "animated_selection": None},
            {**valid, "extra": "not-semantic"},
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for value in invalid:
                with self.subTest(value=repr(value)):
                    payload = _payload(root)
                    payload["allowed_host_animation_overlaps"] = [value]
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

            payload = _payload(root)
            payload["allowed_host_animation_overlaps"] = [
                valid,
                {
                    "host_lod": 0.0,
                    "proxy_selection_name": " PROXY:FIXTURE\\DATA\\PROXY\\WHEEL_1_1.001 ",
                    "animated_selection": " WHEEL_1_1 ",
                },
            ]
            with self.assertRaises(ManifestError):
                self._load_payload(root, payload)

    def test_allowed_axis_parent_selections_are_optional_normalized_and_immutable(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            payload = _payload(root)
            manifest = self._load_payload(root, payload)
            self.assertEqual((), manifest.allowed_axis_parent_selections)

            payload["allowed_axis_parent_selections"] = [
                " Wheel_1_1_Damper ",
                "wheel_1_1_steering",
            ]
            manifest = self._load_payload(root, payload)
            self.assertEqual(
                ("wheel_1_1_damper", "wheel_1_1_steering"),
                manifest.allowed_axis_parent_selections,
            )
            with self.assertRaises(TypeError):
                manifest.allowed_axis_parent_selections[0] = "changed"

    def test_rejects_invalid_allowed_axis_parent_selections(self):
        invalid = (
            None,
            {},
            "wheel_1_1_damper",
            [1],
            [""],
            ["   "],
            ["wheel_1_1_damper", "WHEEL_1_1_DAMPER"],
            ["wheel_1_1_damper", " wheel_1_1_damper "],
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for value in invalid:
                with self.subTest(value=repr(value)):
                    payload = _payload(root)
                    payload["allowed_axis_parent_selections"] = value
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_rejects_incomplete_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            path = root / "manifest.json"
            path.write_text(
                '{"schema_version":1,"vehicle":"x","addon_root":"relative","pieces":[]}',
                encoding="utf-8",
            )
            with self.assertRaises(ManifestError):
                load_manifest(path)

    def test_rejects_each_relative_stored_path(self):
        setters = (
            ("addon_root", lambda p: p.__setitem__("addon_root", "relative")),
            ("host_p3d", lambda p: p.__setitem__("host_p3d", "relative")),
            ("model_cfg", lambda p: p.__setitem__("model_cfg", "relative")),
            ("cfgconvert", lambda p: p.__setitem__("cfgconvert", "relative")),
            ("deployed_pbo", lambda p: p.__setitem__("deployed_pbo", "relative")),
            ("source.scene", lambda p: p["source"].__setitem__("scene", "relative")),
            (
                "source.dependencies.path",
                lambda p: p["source"]["dependencies"][0].__setitem__("path", "relative"),
            ),
            (
                "pieces.source_obj",
                lambda p: p["pieces"][0].__setitem__("source_obj", "relative"),
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for field, setter in setters:
                with self.subTest(field=field):
                    payload = _payload(root)
                    setter(payload)
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_schema_errors_are_manifest_errors_but_io_errors_are_not_wrapped(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            invalid_json = root / "invalid.json"
            invalid_json.write_text("{", encoding="utf-8")
            with self.assertRaises(ManifestError):
                load_manifest(invalid_json)
            with self.assertRaises(FileNotFoundError):
                load_manifest(root / "missing.json")

    def test_rejects_missing_nested_fields_as_manifest_error(self):
        mutators = (
            ("source.matrix", lambda p: p["source"].pop("matrix")),
            ("source.scene_sha256", lambda p: p["source"].pop("scene_sha256")),
            (
                "source.dependencies.sha256",
                lambda p: p["source"]["dependencies"][0].pop("sha256"),
            ),
            ("pieces.variants", lambda p: p["pieces"][0].pop("variants")),
            (
                "pieces.variants.expected_proxy_basename",
                lambda p: p["pieces"][0]["variants"][0].pop(
                    "expected_proxy_basename"
                ),
            ),
            ("thresholds.p95_m", lambda p: p["thresholds"].pop("p95_m")),
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for field, mutate in mutators:
                with self.subTest(field=field):
                    payload = _payload(root)
                    mutate(payload)
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_rejects_malformed_matrix_and_frame_structures(self):
        mutators = (
            ("matrix_null", lambda p: p["source"].__setitem__("matrix", None)),
            (
                "matrix_null_row",
                lambda p: p["source"]["matrix"].__setitem__(0, None),
            ),
            (
                "matrix_string_rows",
                lambda p: p["source"].__setitem__(
                    "matrix", ["1000", "0100", "0010", "0001"]
                ),
            ),
            (
                "matrix_wrong_row_count",
                lambda p: p["source"].__setitem__("matrix", [[1, 0, 0, 0]]),
            ),
            (
                "matrix_wrong_column_count",
                lambda p: p["source"]["matrix"].__setitem__(0, [1, 0, 0]),
            ),
            (
                "frame_string_rows",
                lambda p: p.__setitem__(
                    "canonical_proxy_frame", ["100", "010", "001"]
                ),
            ),
            (
                "frame_wrong_row_count",
                lambda p: p.__setitem__("canonical_proxy_frame", [[1, 0, 0]]),
            ),
            (
                "frame_wrong_column_count",
                lambda p: p["canonical_proxy_frame"].__setitem__(0, [1, 0]),
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for case, mutate in mutators:
                with self.subTest(case=case):
                    payload = _payload(root)
                    mutate(payload)
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_rejects_non_numeric_boolean_or_nonfinite_matrix_cells(self):
        cells = ("1", True, float("nan"), float("inf"), float("-inf"))
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for field in ("matrix", "frame"):
                for value in cells:
                    with self.subTest(field=field, value=repr(value)):
                        payload = _payload(root)
                        target = (
                            payload["source"]["matrix"]
                            if field == "matrix"
                            else payload["canonical_proxy_frame"]
                        )
                        target[0][0] = value
                        with self.assertRaises(ManifestError):
                            self._load_payload(root, payload)

    def test_rejects_malformed_hashes_as_manifest_error(self):
        mutators = (
            ("scene_hash_integer", lambda p: p["source"].__setitem__("scene_sha256", 1)),
            ("scene_hash_short", lambda p: p["source"].__setitem__("scene_sha256", "a")),
            (
                "dependency_hash_integer",
                lambda p: p["source"]["dependencies"][0].__setitem__("sha256", 1),
            ),
            (
                "piece_hash_integer",
                lambda p: p["pieces"][0].__setitem__("source_sha256", 1),
            ),
            (
                "piece_hash_non_hex",
                lambda p: p["pieces"][0].__setitem__("source_sha256", "z" * 64),
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for case, mutate in mutators:
                with self.subTest(case=case):
                    payload = _payload(root)
                    mutate(payload)
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_rejects_invalid_repairs_and_fit_component_sequences(self):
        mutators = (
            (
                "repairs_null",
                lambda p: p["pieces"][0]["variants"][0].__setitem__("repairs", None),
            ),
            (
                "repair_non_string",
                lambda p: p["pieces"][0]["variants"][0].__setitem__(
                    "repairs", [{"name": "warp"}]
                ),
            ),
            (
                "repair_unknown",
                lambda p: p["pieces"][0]["variants"][0].__setitem__(
                    "repairs", ["warp"]
                ),
            ),
            (
                "fit_components_null",
                lambda p: p["pieces"][0]["variants"][0].__setitem__(
                    "allowed_fit_components", None
                ),
            ),
            (
                "fit_component_non_string",
                lambda p: p["pieces"][0]["variants"][0].__setitem__(
                    "allowed_fit_components", [{"name": "rotation"}]
                ),
            ),
            (
                "fit_component_unknown",
                lambda p: p["pieces"][0]["variants"][0].__setitem__(
                    "allowed_fit_components", ["shear"]
                ),
            ),
            (
                "fit_without_affine_repair",
                lambda p: p["pieces"][0]["variants"][0].__setitem__(
                    "allowed_fit_components", ["translation"]
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for case, mutate in mutators:
                with self.subTest(case=case):
                    payload = _payload(root)
                    mutate(payload)
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_rejects_duplicate_variant_lods(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            payload = _payload(root)
            variant = payload["pieces"][0]["variants"][0]
            payload["pieces"][0]["variants"].append(copy.deepcopy(variant))
            with self.assertRaises(ManifestError):
                self._load_payload(root, payload)

    def test_rejects_non_numeric_boolean_or_nonfinite_host_lod(self):
        values = ("0.0", True, float("nan"), float("inf"), float("-inf"))
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for value in values:
                with self.subTest(value=repr(value)):
                    payload = _payload(root)
                    payload["pieces"][0]["variants"][0]["host_lod"] = value
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_rejects_duplicate_nan_variant_lods(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            payload = _payload(root)
            variant = payload["pieces"][0]["variants"][0]
            variant["host_lod"] = "NaN"
            payload["pieces"][0]["variants"].append(copy.deepcopy(variant))
            with self.assertRaises(ManifestError):
                self._load_payload(root, payload)

    def test_requires_exact_boolean_for_include_host_direct(self):
        values = ("false", 0, 1, None, [])
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for value in values:
                with self.subTest(value=repr(value)):
                    payload = _payload(root)
                    payload["pieces"][0]["include_host_direct"] = value
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_schema_version_requires_exact_integer_one(self):
        values = (True, 1.0, "1", None, 0, 2)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for value in values:
                with self.subTest(value=repr(value)):
                    payload = _payload(root)
                    payload["schema_version"] = value
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)

    def test_thresholds_require_finite_json_numbers(self):
        fields = ("translation_m", "rotation_deg", "scale_error", "p95_m")
        values = ("0.01", True, float("nan"), float("inf"), float("-inf"))
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for field in fields:
                for value in values:
                    with self.subTest(field=field, value=repr(value)):
                        payload = _payload(root)
                        payload["thresholds"][field] = value
                        with self.assertRaises(ManifestError):
                            self._load_payload(root, payload)

    def test_stored_string_scalars_require_exact_strings(self):
        setters = (
            ("vehicle", lambda p, value: p.__setitem__("vehicle", value)),
            ("pbo_prefix", lambda p, value: p.__setitem__("pbo_prefix", value)),
            (
                "pieces.name",
                lambda p, value: p["pieces"][0].__setitem__("name", value),
            ),
            (
                "pieces.variants.expected_proxy_basename",
                lambda p, value: p["pieces"][0]["variants"][0].__setitem__(
                    "expected_proxy_basename", value
                ),
            ),
        )
        values = ([], {}, 1, True, None)
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for field, setter in setters:
                for value in values:
                    with self.subTest(field=field, value=repr(value)):
                        payload = _payload(root)
                        setter(payload, copy.deepcopy(value))
                        with self.assertRaises(ManifestError):
                            self._load_payload(root, payload)

    def test_required_properties_requires_string_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for value in ([], None, "autocenter=0"):
                with self.subTest(container=repr(value)):
                    payload = _payload(root)
                    payload["required_properties"] = value
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)
            for value in (1, True, [], {}, None):
                with self.subTest(value=repr(value)):
                    payload = _payload(root)
                    payload["required_properties"] = {"autocenter": value}
                    with self.assertRaises(ManifestError):
                        self._load_payload(root, payload)
            payload = _payload(root)
            payload["required_properties"] = {1: "0"}
            with self.assertRaises(ManifestError):
                manifest_module._parse_manifest(payload)

    def test_structural_containers_require_exact_json_shapes(self):
        cases = (
            (
                "source",
                lambda p, value: p.__setitem__("source", value),
                ([], None, "invalid"),
            ),
            (
                "thresholds",
                lambda p, value: p.__setitem__("thresholds", value),
                ([], None, "invalid"),
            ),
            (
                "pieces",
                lambda p, value: p.__setitem__("pieces", value),
                ({}, None, "invalid"),
            ),
            (
                "pieces.item",
                lambda p, value: p["pieces"].__setitem__(0, value),
                ([], None, "invalid"),
            ),
            (
                "pieces.variants",
                lambda p, value: p["pieces"][0].__setitem__("variants", value),
                ({}, None, "invalid"),
            ),
            (
                "pieces.variants.item",
                lambda p, value: p["pieces"][0]["variants"].__setitem__(0, value),
                ([], None, "invalid"),
            ),
            (
                "source.dependencies",
                lambda p, value: p["source"].__setitem__("dependencies", value),
                ({}, None, "invalid"),
            ),
            (
                "source.dependencies.item",
                lambda p, value: p["source"]["dependencies"].__setitem__(0, value),
                ([], None, "invalid"),
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            for field, setter, values in cases:
                for value in values:
                    with self.subTest(field=field, value=repr(value)):
                        payload = _payload(root)
                        setter(payload, copy.deepcopy(value))
                        with self.assertRaises(ManifestError):
                            self._load_payload(root, payload)

    def test_allows_extra_keys_empty_strings_and_unbounded_thresholds(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            payload = _payload(root)
            payload["vehicle"] = ""
            payload["pbo_prefix"] = ""
            payload["required_properties"] = {"": ""}
            payload["pieces"][0]["name"] = ""
            payload["pieces"][0]["variants"][0]["expected_proxy_basename"] = ""
            payload["thresholds"] = {
                "translation_m": -1.0,
                "rotation_deg": 0,
                "scale_error": -0.5,
                "p95_m": 0.0,
                "extra": "ignored",
            }
            payload["extra"] = "ignored"
            payload["source"]["extra"] = "ignored"
            payload["source"]["dependencies"][0]["extra"] = "ignored"
            payload["pieces"][0]["extra"] = "ignored"
            payload["pieces"][0]["variants"][0]["extra"] = "ignored"
            manifest = self._load_payload(root, payload)
        self.assertEqual("", manifest.vehicle)
        self.assertEqual("", manifest.pbo_prefix)
        self.assertEqual("", manifest.pieces[0].name)
        self.assertEqual("", manifest.pieces[0].variants[0].expected_proxy_basename)
        self.assertEqual((("", ""),), manifest.required_properties)
        self.assertEqual(-1.0, manifest.thresholds.translation_m)
        self.assertEqual(0.0, manifest.thresholds.rotation_deg)
        self.assertEqual(-0.5, manifest.thresholds.scale_error)
        self.assertEqual(0.0, manifest.thresholds.p95_m)

    def test_permission_whitelists_are_private_and_immutable(self):
        self.assertFalse(hasattr(manifest_module, "ALLOWED_REPAIRS"))
        self.assertFalse(hasattr(manifest_module, "ALLOWED_FIT_COMPONENTS"))
        self.assertIsInstance(manifest_module._ALLOWED_REPAIRS, frozenset)
        self.assertIsInstance(manifest_module._ALLOWED_FIT_COMPONENTS, frozenset)
        with self.assertRaises(AttributeError):
            manifest_module._ALLOWED_REPAIRS.add("warp")
        with self.assertRaises(AttributeError):
            manifest_module._ALLOWED_FIT_COMPONENTS.add("shear")
