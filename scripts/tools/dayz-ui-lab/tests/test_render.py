from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


TOOL_DIR = Path(__file__).parents[1]
REPO_ROOT = TOOL_DIR.parents[1]
MODULE_PATH = TOOL_DIR / "dayz_ui_lab" / "render.py"
SCENARIO_MODULE_PATH = TOOL_DIR / "dayz_ui_lab" / "scenario.py"
SCHEMA_PATH = TOOL_DIR / "schemas" / "dayz-ui-render-v1.schema.json"
FIXTURE_DIR = TOOL_DIR / "fixtures" / "scenarios"
THREE_CARDS = FIXTURE_DIR / "three-cards" / "scenario.json"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


scenario = load_module("dayz_ui_lab_render_test_scenario", SCENARIO_MODULE_PATH)
render = load_module("dayz_ui_lab_render", MODULE_PATH) if MODULE_PATH.is_file() else None


def require_render(test_case: unittest.TestCase) -> Any:
    if render is None:
        test_case.fail("render.py does not exist")
    return render


def flatten_composition(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        result.append(node)
        result.extend(flatten_composition(node["children"]))
    return result


def iter_values(value: Any):
    yield value
    if isinstance(value, dict):
        for key in sorted(value):
            yield from iter_values(value[key])
    elif isinstance(value, list):
        for item in value:
            yield from iter_values(item)


def run_process(
    scenario_path: Path,
    viewport: str,
    work_dir: Path,
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    output_path = work_dir / "render.json"
    report_path = work_dir / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--scenario",
            str(scenario_path),
            "--state",
            "populated",
            "--viewport",
            viewport,
            "--out",
            str(output_path),
            "--report",
            str(report_path),
        ],
        cwd=work_dir,
        check=False,
        capture_output=True,
        text=True,
    )
    return result, output_path, report_path


