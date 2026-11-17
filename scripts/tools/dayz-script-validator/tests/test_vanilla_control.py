# Vanilla-control gate tests. Comparison is pure: no vanilla tree, no 85s run.
import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
MINI_TREE = FIXTURES / "vanilla_index" / "mini_tree"
DELIVERED_BASELINE = (
    ROOT / "tests" / "baselines" / "vanilla_control_baseline.json"
)
sys.path.insert(0, str(SCRIPTS))

import build_vanilla_index
import vanilla_control
from shared import vanilla_reference


def _baseline(**overrides):
    document = {
        "errors": [
            {"file": "4_world/a.c", "note": "", "rule_id": "ES-FOO"},
            {"file": "3_game/b.c", "note": "", "rule_id": "ES-BAR"},
        ],
        "schema": 1,
        "totals": {"errors": 2, "warnings": 3},
        "tree": {"digest": "abc"},
        "warning_counts": {"ES-WARN": 3},
    }
    document.update(overrides)
    return document


def _run(errors=None, warnings=None, digest="abc"):
    if errors is None:
        errors = [
            {"file": "4_world/a.c", "line": 10, "rule_id": "ES-FOO"},
            {"file": "3_game\\b.c", "line": 20, "rule_id": "ES-BAR"},
        ]
    if warnings is None:
        warnings = [{"rule_id": "ES-WARN"}] * 3
    return {
        "errors": errors,
        "tree_digest": digest,
        "warnings": warnings,
    }


class TestCompare(unittest.TestCase):
    def test_identical_run_passes(self):
        result = vanilla_control.compare(_run(), _baseline())
        head, details = vanilla_control.format_human(result)
        self.assertEqual("PASS", result["status"])
        self.assertTrue(head.startswith("PASS"))
        self.assertFalse(result["extra_errors"])
        self.assertFalse(result["missing_errors"])
        self.assertFalse(result["digest_mismatch"])
        self.assertFalse(any("new finding" in line for line in details))

    def test_new_error_fails_and_names_rule_and_file(self):
        run = _run(
            errors=[
                {"file": "4_world/a.c", "line": 1, "rule_id": "ES-FOO"},
                {"file": "3_game/b.c", "line": 2, "rule_id": "ES-BAR"},
                {"file": "5_mission\\extra.c", "line": 3, "rule_id": "ES-NEW"},
            ]
        )
        result = vanilla_control.compare(run, _baseline())
        head, details = vanilla_control.format_human(result)
        blob = "\n".join([head] + details)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(head.startswith("FAIL"))
        self.assertIn("ES-NEW", head)
        self.assertIn("5_mission/extra.c", head)
        self.assertIn("ES-NEW", blob)
        self.assertIn("5_mission/extra.c", blob)

    def test_missing_error_fails_as_stale_baseline(self):
        run = _run(
            errors=[{"file": "4_world/a.c", "line": 1, "rule_id": "ES-FOO"}]
        )
        result = vanilla_control.compare(run, _baseline())
        head, details = vanilla_control.format_human(result)
        blob = "\n".join([head] + details)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("stale", blob)
        self.assertIn("--update", blob)
        self.assertIn("ES-BAR", blob)
        self.assertIn("3_game/b.c", blob)

    def test_warning_count_above_fails(self):
        run = _run(warnings=[{"rule_id": "ES-WARN"}] * 4)
        result = vanilla_control.compare(run, _baseline())
        head, details = vanilla_control.format_human(result)
        blob = "\n".join([head] + details)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(head.startswith("FAIL"))
        self.assertIn("ES-WARN", blob)
        self.assertTrue(any("4 > 3" in line for line in [head] + details))

    def test_warning_count_below_passes_as_improvement(self):
        run = _run(warnings=[{"rule_id": "ES-WARN"}] * 2)
        result = vanilla_control.compare(run, _baseline())
        head, details = vanilla_control.format_human(result)
        blob = "\n".join([head] + details)
        self.assertEqual("PASS", result["status"])
        self.assertTrue(head.startswith("PASS"))
        self.assertIn("ES-WARN", blob)
        self.assertIn("--update", blob)
        self.assertTrue(any("2 < 3" in line for line in details))

    def test_new_warning_rule_fails(self):
        run = _run(
            warnings=[{"rule_id": "ES-WARN"}] * 3 + [{"rule_id": "ES-BRAND-NEW"}]
        )
        result = vanilla_control.compare(run, _baseline())
        head, details = vanilla_control.format_human(result)
        blob = "\n".join([head] + details)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(head.startswith("FAIL"))
        self.assertIn("ES-BRAND-NEW", blob)

    def test_digest_mismatch_fails_with_own_message(self):
        result = vanilla_control.compare(_run(digest="fff"), _baseline())
        head, details = vanilla_control.format_human(result)
        blob = "\n".join([head] + details)
        self.assertEqual("FAIL", result["status"])
        self.assertTrue(result["digest_mismatch"])
        self.assertIn(vanilla_control.DIGEST_MISMATCH_MESSAGE, blob)
        self.assertTrue(head.startswith("FAIL"))


class _WithoutLocalIndex(unittest.TestCase):
    # A vanilla_index.json left in the checkout makes main() SKIP, so the
    # loader reads a path in a fresh temporary directory instead.
    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.temp_dir = pathlib.Path(temp_dir.name)
        self.index_path = self.temp_dir / "vanilla_index.json"
        vanilla_reference.set_index_path_for_tests(self.index_path)
        self.addCleanup(vanilla_reference.set_index_path_for_tests, None)


