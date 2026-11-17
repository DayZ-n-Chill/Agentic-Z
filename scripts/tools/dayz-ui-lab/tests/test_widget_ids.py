from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


TOOL_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = TOOL_DIR / "dayz_ui_lab" / "widget_ids.py"
FIXTURES = TOOL_DIR / "fixtures" / "widget-ids"
SPEC = importlib.util.spec_from_file_location("dayz_ui_lab_widget_ids", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
widget_ids = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = widget_ids
SPEC.loader.exec_module(widget_ids)

CASES = json.loads((FIXTURES / "cases.json").read_text(encoding="utf-8"))
TSV_HEADER = "line\tclass\tname\tstored_id\tderived_id\tmatch\tnote"


def run(*argv: str) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = widget_ids.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def tsv_rows(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"))) for line in lines[1:]]


class CrcTests(unittest.TestCase):
    def test_check_value(self) -> None:
        check = CASES["check_value"]
        self.assertEqual(
            "%08X" % widget_ids.widget_crc(check["input"].encode("ascii")), check["crc"]
        )

    def test_empty_input(self) -> None:
        self.assertEqual(widget_ids.widget_crc(b""), 0)

    def test_is_not_zlib(self) -> None:
        self.assertNotEqual(widget_ids.widget_crc(b"123456789"), zlib.crc32(b"123456789"))


class VanillaCaseTests(unittest.TestCase):
    def test_positive_cases(self) -> None:
        self.assertEqual(len(CASES["positive"]), 26)
        for case in CASES["positive"]:
            with self.subTest(source=case["source"]):
                self.assertEqual(widget_ids.chain_id(case["parts"]), case["id"])

    def test_negative_cases(self) -> None:
        self.assertEqual(len(CASES["negative"]), 7)
        for case in CASES["negative"]:
            with self.subTest(source=case["source"]):
                self.assertNotEqual(widget_ids.chain_id(case["parts"]), case["id"])

    def test_controls_miss_every_positive(self) -> None:
        for case in CASES["positive"]:
            with self.subTest(source=case["source"]):
                data = "".join(case["parts"]).encode("utf-8")
                self.assertNotEqual("00000000%08X" % zlib.crc32(data), case["id"])
                if len(case["parts"]) > 1:
                    reversed_chain = list(reversed(case["parts"]))
                    self.assertNotEqual(widget_ids.chain_id(reversed_chain), case["id"])


class DeriveTests(unittest.TestCase):
    def test_name_keyed_layout(self) -> None:
        code, out, err = run("derive", str(FIXTURES / "name-keyed.layout"))
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines()[0], TSV_HEADER)
        rows = tsv_rows(out)
        self.assertNotIn("ScriptParamsClass", out)
        self.assertEqual(len(rows), 6)
        by_name = {row["name"]: row for row in rows}
        expected = {
            "FrameWidget": "00000000D59CB750",
            "Licensing": "00000000564F35E9",
            "version": "00000000308B9F61",
            "copyright": "00000000BB186E8D",
            "dayz_logo": "000000009FF48118",
        }
        for name, derived in expected.items():
            with self.subTest(name=name):
                self.assertEqual(by_name[name]["derived_id"], derived)
                self.assertEqual(by_name[name]["stored_id"], "")
                self.assertEqual(by_name[name]["match"], "")
        self.assertEqual(by_name["version"]["line"], "5")
        unnamed = by_name[""]
        self.assertEqual(unnamed["line"], "19")
        self.assertEqual(unnamed["derived_id"], "")
        self.assertEqual(unnamed["note"], "unnamed")

    def test_id_keyed_layout(self) -> None:
        code, out, err = run("derive", str(FIXTURES / "id-keyed.layout"))
        self.assertEqual(code, 0, err)
        by_name = {row["name"]: row for row in tsv_rows(out)}
        expected = {
            "HudDebugFrameWidget": ("00000000EE70746B", "yes"),
            "StatusWindowWidget": ("000000007BEF443C", "yes"),
            "WindowLabel": ("000000003DB016A1", "yes"),
            "NamesListboxWidget": ("00000000D7D484D1", "yes"),
            "VersionLabel": ("00000000B5FE8D77", "yes"),
            "TemperatureLabel": ("6910D426B2427803", "no"),
        }
        self.assertEqual(set(by_name), set(expected))
        for name, (stored, match) in expected.items():
            with self.subTest(name=name):
                self.assertEqual(by_name[name]["stored_id"], stored)
                self.assertEqual(by_name[name]["match"], match)
        self.assertEqual(by_name["TemperatureLabel"]["derived_id"], "0000000005ADCDA5")

    def test_json_output(self) -> None:
        code, out, err = run("derive", str(FIXTURES / "id-keyed.layout"), "--json")
        self.assertEqual(code, 0, err)
        doc = json.loads(out)
        self.assertEqual(doc["schema"], "dayz-ui-widget-ids-v1")
        self.assertEqual(doc["command"], "derive")
        widgets = doc["widgets"]
        self.assertEqual(len(widgets), 6)
        self.assertEqual(
            set(widgets[0]),
            {"line", "class", "name", "chain", "stored_id", "derived_id", "prefab", "match", "note"},
        )
        self.assertEqual(widgets[0]["chain"], ["HudDebugFrameWidget"])
        self.assertIs(widgets[0]["match"], True)
        temperature = next(w for w in widgets if w["name"] == "TemperatureLabel")
        self.assertEqual(
            temperature["chain"], ["TemperatureLabel", "NamesListboxWidget", "StatusWindowWidget"]
        )
        self.assertIs(temperature["match"], False)
        self.assertIsNone(temperature["prefab"])

    def test_variant_file_reports_prefab(self) -> None:
        code, out, err = run("derive", str(FIXTURES / "variant.layout"), "--json")
        self.assertEqual(code, 0, err)
        widgets = json.loads(out)["widgets"]
        self.assertEqual(len(widgets), 4)
        version = next(w for w in widgets if w["line"] == 6)
        self.assertEqual(version["stored_id"], "00000000308B9F61")
        self.assertEqual(version["prefab"], "00000000308B9F61")
        self.assertIsNone(version["derived_id"])
        self.assertIsNone(version["match"])
        self.assertEqual(version["note"], "unnamed")
        added = next(w for w in widgets if w["name"] == "added_text")
        self.assertEqual(added["stored_id"], "6ACB5888C22B23AC")
        self.assertIsNone(added["prefab"])
        self.assertIsNone(added["derived_id"])
        self.assertEqual(added["note"], "unnamed-ancestor")


class CollideTests(unittest.TestCase):
    def test_same_name_siblings_collide(self) -> None:
        code, out, err = run("collide", str(FIXTURES / "collision.layout"))
        self.assertEqual(code, 1, err)
        self.assertEqual(out.splitlines(), ["00000000CDEFDF47\t7:top; 9:top"])

    def test_no_collision(self) -> None:
        code, out, err = run("collide", str(FIXTURES / "name-keyed.layout"))
        self.assertEqual(code, 0, err)
        self.assertEqual(out, "")


class ScanTests(unittest.TestCase):
    def make_root(self, tmp: str, broken: bool) -> Path:
        root = Path(tmp)
        (root / "sub").mkdir()
        shutil.copyfile(FIXTURES / "id-keyed.layout", root / "sub" / "a.layout")
        shutil.copyfile(FIXTURES / "name-keyed.layout", root / "b.layout")
        (root / "notes.txt").write_text("not a layout\n", encoding="utf-8")
        if broken:
            shutil.copyfile(FIXTURES / "broken.layout", root / "c.layout")
        return root

    def test_totals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run("scan", str(self.make_root(tmp, broken=False)))
        self.assertEqual(code, 0, err)
        self.assertEqual(
            out.splitlines(),
            [
                "b.layout\tstored=0\tderived_match=0\tupper32_nonzero=0",
                "sub/a.layout\tstored=6\tderived_match=5\tupper32_nonzero=1",
                "TOTAL\tfiles=2\tstored=6\tderived_match=5\tupper32_nonzero=1\tparse_errors=0",
            ],
        )

    def test_parse_error_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run("scan", str(self.make_root(tmp, broken=True)))
        self.assertEqual(code, 1, err)
        lines = out.splitlines()
        self.assertTrue(lines[1].startswith("c.layout\tPARSE-ERROR\t"), lines[1])
        self.assertEqual(
            lines[-1],
            "TOTAL\tfiles=2\tstored=6\tderived_match=5\tupper32_nonzero=1\tparse_errors=1",
        )

    def test_missing_root_exits_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run("scan", str(Path(tmp) / "missing"))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotEqual(err, "")


class ErrorTests(unittest.TestCase):
    def test_parse_error_exits_2(self) -> None:
        for command in ("derive", "collide"):
            with self.subTest(command=command):
                code, out, err = run(command, str(FIXTURES / "broken.layout"))
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("broken.layout", err)

    def test_missing_file_exits_2(self) -> None:
        code, out, err = run("derive", str(FIXTURES / "missing.layout"))
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertNotEqual(err, "")


if __name__ == "__main__":
    unittest.main()
