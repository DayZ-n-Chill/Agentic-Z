# Generator + curated/index merge tests. Existing detector expectations stay
# in test_script_validator.py and must not change.
import io
import json
import pathlib
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
MINI_TREE = FIXTURES / "vanilla_index" / "mini_tree"
sys.path.insert(0, str(SCRIPTS))

import build_vanilla_index
from shared import vanilla_reference


class _IndexIsolation(unittest.TestCase):
    def setUp(self):
        vanilla_reference.set_index_path_for_tests(
            pathlib.Path(tempfile.gettempdir()) / "missing-vanilla-index.json"
        )
        self.addCleanup(vanilla_reference.set_index_path_for_tests, None)


class TestGenerator(unittest.TestCase):
    def test_cli_entrypoint_writes_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = pathlib.Path(temp_dir) / "vanilla_index.json"
            with redirect_stdout(io.StringIO()):
                exit_code = build_vanilla_index.main(
                    [
                        "--vanilla-root",
                        str(MINI_TREE),
                        "--out",
                        str(out_path),
                    ]
                )
            self.assertEqual(0, exit_code)
            self.assertTrue(out_path.is_file())

    def test_cli_writes_index_with_provenance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = pathlib.Path(temp_dir) / "vanilla_index.json"
            document = build_vanilla_index.build_index_document(MINI_TREE)
            build_vanilla_index.write_index(document, out_path)
            self.assertTrue(out_path.is_file())
            document = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(
            vanilla_reference.INDEX_SCHEMA_VERSION, document["schema_version"]
        )
        self.assertEqual(str(MINI_TREE.resolve()), document["vanilla_root"])
        self.assertEqual(5, document["file_count"])
        self.assertGreater(document["total_bytes"], 0)
        self.assertEqual(64, len(document["tree_digest"]))
        self.assertRegex(document["tree_digest"], r"^[0-9a-f]{64}$")
        self.assertIn("Alpha", document["global_class_names"])
        self.assertRegex(
            document["global_class_names"]["Alpha"],
            r"3_game/tools/alpha\.c:\d+",
        )
        self.assertIn("m_AlphaMember", document["base_members"]["Alpha"])
        self.assertIn("m_IndexOnlyMember", document["base_members"]["CarScript"])
        self.assertNotIn("UniqueHook", document["override_params"])
        self.assertIn("ConsoleOnlyHook", document["platform_gated_methods"])
        self.assertEqual(
            "PLATFORM_CONSOLE",
            document["platform_gated_methods"]["ConsoleOnlyHook"]["macro"],
        )
        self.assertEqual(
            "Inventory",
            document["platform_gated_methods"]["ConsoleOnlyHook"]["owner"],
        )
        self.assertNotIn("DiagOnlyHook", document["platform_gated_methods"])
        self.assertNotIn("WindowsOnlyHook", document["platform_gated_methods"])
        macros = document["preprocessor_macros"]
        self.assertEqual(
            "console-undefined-on-pc-release",
            macros["PLATFORM_CONSOLE"]["classification"],
        )
        self.assertEqual(
            "reported-undecided",
            macros["DIAG_DEVELOPER"]["classification"],
        )
        for name in vanilla_reference.VANILLA_NONEXISTENT_METHODS:
            self.assertEqual(
                0, document["nonexistent_method_verification"][name]["occurrences"]
            )

    def test_a_byte_that_is_not_utf8_does_not_stop_the_build(self):
        # Inbox 4c83: DayZ 1.30's 3_game/global/world.c has a cp1252 TRADE
        # MARK SIGN (0x99) in a comment. The generator reads the tree as the
        # detectors do, UTF-8 with replacement, and still indexes that file.
        with tempfile.TemporaryDirectory() as temp_dir:
            tree = pathlib.Path(temp_dir) / "tree"
            shutil.copytree(MINI_TREE, tree)
            world = tree / "3_game" / "global" / "world.c"
            world.parent.mkdir(parents=True)
            world.write_bytes(
                b"// Brand\x99 in a comment\n"
                b"class Gamma\n{\n    protected int m_GammaMember;\n}\n"
            )
            document = build_vanilla_index.build_index_document(tree)

        self.assertEqual(6, document["file_count"])
        self.assertEqual(6, document["parsed_file_count"])
        self.assertEqual([], document["diagnostics"]["read_errors"])
        self.assertRegex(
            document["global_class_names"]["Gamma"], r"3_game/global/world\.c:\d+"
        )
        self.assertIn("m_GammaMember", document["base_members"]["Gamma"])