class TestCliSkipAndUpdate(_WithoutLocalIndex):
    def test_missing_tree_exits_2(self):
        with redirect_stdout(io.StringIO()) as captured:
            code = vanilla_control.main(
                [
                    "--vanilla-root",
                    str(ROOT / "no-such-vanilla-tree"),
                    "--baseline",
                    str(DELIVERED_BASELINE),
                ]
            )
        first = captured.getvalue().splitlines()[0]
        self.assertEqual(2, code)
        self.assertTrue(first.startswith("SKIP"))

    def test_missing_baseline_exits_2(self):
        with redirect_stdout(io.StringIO()) as captured:
            code = vanilla_control.main(
                [
                    "--vanilla-root",
                    str(MINI_TREE),
                    "--baseline",
                    str(ROOT / "tests" / "baselines" / "no-such-baseline.json"),
                ]
            )
        first = captured.getvalue().splitlines()[0]
        self.assertEqual(2, code)
        self.assertTrue(first.startswith("SKIP"))

    def test_update_round_trip_on_temp_file(self):
        delivered_before = DELIVERED_BASELINE.read_bytes()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_baseline = pathlib.Path(temp_dir) / "baseline.json"
            with redirect_stdout(io.StringIO()):
                code = vanilla_control.main(
                    [
                        "--vanilla-root",
                        str(MINI_TREE),
                        "--baseline",
                        str(temp_baseline),
                        "--update",
                    ]
                )
            self.assertEqual(0, code)
            self.assertTrue(temp_baseline.is_file())
            raw = temp_baseline.read_bytes()
            self.assertTrue(raw.endswith(b"\n"))
            loaded = json.loads(raw.decode("utf-8"))
            dumped = (
                json.dumps(
                    loaded, indent=2, sort_keys=True, ensure_ascii=True
                )
                + "\n"
            )
            self.assertEqual(dumped.encode("utf-8"), raw)

            with redirect_stdout(io.StringIO()) as captured:
                code = vanilla_control.main(
                    [
                        "--vanilla-root",
                        str(MINI_TREE),
                        "--baseline",
                        str(temp_baseline),
                    ]
                )
            self.assertEqual(0, code)
            self.assertTrue(captured.getvalue().splitlines()[0].startswith("PASS"))
        self.assertEqual(delivered_before, DELIVERED_BASELINE.read_bytes())


class TestLocalIndex(_WithoutLocalIndex):
    # Inbox 4c83: a local 1.29 index turned the control red on 1.30 while
    # the committed validator was clean there.
    def setUp(self):
        super().setUp()
        self.baseline = self.temp_dir / "baseline.json"

    def _write_index(self, text=None):
        if text is None:
            build_vanilla_index.write_index(
                build_vanilla_index.build_index_document(MINI_TREE),
                self.index_path,
            )
        else:
            self.index_path.write_text(text, encoding="utf-8")
        vanilla_reference.reset_index_cache()

    def _main(self, *extra):
        argv = [
            "--vanilla-root",
            str(MINI_TREE),
            "--baseline",
            str(self.baseline),
        ]
        with redirect_stdout(io.StringIO()) as captured:
            code = vanilla_control.main(argv + list(extra))
        return code, captured.getvalue().splitlines()

    def test_a_loaded_index_skips_and_names_the_file(self):
        code, _lines = self._main("--update")
        self.assertEqual(0, code)
        self._write_index()
        code, lines = self._main()
        self.assertEqual(2, code)
        self.assertTrue(lines[0].startswith("SKIP"))
        self.assertIn(str(self.index_path), lines[0])

    def test_a_loaded_index_writes_no_baseline(self):
        self._write_index()
        code, lines = self._main("--update")
        self.assertEqual(2, code)
        self.assertTrue(lines[0].startswith("SKIP"))
        self.assertFalse(self.baseline.exists())

    def test_an_index_the_loader_rejects_does_not_skip(self):
        self._write_index("{not json")
        code, _lines = self._main("--update")
        self.assertEqual(0, code)
        code, lines = self._main()
        self.assertEqual(0, code)
        self.assertTrue(lines[0].startswith("PASS"))


class TestUnexplainedEntries(unittest.TestCase):
    def test_entries_without_a_note_are_named(self):
        document = {
            "errors": [
                {"file": "4_world/a.c", "note": "triaged", "rule_id": "ES-FOO"},
                {"file": "3_game/b.c", "note": "   ", "rule_id": "ES-BAR"},
                {"file": "5_mission/c.c", "rule_id": "ES-BAZ"},
            ]
        }
        self.assertEqual(
            [("ES-BAR", "3_game/b.c"), ("ES-BAZ", "5_mission/c.c")],
            vanilla_control.unexplained_entries(document),
        )

    def test_update_names_the_entries_nobody_triaged(self):
        with redirect_stdout(io.StringIO()) as captured:
            code = vanilla_control.emit_update(
                pathlib.Path("baseline.json"),
                None,
                True,
                [("ES-BAR", "3_game/b.c")],
            )
        blob = captured.getvalue()
        self.assertEqual(0, code)
        self.assertIn("NO REASON WRITTEN", blob)
        self.assertIn("ES-BAR", blob)
        self.assertIn("3_game/b.c", blob)


if __name__ == "__main__":
    unittest.main()
