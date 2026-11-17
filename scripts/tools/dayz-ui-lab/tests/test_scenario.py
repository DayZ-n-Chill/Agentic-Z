from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


TOOL_DIR = Path(__file__).parents[1]
MODULE_PATH = TOOL_DIR / "dayz_ui_lab" / "scenario.py"
SCHEMA_PATH = TOOL_DIR / "schemas" / "dayz-ui-scenario-v1.schema.json"
FIXTURE_DIR = TOOL_DIR / "fixtures" / "scenarios"
THREE_CARDS = FIXTURE_DIR / "three-cards" / "scenario.json"
SPEC = importlib.util.spec_from_file_location("dayz_ui_lab_scenario", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
scenario = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scenario
SPEC.loader.exec_module(scenario)


def flatten(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for node in nodes:
        result.append(node)
        result.extend(flatten(node["children"]))
    return result


def run_cli(fixture: str) -> tuple[int, dict[str, object]]:
    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = Path(temp_dir) / "report.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = scenario.main(
                [
                    "--scenario",
                    str(FIXTURE_DIR / fixture / "scenario.json"),
                    "--viewport",
                    "1920x1080",
                    "--report",
                    str(report_path),
                ]
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
    return exit_code, report


class ScenarioSchemaTests(unittest.TestCase):
    def test_schema_is_versioned_and_declares_every_task3_capability(self) -> None:
        document = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(document["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(
            document["properties"]["schema_version"]["enum"],
            ["dayz-ui-scenario-v1"],
        )
        root_properties = set(document["properties"])
        self.assertTrue(
            {"entrypoint", "viewport", "subviews", "collections"}.issubset(root_properties)
        )
        state_properties = set(
            document["properties"]["states"]["items"]["properties"]
        )
        self.assertTrue(
            {
                "bindings",
                "visibility",
                "colors",
                "positions",
                "tabs",
                "controls",
                "modal",
                "pointer",
            }.issubset(state_properties)
        )

    def test_positive_fixture_validates_with_the_stdlib_validator(self) -> None:
        document = scenario.load_scenario(THREE_CARDS)
        self.assertEqual(document["schema_version"], "dayz-ui-scenario-v1")

    def test_validator_fails_closed_on_an_unsupported_schema_keyword(self) -> None:
        with self.assertRaises(scenario.ScenarioError) as raised:
            scenario.validate_against_schema(
                {}, {"type": "object", "maxLength": 4}, "unsupported.schema.json"
            )
        self.assertEqual(raised.exception.code, "SCENARIO-SCHEMA-INVALID")
        self.assertIn("maxLength", str(raised.exception))


class ScenarioCompositionTests(unittest.TestCase):
    def _cards(self, composition: dict[str, object]) -> list[dict[str, object]]:
        return [
            node
            for node in flatten(composition["roots"])
            if node.get("collection_id") == "cards" and node.get("item_key")
        ]

    def test_three_cards_keep_identity_and_order_across_two_viewports(self) -> None:
        standard = scenario.compose_scenario(
            THREE_CARDS, state_name="populated", viewport=(1920, 1080)
        )
        ultrawide = scenario.compose_scenario(
            THREE_CARDS, state_name="populated", viewport=(3440, 1440)
        )
        standard_cards = self._cards(standard)
        ultrawide_cards = self._cards(ultrawide)

        self.assertEqual(len(standard_cards), 3)
        self.assertEqual([node["sibling_index"] for node in standard_cards], [0, 1, 2])
        standard_ids = [node["id"] for node in standard_cards]
        ultrawide_ids = [node["id"] for node in ultrawide_cards]
        self.assertEqual(len(set(standard_ids)), 3)
        self.assertEqual(standard_ids, ultrawide_ids)
        self.assertNotEqual(
            [node["geometry"] for node in standard_cards],
            [node["geometry"] for node in ultrawide_cards],
        )

    def test_named_states_are_values_and_do_not_mutate_previous_output(self) -> None:
        populated = scenario.compose_scenario(
            THREE_CARDS, state_name="populated", viewport=(1920, 1080)
        )
        populated_bytes_before = json.dumps(
            populated, indent=2, sort_keys=True
        ).encode("utf-8")
        empty = scenario.compose_scenario(
            THREE_CARDS, state_name="empty", viewport=(1920, 1080)
        )

        self.assertEqual(len(self._cards(populated)), 3)
        self.assertEqual(len(self._cards(empty)), 0)
        self.assertNotEqual(populated, empty)
        self.assertEqual(
            json.dumps(populated, indent=2, sort_keys=True).encode("utf-8"),
            populated_bytes_before,
        )

    def test_missing_named_state_fails_closed(self) -> None:
        with self.assertRaises(scenario.ScenarioError) as raised:
            scenario.compose_scenario(
                THREE_CARDS, state_name="absent", viewport=(1920, 1080)
            )
        self.assertEqual(raised.exception.code, "SCENARIO-STATE-MISSING")

    def test_same_scenario_and_viewport_emit_identical_bytes(self) -> None:
        first = scenario.composition_bytes(
            THREE_CARDS, state_name="populated", viewport=(1920, 1080)
        )
        second = scenario.composition_bytes(
            THREE_CARDS, state_name="populated", viewport=(1920, 1080)
        )
        self.assertEqual(first, second)
        self.assertNotIn(b"timestamp", first.lower())
        self.assertNotIn(str(Path.cwd()).encode("utf-8"), first)

    def test_composed_sources_are_repo_relative(self) -> None:
        composition = scenario.compose_scenario(
            THREE_CARDS, state_name="populated", viewport=(1920, 1080)
        )
        self.assertEqual(
            composition["scenario"],
            "tools/dayz-ui-lab/fixtures/scenarios/three-cards/scenario.json",
        )
        for node in flatten(composition["roots"]):
            source = str(node["source"]["path"])
            self.assertFalse(Path(source).is_absolute(), source)
            self.assertNotIn("\\", source)


class ScenarioErrorAndCliTests(unittest.TestCase):
    def test_each_fixture_returns_the_required_error_code_and_nonzero_exit(self) -> None:
        cases = {
            "schema-invalid": "SCENARIO-SCHEMA-INVALID",
            "cycle": "SCENARIO-CYCLE",
            "layout-missing": "SCENARIO-LAYOUT-MISSING",
            "state-missing": "SCENARIO-STATE-MISSING",
            "binding-missing": "SCENARIO-BINDING-MISSING",
            "mount-missing": "SCENARIO-MOUNT-MISSING",
        }
        for fixture, expected_code in cases.items():
            with self.subTest(fixture=fixture):
                exit_code, report = run_cli(fixture)
                self.assertNotEqual(exit_code, 0)
                self.assertEqual(report["verdict"], "FAIL")
                self.assertIn(
                    expected_code,
                    {finding["code"] for finding in report["findings"]},
                )
                for finding in report["findings"]:
                    self.assertFalse(Path(finding["source"]).is_absolute())

    def test_duplicate_widget_id_is_a_hard_error(self) -> None:
        fixture = FIXTURE_DIR / "duplicate-widget-id" / "scenario.json"
        with mock.patch.object(
            scenario, "_stable_widget_id", return_value="widget-collision"
        ):
            with self.assertRaises(scenario.ScenarioError) as raised:
                scenario.compose_scenario(
                    fixture, state_name="default", viewport=(1920, 1080)
                )
        self.assertEqual(
            raised.exception.code, "SCENARIO-DUPLICATE-WIDGET-ID"
        )

    def test_valid_cli_writes_pass_report_and_returns_zero(self) -> None:
        exit_code, report = run_cli("three-cards")
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["verdict"], "PASS")
        self.assertEqual(report["findings"], [])
        self.assertEqual(
            report["composition"]["schema_version"], "dayz-ui-scenario-v1"
        )
        self.assertEqual(report["composition"]["state"], "populated")


if __name__ == "__main__":
    unittest.main()
