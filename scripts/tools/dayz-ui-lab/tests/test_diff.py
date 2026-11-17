from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_DIR = REPO_ROOT / "tools" / "dayz-ui-lab"
MODULE_DIR = TOOL_DIR / "dayz_ui_lab"
THREE_CARDS = TOOL_DIR / "fixtures" / "scenarios" / "three-cards" / "scenario.json"
DEFECT_SCENARIO = TOOL_DIR / "fixtures" / "scenarios" / "defect-overlays" / "scenario.json"
DEFECT_RENDER = DEFECT_SCENARIO.parent / "observed.json"
EXPECTED_SC009_CODES = {
    "DIFF-CLIPPING",
    "DIFF-OVERLAP",
    "DIFF-REFERENCE-MISSING",
    "DIFF-STATE-MISSING",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def find_widget(document: dict, name: str, occurrence: int = 0) -> dict:
    matches = [widget for widget in document["widgets"] if widget["name"] == name]
    return matches[occurrence]


def widget_by_id(document: dict, widget_id: str) -> dict:
    return next(widget for widget in document["widgets"] if widget["id"] == widget_id)


class DiffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.render = load_module("dayz_ui_lab_test_diff_render", MODULE_DIR / "render.py")
        cls.diff = load_module("dayz_ui_lab_test_diff", MODULE_DIR / "diff.py")

    def positive_document(self) -> dict:
        return self.render.render_document(THREE_CARDS, "populated")

    def defect_document(self) -> dict:
        with open(DEFECT_RENDER, "r", encoding="utf-8") as stream:
            return json.load(stream)

    @staticmethod
    def codes(findings: list[dict]) -> set[str]:
        return {finding["code"] for finding in findings}

    def test_sc009_negative_fixture_has_exactly_four_expected_findings(self) -> None:
        findings = self.diff.analyze_document(self.defect_document(), DEFECT_SCENARIO)
        self.assertEqual(4, len(findings))
        self.assertEqual(EXPECTED_SC009_CODES, self.codes(findings))

    def test_three_cards_control_has_zero_findings(self) -> None:
        findings = self.diff.analyze_document(self.positive_document(), THREE_CARDS)
        self.assertEqual([], findings)

    def test_each_sc009_finding_is_actionable_and_repo_relative(self) -> None:
        findings = self.diff.analyze_document(self.defect_document(), DEFECT_SCENARIO)
        required = {"scenario", "widget_id", "property", "expected", "observed", "source"}
        for finding in findings:
            with self.subTest(code=finding["code"]):
                self.assertTrue(required.issubset(finding))
                self.assertEqual("defect-overlays", finding["scenario"])
                self.assertTrue(finding["widget_id"].startswith("widget-"))
                self.assertRegex(finding["source"], r"^[^:]+\.layout:\d+:\d+$")
                source_path = finding["source"].rsplit(":", 2)[0]
                self.assertFalse(Path(source_path).is_absolute())
                self.assertNotIn("\\", source_path)

    def test_structural_diff_matches_widgets_by_id_not_list_position(self) -> None:
        expected = self.positive_document()
        observed = copy.deepcopy(expected)
        observed["widgets"].reverse()
        self.assertEqual([], self.diff.compare_documents(expected, observed))

    def test_structural_diff_reports_added_removed_and_changed_property(self) -> None:
        expected = self.positive_document()
        observed = copy.deepcopy(expected)
        removed = observed["widgets"].pop()
        added = copy.deepcopy(observed["widgets"][0])
        added["id"] = "widget-" + ("e" * 64)
        added["name"] = "AddedWidget"
        added.pop("parent_id", None)
        added["children"] = []
        observed["widgets"].append(added)
        changed = find_widget(observed, "HeaderTitle")
        changed["geometry"]["visible"] = not changed["geometry"]["visible"]

        findings = self.diff.compare_documents(expected, observed)
        codes = self.codes(findings)
        self.assertEqual(
            {"DIFF-WIDGET-ADDED", "DIFF-WIDGET-REMOVED", "DIFF-PROPERTY-CHANGED"},
            codes,
        )
        changed_findings = [
            finding for finding in findings
            if finding["code"] == "DIFF-PROPERTY-CHANGED"
        ]
        self.assertEqual(["geometry.visible"], [finding["property"] for finding in changed_findings])
        self.assertEqual(removed["id"], next(
            finding["widget_id"] for finding in findings
            if finding["code"] == "DIFF-WIDGET-REMOVED"
        ))

    def test_structural_comparison_refuses_two_different_viewports(self) -> None:
        # Geometry resolves against the viewport, so comparing two renders taken
        # at different ones reported 86 property changes on this very fixture,
        # all of them resolution arithmetic. Failing closed is the point.
        expected = self.positive_document()
        observed = self.render.render_document(THREE_CARDS, "populated", viewport=(3440, 1440))

        with self.assertRaises(self.diff.DiffError) as raised:
            self.diff.compare_documents(expected, observed)
        self.assertEqual("DIFF-VIEWPORT-MISMATCH", raised.exception.code)
        self.assertIn("1920x1080", str(raised.exception))
        self.assertIn("3440x1440", str(raised.exception))

    def test_structural_comparison_accepts_two_equal_viewports(self) -> None:
        expected = self.positive_document()
        observed = self.render.render_document(THREE_CARDS, "populated")
        self.assertEqual([], self.diff.compare_documents(expected, observed))

    def test_overlays_still_accept_a_viewport_the_scenario_does_not_declare(self) -> None:
        # The guard must not be wider than the defect: composing one scenario at
        # two resolutions is what SC-005 requires, and an overflow that appears
        # only at 3440x1440 is a real responsive defect, not an artefact.
        observed = self.render.render_document(THREE_CARDS, "populated", viewport=(3440, 1440))
        self.assertNotEqual(observed["viewport"], self.positive_document()["viewport"])
        findings = self.diff.analyze_document(observed, THREE_CARDS)
        self.assertEqual({"DIFF-OVERFLOW"}, self.codes(findings))

    def test_same_report_has_identical_canonical_bytes(self) -> None:
        document = self.defect_document()
        first = self.diff.build_report(document, scenario_path=DEFECT_SCENARIO)
        second = self.diff.build_report(copy.deepcopy(document), scenario_path=DEFECT_SCENARIO)
        self.assertEqual(self.diff.canonical_bytes(first), self.diff.canonical_bytes(second))

    def test_reference_missing_detector_red_and_green(self) -> None:
        green = self.positive_document()
        self.assertNotIn("DIFF-REFERENCE-MISSING", self.codes(
            self.diff.analyze_document(green, THREE_CARDS)
        ))
        red = copy.deepcopy(green)
        red["widgets"][0]["children"].append("widget-" + ("f" * 64))
        self.assertIn("DIFF-REFERENCE-MISSING", self.codes(
            self.diff.analyze_document(red, THREE_CARDS)
        ))

    def test_clipping_detector_red_and_green(self) -> None:
        green = self.positive_document()
        self.assertNotIn("DIFF-CLIPPING", self.codes(
            self.diff.analyze_document(green, THREE_CARDS)
        ))
        red = copy.deepcopy(green)
        child = find_widget(red, "CardTitle")
        parent = widget_by_id(red, child["parent_id"])
        parent["geometry"]["clip_children"] = True
        child["geometry"]["position"]["x"] = parent["geometry"]["size"]["width"] + 1.0
        codes = self.codes(self.diff.analyze_document(red, THREE_CARDS))
        self.assertIn("DIFF-CLIPPING", codes)
        self.assertNotIn("DIFF-OVERFLOW", codes)

    def test_overlap_detector_red_and_green(self) -> None:
        green = self.positive_document()
        self.assertNotIn("DIFF-OVERLAP", self.codes(
            self.diff.analyze_document(green, THREE_CARDS)
        ))
        red = copy.deepcopy(green)
        first = find_widget(red, "HeaderTitle")
        second = find_widget(red, "InventoryTab")
        second["geometry"]["position"] = copy.deepcopy(first["geometry"]["position"])
        second["geometry"]["size"] = copy.deepcopy(first["geometry"]["size"])
        self.assertIn("DIFF-OVERLAP", self.codes(
            self.diff.analyze_document(red, THREE_CARDS)
        ))

    def test_overflow_detector_red_and_green(self) -> None:
        green = self.positive_document()
        self.assertNotIn("DIFF-OVERFLOW", self.codes(
            self.diff.analyze_document(green, THREE_CARDS)
        ))
        red = copy.deepcopy(green)
        child = find_widget(red, "CardTitle")
        parent = widget_by_id(red, child["parent_id"])
        parent["geometry"]["clip_children"] = False
        child["geometry"]["position"]["x"] = parent["geometry"]["size"]["width"] + 1.0
        codes = self.codes(self.diff.analyze_document(red, THREE_CARDS))
        self.assertIn("DIFF-OVERFLOW", codes)
        self.assertNotIn("DIFF-CLIPPING", codes)

    def test_state_missing_detector_red_and_green(self) -> None:
        green = self.positive_document()
        self.assertNotIn("DIFF-STATE-MISSING", self.codes(
            self.diff.analyze_document(green, THREE_CARDS)
        ))
        red = copy.deepcopy(green)
        target = find_widget(red, "CheckoutButton")
        target["state"] = [entry for entry in target["state"] if entry["name"] != "enabled"]
        self.assertIn("DIFF-STATE-MISSING", self.codes(
            self.diff.analyze_document(red, THREE_CARDS)
        ))

    def test_cli_writes_negative_report_and_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "diff.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_DIR / "diff.py"),
                    "--observed",
                    str(DEFECT_RENDER),
                    "--scenario",
                    str(DEFECT_SCENARIO),
                    "--report",
                    str(report_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(1, result.returncode, result.stdout + result.stderr)
            self.assertIn("verdict=FAIL", result.stdout)
            with open(report_path, "r", encoding="utf-8") as stream:
                report = json.load(stream)
            self.assertEqual(4, report["stats"]["finding_count"])
            self.assertEqual("FAIL", report["verdict"])

    def test_cli_writes_positive_report_and_returns_zero(self) -> None:
        document = self.positive_document()
        with tempfile.TemporaryDirectory() as directory:
            observed_path = Path(directory) / "observed.json"
            report_path = Path(directory) / "diff.json"
            with open(observed_path, "wb") as stream:
                stream.write(self.render.canonical_bytes(document))
            result = subprocess.run(
                [
                    sys.executable,
                    str(MODULE_DIR / "diff.py"),
                    "--observed",
                    str(observed_path),
                    "--scenario",
                    str(THREE_CARDS),
                    "--report",
                    str(report_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("verdict=PASS", result.stdout)
            with open(report_path, "r", encoding="utf-8") as stream:
                report = json.load(stream)
            self.assertEqual([], report["findings"])
            self.assertEqual("PASS", report["verdict"])


if __name__ == "__main__":
    unittest.main()