class RenderSchemaTests(unittest.TestCase):
    def test_schema_is_versioned_strict_and_marks_raster_noncanonical(self) -> None:
        self.assertTrue(SCHEMA_PATH.is_file(), "render schema does not exist")
        document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            document["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )
        self.assertFalse(document["additionalProperties"])
        self.assertEqual(
            document["properties"]["schema_version"]["enum"],
            ["dayz-ui-render-v1"],
        )
        canonical = document["properties"]["canonical"]["properties"]
        self.assertEqual(canonical["semantic"]["enum"], [True])
        self.assertEqual(canonical["raster"]["enum"], [False])

    def test_emitted_document_validates_and_unknown_fields_fail_closed(self) -> None:
        module = require_render(self)
        document = module.render_document(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )
        module.validate_render_document(document)

        mutated = dict(document)
        mutated["unexpected"] = True
        with self.assertRaises(module.RenderError) as raised:
            module.validate_render_document(mutated)
        self.assertEqual(raised.exception.code, "RENDER-SCHEMA-INVALID")

    def test_absolute_source_path_fails_closed(self) -> None:
        module = require_render(self)
        document = module.render_document(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )
        document["widgets"][0]["source"]["path"] = "C:/private/layout.layout"

        with self.assertRaises(module.RenderError) as raised:
            module.validate_render_document(document)
        self.assertEqual(raised.exception.code, "RENDER-SCHEMA-INVALID")


class RenderDeterminismTests(unittest.TestCase):
    def test_two_clean_processes_emit_byte_identical_render_hashes(self) -> None:
        require_render(self)
        with tempfile.TemporaryDirectory() as first_temp:
            with tempfile.TemporaryDirectory() as second_temp:
                first_result, first_path, _ = run_process(
                    THREE_CARDS.resolve(),
                    "1920x1080",
                    Path(first_temp),
                )
                second_result, second_path, _ = run_process(
                    THREE_CARDS.resolve(),
                    "1920x1080",
                    Path(second_temp),
                )
                self.assertEqual(first_result.returncode, 0, first_result.stdout)
                self.assertEqual(second_result.returncode, 0, second_result.stdout)
                first_bytes = first_path.read_bytes()
                second_bytes = second_path.read_bytes()

        first_hash = hashlib.sha256(first_bytes).hexdigest()
        second_hash = hashlib.sha256(second_bytes).hexdigest()
        self.assertEqual(first_hash, second_hash)
        self.assertEqual(first_bytes, second_bytes)

    def test_render_has_no_private_or_nondeterministic_metadata(self) -> None:
        module = require_render(self)
        payload = module.render_bytes(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )
        lowered = payload.lower()

        self.assertNotIn(b"\\", payload)
        self.assertNotIn(b"timestamp", lowered)
        self.assertNotIn(b"generated_at", lowered)
        self.assertNotIn(str(Path.cwd()).encode("utf-8"), payload)

        document = json.loads(payload)
        paths = [
            document["scenario"],
            document["entrypoint"],
            *[widget["source"]["path"] for widget in document["widgets"]],
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(Path(path).is_absolute())
                self.assertNotIn("\\", path)

    def test_every_float_is_rounded_to_the_declared_precision(self) -> None:
        module = require_render(self)
        document = module.render_document(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )
        precision = document["normalization"]["float_decimal_places"]
        floats = [
            value
            for value in iter_values(document)
            if isinstance(value, float)
        ]

        self.assertGreater(len(floats), 0)
        for value in floats:
            with self.subTest(value=value):
                self.assertEqual(value, round(value, precision))
                if value == 0:
                    self.assertEqual(str(value), "0.0")

    def test_two_viewports_change_render_bytes_but_keep_widget_ids(self) -> None:
        module = require_render(self)
        standard = module.render_document(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )
        ultrawide = module.render_document(
            THREE_CARDS,
            state_name="populated",
            viewport=(3440, 1440),
        )
        standard_bytes = module.canonical_bytes(standard)
        ultrawide_bytes = module.canonical_bytes(ultrawide)

        self.assertNotEqual(
            hashlib.sha256(standard_bytes).hexdigest(),
            hashlib.sha256(ultrawide_bytes).hexdigest(),
        )
        self.assertEqual(
            [widget["id"] for widget in standard["widgets"]],
            [widget["id"] for widget in ultrawide["widgets"]],
        )

    def test_render_ids_are_the_compositor_ids_node_for_node(self) -> None:
        module = require_render(self)
        composition = scenario.compose_scenario(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )
        document = module.render_document(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )

        self.assertEqual(
            [node["id"] for node in flatten_composition(composition["roots"])],
            [widget["id"] for widget in document["widgets"]],
        )

    def test_semantic_is_canonical_and_raster_is_not(self) -> None:
        module = require_render(self)
        document = module.render_document(
            THREE_CARDS,
            state_name="populated",
            viewport=(1920, 1080),
        )
        self.assertEqual(
            document["canonical"],
            {"raster": False, "semantic": True},
        )


class RenderCliTests(unittest.TestCase):
    def test_valid_cli_writes_output_report_and_returns_zero(self) -> None:
        module = require_render(self)
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "render.json"
            report_path = Path(temp_dir) / "report.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = module.main(
                    [
                        "--scenario",
                        str(THREE_CARDS),
                        "--state",
                        "populated",
                        "--viewport",
                        "1920x1080",
                        "--out",
                        str(output_path),
                        "--report",
                        str(report_path),
                    ]
                )
            payload = output_path.read_bytes()
            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["findings"], [])
        self.assertEqual(
            report["artifact"]["sha256"],
            hashlib.sha256(payload).hexdigest(),
        )
        self.assertIn("verdict=PASS", stdout.getvalue())

    def test_invalid_scenario_propagates_stable_code_and_nonzero_exit(self) -> None:
        module = require_render(self)
        invalid = FIXTURE_DIR / "schema-invalid" / "scenario.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "render.json"
            report_path = Path(temp_dir) / "report.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = module.main(
                    [
                        "--scenario",
                        str(invalid),
                        "--state",
                        "default",
                        "--viewport",
                        "1920x1080",
                        "--out",
                        str(output_path),
                        "--report",
                        str(report_path),
                    ]
                )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            output_exists = output_path.exists()

        self.assertNotEqual(exit_code, 0)
        self.assertEqual(report["verdict"], "FAIL")
        self.assertEqual(
            {item["code"] for item in report["findings"]},
            {"SCENARIO-SCHEMA-INVALID"},
        )
        self.assertFalse(output_exists)
        self.assertIn("verdict=FAIL", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
