from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "probe" / "prepare_probe.py"
SPEC = importlib.util.spec_from_file_location("dayz_ui_probe_prepare", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
prepare_probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prepare_probe)


class ProbePreparationTests(unittest.TestCase):
    def test_build_probe_generates_byte_equivalent_lf_and_crlf_layouts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "LF_UIProbe"
            prepare_probe.build_probe(destination)

            layouts = destination / "gui" / "layouts"
            lf_bytes = (layouts / "continuation-lf.layout").read_bytes()
            crlf_bytes = (layouts / "continuation-crlf.layout").read_bytes()

            self.assertNotIn(b"\r", lf_bytes)
            self.assertNotIn(b"\n", crlf_bytes.replace(b"\r\n", b""))
            self.assertEqual(crlf_bytes.replace(b"\r\n", b"\n"), lf_bytes)
            self.assertEqual(lf_bytes.count(b"\\\n"), 1)
            self.assertEqual(crlf_bytes.count(b"\\\r\n"), 1)

    def test_probe_is_vanilla_first_and_keeps_engine_expectation_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "LF_UIProbe"
            prepare_probe.build_probe(destination)

            config = (destination / "config.cpp").read_text(encoding="utf-8")
            mission = (
                destination
                / "scripts"
                / "5_Mission"
                / "LF_UIProbe_Mission.c"
            ).read_text(encoding="utf-8")

            self.assertNotIn("Dabs", config)
            self.assertIn('"DZ_Scripts"', config)
            self.assertIn("ButtonWidget.GetText", mission)
            self.assertIn("button.GetText(value);", mission)
            self.assertNotIn("if (!button.GetText", mission)
            self.assertNotIn("EXPECTED_ENGINE_VALUE", mission)

    def test_probe_mission_keeps_every_call_argument_list_on_one_line(self) -> None:
        # DayZDiag 1.29.163451 rejected an argument list split across physical
        # lines: "Expected ',' or ')'" at the continuation line, then "Syntax
        # error" for the whole file, which dropped the entire 5_Mission module
        # and left the probe unable to report anything. A line left open on '('
        # or ',' is the shape that produces it.
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "LF_UIProbe"
            prepare_probe.build_probe(destination)

            mission_path = (
                destination / "scripts" / "5_Mission" / "LF_UIProbe_Mission.c"
            )
            offenders = []
            for number, raw in enumerate(
                mission_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                line = raw.split("//", 1)[0].rstrip()
                if line.endswith("(") or line.endswith(","):
                    offenders.append(f"{number}: {raw.strip()}")

            self.assertEqual(offenders, [], f"open call argument list: {offenders}")

    def test_probe_reports_the_observed_value_between_delimiters(self) -> None:
        # An empty result and a missing field are indistinguishable in the RPT
        # unless the value is bounded, and B20 cannot be fixed from an ambiguous
        # observation.
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "LF_UIProbe"
            prepare_probe.build_probe(destination)

            mission = (
                destination / "scripts" / "5_Mission" / "LF_UIProbe_Mission.c"
            ).read_text(encoding="utf-8")

            self.assertIn('|value=<" + value + ">', mission)
            self.assertIn("value.Length()", mission)

    def test_build_probe_refuses_to_merge_into_nonempty_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "LF_UIProbe"
            destination.mkdir()
            (destination / "keep.txt").write_text("user data", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                prepare_probe.build_probe(destination)


if __name__ == "__main__":
    unittest.main()