class TestWithoutIndexMatchesCurated(_IndexIsolation):
    def test_query_functions_match_today(self):
        self.assertEqual(
            {"m_NoiseSystem"}, vanilla_reference.base_member_set("CarScript")
        )
        self.assertIs(
            vanilla_reference.VANILLA_BASE_MEMBERS["CarScript"],
            vanilla_reference.base_member_set("CarScript"),
        )
        self.assertEqual(set(), vanilla_reference.base_member_set("Alpha"))
        self.assertEqual(
            ["action_data"],
            vanilla_reference.override_param_names("OnExecuteServer"),
        )
        self.assertIs(
            vanilla_reference.VANILLA_OVERRIDE_PARAMS["OnExecuteServer"],
            vanilla_reference.override_param_names("OnExecuteServer"),
        )
        self.assertIsNone(vanilla_reference.override_param_names("ConsoleOnlyHook"))
        self.assertTrue(vanilla_reference.is_vanilla_global_class_name("LogManager"))
        self.assertFalse(vanilla_reference.is_vanilla_global_class_name("Alpha"))
        self.assertEqual(
            "scripts/3_game/tools/debug.c:691",
            vanilla_reference.vanilla_global_class_citation("LogManager"),
        )
        self.assertIsNone(vanilla_reference.vanilla_global_class_citation("Alpha"))
        self.assertEqual(
            vanilla_reference.VANILLA_PLATFORM_GATED_METHODS["GetConsoleToolbarText"],
            vanilla_reference.platform_gated_method("GetConsoleToolbarText"),
        )
        self.assertIsNone(vanilla_reference.platform_gated_method("ConsoleOnlyHook"))
        self.assertEqual(
            {
                "AddIngredient",
                "SetIsCacheable",
                "ProcessIndirectDamage",
            },
            set(vanilla_reference.VANILLA_NONEXISTENT_METHODS),
        )


class TestIndexExtendsAndCuratedWins(_IndexIsolation):
    def _load_mini_index(self):
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            delete=False,
        )
        handle.close()
        out_path = pathlib.Path(handle.name)
        self.addCleanup(out_path.unlink)
        document = build_vanilla_index.build_index_document(MINI_TREE)
        build_vanilla_index.write_index(document, out_path)
        vanilla_reference.set_index_path_for_tests(out_path)
        return document

    def test_index_extends_tables(self):
        document = self._load_mini_index()
        self.assertIn("Alpha", document["global_class_names"])
        self.assertTrue(vanilla_reference.is_vanilla_global_class_name("Alpha"))
        self.assertEqual(
            document["global_class_names"]["Alpha"],
            vanilla_reference.vanilla_global_class_citation("Alpha"),
        )
        self.assertIn(
            "m_AlphaMember", vanilla_reference.base_member_set("Alpha")
        )
        self.assertIn(
            "m_IndexOnlyMember", vanilla_reference.base_member_set("CarScript")
        )
        self.assertIn(
            "m_NoiseSystem", vanilla_reference.base_member_set("CarScript")
        )
        self.assertEqual(
            ["action_data"],
            vanilla_reference.override_param_names("OnExecuteServer"),
        )
        gated = vanilla_reference.platform_gated_method("ConsoleOnlyHook")
        self.assertEqual("Inventory", gated["owner"])
        self.assertEqual("PLATFORM_CONSOLE", gated["macro"])
        self.assertIn(":", gated["citation"])

    def test_curated_wins_on_conflict(self):
        document = self._load_mini_index()
        self.assertIn("LogManager", document["global_class_names"])
        self.assertNotEqual(
            document["global_class_names"]["LogManager"],
            "scripts/3_game/tools/debug.c:691",
        )
        self.assertEqual(
            "scripts/3_game/tools/debug.c:691",
            vanilla_reference.vanilla_global_class_citation("LogManager"),
        )
        indexed_params = document["override_params"].get("OnExecuteServer", {})
        self.assertEqual(["other_name"], indexed_params.get("params"))
        self.assertEqual(
            ["action_data"],
            vanilla_reference.override_param_names("OnExecuteServer"),
        )
        self.assertIs(
            vanilla_reference.VANILLA_PLATFORM_GATED_METHODS["GetConsoleToolbarText"],
            vanilla_reference.platform_gated_method("GetConsoleToolbarText"),
        )

    def test_nonexistent_methods_are_not_expanded(self):
        document = self._load_mini_index()
        self.assertNotIn("nonexistent_methods", document)
        self.assertEqual(
            set(vanilla_reference.VANILLA_NONEXISTENT_METHODS),
            {"AddIngredient", "SetIsCacheable", "ProcessIndirectDamage"},
        )


class TestIndexFallback(_IndexIsolation):
    def test_corrupt_index_falls_back_to_curated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "vanilla_index.json"
            path.write_text("{not json", encoding="utf-8")
            vanilla_reference.set_index_path_for_tests(path)
            self.assertFalse(vanilla_reference.is_vanilla_global_class_name("Alpha"))
            self.assertEqual(
                {"m_NoiseSystem"}, vanilla_reference.base_member_set("CarScript")
            )

    def test_schema_mismatch_falls_back_to_curated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "vanilla_index.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 999,
                        "global_class_names": {"Alpha": "x.c:1"},
                    }
                ),
                encoding="utf-8",
            )
            vanilla_reference.set_index_path_for_tests(path)
            self.assertFalse(vanilla_reference.is_vanilla_global_class_name("Alpha"))
            self.assertTrue(vanilla_reference.is_vanilla_global_class_name("LogManager"))

    def test_loaded_index_path_names_only_an_index_in_use(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "vanilla_index.json"
            vanilla_reference.set_index_path_for_tests(path)
            self.assertIsNone(vanilla_reference.loaded_index_path())
            for text in (
                "{not json",
                json.dumps({"schema_version": 999}),
            ):
                path.write_text(text, encoding="utf-8")
                vanilla_reference.reset_index_cache()
                self.assertIsNone(vanilla_reference.loaded_index_path())
            build_vanilla_index.write_index(
                build_vanilla_index.build_index_document(MINI_TREE), path
            )
            vanilla_reference.reset_index_cache()
            self.assertEqual(path, vanilla_reference.loaded_index_path())


if __name__ == "__main__":
    unittest.main()
