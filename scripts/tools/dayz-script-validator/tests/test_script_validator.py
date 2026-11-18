# Test suite for script_validator.py and its detectors.
import json
import os
import pathlib
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
FIXTURES = ROOT / "tests" / "fixtures"
sys.path.insert(0, str(SCRIPTS))

import script_validator
from shared import vanilla_build, vanilla_tree


_MODULE_PATCHES = []


def setUpModule():
    # run() looks for the vanilla tree in DAYZ_VANILLA_ROOT, then P:\scripts,
    # and for the installed game in DAYZ_GAME_ROOT. A unit test must not
    # change verdict with what this machine has mounted, so none is visible
    # here; tests that need a tree pass --vanilla-root.
    env = mock.patch.dict(os.environ)
    env.start()
    _MODULE_PATCHES.append(env)
    os.environ.pop("DAYZ_VANILLA_ROOT", None)
    os.environ.pop("DAYZ_GAME_ROOT", None)
    pdrive = mock.patch.object(
        vanilla_tree, "PDRIVE_SCRIPTS", FIXTURES / "no_vanilla_tree_in_unit_tests"
    )
    pdrive.start()
    _MODULE_PATCHES.append(pdrive)


def tearDownModule():
    while _MODULE_PATCHES:
        _MODULE_PATCHES.pop().stop()


REQUIRED_FINDING_KEYS = {"check", "file", "line", "message", "severity", "rule_id"}


def assert_standard_findings(testcase, result):
    for collection_name in ("errors", "warnings"):
        for finding in result[collection_name]:
            testcase.assertTrue(
                REQUIRED_FINDING_KEYS.issubset(finding.keys()),
                f"{collection_name} finding has non-standard schema: {finding}",
            )


class TestSkeleton(unittest.TestCase):
    def test_empty_fixture_passes(self):
        exit_code, result = script_validator.run([str(FIXTURES / "empty")])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(0, result["info"]["files_scanned"])
        json.dumps(result)

    def test_nonexistent_path_fails(self):
        missing_path = "C:/this/path/does/not/exist"
        exit_code, result = script_validator.run([missing_path])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual(0, result["info"]["files_scanned"])
        self.assertEqual("INPUT-NOT-FOUND", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(str(pathlib.Path(missing_path)), result["errors"][0]["file"])
        self.assertIsNone(result["errors"][0]["line"])
        self.assertIn(str(pathlib.Path(missing_path)), result["errors"][0]["message"])

    def test_nonexistent_path_emits_standard_schema(self):
        exit_code, result = script_validator.run(["C:/this/path/does/not/exist"])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        assert_standard_findings(self, result)

    def test_non_utf8_source_returns_structured_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            bad_file = temp_path / "bad_cp1252.c"
            bad_file.write_bytes(b"// caf\xe9\n")

            exit_code, result = script_validator.run([str(temp_path)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])
        self.assertEqual("INPUT-ENCODING-ERROR", result["errors"][0]["rule_id"])
        self.assertEqual("INPUT-ENCODING-ERROR", result["errors"][0]["check"])
        self.assertEqual("bad_cp1252.c", result["errors"][0]["file"])
        self.assertEqual(1, result["errors"][0]["line"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertIn("file is not valid UTF-8", result["errors"][0]["message"])
        self.assertIn("Decode error at byte", result["errors"][0]["message"])
        assert_standard_findings(self, result)
        json.dumps(result)


class TestStripper(unittest.TestCase):
    def stripped_fixture(self, name):
        source = (FIXTURES / "es" / name).read_text(encoding="utf-8")
        stripped, warnings = script_validator.strip_enforce_comments_and_strings(
            source, name
        )
        return source, stripped, warnings

    def test_delete_in_string_literal_removed(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_delete_in_string_literal.c"
        )

        self.assertNotIn("delete", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_delete_in_block_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_delete_in_block_comment.c"
        )

        self.assertNotIn("delete", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_ctx_read_in_block_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_ctx_read_in_block_comment.c"
        )

        self.assertNotIn("ctx.Read", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_delete_in_line_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_delete_in_line_comment.c"
        )

        self.assertNotIn("delete", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_ctx_read_in_line_comment_removed_and_lines_preserved(self):
        source, stripped, warnings = self.stripped_fixture(
            "ok_ctx_read_in_line_comment.c"
        )

        self.assertNotIn("ctx.Read", stripped)
        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual([], warnings)

    def test_unterminated_string_emits_warning(self):
        source, stripped, warnings = self.stripped_fixture("bad_unterminated_string.c")

        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual(1, len(warnings))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-STRING", warnings[0]["rule_id"]
        )
        self.assertEqual("WARN", warnings[0]["severity"])
        self.assertIn("bad_unterminated_string.c", warnings[0]["message"])

    def test_unterminated_block_comment_emits_warning(self):
        source, stripped, warnings = self.stripped_fixture(
            "bad_unterminated_block_comment.c"
        )

        self.assertEqual(source.count("\n"), stripped.count("\n"))
        self.assertEqual(1, len(warnings))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-BLOCK-COMMENT", warnings[0]["rule_id"]
        )
        self.assertEqual("WARN", warnings[0]["severity"])
        self.assertIn("bad_unterminated_block_comment.c", warnings[0]["message"])


class TestRvmat(unittest.TestCase):
    def test_super_shader_passes(self):
        exit_code, result = script_validator.run(
            [str(FIXTURES / "rvmat" / "ok_super_shader.rvmat")]
        )

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_normalmapmacro_fails(self):
        fixture = FIXTURES / "rvmat" / "bad_normalmapmacro.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_normalmapmacro.rvmat line 3: rvmat uses "
            "'shader = NormalMapMacro;'. Causes dedicated server crash at model "
            "load (pitfalls-advanced.md:99). Replace with 'shader = Super;'."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("RVMAT-NO-NORMALMAPMACRO", result["errors"][0]["rule_id"])
        self.assertEqual("bad_normalmapmacro.rvmat", result["errors"][0]["file"])
        self.assertEqual(3, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_normalmapmacro_in_line_comment_passes(self):
        fixture = FIXTURES / "rvmat" / "ok_normalmapmacro_in_comment.rvmat"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_normalmapmacro_with_trailing_comment_fails(self):
        fixture = FIXTURES / "rvmat" / "bad_normalmapmacro_with_trailing_comment.rvmat"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual(
            "RVMAT-NO-NORMALMAPMACRO", result["errors"][0]["rule_id"]
        )
        self.assertEqual(
            "bad_normalmapmacro_with_trailing_comment.rvmat",
            result["errors"][0]["file"],
        )
        self.assertEqual(3, result["errors"][0]["line"])

    def test_directory_with_rvmat_reports_errors(self):
        exit_code, result = script_validator.run([str(FIXTURES / "rvmat")])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(4, result["info"]["files_scanned"])
        self.assertEqual(2, len(result["errors"]))
        error_files = {error["file"] for error in result["errors"]}
        self.assertEqual(
            {
                "bad_normalmapmacro.rvmat",
                "bad_normalmapmacro_with_trailing_comment.rvmat",
            },
            error_files,
        )
        for error in result["errors"]:
            self.assertEqual("RVMAT-NO-NORMALMAPMACRO", error["rule_id"])


class TestEsNoDelete(unittest.TestCase):
    def test_no_delete_passes(self):
        fixture = FIXTURES / "es" / "ok_no_delete.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_widget_unlink_does_not_trigger_delete_rule(self):
        fixture = FIXTURES / "es" / "ok_widget_unlink.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_delete_in_string_literal_still_passes_end_to_end(self):
        fixture = FIXTURES / "es" / "ok_delete_in_string_literal.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_delete_in_block_comment_still_passes_end_to_end(self):
        fixture = FIXTURES / "es" / "ok_delete_in_block_comment.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_delete_in_line_comment_still_passes_end_to_end(self):
        fixture = FIXTURES / "es" / "ok_delete_in_line_comment.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_unterminated_string_emits_warn_no_delete_finding(self):
        fixture = FIXTURES / "es" / "bad_unterminated_string.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-STRING", result["warnings"][0]["rule_id"]
        )

    def test_unterminated_block_comment_emits_warn_no_delete_finding(self):
        fixture = FIXTURES / "es" / "bad_unterminated_block_comment.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-SOURCE-UNTERMINATED-BLOCK-COMMENT",
            result["warnings"][0]["rule_id"],
        )

    def test_directory_with_fail_and_warn_returns_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = pathlib.Path(temp_dir)
            (temp_path / "bad_local_var_redeclare.c").write_text(
                "\n".join(
                    [
                        "class BadLocalFixture",
                        "{",
                        "    void Check(bool c)",
                        "    {",
                        "        if (c)",
                        "        {",
                        "            int x = 5;",
                        "        }",
                        "        else",
                        "        {",
                        "            int x = 10;",
                        "        }",
                        "    }",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )
            (temp_path / "bad_unterminated_string.c").write_text(
                "\n".join(
                    [
                        "class BadStringFixture",
                        "{",
                        "    void Broken()",
                        "    {",
                        '        string value = "unterminated;',
                        "    }",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            exit_code, result = script_validator.run([str(temp_path)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual(
            "ES-LOCAL-VAR-REDECLARE", result["errors"][0]["rule_id"]
        )
        self.assertGreaterEqual(len(result["warnings"]), 1)
        warning_rule_ids = {warning["rule_id"] for warning in result["warnings"]}
        self.assertIn("ES-SOURCE-UNTERMINATED-STRING", warning_rule_ids)
        self.assertEqual(2, result["info"]["files_scanned"])
        assert_standard_findings(self, result)


class TestEsEmptyIfdef(unittest.TestCase):
    def test_ifdef_with_statement_passes(self):
        fixture = FIXTURES / "es" / "ok_ifdef_with_statement.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ifndef_with_statement_passes(self):
        fixture = FIXTURES / "es" / "ok_ifndef_with_statement.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    # On DayZDiag 1.30.164289 a block holding only a
    # comment compiled and ran on server and client, so no crash is on record
    # and the rule warns.
    EMPTY_IFDEF_MEASURED = (
        "block contains no statements (comments do not count). Such blocks "
        "were reported to segfault, and no measurement shows it: on DayZDiag "
        "1.30.164289 a block holding only a comment compiled and ran on server "
        "and client, at file scope, in a class body and in a method body, with "
        "a macro DayZDiag defines and with one nobody defines "
        "(skills/_shared/enscript/depth/pitfalls-advanced.md, section 5). Not "
        "measured: a block with nothing at all inside, a retail build, DayZ "
        "1.29. Remove the block if it holds no code."
    )

    def test_empty_ifdef_with_comments_warns(self):
        fixture = FIXTURES / "es" / "bad_empty_ifdef_with_comments.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] bad_empty_ifdef_with_comments.c line 1: '#ifdef MY_MOD' "
            + self.EMPTY_IFDEF_MEASURED
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-EMPTY-IFDEF", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("bad_empty_ifdef_with_comments.c", result["warnings"][0]["file"])
        self.assertEqual(1, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])
        self.assertNotIn("Documented segfault", result["warnings"][0]["message"])

    def test_empty_ifndef_with_comments_warns(self):
        fixture = FIXTURES / "es" / "bad_empty_ifndef_with_comments.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] bad_empty_ifndef_with_comments.c line 1: '#ifndef SERVER' "
            + self.EMPTY_IFDEF_MEASURED
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-EMPTY-IFDEF", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("bad_empty_ifndef_with_comments.c", result["warnings"][0]["file"])
        self.assertEqual(1, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])

    def test_ifdef_nested_passes(self):
        fixture = FIXTURES / "es" / "ok_ifdef_nested.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ifdef_with_unsupported_inner_passes_with_warning(self):
        fixture = FIXTURES / "es" / "ok_ifdef_with_unsupported_inner.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertGreaterEqual(len(result["warnings"]), 1)
        warning_rule_ids = {warning["rule_id"] for warning in result["warnings"]}
        self.assertIn("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", warning_rule_ids)

    def test_ifdef_empty_with_only_unsupported_passes_with_warning(self):
        fixture = FIXTURES / "es" / "bad_ifdef_empty_with_unsupported_only.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertGreaterEqual(len(result["warnings"]), 1)
        warning_rule_ids = {warning["rule_id"] for warning in result["warnings"]}
        self.assertIn("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", warning_rule_ids)

    def test_ifdef_unterminated_warns(self):
        fixture = FIXTURES / "es" / "warn_ifdef_unterminated.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_ifdef_unterminated.c", result["warnings"][0]["file"])
        self.assertEqual(1, result["warnings"][0]["line"])
        self.assertIn("unterminated #ifdef MY_MOD", result["warnings"][0]["message"])

    def test_endif_stray_warns(self):
        fixture = FIXTURES / "es" / "warn_endif_stray.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_endif_stray.c", result["warnings"][0]["file"])
        self.assertEqual(2, result["warnings"][0]["line"])
        self.assertIn("stray #endif without matching #ifdef", result["warnings"][0]["message"])


class TestEsCtxReadUnchecked(unittest.TestCase):
    def test_ctx_read_checked_passes(self):
        fixture = FIXTURES / "es" / "ok_ctx_read_checked.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ctx_read_pattern_b_passes(self):
        fixture = FIXTURES / "es" / "ok_ctx_read_pattern_b.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ctx_read_bool_local_passes(self):
        fixture = FIXTURES / "es" / "ok_ctx_read_bool_local.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ctx_read_unchecked_onstoreload_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_onstoreload.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_onstoreload.c line 7: ctx.Read() "
            "return not checked inside OnStoreLoad (fail-closed context). "
            "Required: 'if (!ctx.Read(...)) return false;' (SKILL.md rule 18, "
            "networking.md:169). Silent corruption on truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_onstoreload.c", result["errors"][0]["file"]
        )
        self.assertEqual(7, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_multiline_signature_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_onstoreload_multiline.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_onstoreload_multiline.c line 10: "
            "ctx.Read() return not checked inside OnStoreLoad (fail-closed "
            "context). Required: 'if (!ctx.Read(...)) return false;' "
            "(SKILL.md rule 18, networking.md:169). Silent corruption on "
            "truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_onstoreload_multiline.c",
            result["errors"][0]["file"],
        )
        self.assertEqual(10, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_with_renamed_param_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_with_renamed_param.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_with_renamed_param.c line 7: "
            "ctx.Read() return not checked inside OnStoreLoad (fail-closed "
            "context). Required: 'if (!ctx.Read(...)) return false;' "
            "(SKILL.md rule 18, networking.md:169). Silent corruption on "
            "truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_with_renamed_param.c",
            result["errors"][0]["file"],
        )
        self.assertEqual(7, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_in_rpc_server_guard_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_in_rpc.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_in_rpc.c line 8: ctx.Read() return "
            "not checked inside OnRPC (fail-closed context). Required: "
            "'if (!ctx.Read(...)) return false;' (SKILL.md rule 18, "
            "networking.md:169). Silent corruption on truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual("bad_ctx_read_unchecked_in_rpc.c", result["errors"][0]["file"])
        self.assertEqual(8, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_in_rpc_outer_server_guard_fails(self):
        fixture = FIXTURES / "es" / "bad_ctx_read_unchecked_in_rpc_outer_server_guard.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[FAIL] bad_ctx_read_unchecked_in_rpc_outer_server_guard.c line 8: "
            "ctx.Read() return not checked inside OnRPC (fail-closed context). "
            "Required: 'if (!ctx.Read(...)) return false;' (SKILL.md rule 18, "
            "networking.md:169). Silent corruption on truncated/corrupted packet."
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(
            "bad_ctx_read_unchecked_in_rpc_outer_server_guard.c",
            result["errors"][0]["file"],
        )
        self.assertEqual(8, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def test_ctx_read_unchecked_under_ifndef_server_warns(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_in_rpc_ifndef_server.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] warn_ctx_read_unchecked_in_rpc_ifndef_server.c line 8: "
            "ctx.Read() return not checked. Recommended: "
            "'if (!ctx.Read(...)) ...'."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_in_rpc_ifndef_server.c",
            result["warnings"][0]["file"],
        )
        self.assertEqual(8, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])

    def test_ctx_read_unchecked_in_onvarsync_warns(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_in_onvarsync.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] warn_ctx_read_unchecked_in_onvarsync.c line 7: ctx.Read() "
            "return not checked. Recommended: 'if (!ctx.Read(...)) ...'."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_in_onvarsync.c", result["warnings"][0]["file"]
        )
        self.assertEqual(7, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])

    def test_ctx_read_combined_condition_emits_unsupported_warning(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_combined_condition.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-CTX-READ-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_combined_condition.c",
            result["warnings"][0]["file"],
        )
        self.assertEqual(7, result["warnings"][0]["line"])
        self.assertIn("combined condition", result["warnings"][0]["message"])

    def test_ctx_read_in_try_catch_emits_unsupported_warning(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_in_try_catch.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-CTX-READ-UNSUPPORTED-PATTERN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_ctx_read_in_try_catch.c", result["warnings"][0]["file"])
        self.assertEqual(8, result["warnings"][0]["line"])
        self.assertIn("inside try/catch block", result["warnings"][0]["message"])

    def test_ctx_read_unchecked_in_rpc_no_guard_warns(self):
        fixture = FIXTURES / "es" / "warn_ctx_read_unchecked_in_rpc_no_guard.c"
        exit_code, result = script_validator.run([str(fixture)])
        expected_message = (
            "[WARN] warn_ctx_read_unchecked_in_rpc_no_guard.c line 7: ctx.Read() "
            "return not checked. Recommended: 'if (!ctx.Read(...)) ...'."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual("ES-CTX-READ-UNCHECKED", result["warnings"][0]["rule_id"])
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual(
            "warn_ctx_read_unchecked_in_rpc_no_guard.c",
            result["warnings"][0]["file"],
        )
        self.assertEqual(7, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])


CONSTRUCTION = FIXTURES / "syncvar_construction"


class TestEsSyncvarContract(unittest.TestCase):
    def run_fixture(self, name, folder=FIXTURES / "es", vanilla=None, external=None):
        argv = [str(folder / name)]
        if vanilla is not None:
            argv += ["--vanilla-root", str(folder / vanilla)]
        if external is not None:
            argv += ["--external-scripts", str(folder / external)]
        return script_validator.run(argv)

    def assert_syncvar_passes(
        self, name, folder=FIXTURES / "es", vanilla=None, external=None
    ):
        exit_code, result = self.run_fixture(name, folder, vanilla, external)

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def assert_syncvar_error(
        self,
        name,
        line_number,
        expected_message,
        folder=FIXTURES / "es",
        vanilla=None,
        external=None,
    ):
        exit_code, result = self.run_fixture(name, folder, vanilla, external)

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        self.assertEqual("ES-SYNCVAR-CONTRACT", result["errors"][0]["rule_id"])
        self.assertEqual("FAIL", result["errors"][0]["severity"])
        self.assertEqual(name, result["errors"][0]["file"])
        self.assertEqual(line_number, result["errors"][0]["line"])
        self.assertEqual(expected_message, result["errors"][0]["message"])

    def assert_syncvar_unsupported_warning(self, name, line_number, expected_text):
        exit_code, result = self.run_fixture(name)

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        matching = [
            warning
            for warning in result["warnings"]
            if warning["rule_id"] == "ES-SYNCVAR-UNSUPPORTED-PATTERN"
        ]
        self.assertEqual(1, len(matching))
        self.assertEqual("WARN", matching[0]["severity"])
        self.assertEqual(name, matching[0]["file"])
        self.assertEqual(line_number, matching[0]["line"])
        self.assertIn(expected_text, matching[0]["message"])

    def test_syncvar_full_contract_passes(self):
        self.assert_syncvar_passes("ok_syncvar_full.c")

    def test_syncvar_modded_class_passes(self):
        self.assert_syncvar_passes("ok_modded_class_syncvar.c")

    def test_syncvar_long_server_block_single_dirty_passes(self):
        self.assert_syncvar_passes("ok_syncvar_long_server_block.c")

    def test_syncvar_class_brace_next_line_passes(self):
        self.assert_syncvar_passes("ok_syncvar_class_brace_next_line.c")

    def test_syncvar_extends_class_passes(self):
        self.assert_syncvar_passes("ok_syncvar_extends_class.c")

    def test_syncvar_init_item_variables_passes(self):
        self.assert_syncvar_passes("ok_syncvar_init_item_variables.c")

    def test_syncvar_register_construction_sync_variables_passes(self):
        self.assert_syncvar_passes(
            "ok_syncvar_register_construction_sync_variables.c",
            CONSTRUCTION,
            "vanilla_130",
        )

    def test_syncvar_class_named_like_the_construction_hook_passes(self):
        self.assert_syncvar_passes(
            "ok_syncvar_register_construction_class_ctor.c",
            CONSTRUCTION,
            "vanilla_130",
        )

    def test_syncvar_construction_hook_after_a_brace_in_a_string_passes(self):
        self.assert_syncvar_passes(
            "ok_syncvar_register_construction_sync_variables.c",
            CONSTRUCTION,
            "vanilla_hook_after_brace_string",
        )

    def test_syncvar_construction_hook_of_a_class_derived_through_the_addon_passes(self):
        self.assert_syncvar_passes(
            "ok_syncvar_register_construction_addon_base.c",
            CONSTRUCTION,
            "vanilla_130",
        )

    def test_syncvar_construction_hook_of_a_class_with_an_unknown_base_passes(self):
        self.assert_syncvar_passes(
            "ok_syncvar_register_construction_unknown_base.c",
            CONSTRUCTION,
            "vanilla_130",
        )

    def test_syncvar_construction_hook_with_an_external_entityai_base_passes(self):
        self.assert_syncvar_passes(
            "ok_syncvar_register_construction_external_base.c",
            CONSTRUCTION,
            "vanilla_130",
            "external_entityai",
        )

    def test_syncvar_other_prefix_does_not_trigger_write_rule(self):
        self.assert_syncvar_passes("ok_syncvar_other_prefix.c")

    def test_syncvar_field_declaration_with_initializer_passes(self):
        self.assert_syncvar_passes("ok_syncvar_field_declaration_with_initializer.c")

    def test_syncvar_register_outside_constructor_fails(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_outside_ctor.c line 6: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_outside_ctor.c", 6, expected_message
        )

    def test_syncvar_register_construction_helper_fails(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_helper.c line 12: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_helper.c",
            12,
            expected_message,
            CONSTRUCTION,
            "vanilla_130",
        )

    def test_syncvar_own_register_construction_override_fails_on_1_29(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_own_hook.c line 19: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_own_hook.c",
            19,
            expected_message,
            CONSTRUCTION,
            "vanilla_129",
        )

    def test_syncvar_own_register_construction_override_fails_on_1_30(self):
        # On 1.30 the override passed, though
        # SyncVarOwnHookFixture does not derive from EntityAI.
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_own_hook.c line 19: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_own_hook.c",
            19,
            expected_message,
            CONSTRUCTION,
            "vanilla_130",
        )

    def test_syncvar_construction_hook_with_an_external_foreign_base_fails_on_1_30(self):
        # The base class is only in an
        # --external-scripts root, and does not derive from EntityAI.
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_external_base.c line 7: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_external_base.c",
            7,
            expected_message,
            CONSTRUCTION,
            "vanilla_130",
            "external_own_hook",
        )

    def test_syncvar_register_construction_override_fails_without_vanilla(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_own_hook.c line 19: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_own_hook.c",
            19,
            expected_message,
            CONSTRUCTION,
        )

    def test_syncvar_own_register_construction_override_fails_on_a_string(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_own_hook.c line 19: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_own_hook.c",
            19,
            expected_message,
            CONSTRUCTION,
            "vanilla_hook_string",
        )

    def test_syncvar_own_register_construction_override_fails_on_a_field(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_own_hook.c line 19: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_own_hook.c",
            19,
            expected_message,
            CONSTRUCTION,
            "vanilla_hook_field",
        )

    def test_syncvar_register_construction_override_with_parameters_fails(self):
        expected_message = (
            "[FAIL] bad_syncvar_register_construction_with_parameters.c line 12: "
            "RegisterNetSyncVariable*('m_X') called outside constructor. "
            "SyncVars must register in constructor (networking.md:42)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_register_construction_with_parameters.c",
            12,
            expected_message,
            CONSTRUCTION,
            "vanilla_130",
        )

    def test_syncvar_write_without_dirty_fails(self):
        expected_message = (
            "[FAIL] bad_syncvar_write_no_dirty.c line 12: SyncVar 'm_X' "
            "assigned inside '#ifdef SERVER' but missing 'SetSynchDirty()' "
            "in the same block. Clients won't see the change (networking.md:59)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_write_no_dirty.c", 12, expected_message
        )

    def test_syncvar_dirty_in_other_method_does_not_cover_write(self):
        expected_message = (
            "[FAIL] bad_syncvar_dirty_in_other_method.c line 17: SyncVar 'm_X' "
            "assigned inside '#ifdef SERVER' but missing 'SetSynchDirty()' "
            "in the same block. Clients won't see the change (networking.md:59)."
        )

        self.assert_syncvar_error(
            "bad_syncvar_dirty_in_other_method.c", 17, expected_message
        )

    def test_syncvar_template_class_warns_unknown(self):
        exit_code, result = self.run_fixture("warn_syncvar_class_template.c")
        expected_message = (
            "[WARN] warn_syncvar_class_template.c line 1: class declaration not "
            "recognized; SyncVar checks skipped for this block (rule_id: "
            "ES-SYNCVAR-CLASS-UNKNOWN)."
        )

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        self.assertEqual(
            "ES-SYNCVAR-CLASS-UNKNOWN", result["warnings"][0]["rule_id"]
        )
        self.assertEqual("WARN", result["warnings"][0]["severity"])
        self.assertEqual("warn_syncvar_class_template.c", result["warnings"][0]["file"])
        self.assertEqual(1, result["warnings"][0]["line"])
        self.assertEqual(expected_message, result["warnings"][0]["message"])

    def test_syncvar_else_branch_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "bad_syncvar_in_else_branch.c",
            14,
            "unsupported preprocessor branch",
        )

    def test_syncvar_alternative_guard_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "warn_syncvar_alternative_guard.c",
            13,
            "alternative guard 'if (GetGame().IsServer())'",
        )

    def test_syncvar_ggame_is_server_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "warn_syncvar_ggame_is_server.c",
            13,
            "alternative guard",
        )

    def test_syncvar_generic_return_method_warns_unsupported(self):
        self.assert_syncvar_unsupported_warning(
            "warn_syncvar_method_generic_return.c",
            12,
            "method enclosing the assignment could not be parsed",
        )


class TestEsIntMinCompare(unittest.TestCase):
    def test_no_int_min_compare_passes(self):
        fixture = FIXTURES / "es" / "ok_int_min_no_compare.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_int_min_symbolic_warns(self):
        fixture = FIXTURES / "es" / "warn_int_min_compare_symbolic.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-INT-MIN-COMPARISON", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_int_min_compare_symbolic.c", warning["file"])
        self.assertEqual(5, warning["line"])
        self.assertIn("int.MIN", warning["message"])
        self.assertIn("pitfalls-advanced.md:5-14", warning["message"])
        assert_standard_findings(self, result)

    def test_int_min_literal_warns(self):
        fixture = FIXTURES / "es" / "warn_int_min_compare_literal.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-INT-MIN-COMPARISON", warning["rule_id"])
        self.assertEqual("warn_int_min_compare_literal.c", warning["file"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_int_min_inside_string_literal_passes(self):
        fixture = FIXTURES / "es" / "ok_int_min_string_literal.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])


class TestEsGettypeExactMatch(unittest.TestCase):
    def test_iskindof_passes(self):
        fixture = FIXTURES / "es" / "ok_gettype_iskindof.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_gettype_enum_compare_passes(self):
        fixture = FIXTURES / "es" / "ok_gettype_enum_compare.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_gettype_not_equal_warns(self):
        fixture = FIXTURES / "es" / "warn_gettype_equality.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-GETTYPE-EXACT-MATCH", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_gettype_equality.c", warning["file"])
        self.assertEqual(5, warning["line"])
        self.assertIn("IsKindOf", warning["message"])
        self.assertIn("rules 31-32", warning["message"])
        assert_standard_findings(self, result)

    def test_gettype_equal_warns(self):
        fixture = FIXTURES / "es" / "warn_gettype_equality_eq.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-GETTYPE-EXACT-MATCH", warning["rule_id"])
        self.assertEqual("warn_gettype_equality_eq.c", warning["file"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_gettype_typename_uppercase_warns(self):
        fixture = FIXTURES / "es" / "warn_gettype_typename_uppercase.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-GETTYPE-EXACT-MATCH", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_gettype_typename_uppercase.c", warning["file"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_gettype_inside_string_literal_passes(self):
        fixture = FIXTURES / "es" / "ok_gettype_in_string.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])


class TestEsLayoutPathPboprefix(unittest.TestCase):
    def test_layout_path_match_passes(self):
        addon_root = FIXTURES / "layout_pboprefix" / "ok_match"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(2, result["info"]["files_scanned"])

    def test_layout_path_mismatch_fails(self):
        addon_root = FIXTURES / "layout_pboprefix" / "bad_mismatch"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-LAYOUT-PATH-PBOPREFIX-MISMATCH", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("dialog.c", error["file"])
        self.assertEqual(5, error["line"])
        self.assertIn("FxGroupMod", error["message"])
        self.assertIn("FxTerritory", error["message"])
        self.assertIn("rule 34", error["message"])
        assert_standard_findings(self, result)

    def test_no_pboprefix_skips_check(self):
        # When $PBOPREFIX$ is missing, the check is skipped silently — phase 1
        # does not bootstrap the prefix from other sources. The .c file uses a
        # layout path that would normally fail; without the prefix anchor, the
        # detector returns no findings.
        addon_root = FIXTURES / "layout_pboprefix" / "ok_no_prefix"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])

    def test_message_that_names_a_layout_is_not_a_path(self):
        # A Print after a failed CreateWidgets names the layout in a message.
        # The message is not judged, the path beside it is.
        from detectors.es_layout_path_pboprefix import check_es_layout_path_pboprefix

        addon_root = FIXTURES / "layout_pboprefix" / "ok_message_names_layout"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

        source = (addon_root / "dialog.c").read_text(encoding="utf-8")
        errors = check_es_layout_path_pboprefix(source, "dialog.c", "OtherGroup")
        self.assertEqual([9], [error["line"] for error in errors])

class TestLayoutLeafMissingBraces(unittest.TestCase):
    # LAYOUT-LEAF-MISSING-BRACES is quarantined: a leaf widget
    # without a child { } block is valid Enfusion layout syntax. The detector
    # file remains on disk but is not imported or called. These tests assert
    # the run loop no longer emits that rule, including on the former
    # "bad_*" fixtures that the false rule used to fail.

    def run_layout_fixture(self, fixture_name):
        fixture = FIXTURES / "layout_braces" / fixture_name
        return script_validator.run([str(fixture)])

    def assert_layout_passes(self, fixture_name):
        exit_code, result = self.run_layout_fixture(fixture_name)

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, result["info"]["files_scanned"])
        assert_standard_findings(self, result)

    def test_leaf_with_empty_braces_passes(self):
        self.assert_layout_passes("ok_leaf_with_empty_braces.layout")

    def test_leaf_missing_braces_is_valid_syntax(self):
        self.assert_layout_passes("bad_leaf_missing_braces.layout")

    def test_inline_widget_passes(self):
        self.assert_layout_passes("ok_inline_widget.layout")

    def test_inline_missing_braces_is_valid_syntax(self):
        self.assert_layout_passes("bad_inline_missing_braces.layout")

    def test_fp_traps_pass(self):
        for fixture_name in (
            "ok_nested_widgets.layout",
            "ok_scriptparams_double_block.layout",
            "ok_string_with_brace_literal.layout",
        ):
            with self.subTest(fixture_name=fixture_name):
                self.assert_layout_passes(fixture_name)

class TestEsRefAutoptrCombined(unittest.TestCase):
    def test_separate_qualifiers_and_generics_pass(self):
        fixture = FIXTURES / "es" / "ok_ref_autoptr_generics.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_ref_autoptr_combined_warns(self):
        fixture = FIXTURES / "es" / "warn_ref_autoptr_combined.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-REF-AUTOPTR-COMBINED", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_ref_autoptr_combined.c", warning["file"])
        self.assertEqual(3, warning["line"])
        self.assertIn("SKILL.md:38", warning["message"])
        assert_standard_findings(self, result)

    def test_autoptr_ref_combined_warns(self):
        fixture = FIXTURES / "es" / "warn_autoptr_ref_combined.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-REF-AUTOPTR-COMBINED", warning["rule_id"])
        self.assertEqual("warn_autoptr_ref_combined.c", warning["file"])
        self.assertEqual(3, warning["line"])
        assert_standard_findings(self, result)


class TestEsOnMouseLeaveParamCount(unittest.TestCase):
    def test_four_param_declaration_and_calls_pass(self):
        fixture = FIXTURES / "es" / "ok_onmouseleave_signature.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_three_param_declaration_warns(self):
        fixture = FIXTURES / "es" / "warn_onmouseleave_3params.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-ONMOUSELEAVE-PARAM-COUNT", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("warn_onmouseleave_3params.c", warning["file"])
        self.assertEqual(3, warning["line"])
        self.assertIn("SKILL.md:635", warning["message"])
        assert_standard_findings(self, result)

    def test_delegate_class_without_handler_base_passes(self):
        fixture = FIXTURES / "es" / "ok_onmouseleave_delegate_3params.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_three_param_multiline_declaration_warns(self):
        fixture = FIXTURES / "es" / "warn_onmouseleave_3params_multiline.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-ONMOUSELEAVE-PARAM-COUNT", warning["rule_id"])
        self.assertEqual(
            "warn_onmouseleave_3params_multiline.c", warning["file"]
        )
        self.assertEqual(3, warning["line"])
        assert_standard_findings(self, result)


class TestEsRegisterRecipesTypo(unittest.TestCase):
    def test_correct_double_i_hook_passes(self):
        fixture = FIXTURES / "es" / "ok_registerrecipies_correct.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_override_single_i_fails(self):
        fixture = FIXTURES / "es" / "bad_registerrecipes_override.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual([], result["warnings"])
        error = result["errors"][0]
        self.assertEqual("ES-REGISTERRECIPES-TYPO", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_registerrecipes_override.c", error["file"])
        self.assertEqual(3, error["line"])
        self.assertIn("RegisterRecipies", error["message"])
        assert_standard_findings(self, result)

    def test_plain_single_i_warns(self):
        fixture = FIXTURES / "es" / "warn_registerrecipes_plain.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("ES-REGISTERRECIPES-TYPO", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual(3, warning["line"])
        self.assertIn("silently not registered", warning["message"])
        assert_standard_findings(self, result)


class TestEsNonexistentMethod(unittest.TestCase):
    def test_verified_alternatives_pass(self):
        fixture = FIXTURES / "es" / "ok_nonexistent_method_alternatives.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_nonexistent_method_calls_fail(self):
        fixture = FIXTURES / "es" / "bad_nonexistent_method_call.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(3, len(result["errors"]))
        by_line = {error["line"]: error for error in result["errors"]}
        self.assertEqual({5, 6, 11}, set(by_line.keys()))
        for error in result["errors"]:
            self.assertEqual("ES-NONEXISTENT-METHOD", error["rule_id"])
            self.assertEqual("FAIL", error["severity"])
        self.assertIn("InsertIngredient", by_line[5]["message"])
        self.assertIn("SetIsCacheable", by_line[6]["message"])
        self.assertIn("DamageSystem.ExplosionDamage", by_line[11]["message"])
        assert_standard_findings(self, result)

    def test_mod_declared_homonym_passes(self):
        fixture = FIXTURES / "es" / "ok_nonexistent_method_declared.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestEsRespawnEquipOnClientRespawnEvent(unittest.TestCase):
    def test_kill_only_respawn_and_newevent_equip_pass(self):
        fixture = FIXTURES / "es" / "ok_onclientrespawn_kill_only.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_equip_in_respawn_event_warns(self):
        fixture = FIXTURES / "es" / "warn_onclientrespawn_equip.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(2, len(result["warnings"]))
        by_line = {warning["line"]: warning for warning in result["warnings"]}
        self.assertEqual({6, 7}, set(by_line.keys()))
        for warning in result["warnings"]:
            self.assertEqual(
                "ES-RESPAWN-EQUIP-IN-ONCLIENTRESPAWNEVENT", warning["rule_id"]
            )
            self.assertEqual("WARN", warning["severity"])
        self.assertIn("CreateInInventory", by_line[6]["message"])
        self.assertIn("CreateAttachment", by_line[7]["message"])
        self.assertIn("OnClientNewEvent", by_line[6]["message"])
        assert_standard_findings(self, result)


class TestFullCorpus(unittest.TestCase):
    def test_full_es_corpus_consolidated_json(self):
        exit_code, result = script_validator.run([str(FIXTURES / "es")])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(103, result["info"]["files_scanned"])
        assert_standard_findings(self, result)

        observed_errors = {
            (finding["rule_id"], pathlib.Path(finding["file"]).name)
            for finding in result["errors"]
        }
        observed_warnings = {
            (finding["rule_id"], pathlib.Path(finding["file"]).name)
            for finding in result["warnings"]
        }

        expected_errors = {
            ("ES-CTX-READ-UNCHECKED", "bad_ctx_read_unchecked_in_rpc.c"),
            (
                "ES-CTX-READ-UNCHECKED",
                "bad_ctx_read_unchecked_in_rpc_outer_server_guard.c",
            ),
            ("ES-CTX-READ-UNCHECKED", "bad_ctx_read_unchecked_onstoreload.c"),
            (
                "ES-CTX-READ-UNCHECKED",
                "bad_ctx_read_unchecked_onstoreload_multiline.c",
            ),
            (
                "ES-CTX-READ-UNCHECKED",
                "bad_ctx_read_unchecked_with_renamed_param.c",
            ),
            ("ES-SYNCVAR-CONTRACT", "bad_syncvar_dirty_in_other_method.c"),
            ("ES-SYNCVAR-CONTRACT", "bad_syncvar_register_outside_ctor.c"),
            ("ES-SYNCVAR-CONTRACT", "bad_syncvar_write_no_dirty.c"),
            ("ES-LOCAL-VAR-REDECLARE", "bad_local_var_redeclare_sibling.c"),
            ("ES-LOCAL-VAR-REDECLARE", "bad_local_var_redeclare_nested_for.c"),
            ("ES-MEMBER-REDECLARE-BASE", "bad_member_redeclare_base.c"),
            ("ES-OVERRIDE-PARAM-NAME-MISMATCH", "bad_override_param_mismatch.c"),
            ("ES-METHOD-NAME-COLLIDES-VANILLA-CLASS", "bad_method_name_collides.c"),
            ("ES-REGISTERRECIPES-TYPO", "bad_registerrecipes_override.c"),
            ("ES-NONEXISTENT-METHOD", "bad_nonexistent_method_call.c"),
            (
                "ES-OVERRIDE-OF-PLATFORM-GATED-METHOD",
                "bad_override_platform_gated.c",
            ),
        }
        expected_warnings = {
            ("ES-EMPTY-IFDEF", "bad_empty_ifdef_with_comments.c"),
            ("ES-EMPTY-IFDEF", "bad_empty_ifndef_with_comments.c"),
            ("ES-SOURCE-UNTERMINATED-BLOCK-COMMENT", "bad_unterminated_block_comment.c"),
            ("ES-SOURCE-UNTERMINATED-STRING", "bad_unterminated_string.c"),
            (
                "ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN",
                "bad_ifdef_empty_with_unsupported_only.c",
            ),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "bad_syncvar_in_else_branch.c"),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "ok_ifdef_with_unsupported_inner.c"),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "warn_endif_stray.c"),
            ("ES-EMPTY-IFDEF-UNSUPPORTED-PATTERN", "warn_ifdef_unterminated.c"),
            (
                "ES-CTX-READ-UNSUPPORTED-PATTERN",
                "warn_ctx_read_unchecked_combined_condition.c",
            ),
            ("ES-CTX-READ-UNSUPPORTED-PATTERN", "warn_ctx_read_in_try_catch.c"),
            ("ES-CTX-READ-UNCHECKED", "warn_ctx_read_unchecked_in_onvarsync.c"),
            (
                "ES-CTX-READ-UNCHECKED",
                "warn_ctx_read_unchecked_in_rpc_ifndef_server.c",
            ),
            ("ES-CTX-READ-UNCHECKED", "warn_ctx_read_unchecked_in_rpc_no_guard.c"),
            ("ES-SYNCVAR-CLASS-UNKNOWN", "warn_syncvar_class_template.c"),
            ("ES-SYNCVAR-UNSUPPORTED-PATTERN", "bad_syncvar_in_else_branch.c"),
            ("ES-SYNCVAR-UNSUPPORTED-PATTERN", "warn_syncvar_alternative_guard.c"),
            (
                "ES-SYNCVAR-UNSUPPORTED-PATTERN",
                "warn_syncvar_method_generic_return.c",
            ),
            ("ES-INT-MIN-COMPARISON", "warn_int_min_compare_symbolic.c"),
            ("ES-INT-MIN-COMPARISON", "warn_int_min_compare_literal.c"),
            ("ES-GETTYPE-EXACT-MATCH", "warn_gettype_equality.c"),
            ("ES-GETTYPE-EXACT-MATCH", "warn_gettype_equality_eq.c"),
            ("ES-GETTYPE-EXACT-MATCH", "warn_gettype_typename_uppercase.c"),
            ("ES-REF-AUTOPTR-COMBINED", "warn_ref_autoptr_combined.c"),
            ("ES-REF-AUTOPTR-COMBINED", "warn_autoptr_ref_combined.c"),
            ("ES-ONMOUSELEAVE-PARAM-COUNT", "warn_onmouseleave_3params.c"),
            (
                "ES-ONMOUSELEAVE-PARAM-COUNT",
                "warn_onmouseleave_3params_multiline.c",
            ),
            ("ES-REGISTERRECIPES-TYPO", "warn_registerrecipes_plain.c"),
            (
                "ES-RESPAWN-EQUIP-IN-ONCLIENTRESPAWNEVENT",
                "warn_onclientrespawn_equip.c",
            ),
        }

        self.assertTrue(expected_errors.issubset(observed_errors))
        self.assertTrue(expected_warnings.issubset(observed_warnings))


class TestEsLocalVarRedeclare(unittest.TestCase):
    def test_sibling_redeclare_fails(self):
        fixture = FIXTURES / "es" / "bad_local_var_redeclare_sibling.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-LOCAL-VAR-REDECLARE", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_local_var_redeclare_sibling.c", error["file"])
        self.assertEqual(11, error["line"])
        self.assertIn("multiple declaration", error["message"])
        assert_standard_findings(self, result)

    def test_nested_for_shadow_fails(self):
        fixture = FIXTURES / "es" / "bad_local_var_redeclare_nested_for.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        self.assertEqual("ES-LOCAL-VAR-REDECLARE", result["errors"][0]["rule_id"])
        self.assertEqual(6, result["errors"][0]["line"])
        assert_standard_findings(self, result)

    def test_hoisted_single_declaration_passes(self):
        fixture = FIXTURES / "es" / "ok_local_var_hoisted.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_same_name_distinct_methods_passes(self):
        fixture = FIXTURES / "es" / "ok_local_var_distinct_methods.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_sequential_for_loops_pass(self):
        fixture = FIXTURES / "es" / "ok_local_var_sequential_for.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_ifdef_else_same_name_is_not_redeclare(self):
        fixture = FIXTURES / "es" / "ok_local_var_ifdef_else.c"
        exit_code, result = script_validator.run([str(fixture)])

        redeclare = [
            error
            for error in result["errors"]
            if error["rule_id"] == "ES-LOCAL-VAR-REDECLARE"
        ]
        self.assertEqual([], redeclare)
        assert_standard_findings(self, result)


class TestEsMemberRedeclareBase(unittest.TestCase):
    def test_member_redeclare_fails(self):
        fixture = FIXTURES / "es" / "bad_member_redeclare_base.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-MEMBER-REDECLARE-BASE", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(3, error["line"])
        self.assertIn("m_NoiseSystem", error["message"])
        assert_standard_findings(self, result)

    def test_distinct_member_name_passes(self):
        fixture = FIXTURES / "es" / "ok_member_distinct_name.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_unknown_base_passes(self):
        fixture = FIXTURES / "es" / "ok_member_unknown_base.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsOverrideParamNameMismatch(unittest.TestCase):
    def test_param_name_mismatch_fails(self):
        fixture = FIXTURES / "es" / "bad_override_param_mismatch.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-OVERRIDE-PARAM-NAME-MISMATCH", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(3, error["line"])
        self.assertIn("action_data", error["message"])
        assert_standard_findings(self, result)

    def test_param_name_match_passes(self):
        fixture = FIXTURES / "es" / "ok_override_param_match.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_unknown_override_method_passes(self):
        fixture = FIXTURES / "es" / "ok_override_unknown_method.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsConfigNestedOverride(unittest.TestCase):
    def test_missing_forward_ref_fails(self):
        addon_root = FIXTURES / "config_nested" / "bad"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual(
            "ES-CONFIG-NESTED-OVERRIDE-NO-FORWARDREF", error["rule_id"]
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(14, error["line"])
        self.assertIn("SimulationModule", error["message"])
        assert_standard_findings(self, result)

    def test_with_forward_ref_passes(self):
        addon_root = FIXTURES / "config_nested" / "ok"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsInputsXmlNotRegistered(unittest.TestCase):
    def test_inputs_xml_present_unregistered_fails(self):
        addon_root = FIXTURES / "config_inputs" / "bad_missing"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        error = next(
            e for e in result["errors"]
            if e["rule_id"] == "CONFIG-INPUTS-XML-NOT-REGISTERED"
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(1, error["line"])
        assert_standard_findings(self, result)

    def test_inputs_xml_registered_passes(self):
        addon_root = FIXTURES / "config_inputs" / "ok_registered"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_no_inputs_xml_passes(self):
        addon_root = FIXTURES / "config_inputs" / "ok_no_inputs_xml"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])


class TestEsAttachmentsCompoundAppendCrossPbo(unittest.TestCase):
    def test_crosspbo_append_warns(self):
        addon_root = FIXTURES / "config_attachments" / "bad"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        warning = next(
            w for w in result["warnings"]
            if w["rule_id"] == "ES-ATTACHMENTS-COMPOUND-APPEND-CROSSPBO"
        )
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual(6, warning["line"])
        assert_standard_findings(self, result)

    def test_full_list_passes(self):
        addon_root = FIXTURES / "config_attachments" / "ok_full_list"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["warnings"])

    def test_same_pbo_parent_passes(self):
        addon_root = FIXTURES / "config_attachments" / "ok_same_pbo"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["warnings"])


class TestPdrivePathRvmat(unittest.TestCase):
    def test_relative_path_passes(self):
        fixture = FIXTURES / "pdrive" / "ok_relative_path.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_pdrive_path_warns(self):
        fixture = FIXTURES / "pdrive" / "bad_pdrive_path.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(result["warnings"]))
        warning = result["warnings"][0]
        self.assertEqual("RVMAT-PDRIVE-PATH", warning["rule_id"])
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual("bad_pdrive_path.rvmat", warning["file"])
        self.assertEqual(3, warning["line"])
        assert_standard_findings(self, result)

    def test_pdrive_in_comment_passes(self):
        fixture = FIXTURES / "pdrive" / "ok_pdrive_in_comment.rvmat"
        exit_code, result = script_validator.run([str(fixture)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["warnings"])


class TestPdrivePathConfig(unittest.TestCase):
    def test_pdrive_path_warns(self):
        addon_root = FIXTURES / "pdrive" / "config_bad"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(2, exit_code)
        self.assertEqual("WARN", result["status"])
        self.assertEqual([], result["errors"])
        warning = next(
            w for w in result["warnings"] if w["rule_id"] == "CONFIG-PDRIVE-PATH"
        )
        self.assertEqual("WARN", warning["severity"])
        self.assertEqual(5, warning["line"])
        assert_standard_findings(self, result)

    def test_relative_path_passes(self):
        addon_root = FIXTURES / "pdrive" / "config_ok"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestEsInputsXmlWrongRoot(unittest.TestCase):
    def test_wrong_root_fails(self):
        addon_root = FIXTURES / "inputs_root" / "bad"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        error = next(
            e for e in result["errors"]
            if e["rule_id"] == "CONFIG-INPUTS-XML-WRONG-ROOT"
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(1, error["line"])
        self.assertEqual("inputs.xml", error["file"])
        self.assertIn("modded_inputs", error["message"])
        assert_standard_findings(self, result)

    def test_correct_root_passes(self):
        addon_root = FIXTURES / "inputs_root" / "ok"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])

    def test_non_inputs_xml_ignored(self):
        addon_root = FIXTURES / "inputs_root" / "ok_other_xml"
        exit_code, result = script_validator.run([str(addon_root)])
        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestLayoutXmlFormat(unittest.TestCase):
    def test_brace_layout_passes(self):
        fixture = FIXTURES / "layout_xml" / "ok_brace.layout"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_xml_layout_fails(self):
        fixture = FIXTURES / "layout_xml" / "bad_xml.layout"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("LAYOUT-XML-FORMAT", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_xml.layout", error["file"])
        self.assertEqual(1, error["line"])
        self.assertIn("XML", error["message"])
        assert_standard_findings(self, result)


class TestEsLayoutFileMissing(unittest.TestCase):
    def test_present_layout_passes(self):
        addon_root = FIXTURES / "layout_file_missing" / "ok_present"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(2, result["info"]["files_scanned"])

    def test_missing_layout_fails(self):
        addon_root = FIXTURES / "layout_file_missing" / "bad_missing"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-LAYOUT-FILE-MISSING", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("dialog.c", error["file"])
        self.assertEqual(5, error["line"])
        self.assertIn("my_dialog.layout", error["message"])
        assert_standard_findings(self, result)

    def test_no_prefix_skips(self):
        addon_root = FIXTURES / "layout_file_missing" / "ok_no_prefix"
        exit_code, result = script_validator.run([str(addon_root)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])


class TestEsMethodNameCollidesVanillaClass(unittest.TestCase):
    def test_safe_method_name_passes(self):
        fixture = FIXTURES / "es" / "ok_method_name_safe.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_collision_fails(self):
        fixture = FIXTURES / "es" / "bad_method_name_collides.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-METHOD-NAME-COLLIDES-VANILLA-CLASS", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_method_name_collides.c", error["file"])
        self.assertEqual(3, error["line"])
        self.assertIn("LogManager", error["message"])
        assert_standard_findings(self, result)


class TestEsOverrideOfPlatformGatedMethod(unittest.TestCase):
    def test_unguarded_override_fails(self):
        fixture = FIXTURES / "es" / "bad_override_platform_gated.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual([], result["warnings"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual(
            "ES-OVERRIDE-OF-PLATFORM-GATED-METHOD", error["rule_id"]
        )
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual("bad_override_platform_gated.c", error["file"])
        self.assertEqual(3, error["line"])
        self.assertIn("GetConsoleToolbarText", error["message"])
        self.assertIn("PLATFORM_CONSOLE", error["message"])
        assert_standard_findings(self, result)

    def test_guarded_override_passes(self):
        fixture = FIXTURES / "es" / "ok_override_platform_gated.c"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])
        self.assertEqual([], result["warnings"])

    def test_other_class_override_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "ok_other_class.c"
            path.write_text(
                "class WidgetHost\n"
                "{\n"
                "    override string GetConsoleToolbarText()\n"
                "    {\n"
                "        return \"\";\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            exit_code, result = script_validator.run([str(path)])

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        self.assertEqual([], result["errors"])



class TerseOutputTests(unittest.TestCase):
    """The verdict must be the FIRST line: a reader that stops there has the answer."""

    def test_pass_is_a_single_line(self):
        _code, result = script_validator.run([str(FIXTURES / "empty")])
        terse = script_validator.format_terse(result)

        self.assertEqual("PASS", terse)

    def test_verdict_leads_and_counts_are_summarised(self):
        result = {
            "status": "FAIL",
            "errors": [{"rule_id": "ES-NO-DELETE", "message": "boom"}],
            "warnings": [{"rule_id": "ES-EMPTY-IFDEF", "message": "meh"}],
        }
        lines = script_validator.format_terse(result).split("\n")

        self.assertEqual("FAIL - 1 error, 1 warning", lines[0])
        self.assertEqual(3, len(lines))
        self.assertIn("ES-NO-DELETE", lines[1])
        self.assertIn("ES-EMPTY-IFDEF", lines[2])

    def test_json_stays_the_default(self):
        parser = script_validator.build_parser()

        self.assertFalse(parser.parse_args(["some_root"]).terse)
        self.assertTrue(parser.parse_args(["some_root", "--terse"]).terse)

class TestProtectedCrossModule(unittest.TestCase):
    """ES-PROTECTED-CROSS-MODULE — verified at runtime 2026-09-17.

    A disposable probe was built into a PBO and booted on a dedicated server:
    World compiled, Mission did not, with "Variable 'm_FX_ProbeValue' is
    protected" / "Can't compile \"Mission\" script module!".
    """

    def test_mission_reading_world_protected_fails(self):
        fixture = FIXTURES / "protected_cross_module" / "bad"
        exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-PROTECTED-CROSS-MODULE", error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertIn("m_FxHidden", error["message"])
        self.assertIn("4_World", error["message"])
        assert_standard_findings(self, result)

    def test_public_accessor_passes(self):
        fixture = FIXTURES / "protected_cross_module" / "ok_accessor"
        _exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)

    def test_same_module_access_passes(self):
        """`protected` within one module is legal and must not fire."""
        fixture = FIXTURES / "protected_cross_module" / "ok_same_module"
        _exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)


class TestExternalConsumerMissing(unittest.TestCase):
    """ES-EXTERNAL-CONSUMER-MISSING — observed 2026-09-17.

    A refactor deleted facade methods after proving no file under the addon's
    own scripts/ called them. The mission init.c did, and the server refused to
    compile it. The deleted names still existed on a subclass, so a plain
    "declared somewhere" search stays silent: the receiver's declared type is
    what decides.
    """

    def test_external_call_to_deleted_method_fails(self):
        fixture = FIXTURES / "external_consumer"
        exit_code, result = script_validator.run(
            [str(fixture / "bad"),
             "--external-scripts", str(fixture / "bad_external")]
        )

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual("ES-EXTERNAL-CONSUMER-MISSING", error["rule_id"])
        self.assertIn("FX_GetOutgoing", error["message"])
        self.assertIn("FX_GraphImpl", error["message"])
        assert_standard_findings(self, result)

    def test_method_declared_on_receiver_passes(self):
        fixture = FIXTURES / "external_consumer"
        _exit_code, result = script_validator.run(
            [str(fixture / "ok_declared"),
             "--external-scripts", str(fixture / "ok_external")]
        )

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)

    def test_vanilla_method_not_declared_in_addon_passes(self):
        """The addon declares the name nowhere, so it comes from vanilla."""
        fixture = FIXTURES / "external_consumer"
        _exit_code, result = script_validator.run(
            [str(fixture / "ok_vanilla_method"),
             "--external-scripts", str(fixture / "ok_vanilla_external")]
        )

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)

    def test_check_is_inert_without_external_roots(self):
        """Without --external-scripts there is nothing to compare against."""
        fixture = FIXTURES / "external_consumer" / "bad"
        _exit_code, result = script_validator.run([str(fixture)])

        self.assertEqual([], result["errors"])
        assert_standard_findings(self, result)


RESERVED = FIXTURES / "reserved_word_identifier"
RESERVED_RULE = "ES-RESERVED-WORD-IDENTIFIER"


def _errors_of(result, rule_id):
    return [e for e in result["errors"] if e["rule_id"] == rule_id]


class TestReservedWordIdentifier(unittest.TestCase):
    """ES-RESERVED-WORD-IDENTIFIER: a keyword used as a name.

    sealed: parameter, DayZDiag 1.29.163709, 2026-10-02, "Expected name, not a
    keyword 'sealed'". local: local variable, DayZDiag 1.30.164014 (Exp),
    2026-09-28, "Broken expression (missing ';'?)". owned and out: the same
    error on a local (skills/_shared/enscript/depth/review-and-troubleshooting.md and compiler-traps.md).
    """

    def test_sealed_parameter_fails(self):
        exit_code, result = script_validator.run([str(RESERVED / "bad_sealed_param")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, RESERVED_RULE)
        self.assertEqual([5], [e["line"] for e in errors])
        self.assertIn("fx_probe_sealed.c", errors[0]["file"])
        self.assertIn("'sealed'", errors[0]["message"])
        self.assertEqual("FAIL", errors[0]["severity"])
        assert_standard_findings(self, result)

    def test_local_variable_fails_on_its_declaration(self):
        exit_code, result = script_validator.run([str(RESERVED / "bad_local_var")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, RESERVED_RULE)
        # The declaration only; `local[0] = mx;` and `return local;` follow it.
        self.assertEqual([7], [e["line"] for e in errors])
        self.assertIn("'local'", errors[0]["message"])

    def test_owned_member_and_out_local_fail(self):
        _code, result = script_validator.run([str(RESERVED / "bad_owned_out")])

        errors = _errors_of(result, RESERVED_RULE)
        self.assertEqual(
            [(3, "owned"), (7, "out")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )

    def test_keywords_where_vanilla_puts_them_pass(self):
        _code, result = script_validator.run([str(RESERVED / "ok_modifiers")])

        self.assertEqual([], _errors_of(result, RESERVED_RULE))

    def test_only_branches_that_can_compile_are_judged(self):
        _code, result = script_validator.run([str(RESERVED / "preprocessor")])

        # `vector local;` and `EntityAI owned;` under #ifndef of macros this file
        # always defines (one of them under an #ifdef it guarantees) and
        # `int out;` under #if 0 never compile; `vector sealed;` compiles once
        # FX_SOME_OTHER_MOD's mod is loaded.
        self.assertEqual(
            [(16, "sealed")],
            [(e["line"], e["message"].split("'")[1])
             for e in _errors_of(result, RESERVED_RULE)],
        )

    def test_else_follows_its_macro_both_ways(self):
        _code, result = script_validator.run([str(RESERVED / "else_branches")])

        # FX_ELSE_ON is always defined: the #else of its #ifndef compiles
        # (`vector local;`) and so does its #ifdef branch (`EntityAI owned;`);
        # `vector sealed;` and `int out;` never compile.
        self.assertEqual(
            [(12, "local"), (15, "owned")],
            [(e["line"], e["message"].split("'")[1])
             for e in _errors_of(result, RESERVED_RULE)],
        )

    def test_names_without_their_type_before_them_on_the_line(self):
        exit_code, result = script_validator.run(
            [str(RESERVED / "bad_more_declarations")]
        )

        # A parameter split over two lines, a later declarator, a foreach
        # variable and the second variable of a for header; not the use of
        # `out` among the arguments of line 11. Later declarators end with
        # `=`, `;`, `,` and `[`.
        self.assertEqual(1, exit_code)
        self.assertEqual(
            [(8, "sealed"), (10, "out"), (12, "local"), (15, "owned"),
             (18, "local"), (19, "owned"), (20, "out")],
            [(e["line"], e["message"].split("'")[1])
             for e in _errors_of(result, RESERVED_RULE)],
        )

    def test_template_arguments_end_at_their_own_bracket(self):
        # The type's template arguments could
        # run on to any later `>` of the statement, so each place a
        # declaration can start read to its end. These 8 000 template
        # arguments in 96 KB took 9 s, and take 0.02 s.
        from detectors.es_reserved_word_identifier import (
            check_es_reserved_word_identifier,
        )

        source = (
            "class A\n{\n    void F()\n    {\n        auto x = new Param<"
            + "array<int>, " * 7999
            + "array<int>>(1);\n    }\n}\n"
        )

        start = time.perf_counter()
        errors = check_es_reserved_word_identifier(source, "scripts/4_World/x.c")

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual([], errors)

    def test_a_type_with_templates_five_deep_is_read(self):
        # Four levels were read, and a mod's fifth
        # hid the name.
        from detectors.es_reserved_word_identifier import (
            check_es_reserved_word_identifier,
        )

        errors = check_es_reserved_word_identifier(
            "class A\n{\n"
            "    map<string, ref map<string, ref map<string, ref map<string,"
            " ref array<int>>>>> local;\n"
            "}\n",
            "scripts/4_World/x.c",
        )

        self.assertEqual([3], [e["line"] for e in errors])

    def test_two_comparisons_hide_no_later_declarator(self):
        # The declaration patterns read `< b, out = c >` blanked, as template
        # arguments; the walk to the later declarators reads the source.
        from detectors.es_reserved_word_identifier import (
            check_es_reserved_word_identifier,
        )

        errors = check_es_reserved_word_identifier(
            "class A\n{\n    void F()\n    {\n"
            "        bool first = a < b, out = c > d;\n"
            "    }\n}\n",
            "scripts/4_World/x.c",
        )

        self.assertEqual([5], [e["line"] for e in errors])

    def test_vanilla_closers_and_one_line_ifs_hide_no_word(self):
        # Vanilla closes a template with one `>` too
        # many (`map<string, int>> name;`, 3_game/global/ammotypes.c:80 on
        # 1.30); and in `if (a < b) ... if (c > d)` no template runs from the
        # `<` to the `>`.
        from detectors.es_reserved_word_identifier import (
            check_es_reserved_word_identifier,
        )

        errors = check_es_reserved_word_identifier(
            "class A\n{\n"
            "    static ref map<string, int>> local;\n"
            "    void F(array<int> values, int a, int b, int c, int d)\n    {\n"
            "        if (a < b) foreach (int local : values) if (c > d) Print(local);\n"
            "    }\n}\n",
            "scripts/4_World/x.c",
        )

        self.assertEqual([3, 6], [e["line"] for e in errors])

    def test_each_declaration_is_read_once(self):
        # Each parameter on a line of its own read on
        # to the `)`. These 2 400 took 6.6 s, and take 0.01 s.
        from detectors.es_reserved_word_identifier import (
            check_es_reserved_word_identifier,
        )

        source = (
            "class A\n{\n    void F(\n"
            + ",\n".join("        int a%d" % i for i in range(2400))
            + ")\n    {\n    }\n}\n"
        )

        start = time.perf_counter()
        errors = check_es_reserved_word_identifier(source, "scripts/4_World/x.c")

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual([], errors)

    def test_lines_are_counted_once_per_file(self):
        # Each word found counted the lines from the
        # start of the file again. These 64 000 members took 12 s, and take
        # 0.4 s.
        from detectors.es_reserved_word_identifier import (
            check_es_reserved_word_identifier,
        )

        source = "class A\n{\n" + "    int local;\n" * 64000 + "}\n"

        start = time.perf_counter()
        errors = check_es_reserved_word_identifier(source, "scripts/4_World/x.c")

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual(64000, len(errors))
        self.assertEqual(64002, errors[-1]["line"])

    def test_a_word_that_starts_its_line_is_on_that_line(self):
        # The members above all follow a space, so
        # counting the lines up to one character before each word passed them.
        from detectors.es_reserved_word_identifier import (
            check_es_reserved_word_identifier,
        )

        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                source = newline.join(
                    ["class A", "{", "int", "local;", "int", "local;", "}", ""]
                )

                errors = check_es_reserved_word_identifier(
                    source, "scripts/4_World/x.c"
                )

                self.assertEqual([4, 6], [e["line"] for e in errors])


MODULO = FIXTURES / "modulo_float_context"
MODULO_RULE = "ES-MODULO-FLOAT-CONTEXT"


class TestModuloFloatContext(unittest.TestCase):
    """ES-MODULO-FLOAT-CONTEXT: '%' in an expression with a float literal.

    `((g % 5) - 2) * 7.0` failed on DayZDiag 1.29 (2026-09-28) and
    `float ox = (n % 4) * 0.7 - 1.05;` on DayZ 1.30 Exp (2026-09-24), both
    with "Unknown operator '%'". On DayZDiag 1.30.164289 (2026-11-09)
    two more failed with it, each at its own line, and
    the third shape, with the '%' in an int local first, compiled.
    """

    def _errors_in(self, result, name):
        return [
            e for e in _errors_of(result, MODULO_RULE)
            if pathlib.Path(e["file"]).name == name
        ]

    def test_both_failing_shapes_fail(self):
        exit_code, result = script_validator.run([str(MODULO / "bad")])

        self.assertEqual(1, exit_code)
        errors = self._errors_in(result, "fx_probe_grid.c")
        self.assertEqual([7, 12], [e["line"] for e in errors])
        self.assertIn("7.0", errors[0]["message"])
        self.assertIn("0.7", errors[1]["message"])
        assert_standard_findings(self, result)

    def test_the_two_d35a_statements_fail_at_the_line_the_compiler_named(self):
        _code, result = script_validator.run([str(MODULO / "bad")])

        # mcpprobed35ab.c,6 and mcpprobed35ac.c,10 in the server script logs.
        literals = self._errors_in(result, "fx_cell_literals.c")
        static_const = self._errors_in(result, "fx_cell_static_const.c")
        self.assertEqual([6], [e["line"] for e in literals])
        self.assertEqual([10], [e["line"] for e in static_const])
        for error in literals + static_const:
            self.assertEqual("FAIL", error["severity"])
            self.assertIn("float literal 0.5.", error["message"])

    def test_integer_modulo_and_the_int_local_fix_pass(self):
        _code, result = script_validator.run([str(MODULO / "ok")])

        self.assertEqual([], _errors_of(result, MODULO_RULE))

    def test_the_three_d35a_statements_that_compiled_give_no_finding(self):
        exit_code, result = script_validator.run([str(MODULO / "ok")])

        self.assertEqual(0, exit_code)
        findings = [
            f for f in result["errors"] + result["warnings"]
            if pathlib.Path(f["file"]).name == "fx_cell_int_local.c"
        ]
        self.assertEqual([], findings)

    def test_expression_boundaries(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        def flagged(statement):
            source = (
                "class C\n{\n    void F(int n, int i)\n    {\n        %s\n    }\n}\n"
                % statement
            )
            stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
            return bool(check_es_modulo_float_context(source, stripped, "x.c"))

        # Same expression as the float literal: judged.
        self.assertTrue(flagged("float a = 0.5 * (n % 4);"))
        self.assertTrue(flagged("return (n % 4) * 0.5;"))
        self.assertTrue(flagged("SetPos(1, ((n % 3) + 1) * 2.5);"))
        # Another expression: an argument, an index, a comparison, another
        # statement, or a call's arguments. Not judged.
        self.assertFalse(flagged("Foo(n % 4, 0.5);"))
        self.assertFalse(flagged("float b = m_Arr[i % 3] * 0.5;"))
        self.assertFalse(flagged("if (n % 2 == 0) x = 1.5;"))
        self.assertFalse(flagged("int k = n % 4; float c = k * 0.5;"))
        self.assertFalse(flagged("float d = Math.Floor(n % 4) * 0.5;"))
        self.assertFalse(flagged("n %= 4;"))
        # A string literal makes `+` a concatenation: not judged, also when
        # the string comes first.
        self.assertFalse(flagged('Print("cell " + (n % 4) + " of " + 0.5);'))
        self.assertFalse(flagged('Print("cell " + (n % 4) + 0.5);'))
        # A comment is not part of the expression, quotes in it included.
        self.assertFalse(flagged("int k = n % 4; // scale by 0.5 later"))
        self.assertTrue(flagged("float e = (n % 4) /* cell */ * 0.5;"))
        self.assertTrue(flagged('float e2 = (n % 4) /* "cell" */ * 0.5;'))
        self.assertTrue(flagged('float e3 = (n % 4) // "cell"\n            * 0.5;'))
        # An int cast makes an int of its operand, float literal or not.
        self.assertFalse(flagged("int j = n % (int)2.5;"))
        self.assertFalse(flagged("int j2 = n % ((int)-2.5);"))
        self.assertFalse(flagged("int j3 = n % (int)(2.5 * i);"))
        self.assertTrue(flagged("float j4 = (n % 4) * (int)i + 0.5;"))
        # A condition in parentheses is a value of its own; behind a `?` only
        # the results count; arithmetic before a comparison is still judged.
        self.assertFalse(flagged("int b = n % (i > 0.5);"))
        self.assertFalse(flagged("float t = (n % 4) * (i > 0.5 ? 1 : 2);"))
        self.assertTrue(flagged("float t2 = (n % 4) * (i > 1 ? 0.5 : 2);"))
        self.assertTrue(flagged("bool t3 = (n % 4 * 0.5 > 2);"))
        self.assertTrue(flagged("float t4 = (n % 4) * (Max(i > 1, 2) + 0.5);"))
        # Code that never compiles is not judged; another mod's branch is.
        self.assertFalse(flagged("#if 0\nfloat g = (n % 4) * 0.5;\n#endif"))
        self.assertTrue(flagged("#ifdef FX_OTHER_MOD\nfloat h = (n % 4) * 0.5;\n#endif"))

    def test_an_expression_skips_dead_lines_and_other_branches_of_its_blocks(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        def flagged(body):
            source = "class C\n{\n    int F(int n)\n    {\n%s\n    }\n}\n" % body
            stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
            return bool(check_es_modulo_float_context(source, stripped, "x.c"))

        # Every block around the `%` counts, not only the innermost one.
        self.assertFalse(flagged(
            "        return n\n"
            "#ifdef FX_OUTER\n#ifdef FX_INNER\n            % 4\n"
            "#else\n            % 4\n#endif\n"
            "#else\n            * 0.5\n#endif\n        ;"
        ))

        # A float in a branch that never compiles is no part of the
        # expression.
        self.assertFalse(flagged(
            "#define FX_INTEGER\n"
            "        return (n % 4)\n"
            "#ifdef FX_INTEGER\n            + 1\n"
            "#else\n            * 0.5\n#endif\n        ;"
        ))
        # Nor is a float in the other branch of the block the `%` sits in,
        # whatever the macro: the two never compile together.
        self.assertFalse(flagged(
            "        return n\n"
            "#ifdef FX_OTHER_MOD\n            % 4\n"
            "#else\n            * 0.5\n#endif\n        ;"
        ))
        # A float in a branch that compiles along with the `%` is.
        self.assertTrue(flagged(
            "        return (n % 4)\n"
            "#ifdef FX_OTHER_MOD\n            * 0.5\n#endif\n        ;"
        ))

    def test_deep_parentheses_end_in_a_finding_not_an_exception(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        # Deeper than the interpreter's recursion limit
        # (1100 pairs raised RecursionError).
        depth = sys.getrecursionlimit() + 200
        statement = (
            "return (n % 4) * " + "(" * depth + "0.7" + ")" * depth + " - 1.05;"
        )
        source = "class C\n{\n    float F(int n)\n    {\n        %s\n    }\n}\n" % statement
        stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
        errors = check_es_modulo_float_context(source, stripped, "x.c")

        self.assertEqual([5], [e["line"] for e in errors])
        self.assertIn("0.7", errors[0]["message"])

    def test_an_index_before_the_float_does_not_end_the_expression(self):
        from detectors.es_modulo_float_context import check_es_modulo_float_context
        from stripper import strip_enforce_comments_and_strings

        # The index is skipped and the expression reads on to the float after
        # it, at the top level and inside a group
        # (ending the expression at an index kept every other test green).
        source = (
            "class C\n{\n    int m_Values[2];\n    float F(int n, int i)\n    {\n"
            "        float a = (n % 4) + m_Values[i] * 0.5;\n"
            "        return (n % 4) * (m_Values[0] + 2.5);\n"
            "    }\n}\n"
        )
        stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
        errors = check_es_modulo_float_context(source, stripped, "x.c")

        self.assertEqual([6, 7], [e["line"] for e in errors])
        self.assertIn("float literal 0.5.", errors[0]["message"])
        self.assertIn("float literal 2.5.", errors[1]["message"])

    def test_string_spans_are_the_strings_the_stripper_blanks(self):
        from detectors.es_modulo_float_context import _string_spans
        from stripper import strip_enforce_comments_and_strings

        source = (
            'a = "x \\" // y" + b; // "not a string"\n'
            '/* "nor this" */ c = "z";\n'
            'd = "open'
        )
        stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
        spans = _string_spans(source)

        self.assertEqual(
            ['"x \\" // y"', '"z"', '"open'],
            [source[start:end] for start, end in spans],
        )
        for start, end in spans:
            self.assertEqual("", stripped[start:end].strip())


FORMULA = FIXTURES / "formula_too_complex"
FORMULA_RULE = "ES-FORMULA-TOO-COMPLEX"


def _formula_chain(terms):
    """The probes' pattern: literal, int, literal, float.ToString(), ..."""
    parts = []
    for index in range(terms):
        if index % 2 == 1:
            parts.append("i0" if index % 4 == 1 else "f0.ToString()")
        else:
            parts.append('"%s"' % ("a" if index == 0 else " " + chr(ord("a") + index // 2)))
    return " + ".join(parts)


class TestFormulaTooComplex(unittest.TestCase):
    """ES-FORMULA-TOO-COMPLEX: 18 or more terms joined by '+' with a string.

    DayZDiag 1.30.164289 (2026-11-09): one line
    alternating string literals with an int and a float's ToString()
    compiled with 14 and 17 terms and failed with "Formula too complex" with
    18 and 20.
    """

    def _flagged(self, body):
        from detectors.es_formula_too_complex import check_es_formula_too_complex
        from stripper import strip_enforce_comments_and_strings

        source = (
            "class C\n{\n    string F(int i0, float f0)\n    {\n%s\n    }\n}\n" % body
        )
        stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
        return [
            w["line"] for w in check_es_formula_too_complex(source, stripped, "x.c")
        ]

    def test_the_chain_is_the_probes_pattern(self):
        self.assertEqual(
            '"a" + i0 + " b" + f0.ToString() + " c"', _formula_chain(5)
        )
        probe = (
            '"a" + i0 + " b" + f0.ToString() + " c" + i0 + " d" + f0.ToString()'
            ' + " e" + i0 + " f" + f0.ToString() + " g" + i0 + " h"'
            ' + f0.ToString() + " i" + i0 + " j" + f0.ToString()'
        )
        self.assertEqual(probe, _formula_chain(20))

    def test_18_and_20_terms_warn_at_the_line_the_compiler_named(self):
        exit_code, result = script_validator.run([str(FORMULA / "bad")])

        self.assertEqual(2, exit_code)
        self.assertEqual([], result["errors"])
        warnings = [w for w in result["warnings"] if w["rule_id"] == FORMULA_RULE]
        # mcpprobeterms18.c,6 and mcpprobeterms20.c,6 in the server script logs.
        self.assertEqual(
            [("fx_terms18.c", 6), ("fx_terms20.c", 6)],
            sorted((pathlib.Path(w["file"]).name, w["line"]) for w in warnings),
        )
        for warning in warnings:
            self.assertEqual("WARN", warning["severity"])
            self.assertIn("Formula too complex", warning["message"])
            self.assertIn(
                "Other operand types and a statement over several lines are "
                "not measured.",
                warning["message"],
            )
        self.assertIn("joins 18 terms", warnings[0]["message"])
        assert_standard_findings(self, result)

    def test_14_and_17_terms_numbers_alone_and_a_split_give_no_finding(self):
        exit_code, result = script_validator.run([str(FORMULA / "ok")])

        self.assertEqual(0, exit_code)
        self.assertEqual([], result["errors"] + result["warnings"])

    def test_what_counts_as_a_join(self):
        chain17 = _formula_chain(17)
        self.assertEqual([], self._flagged("        string s = %s;" % chain17))
        self.assertEqual(
            [5], self._flagged("        string s = %s + i0;" % chain17)
        )
        # `++`, `+=` and a unary `+` join nothing.
        self.assertEqual([], self._flagged(
            "        int k = 0;\n"
            "        string s = %s + (k++).ToString() + (+k).ToString();\n"
            "        s += i0;" % _formula_chain(15)
        ))
        # A `+` after a postfix increment does join.
        self.assertEqual([6], self._flagged(
            "        int k = 0;\n"
            "        string s = %s + k++ + i0;" % chain17[:chain17.rindex(" + ")]
        ))
        # A `+` in a string or a comment is none: 17 terms.
        self.assertEqual([], self._flagged(
            '        string s = %s + "+ + + +" /* + + + */ + i0; // + + +'
            % _formula_chain(15)
        ))
        # Numbers alone are not judged, however many.
        self.assertEqual([], self._flagged(
            "        int n = %s;" % " + ".join(["i0"] * 30)
        ))
        # A `+` inside parentheses or a call's arguments counts.
        self.assertEqual([5], self._flagged(
            '        string s = "a" + (%s).ToString() + i0;'
            % " + ".join(["i0"] * 16)
        ))

    def test_a_statement_over_several_lines_is_reported_at_its_first_line(self):
        chain = _formula_chain(18).split(" + ")
        body = "        string s = %s\n            + %s\n            + %s;" % (
            " + ".join(chain[:6]),
            " + ".join(chain[6:12]),
            " + ".join(chain[12:]),
        )

        self.assertEqual([5], self._flagged(body))

    def test_what_never_compiles_and_other_branches_are_not_counted(self):
        head = _formula_chain(9)
        tail = " + ".join(["i0"] * 6)
        # Under #if 0: never compiled, so 9 terms.
        self.assertEqual([], self._flagged(
            "        string s = %s\n#if 0\n            + %s + i0 + i0 + i0\n#endif\n"
            "            ;" % (head, tail)
        ))
        # Each branch of one block holds 6 more terms: 15 in either build,
        # though the file holds 21.
        self.assertEqual([], self._flagged(
            "        string s = %s\n#ifdef FX_OTHER_MOD\n            + %s\n"
            "#else\n            + %s\n#endif\n            ;" % (head, tail, tail)
        ))
        # Another mod's branch compiles along with the rest: 18 terms.
        self.assertEqual([5], self._flagged(
            "        string s = %s\n#ifdef FX_OTHER_MOD\n            + %s + i0 + i0 + i0\n"
            "#endif\n            ;" % (head, tail)
        ))
        # Two blocks side by side are not counted together either: 15 terms
        # in each view, though both can compile in one build (21).
        self.assertEqual([], self._flagged(
            "        string s = %s\n#ifdef FX_ONE\n            + %s\n#endif\n"
            "#ifdef FX_TWO\n            + %s\n#endif\n            ;" % (head, tail, tail)
        ))


UNDEFINED = FIXTURES / "undefined_class_ref"
UNDEFINED_RULE = "ES-UNDEFINED-CLASS-REF"


def _undefined_run(fixture, *extra):
    return script_validator.run(
        [str(UNDEFINED / fixture), "--vanilla-root", str(UNDEFINED / "vanilla")]
        + [str(arg) for arg in extra]
    )


def _rule_errors(result):
    return [e for e in result["errors"] if e["rule_id"] == UNDEFINED_RULE]


def _rule_skips(result):
    return [
        s for s in result["info"].get("skipped_checks", [])
        if s["rule_id"] == UNDEFINED_RULE
    ]


class TestUndefinedClassRef(unittest.TestCase):
    """ES-UNDEFINED-CLASS-REF — observed 2026-09-19 on a mod.

    A change deleted a class from 4_World while 5_Mission still called its
    static Sort(...). The
    type existed in no module, so Mission could not compile; the linter said
    WARN with 0 errors. `bad_mission_ref` is that shape with fixture names.
    """

    def test_mission_calls_class_that_exists_in_no_module_fails(self):
        exit_code, result = _undefined_run("bad_mission_ref")

        self.assertEqual(1, exit_code)
        self.assertEqual("FAIL", result["status"])
        self.assertEqual(1, len(result["errors"]))
        error = result["errors"][0]
        self.assertEqual(UNDEFINED_RULE, error["rule_id"])
        self.assertEqual("FAIL", error["severity"])
        self.assertEqual(11, error["line"])
        self.assertIn("fx_maintenance_client.c", error["file"])
        self.assertIn("FX_ExternalStagingSortPlanner", error["message"])
        self.assertIn("5_Mission", error["message"])
        self.assertEqual([], _rule_skips(result))
        assert_standard_findings(self, result)

    def test_same_tree_with_the_class_declared_passes(self):
        exit_code, result = _undefined_run("ok_mission_ref")

        self.assertEqual(0, exit_code)
        self.assertEqual([], result["errors"])
        self.assertEqual([], _rule_skips(result))

    def test_each_reference_form_and_macro_gate(self):
        _exit_code, result = _undefined_run("forms")

        flagged = {
            e["message"].split("'")[1] for e in _rule_errors(result)
        }
        self.assertEqual(
            {
                "FX_MissingNew",
                "FX_MissingCast",
                "FX_MissingDecl",
                "FX_MissingTemplateArg",
                "FX_MissingStatic",
                # a space before the call's parenthesis, as in vanilla's
                # `Math.Sqrt (` (5_mission/dayzintroscenepc.c:32)
                "FX_MissingSpacedCall",
                # judged: DIAG_DEVELOPER is a build flag vanilla tests, so both
                # of its branches compile in some build; FX_FORMS_ON is in the
                # addon's defines[] and FX_LOCAL_FLAG is #define'd, so the
                # branch where they are defined compiles
                "FX_MissingUnderVanillaMacro",
                "FX_MissingUnderVanillaElse",
                "FX_MissingUnderConfigDefine",
                "FX_MissingUnderLocalDefine",
                # FX_DIAG_ONLY_FLAG is #define'd only under #ifdef DIAG_DEVELOPER,
                # and FX_CONDITIONAL_CONFIG_FLAG is in a defines[] under
                # #ifdef FX_OPTIONAL_MOD: neither is always on, so their
                # #ifndef branches compile too
                "FX_MissingUnderConditionalDefine",
                "FX_MissingUnderConditionalConfigDefine",
                # one entry of a defines[] sits under #ifdef FX_OPTIONAL_MOD
                "FX_MissingUnderSpanningDefine",
                # named as a template argument in an unjudged branch: a comma
                # inside `<...>` does not declare a variable
                "FX_MissingBehindTemplate",
                "FX_MissingBehindBoxTemplate",
            },
            flagged,
        )
        # Not flagged: a PascalCase member used as a receiver (Planner), enum
        # access, a typedef, a template parameter, a vanilla class declared
        # under #ifdef, a `/*sealed*/ class`, code under another mod's flag,
        # the second variable of `string fx_first, FX_Second;`, and the
        # #ifndef / #else branches of macros the addon always defines.
        for name in ("Planner", "EVanillaMode", "TStringArray", "TItem",
                     "FX_VanillaDiagOnly", "PlayerBase", "FX_OptionalDependency",
                     "SurfaceDetectionParameters", "FX_Second",
                     "FX_DeadUnderIfndef", "FX_DeadUnderElse",
                     # `fx_a<fx_b` is a comparison, so FX_LocalFlag is the
                     # second variable of its declaration
                     "FX_LocalFlag",
                     # FX_SWITCHED_FLAG (config) and FX_LOCAL_DERIVED (script)
                     # are defined under an #ifdef the same file guarantees
                     "FX_DeadUnderSwitchedDefine", "FX_DeadUnderDerivedDefine"):
            self.assertNotIn(name, flagged)
        assert_standard_findings(self, result)

    def test_uncovered_dependency_is_skipped_not_failed(self):
        """requiredAddons names a mod no scanned root provides: the type may live there."""
        exit_code, result = _undefined_run("dependency")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("FX_Dep_Scripts", skips[0]["reason"])
        self.assertEqual(
            {"FX_DepManager", "FX_GonePlanner"},
            {item["name"] for item in skips[0]["unresolved"]},
        )

    def test_dependency_passed_as_external_root_turns_skip_into_verdict(self):
        exit_code, result = _undefined_run(
            "dependency",
            "--external-scripts", UNDEFINED / "dependency_external",
        )

        self.assertEqual(1, exit_code)
        errors = _rule_errors(result)
        self.assertEqual(1, len(errors))
        self.assertIn("FX_GonePlanner", errors[0]["message"])
        self.assertEqual([], _rule_skips(result))

    def test_dependency_named_by_a_macro_is_unknown(self):
        exit_code, result = _undefined_run("macro_required_addon")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("FX_DEPENDENCY (not a string literal)", skips[0]["reason"])
        self.assertIn("123 (not a string literal)", skips[0]["reason"])

    def test_dependency_of_a_dependency_must_be_scanned_too(self):
        exit_code, result = _undefined_run(
            "transitive",
            "--external-scripts", UNDEFINED / "transitive_dep_a",
        )

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("FX_DepB_Scripts", skips[0]["reason"])

        exit_code, result = _undefined_run(
            "transitive",
            "--external-scripts", UNDEFINED / "transitive_dep_a",
            "--external-scripts", UNDEFINED / "transitive_dep_b",
        )

        self.assertEqual(1, exit_code)
        self.assertEqual(
            ["FX_GoneEverywhere"],
            [e["message"].split("'")[1] for e in _rule_errors(result)],
        )
        self.assertEqual([], _rule_skips(result))

    def test_a_dz_prefixed_mod_patch_is_not_vanilla(self):
        exit_code, result = _undefined_run("dz_prefixed_dependency")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("DZ_FX_ThirdParty", skips[0]["reason"])

    def test_a_file_is_not_a_vanilla_root(self):
        path, reason = vanilla_tree.resolve_vanilla_root(
            str(UNDEFINED / "bad_mission_ref" / "config.cpp")
        )

        self.assertIsNone(path)
        self.assertIn("vanilla tree not found", reason)

    def test_vanilla_root_that_is_empty_a_file_or_without_the_class_skips(self):
        with tempfile.TemporaryDirectory() as empty:
            with tempfile.TemporaryDirectory() as enum_only:
                # an enum named Managed is not the class every scripts tree
                # declares
                (pathlib.Path(enum_only) / "only.c").write_text(
                    "enum Managed\n{\n    FX_Value\n}\n", encoding="utf-8"
                )
                for vanilla in (empty, enum_only,
                                UNDEFINED / "bad_mission_ref" / "config.cpp"):
                    exit_code, result = script_validator.run(
                        [str(UNDEFINED / "bad_mission_ref"),
                         "--vanilla-root", str(vanilla)]
                    )

                    self.assertEqual(0, exit_code)
                    self.assertEqual([], _rule_errors(result))
                    self.assertEqual(1, len(_rule_skips(result)))

    def test_empty_required_addons_means_unknown_dependencies(self):
        exit_code, result = _undefined_run("no_required_addons")

        self.assertEqual(0, exit_code)
        self.assertEqual([], _rule_errors(result))
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertEqual(
            ["FX_SomeoneElsesType"], [item["name"] for item in skips[0]["unresolved"]]
        )

    def test_missing_vanilla_tree_is_a_skip_never_a_fail(self):
        exit_code, result = script_validator.run(
            [str(UNDEFINED / "bad_mission_ref"),
             "--vanilla-root", str(UNDEFINED / "no_such_vanilla_tree")]
        )

        self.assertEqual(0, exit_code)
        self.assertEqual("PASS", result["status"])
        skips = _rule_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("vanilla tree not found", skips[0]["reason"])

    def test_default_resolution_without_any_vanilla_tree_skips(self):
        """No --vanilla-root, no DAYZ_VANILLA_ROOT, no P:\\scripts (setUpModule)."""
        exit_code, result = script_validator.run([str(UNDEFINED / "bad_mission_ref")])

        self.assertEqual(0, exit_code)
        self.assertEqual([], result["errors"])
        self.assertEqual(1, len(_rule_skips(result)))

    def test_vanilla_tree_as_its_own_addon_is_clean(self):
        """The vanilla control shape: the tree is both the addon and vanilla.

        Its config-less layout must not turn into "dependencies unknown": a
        finding here has to fail the control, not hide in a SKIP.
        """
        vanilla = UNDEFINED / "vanilla"
        result = script_validator.validate_addon(vanilla, vanilla_root=vanilla)

        self.assertEqual([], _rule_errors(result))
        self.assertEqual([], _rule_skips(result))

    def test_skip_is_printed_after_the_verdict_in_terse_mode(self):
        _code, result = _undefined_run("dependency")
        lines = script_validator.format_terse(result).split("\n")

        self.assertEqual("PASS", lines[0])
        self.assertTrue(lines[1].startswith("  SKIP ES-UNDEFINED-CLASS-REF"))
        self.assertIn("FX_GonePlanner", lines[1])

    def test_template_arguments_end_at_their_own_bracket(self):
        # In declared_variables, the same
        # statement as in TestReservedWordIdentifier took 15 s, and takes
        # 0.02 s.
        from detectors.es_undefined_class_ref import declared_variables

        source = (
            "class A\n{\n    void F()\n    {\n        auto x = new Param<"
            + "array<int>, " * 7999
            + "array<int>>(1);\n    }\n}\n"
        )

        start = time.perf_counter()
        names = declared_variables(source)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual(set(), names)

    def test_template_arguments_declare_no_variable(self):
        # Each `ref AuditEntry,` read like a
        # declaration of AuditEntry, and each was read to the end of the
        # statement. These 2 400 took 7.8 s, and take 0.01 s.
        from detectors.es_undefined_class_ref import declared_variables

        source = (
            "class A\n{\n    void F()\n    {\n        auto x = new Param<"
            + "ref AuditEntry, " * 2399
            + "ref AuditEntry>(1);\n    }\n}\n"
        )

        start = time.perf_counter()
        names = declared_variables(source)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual(set(), names)

    def test_a_variable_with_nested_templates_is_no_class(self):
        # A variable is collected however
        # deep its type nests, and a later declarator after two comparisons
        # too, so a call on it is no static call on an undefined class.
        from detectors.es_undefined_class_ref import (
            check_es_undefined_class_ref,
            declared_variables,
        )

        source = (
            "class A\n{\n"
            "    array<ref array<int>> AuditMatrix;\n"
            "    map<string, ref map<string, ref map<string, ref map<string,"
            " ref array<ref EntityAI>>>>> AuditFoodProperties;\n"
            "    void F()\n    {\n"
            "        bool first = a < b, AuditLater = c > d;\n"
            "        AuditMatrix.Count();\n"
            "        AuditFoodProperties.Count();\n"
            "        AuditLater.Count();\n"
            "    }\n}\n"
        )
        config = (
            "class CfgPatches\n{\n    class FX_Audit\n    {\n"
            "        requiredAddons[] = {\"DZ_Data\", \"DZ_Scripts\"};\n"
            "    };\n};\n"
        )

        names = declared_variables(source)
        result = check_es_undefined_class_ref(
            [("scripts/4_World/x.c", source)],
            [("config.cpp", config)],
            [],
            [],
            UNDEFINED / "vanilla",
        )

        self.assertLessEqual(
            {"AuditMatrix", "AuditFoodProperties", "AuditLater"}, names
        )
        self.assertEqual(([], []), result)

    def test_vanilla_closers_and_one_line_ifs_hide_no_variable(self):
        # Vanilla closes a template with one `>` too
        # many (`map<string, int>> name;`, 3_game/global/ammotypes.c:80 on
        # 1.30); and in `if (a < b) ... if (c > d)` no template runs from the
        # `<` to the `>`. A call on either variable is no static call on an
        # undefined class.
        from detectors.es_undefined_class_ref import (
            check_es_undefined_class_ref,
            declared_variables,
        )

        source = (
            "class A\n{\n"
            "    static ref map<string, int>> AuditSurfaceEffects;\n"
            "    void F(array<int> values, int a, int b, int c, int d)\n    {\n"
            "        AuditSurfaceEffects.Count();\n"
            "        if (a < b) foreach (int AuditValue : values)"
            " if (c > d) AuditValue.ToString();\n"
            "    }\n}\n"
        )
        config = (
            "class CfgPatches\n{\n    class FX_Audit\n    {\n"
            "        requiredAddons[] = {\"DZ_Data\", \"DZ_Scripts\"};\n"
            "    };\n};\n"
        )

        names = declared_variables(source)
        result = check_es_undefined_class_ref(
            [("scripts/4_World/x.c", source)],
            [("config.cpp", config)],
            [],
            [],
            UNDEFINED / "vanilla",
        )

        self.assertLessEqual({"AuditSurfaceEffects", "AuditValue"}, names)
        self.assertEqual(([], []), result)

    def test_template_arguments_over_lines_declare_no_variable(self):
        # With a newline after `Param<` the
        # arguments were not blanked, so `ref AuditEntry,` declared AuditEntry,
        # and so did the declarator after its comma, read on to the end of the
        # statement. These 4 800 took 15 s, and take 0.01 s.
        from detectors.es_undefined_class_ref import declared_variables

        source = (
            "class A\n{\n    void F()\n    {\n        auto x = new Param<\n"
            + "ref AuditEntry, AuditEntry, " * 2399
            + "ref AuditEntry, AuditEntry>(1);\n    }\n}\n"
        )

        start = time.perf_counter()
        names = declared_variables(source)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual(set(), names)

    def test_template_arguments_after_a_space_declare_no_variable(self):
        # With a space or a tab before the `<`, the
        # template arguments over lines were read as code, so `ref AuditEntry,`
        # declared AuditEntry and the static call on that undefined class went
        # unreported. On one line, so did the type after a comma.
        from detectors.es_undefined_class_ref import (
            check_es_undefined_class_ref,
            declared_variables,
        )

        config = (
            "class CfgPatches\n{\n    class FX_Audit\n    {\n"
            "        requiredAddons[] = {\"DZ_Data\", \"DZ_Scripts\"};\n"
            "    };\n};\n"
        )
        for gap in (" ", "\t"):
            with self.subTest(gap=repr(gap)):
                source = (
                    "class A\n{\n    void F()\n    {\n"
                    "        auto p = new map" + gap + "<\n"
                    "            ref AuditEntry, bool>();\n"
                    "        AuditEntry.Method();\n"
                    "    }\n}\n"
                )

                errors, _skipped = check_es_undefined_class_ref(
                    [("scripts/4_World/x.c", source)],
                    [("config.cpp", config)],
                    [],
                    [],
                    UNDEFINED / "vanilla",
                )

                self.assertEqual([7], [e["line"] for e in errors])
                self.assertEqual(
                    set(),
                    declared_variables(
                        "auto q = new Param3" + gap + "<int, AuditTarget, int>(1, x, 2);"
                    ),
                )

    def test_a_declaration_among_template_arguments_begins_nothing_after_them(self):
        # `ref AuditEntry,` among template arguments
        # over lines starts no declaration, so the comma after the template
        # separates the arguments of the call, and AuditTarget is no variable.
        from detectors.es_undefined_class_ref import declared_variables

        source = (
            "class A\n{\n    void F()\n    {\n        Send(new Param2<\n"
            "            ref AuditEntry, ref AuditEntry>(a, b), AuditTarget);\n"
            "    }\n}\n"
        )

        self.assertEqual(set(), declared_variables(source))

    def test_a_declaration_ends_at_a_bracket_it_did_not_open(self):
        # Like the walks from each start that it
        # replaced, the pass ends a declaration at a bracket that closes
        # around it, even one this text never opened: `, C` is no declarator.
        from detectors.es_undefined_class_ref import declarator_commas

        self.assertEqual([5], declarator_commas("int a, B), C;", [5]))

    def test_each_declaration_is_read_once(self):
        # Each parameter on a line of its own
        # read on to the `)`, and each `1<` of a chain of shifts on to the `;`.
        # These 2 400 parameters took 9 s and these 8 000 shifts 4.7 s; each
        # takes 0.01 s.
        from detectors.es_undefined_class_ref import declared_variables

        sources = {
            "parameters": (
                "class A\n{\n    void F(\n"
                + ",\n".join("        int a%d" % i for i in range(2400))
                + ")\n    {\n    }\n}\n"
            ),
            "shifts": (
                "class A\n{\n    void F()\n    {\n        int x = 1"
                + "<<1" * 8000
                + ";\n    }\n}\n"
            ),
        }

        for label, source in sources.items():
            with self.subTest(label):
                start = time.perf_counter()
                names = declared_variables(source)

                self.assertLess(time.perf_counter() - start, 2)
                self.assertEqual(set(), names)


BRACKETS = FIXTURES / "unbalanced_brackets"
BRACKETS_RULE = "ES-UNBALANCED-BRACKETS"


def _bracket_errors(source):
    from detectors.es_unbalanced_brackets import check_es_unbalanced_brackets
    from stripper import strip_enforce_comments_and_strings

    stripped, _warnings = strip_enforce_comments_and_strings(source, "x.c")
    return check_es_unbalanced_brackets(stripped, "x.c")


class TestUnbalancedBrackets(unittest.TestCase):
    """ES-UNBALANCED-BRACKETS: a bracket never closed, or closed by another kind.

    `m_Objects.Clear(;` got PASS.
    """

    def test_ticket_repro_fails_on_the_open_parenthesis(self):
        exit_code, result = script_validator.run([str(BRACKETS / "bad")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, BRACKETS_RULE)
        self.assertEqual([9], [e["line"] for e in errors])
        self.assertIn(
            "'(' is never closed before the '}' on line 10", errors[0]["message"]
        )
        self.assertIn("fx_group_objects.c", errors[0]["file"])
        assert_standard_findings(self, result)

    def test_brackets_in_strings_comments_and_branches_pass(self):
        _code, result = script_validator.run([str(BRACKETS / "ok")])

        # Strings and comments are blanks; each branch of an #ifdef/#else that
        # writes the opening line twice is counted once; the #ifndef of a
        # macro the file defines and an #if 0 block never compile.
        self.assertEqual([], _errors_of(result, BRACKETS_RULE))

    def test_unclosed_at_end_and_stray_closer(self):
        unclosed = _bracket_errors("class C\n{\n    void F()\n    {\n    }\n")
        stray = _bracket_errors("class C\n{\n}\n}\n")

        self.assertEqual([2], [e["line"] for e in unclosed])
        self.assertIn("before the end of the file", unclosed[0]["message"])
        self.assertEqual([4], [e["line"] for e in stray])
        self.assertIn("'}' closes nothing", stray[0]["message"])

    def test_a_defect_after_a_duplicated_header_is_found(self):
        source = (
            "class C\n{\n#ifdef FX_A\n    void F(int a)\n    {\n#else\n"
            "    void F()\n    {\n#endif\n        Print(1;\n    }\n}\n"
        )

        self.assertEqual([10], [e["line"] for e in _bracket_errors(source)])

    def test_branches_that_end_differently_are_not_judged(self):
        # Which build the closing braces belong to is unknown, with or
        # without an #else.
        without_else = "class C\n{\n#ifdef FX_A\n    void F() {\n#endif\n}\n"
        with_else = (
            "class C\n{\n#ifdef FX_A\n#else\n    void F() {\n#endif\n    }\n}\n"
        )

        self.assertEqual([], _bracket_errors(without_else))
        self.assertEqual([], _bracket_errors(with_else))
        # An #ifdef never closed: ES-EMPTY-IFDEF warns about that one.
        self.assertEqual([], _bracket_errors("class C\n{\n#ifdef FX_A\n    void F()\n"))

    def test_unterminated_string_is_left_to_the_stripper(self):
        fixture = FIXTURES / "es" / "bad_unterminated_string.c"
        _code, result = script_validator.run([str(fixture)])

        self.assertEqual([], _errors_of(result, BRACKETS_RULE))


ENGINE = FIXTURES / "modded_engine_class"
ENGINE_RULE = "ES-MODDED-ENGINE-CLASS"


class TestModdedEngineClass(unittest.TestCase):
    """ES-MODDED-ENGINE-CLASS: `modded class` of a class the engine refuses.

    DayZDiag 1.29.163709: "Engine class
    'Transport' cannot be modded."
    """

    def test_modded_transport_fails(self):
        exit_code, result = script_validator.run([str(ENGINE / "bad")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, ENGINE_RULE)
        self.assertEqual([9], [e["line"] for e in errors])
        self.assertIn("'modded class Transport'", errors[0]["message"])
        self.assertEqual("FAIL", errors[0]["severity"])
        assert_standard_findings(self, result)

    def test_script_bases_subclasses_and_comments_pass(self):
        _code, result = script_validator.run([str(ENGINE / "ok")])

        # `modded class CarScript`, `class FX_MyTransport extends Transport`,
        # and `modded class Transport` in a comment, a string or #if 0.
        self.assertEqual([], _errors_of(result, ENGINE_RULE))

    def test_modded_inventory_and_magazine_fail_on_130(self):
        # DayZDiag 1.30.164200: "Engine class 'DayZPlayerInventory' cannot be
        # modded." and "Engine class 'Magazine' cannot be modded."
        exit_code, result = script_validator.run([str(ENGINE / "bad_130")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, ENGINE_RULE)
        self.assertEqual([7, 15], [e["line"] for e in errors])
        self.assertIn("'modded class DayZPlayerInventory'", errors[0]["message"])
        self.assertIn("'modded class Magazine'", errors[1]["message"])
        assert_standard_findings(self, result)

    def test_script_subclasses_of_magazine_pass(self):
        _code, result = script_validator.run([str(ENGINE / "ok_130")])

        # `modded class Ammunition_Base`, `modded class ItemBase`, a class
        # extending Magazine, and the names in a comment and a string.
        self.assertEqual([], _errors_of(result, ENGINE_RULE))

    def test_only_the_whole_class_name_counts(self):
        from detectors.es_modded_engine_class import check_es_modded_engine_class

        self.assertEqual(
            [], check_es_modded_engine_class("modded class TransportX\n{\n}\n", "x.c")
        )



NAMED = FIXTURES / "variable_named_as_type"
NAMED_RULE = "ES-VARIABLE-NAMED-AS-TYPE"


def _named_errors(source, rel_path="scripts/4_World/x.c", external=(),
                  vanilla=NAMED / "vanilla"):
    from detectors.es_variable_named_as_type import (
        check_es_variable_named_as_type,
    )
    from stripper import strip_enforce_comments_and_strings

    def strip(text):
        return strip_enforce_comments_and_strings(text, "x.c")[0]

    return check_es_variable_named_as_type(
        [(rel_path, strip(source))],
        [(path, strip(text)) for path, text in external],
        vanilla,
    )


def _named_skips(result):
    return [
        s for s in result["info"].get("skipped_checks", [])
        if s["rule_id"] == NAMED_RULE
    ]


class TestVariableNamedAsType(unittest.TestCase):
    """ES-VARIABLE-NAMED-AS-TYPE: a variable, member or parameter named as a type.

    DayZDiag 1.29:
    `bool Debug;` in a 4_World settings class, "Variable name 'Debug' already
    used as type name".
    """

    def test_ticket_member_fails_with_the_vanilla_tree(self):
        exit_code, result = script_validator.run(
            [str(NAMED / "bad"), "--vanilla-root", str(NAMED / "vanilla")]
        )

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, NAMED_RULE)
        self.assertEqual([9], [e["line"] for e in errors])
        self.assertIn("'Debug'", errors[0]["message"])
        self.assertIn("vanilla scripts tree", errors[0]["message"])
        self.assertIn("fx_settings.c", errors[0]["file"])
        self.assertEqual([], _named_skips(result))
        assert_standard_findings(self, result)

    def test_without_the_vanilla_tree_the_vanilla_part_is_skipped(self):
        _code, result = script_validator.run([str(NAMED / "bad")])

        self.assertEqual([], _errors_of(result, NAMED_RULE))
        skips = _named_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("vanilla type", skips[0]["reason"])
        terse = script_validator.format_terse(result)
        self.assertIn("SKIP %s" % NAMED_RULE, terse)

    def test_usage_lower_case_comments_strings_and_dead_code_pass(self):
        _code, result = script_validator.run(
            [str(NAMED / "ok"), "--vanilla-root", str(NAMED / "vanilla")]
        )

        # `Debug.Log(...)`, `Insert(new Debug)`, a member `debug`,
        # `Debug m_Logger`, `bool Debug;`
        # in a comment, a string and #if 0, a 4_World local named like a
        # 5_Mission type, and a name only a vanilla comment declares.
        self.assertEqual([], _errors_of(result, NAMED_RULE))

    def test_local_parameter_later_declarator_and_foreach(self):
        source = (
            "class C\n{\n"
            "    void F(int FX_VanillaEnum)\n    {\n"
            "        Widget map = null;\n"
            "        int a = 1, FX_VanillaTypedef;\n"
            "        foreach (int Debug : m_List)\n        {\n        }\n"
            "    }\n}\n"
        )
        errors, skipped = _named_errors(source)

        self.assertEqual(
            [(3, "FX_VanillaEnum"), (5, "map"), (6, "FX_VanillaTypedef"),
             (7, "Debug")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )
        self.assertEqual([], skipped)

    def test_a_type_is_seen_from_its_module_and_above(self):
        source = "class C\n{\n    int FX_MissionOnly;\n}\n"

        self.assertEqual([], _named_errors(source)[0])
        self.assertEqual(
            [3],
            [e["line"] for e in _named_errors(
                source, rel_path="scripts/5_Mission/x.c")[0]],
        )

    def test_addon_and_external_types_are_judged_without_vanilla(self):
        source = (
            "class FX_Own\n{\n}\n"
            "class C\n{\n    int FX_Own;\n    int FX_Dep;\n    bool Debug;\n}\n"
        )
        external = [("scripts/3_Game/dep.c", "class FX_Dep\n{\n}\n")]
        errors, skipped = _named_errors(source, external=external, vanilla=None)

        self.assertEqual([6, 7], [e["line"] for e in errors])
        self.assertIn("declared in the addon", errors[0]["message"])
        self.assertIn("--external-scripts", errors[1]["message"])
        self.assertEqual([NAMED_RULE], [s["rule_id"] for s in skipped])

    def test_a_type_outside_any_module_counts_only_in_its_own_file(self):
        source = "class C\n{\n    int FX_Loose;\n}\n"
        external = [("dep.c", "class FX_Loose\n{\n}\n")]

        self.assertEqual([], _named_errors(source, external=external)[0])
        # Two files outside any module may compile in different modules.
        self.assertEqual(
            [], _named_errors(source, rel_path="x.c", external=external)[0]
        )
        own = "class FX_Loose\n{\n}\n" + source
        self.assertEqual(
            [6], [e["line"] for e in _named_errors(own, rel_path="x.c")[0]]
        )

    def test_a_file_outside_any_module_is_judged_against_1_core_only(self):
        # Measured on 2026-10-17: a member `Attachments` in a mod
        # laid out without its module folders was reported against the
        # 5_Mission class Attachments; the classes that use it are 4_World.
        source = (
            "class C\n{\n    int FX_MissionOnly;\n    int Debug;\n"
            "    int Managed;\n}\n"
        )
        errors, _skipped = _named_errors(
            source, rel_path="Scripts/HM_Virtual_Garage/x.c"
        )

        self.assertEqual(
            [(5, "Managed")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )

    def test_template_arguments_and_typedef_names_are_not_declarators(self):
        # Vanilla control 2026-10-13: commas between template arguments and a
        # typedef's own name were read as declarators (104 findings on 1.29,
        # 109 on 1.30), e.g. `Param3<bool, vector, int> x` and
        # `typedef map<string,ref array<string>> DamageZoneMap;`. Again with a
        # space or a tab before the `<`.
        # A nested template is stepped over whole, so the arguments after it
        # are still inside the outer one.
        source = (
            "typedef map<string, ref array<Debug>> FX_OwnMap;\n"
            "class C\n{\n"
            "    ref Param3<int, Debug, Debug> m_Pair;\n"
            "    void F(Param2<int, Debug> p, int Debug)\n    {\n"
            "        float r = Param2<float, Debug>.Cast(p).param1;\n"
            "        auto q = new Param3<int, Debug, int>(0, null, 0);\n"
            "        auto s = new Param3 <int, Debug, int>(0, null, 0);\n"
            "        auto t = new Param3\t<int, Debug, int>(0, null, 0);\n"
            "        auto u = new Param3<array<int>, Debug, int>(null, null, 0);\n"
            "        ref map<int, Debug> m, map;\n"
            "    }\n}\n"
        )
        errors, _skipped = _named_errors(source)

        # Still reported: the parameter after a template-typed one, and the
        # later declarator after a template-typed local.
        self.assertEqual(
            [(5, "Debug"), (12, "map")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )

    def test_a_type_that_never_compiles_with_the_name_is_no_type(self):
        # A type declared where it never compiles,
        # or only in the other branch of the name's block, failed valid code.
        cases = [
            "#if 0\nclass FX_Gone\n{\n}\n#endif\n"
            "class C\n{\n    int FX_Gone;\n}\n",
            "#define FX_ON\n#ifndef FX_ON\nclass FX_Gone\n{\n}\n#endif\n"
            "class C\n{\n    int FX_Gone;\n}\n",
            "#ifdef FX_X\nclass FX_Gone\n{\n}\n#else\n"
            "class C\n{\n    int FX_Gone;\n}\n#endif\n",
        ]
        for source in cases:
            self.assertEqual([], _named_errors(source, vanilla=None)[0], source)

        # Under another mod's #ifdef the type compiles: with the name outside
        # the block, in the same branch, or in a branch of another file's block.
        outside = (
            "#ifdef FX_X\nclass FX_Opt\n{\n}\n#endif\n"
            "class C\n{\n    int FX_Opt;\n}\n"
        )
        same_branch = (
            "#ifdef FX_X\nclass FX_Opt\n{\n}\n"
            "class C\n{\n    int FX_Opt;\n}\n#endif\n"
        )
        other_file = "#ifdef FX_X\n#else\nclass C\n{\n    int FX_Opt;\n}\n#endif\n"
        external = [("scripts/3_Game/dep.c", "#ifdef FX_X\nclass FX_Opt\n{\n}\n#endif\n")]
        self.assertEqual(
            [8], [e["line"] for e in _named_errors(outside, vanilla=None)[0]]
        )
        self.assertEqual(
            [7], [e["line"] for e in _named_errors(same_branch, vanilla=None)[0]]
        )
        self.assertEqual(
            [5],
            [e["line"] for e in _named_errors(
                other_file, external=external, vanilla=None)[0]],
        )

    def test_opposite_tests_of_one_macro_never_compile_together(self):
        # The type under
        # `#ifdef FX_ON` and the name under a later `#ifndef FX_ON`, or under
        # an `#ifndef FX_ON` inside the type's block, failed valid code. An
        # `#if 0` block inside the type's block does not end it.
        cases = [
            "#ifdef FX_ON\nclass FX_Gone\n{\n}\n#endif\n"
            "#ifndef FX_ON\nclass C\n{\n    int FX_Gone;\n}\n#endif\n",
            "#ifdef FX_ON\n#if 0\n#endif\nclass FX_Gone\n{\n}\n#endif\n"
            "#ifndef FX_ON\nclass C\n{\n    int FX_Gone;\n}\n#endif\n",
            "#ifdef FX_ON\n#else\nclass FX_Gone\n{\n}\n#endif\n"
            "#ifdef FX_ON\nclass C\n{\n    int FX_Gone;\n}\n#endif\n",
            "#ifdef FX_ON\nclass FX_Gone\n{\n}\n"
            "class C\n{\n#ifndef FX_ON\n    int FX_Gone;\n#endif\n}\n#endif\n",
            "#ifdef FX_ON\n#ifndef FX_ON\nclass FX_Gone\n{\n}\n#endif\n#endif\n"
            "class C\n{\n    int FX_Gone;\n}\n",
        ]
        for source in cases:
            self.assertEqual([], _named_errors(source, vanilla=None)[0], source)
        nested = "class C\n{\n#ifdef FX_ON\n#ifndef FX_ON\n    bool Debug;\n#endif\n#endif\n}\n"
        self.assertEqual([], _named_errors(nested)[0])

        # Still reported: the same test twice, tests of two macros, and a
        # macro the file #defines or #undefs between the two blocks.
        reported = [
            ("#ifdef FX_ON\nclass FX_Opt\n{\n}\n#endif\n"
             "#ifdef FX_ON\nclass C\n{\n    int FX_Opt;\n}\n#endif\n", [9]),
            ("#ifdef FX_ON\nclass FX_Opt\n{\n}\n#endif\n"
             "#ifndef FX_OFF\nclass C\n{\n    int FX_Opt;\n}\n#endif\n", [9]),
            ("#ifndef FX_ON\nclass FX_Opt\n{\n}\n#endif\n#define FX_ON\n"
             "#ifdef FX_ON\nclass C\n{\n    int FX_Opt;\n}\n#endif\n", [10]),
            ("#ifdef FX_ON\nclass FX_Opt\n{\n}\n#endif\n#undef FX_ON\n"
             "#ifndef FX_ON\nclass C\n{\n    int FX_Opt;\n}\n#endif\n", [10]),
        ]
        for source, lines in reported:
            self.assertEqual(
                lines,
                [e["line"] for e in _named_errors(source, vanilla=None)[0]],
                source,
            )

    def test_a_comparison_hides_no_later_declarator(self):
        # The `<` of a comparison was read as
        # opening template arguments, so the later declarator went unseen.
        source = (
            "class C\n{\n    void F(int a, int b)\n    {\n"
            "        bool first = a < b, Debug = false;\n"
            "        bool second = a<b, map;\n"
            "    }\n}\n"
        )
        errors, _skipped = _named_errors(source)

        self.assertEqual(
            [(5, "Debug"), (6, "map")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )

    def test_line_tests_cost_grows_with_the_lines(self):
        # line_tests ran its #define/#undef
        # pattern over the whole text, and its \s* ran on across blank lines.
        # On two machines these 64 000 lines took 30 s and 31 s, and take 0.1 s.
        # Wall time: on one of them process_time() reads a fraction of the
        # time the CPU spends.
        from shared.dead_branches import line_tests

        start = time.perf_counter()
        line_tests("    \n" * 64000)

        self.assertLess(time.perf_counter() - start, 2)

    def test_lines_are_counted_once_per_file(self):
        # The rule counted lines from the
        # start of the file for each name that is a type. On two machines
        # these 64 000 members took 42 s and 62 s, and take 1.5 s.
        source = (
            "#ifdef X\nclass Debug\n{\n}\n#else\nclass A\n{\n"
            + "    int Debug; // the member is named like the type\n" * 64000
            + "}\n#endif\n"
        )

        start = time.perf_counter()
        errors, _skipped = _named_errors(source, vanilla=None)

        self.assertLess(time.perf_counter() - start, 10)
        self.assertEqual([], errors)

    def test_template_arguments_are_read_once_per_file(self):
        # At each comma of a declaration the rule
        # read the statement again from its start, looking for template
        # arguments. These 16 000 names in 117 KB took 46 s and 48 s on two
        # machines, and take 0.05 s.
        source = (
            "class A\n{\n    int "
            + ", ".join(f"m{i}" for i in range(16000))
            + ";\n}\n"
        )

        start = time.perf_counter()
        errors, _skipped = _named_errors(source, vanilla=None)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual([], errors)

    def test_shift_chains_are_read_once_per_file(self):
        # A `<` that opened no template was read up
        # to the end of its statement, so a chain of shifts with no comma grew
        # with the square of its length. These 16 000 shifts in 80 KB took 37 s.
        source = (
            "class A\n{\n    void F()\n    {\n        int value = 1"
            + " << 0" * 16000
            + ";\n    }\n}\n"
        )

        start = time.perf_counter()
        errors, _skipped = _named_errors(source, vanilla=None)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual([], errors)

    def test_template_arguments_end_at_their_own_bracket(self):
        # The same statement as in
        # TestReservedWordIdentifier took 9 s, and takes 0.04 s.
        source = (
            "class A\n{\n    void F()\n    {\n        auto x = new Param<"
            + "array<int>, " * 7999
            + "array<int>>(1);\n    }\n}\n"
        )

        start = time.perf_counter()
        errors, _skipped = _named_errors(source, vanilla=None)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual([], errors)

    def test_a_type_with_templates_five_deep_is_read(self):
        # With a later declarator after two
        # comparisons: the walk reads the source, not the blanked text.
        source = (
            "class C\n{\n"
            "    map<string, ref map<string, ref map<string, ref map<string,"
            " ref array<int>>>>> Debug;\n"
            "    void F()\n    {\n"
            "        bool first = a < b, Debug = c > d;\n"
            "    }\n}\n"
        )
        errors, skipped = _named_errors(source)

        self.assertEqual(
            [(3, "Debug"), (6, "Debug")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )
        self.assertEqual([], skipped)

    def test_vanilla_closers_and_one_line_ifs_hide_no_name(self):
        # Vanilla closes a template with one `>` too
        # many (`map<string, int>> name;`, 3_game/global/ammotypes.c:80 on
        # 1.30); and in `if (a < b) ... if (c > d)` no template runs from the
        # `<` to the `>`.
        source = (
            "class C\n{\n"
            "    static ref map<string, int>> Debug;\n"
            "    void F(array<int> values, int a, int b, int c, int d)\n    {\n"
            "        if (a < b) foreach (int Debug : values) if (c > d) Print(Debug);\n"
            "    }\n}\n"
        )
        errors, skipped = _named_errors(source)

        self.assertEqual(
            [(3, "Debug"), (6, "Debug")],
            [(e["line"], e["message"].split("'")[1]) for e in errors],
        )
        self.assertEqual([], skipped)

    def test_each_declaration_is_read_once(self):
        # Each parameter on a line of its own read on
        # to the `)`. These 2 400 took 7.6 s, and take 0.02 s.
        source = (
            "class A\n{\n    void F(\n"
            + ",\n".join("        int a%d" % i for i in range(2400))
            + ")\n    {\n    }\n}\n"
        )

        start = time.perf_counter()
        errors, _skipped = _named_errors(source, vanilla=None)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual([], errors)

    def test_a_folder_without_class_managed_is_no_vanilla_tree(self):
        errors, skipped = _named_errors(
            "class C\n{\n    bool Debug;\n}\n", vanilla=NAMED / "bad"
        )

        self.assertEqual([], errors)
        self.assertIn("declares no class Managed", skipped[0]["reason"])



CAST = FIXTURES / "cast_unrelated_types"
CAST_RULE = "ES-CAST-UNRELATED-TYPES"


def _cast_errors(source, external=(), vanilla=CAST / "vanilla"):
    from detectors.es_cast_unrelated_types import check_es_cast_unrelated_types
    from stripper import strip_enforce_comments_and_strings

    def strip(text):
        return strip_enforce_comments_and_strings(text, "x.c")[0]

    return check_es_cast_unrelated_types(
        [("scripts/5_Mission/x.c", strip(source))],
        [(path, strip(text)) for path, text in external],
        vanilla,
    )


class TestCastUnrelatedTypes(unittest.TestCase):
    """ES-CAST-UNRELATED-TYPES: `X.Cast(y)` between classes on separate branches.

    DayZDiag 1.29: `IngameHud.Cast(mission)`
    with `Mission mission`, "Types 'IngameHud' and 'Mission' are not related".
    """

    def test_ticket_repro_fails(self):
        exit_code, result = script_validator.run(
            [str(CAST / "bad"), "--vanilla-root", str(CAST / "vanilla")]
        )

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, CAST_RULE)
        self.assertEqual([12], [e["line"] for e in errors])
        self.assertIn("'IngameHud.Cast(mission)'", errors[0]["message"])
        self.assertIn("IngameHud > Hud > Managed", errors[0]["message"])
        self.assertIn("fx_hudhook.c", errors[0]["file"])
        assert_standard_findings(self, result)

    def test_without_the_vanilla_tree_nothing_is_judged(self):
        _code, result = script_validator.run([str(CAST / "bad")])

        self.assertEqual([], _errors_of(result, CAST_RULE))

    def test_related_and_unknown_casts_pass(self):
        _code, result = script_validator.run(
            [str(CAST / "ok"), "--vanilla-root", str(CAST / "vanilla")]
        )

        # Down- and up-casts, the HUD from GetHud(), a call's result, an
        # undeclared name, a typedef, Class, a parameter of a related type,
        # and the failing cast in a comment, a string and #if 0.
        self.assertEqual([], _errors_of(result, CAST_RULE))

    def test_a_parameter_and_a_member_are_resolved(self):
        source = (
            "class C\n{\n    Mission m_Mission;\n\n"
            "    void F(Mission param, int n)\n    {\n"
            "        IngameHud.Cast(param);\n"
            "        IngameHud.Cast(m_Mission);\n"
            "    }\n}\n"
        )

        self.assertEqual([7, 8], [e["line"] for e in _cast_errors(source)])

    def test_a_local_of_a_closed_block_is_out_of_scope(self):
        source = (
            "class C\n{\n    Hud m_X;\n\n    void F()\n    {\n"
            "        if (m_X)\n        {\n            Mission m_X = null;\n"
            "        }\n        IngameHud.Cast(m_X);\n"
            "        Mission m_Y = null;\n        IngameHud.Cast(m_Y);\n"
            "    }\n}\n"
        )

        self.assertEqual([13], [e["line"] for e in _cast_errors(source)])

    def test_a_local_after_a_case_label_is_resolved(self):
        # On the line of its label the local was
        # passed over for the member of that name.
        source = (
            "class C\n{\n    Hud m_X;\n\n    void F(int n)\n    {\n"
            "        switch (n)\n        {\n"
            "            case 0: Mission m_X = null;\n"
            "                IngameHud.Cast(m_X);\n                break;\n"
            "        }\n    }\n}\n"
        )

        self.assertEqual([10], [e["line"] for e in _cast_errors(source)])

    def test_unresolvable_chains_and_declarations_are_skipped(self):
        cases = {
            # a parent nobody declares
            "class FX_A : FX_Nowhere\n{\n}\n"
            "void F(Mission m)\n{\n    FX_A.Cast(m);\n}\n",
            # two parents for one class
            "class FX_B : Hud\n{\n}\n"
            "#ifdef FX_OTHER\nclass FX_B : IngameHud\n{\n}\n#endif\n"
            "void F(Mission m)\n{\n    FX_B.Cast(m);\n}\n",
            # only a modded declaration
            "modded class FX_Unseen\n{\n}\n"
            "void F(Mission m)\n{\n    FX_Unseen.Cast(m);\n}\n",
            # a template class, a template-typed and an array variable
            "class FX_T<Class T>\n{\n}\n"
            "void F(array<Mission> a, Mission b[2])\n{\n"
            "    FX_T.Cast(a);\n    IngameHud.Cast(a);\n    IngameHud.Cast(b);\n}\n",
            # a later declarator makes the name unknown, even with a member
            "class C\n{\n    Mission m;\n    void F()\n    {\n"
            "        Hud a, m;\n        IngameHud.Cast(m);\n    }\n}\n",
            # a template class as the target
            "class FX_T<Class T>\n{\n}\n"
            "void F(Mission m)\n{\n    FX_T.Cast(m);\n}\n",
            # a name that is a template parameter somewhere
            "class FX_Box<Class FX_Item>\n{\n}\nclass FX_Item\n{\n}\n"
            "void F(Mission m)\n{\n    FX_Item.Cast(m);\n}\n",
            # a class that is also a typedef, and a primitive declared as a class
            "class FX_Dual\n{\n}\ntypedef Hud FX_Dual;\nclass int\n{\n}\n"
            "void F(Mission m, int i)\n{\n    FX_Dual.Cast(m);\n"
            "    IngameHud.Cast(i);\n}\n",
            # Class, the implicit root of every class
            "void F(Mission m)\n{\n    Class.Cast(m);\n}\n",
            # a parent cycle
            "class FX_C1 : FX_C2\n{\n}\nclass FX_C2 : FX_C1\n{\n}\n"
            "void F(Mission m)\n{\n    FX_C1.Cast(m);\n}\n",
            # a parent behind a directive in the header, after `:` and after `extends`
            "class FX_D\n#ifdef FX_X\n    : Mission\n#endif\n{\n}\n"
            "void F(FX_D d)\n{\n    Mission.Cast(d);\n}\n",
            "class FX_E extends\n#ifdef FX_X\n    Mission\n#else\n    Hud\n"
            "#endif\n{\n}\nvoid F(FX_E e)\n{\n    Mission.Cast(e);\n}\n",
            # the cast under #if 0
            "void F(Mission m)\n{\n#if 0\n    IngameHud.Cast(m);\n#endif\n}\n",
            # two types in two branches, for a local and for a member
            "void F()\n{\n#ifdef FX_A\n    Mission x;\n#else\n"
            "    MissionGameplay x;\n#endif\n    IngameHud.Cast(x);\n}\n",
            "class C\n{\n#ifdef FX_A\n    Mission m_X;\n#else\n"
            "    MissionGameplay m_X;\n#endif\n"
            "    void F()\n    {\n        IngameHud.Cast(m_X);\n    }\n}\n",
            # a parameter of another method is no member
            "class C\n{\n    void G(Mission m_P)\n    {\n    }\n"
            "    void F()\n    {\n        IngameHud.Cast(m_P);\n    }\n}\n",
            # a local of another method is no member
            "class C\n{\n    void G()\n    {\n        Mission m_Z;\n    }\n"
            "    void F()\n    {\n        IngameHud.Cast(m_Z);\n    }\n}\n",
            # a local under #if 0 does not hide the member
            "class C\n{\n    Hud m_Q;\n    void F()\n    {\n#if 0\n"
            "        Mission m_Q;\n#endif\n        IngameHud.Cast(m_Q);\n    }\n}\n",
            # this, and an enum
            "enum FX_E\n{\n    A\n}\n"
            "void F(FX_E e)\n{\n    IngameHud.Cast(this);\n    IngameHud.Cast(e);\n}\n",
        }
        for source in cases:
            self.assertEqual([], _cast_errors(source), source)

    def test_modded_class_keeps_the_hierarchy_and_addon_classes_resolve(self):
        source = (
            "modded class Mission\n{\n}\n"
            "class FX_Own\n{\n}\n"
            "void F(Mission m, FX_Own o)\n{\n"
            "    MissionGameplay.Cast(m);\n    IngameHud.Cast(o);\n}\n"
        )

        self.assertEqual([10], [e["line"] for e in _cast_errors(source)])
        modded_with_parent = (
            "modded class IngameHud\n{\n}\n"
            "void F(Mission m)\n{\n    IngameHud.Cast(m);\n}\n"
        )
        self.assertEqual(
            [6], [e["line"] for e in _cast_errors(modded_with_parent)]
        )
        forward = (
            "class IngameHud;\n"
            "void F(Mission m)\n{\n    IngameHud.Cast(m);\n}\n"
        )
        self.assertEqual([4], [e["line"] for e in _cast_errors(forward)])
        returned = (
            "Mission F(Mission m)\n{\n    if (!m)\n        return m;\n"
            "    return IngameHud.Cast(m);\n}\n"
        )
        self.assertEqual([5], [e["line"] for e in _cast_errors(returned)])
        # Without the vanilla tree IngameHud's chain does not resolve.
        self.assertEqual([], _cast_errors(source, vanilla=None))
        # Classes the addon and an external root declare whole still do.
        own = "class FX_P\n{\n}\nvoid F(FX_P p)\n{\n    FX_Q.Cast(p);\n}\n"
        external = [("scripts/3_Game/q.c", "class FX_Q\n{\n}\n")]
        self.assertEqual(
            [6], [e["line"] for e in _cast_errors(own, external, vanilla=None)]
        )


class TestFileScopes(unittest.TestCase):
    """The lookups of ES-CAST-UNRELATED-TYPES and ES-PROTECTED-METHOD-CROSS-CLASS.

    Measured on 2026-10-17: counting lines from the start of the file
    and scanning every method and class body at each call kept the protected
    method rule running for more than 20 minutes on a 10 MB file. FileScopes
    reads them once; it must give what the scans gave.
    """

    SOURCE = (
        "class FX_A\n{\n    FX_A m_X;\n    void F()\n    {\n        m_X.G();\n"
        "    }\n"
        # A class header inside a body: its braces nest in FX_A's.
        "class FX_In\n{\n    void H()\n    {\n    }\n}\n"
        "    void G()\n    {\n        m_X.G();\n    }\n}\n"
        "void Loose()\n{\n}\n"
        "class FX_B\n{\n    Managed m_X;\n    void K()\n    {\n        m_X.G();\n"
        "    }\n}\n"
    )

    def _scopes(self):
        from detectors.es_cast_unrelated_types import FileScopes
        from stripper import strip_enforce_comments_and_strings

        stripped = strip_enforce_comments_and_strings(self.SOURCE, "x.c")[0]
        return stripped, FileScopes(stripped)

    def test_lookups_give_what_the_scans_gave(self):
        from detectors.es_cast_unrelated_types import _class_regions
        from shared.method_recognition import find_method_for_line, find_method_regions

        stripped, scopes = self._scopes()
        methods = find_method_regions(stripped)
        regions = _class_regions(stripped)

        self.assertEqual(3, len(regions))
        for line in range(stripped.count("\n") + 3):
            self.assertEqual(find_method_for_line(methods, line), scopes.method(line))
        for at in range(len(stripped) + 1):
            self.assertEqual(stripped.count("\n", 0, at) + 1, scopes.line(at))
            around = [r for r in regions if r[0] < at < r[1]]
            self.assertEqual(max(around) if around else None, scopes.class_body(at))

    def test_a_member_is_read_in_its_own_class_body(self):
        from detectors.es_cast_unrelated_types import _argument_type

        stripped, scopes = self._scopes()
        calls = [i for i in range(len(stripped)) if stripped.startswith("m_X.G(", i)]

        # F and G of FX_A (G after the nested body), then K of FX_B.
        self.assertEqual(
            ["FX_A", "FX_A", "Managed"],
            [_argument_type(stripped, scopes, "m_X", at) for at in calls],
        )


class TestMethodSignatureCollection(unittest.TestCase):
    """find_method_regions, which FileScopes and nine other rules read.

    Measured on 2026-10-17: it collected a signature at every
    line, and from a "(" that never closes each one ran to the end of the
    file, rebuilding the string at every line. Two files
    of up to 20 MB of binary data still passed 20 minutes, and method headers
    split by #ifdef branches took 21 s for 135 KB.
    Only a line that can start a signature is read now, and each is read up
    to what METHOD_SIGNATURE_RE needs, from tables built once per file.
    """

    SPLIT = (
        "class C\n{\n#ifdef X\n    void F(int a,\n#else\n    void F(int a, int b,\n"
        "#endif\n        int c)\n    {\n    }\n}\n"
    )

    def test_only_a_line_that_can_start_a_signature_is_read(self):
        from shared import method_recognition

        source = "\n".join(
            [
                "x = Foo(a,",  # "=" before the "("
                "Print(a,",  # one word before it
                "\ufffd(",  # binary data read with errors="replace"
                "void F(int a,",
                "    int b)",
                "{",
                "}",
            ]
        )
        read = []
        collect = method_recognition._Signatures.collect

        def counted(signatures, start):
            read.append(start)
            return collect(signatures, start)

        with mock.patch.object(method_recognition._Signatures, "collect", counted):
            methods = method_recognition.find_method_regions(source)

        self.assertEqual([3], read)
        self.assertEqual(
            [("F", "int a, int b", 6)],
            [(m["name"], m["params"], m["brace_line"]) for m in methods],
        )

    def test_the_reader_gives_what_collect_method_signature_gives(self):
        from shared import method_recognition as recognition

        sources = (
            self.SPLIT,
            "void T((int a)\n{\n}\n",  # the "{" after ")" is on the next line
            "void K(int a\n{\n}\n",  # no ")" at all
            "void Q(int a,\n\n int b)\n\n{\n}\n",
            "void F(int a) { }\n",
        )
        groups = ("indent", "return_type", "name", "params", "brace")
        for source in sources:
            lines = source.split("\n")
            signatures = recognition._Signatures(lines)
            for start, line in enumerate(lines):
                if not recognition.may_start_method_signature(line):
                    continue
                with self.subTest(source=source, start=start):
                    full, end = recognition.collect_method_signature(lines, start)
                    read, read_end = signatures.collect(start)
                    self.assertEqual(end, read_end)
                    whole = recognition.METHOD_SIGNATURE_RE.match(full)
                    cut = recognition.METHOD_SIGNATURE_RE.match(read)
                    self.assertEqual(
                        whole and [whole.group(g) for g in groups],
                        cut and [cut.group(g) for g in groups],
                    )

    def test_a_header_that_never_closes_is_not_read_to_the_end(self):
        from shared import method_recognition

        lines = (self.SPLIT * 200).split("\n")
        signature, end = method_recognition._Signatures(lines).collect(3)

        self.assertEqual(len(lines) - 1, end)
        self.assertEqual(
            "    void F(int a, #else void F(int a, int b, #endif int c) {", signature
        )


STATIC_MEMBER = FIXTURES / "undeclared_static_member"
STATIC_MEMBER_RULE = "ES-UNDECLARED-STATIC-MEMBER"


def _static_member_errors(sources, external=(), vanilla=None):
    from detectors.es_undeclared_static_member import (
        check_es_undeclared_static_member,
    )
    from stripper import strip_enforce_comments_and_strings

    def strip(text):
        return strip_enforce_comments_and_strings(text, "x.c")[0]

    if isinstance(sources, str):
        sources = [("scripts/4_World/x.c", sources)]
    return check_es_undeclared_static_member(
        [(path, strip(text)) for path, text in sources],
        [(path, strip(text)) for path, text in external],
        vanilla,
    )


class TestUndeclaredStaticMember(unittest.TestCase):
    """ES-UNDECLARED-STATIC-MEMBER: `Class.Member` the addon's class lacks.

    ANIM_SWAP_ENABLED deleted from FX_Constants while seven call sites still read it; DayZ refused
    the World module on the first boot.
    """

    def test_ticket_repro_fails(self):
        exit_code, result = script_validator.run([str(STATIC_MEMBER / "bad")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, STATIC_MEMBER_RULE)
        self.assertEqual([9, 11], [e["line"] for e in errors])
        self.assertIn("'FX_Constants.ANIM_SWAP_ENABLED'", errors[0]["message"])
        self.assertIn("'FX_Constants.Reload('", errors[1]["message"])
        self.assertIn("fx_ride.c", errors[0]["file"])
        assert_standard_findings(self, result)

    def test_declared_inherited_and_foreign_members_pass(self):
        _code, result = script_validator.run([str(STATIC_MEMBER / "ok")])

        # A const and a method of an addon ancestor, a const under #ifdef, a
        # member of a modded declaration in another module, Cast, a class
        # whose parent is not the addon's, and the bad reference in a
        # comment, a string and #if 0.
        self.assertEqual([], _errors_of(result, STATIC_MEMBER_RULE))

    def test_every_addon_declaration_and_ancestor_counts(self):
        sources = [
            ("scripts/3_Game/a.c",
             "class FX_Base\n{\n    static int A;\n}\n"
             "class FX_K : FX_Base\n{\n    static int B;\n}\n"),
            ("scripts/4_World/b.c",
             "modded class FX_K\n{\n    static int C()\n    {\n"
             "        return D;\n    }\n}\n"
             "void F()\n{\n    int x = FX_K.A + FX_K.B + FX_K.C();\n"
             "    x = FX_K.D;\n    x = FX_K.E;\n}\n"),
        ]

        # D is only read inside a method body, so it is no declaration.
        self.assertEqual(
            [11, 12], [e["line"] for e in _static_member_errors(sources)]
        )

    def test_template_arguments_after_a_space_declare_no_variable(self):
        # With a space or a tab before the `<`,
        # `ref AuditEntry,` among template arguments over lines declared
        # AuditEntry, so a member its class lacks went unreported.
        for gap in (" ", "\t"):
            with self.subTest(gap=repr(gap)):
                source = (
                    "class AuditEntry\n{\n    static int AUDIT_FOUND;\n}\n"
                    "class FX_A\n{\n    void F()\n    {\n"
                    "        auto p = new map" + gap + "<\n"
                    "            ref AuditEntry, bool>();\n"
                    "        int x = AuditEntry.AUDIT_MISSING;\n"
                    "    }\n}\n"
                )

                self.assertEqual(
                    [11], [e["line"] for e in _static_member_errors(source)]
                )

    def test_classes_not_wholly_the_addons_are_skipped(self):
        cases = {
            # a parent nobody declares, or one outside the addon
            "class FX_A : FX_Nowhere\n{\n}\nvoid F()\n{\n    FX_A.X;\n}\n",
            # only a modded declaration
            "modded class FX_M\n{\n}\nvoid F()\n{\n    FX_M.X;\n}\n",
            # two parents for one class
            "class FX_P1\n{\n}\nclass FX_P2\n{\n}\n"
            "class FX_B : FX_P1\n{\n}\n#ifdef FX_O\nclass FX_B : FX_P2\n{\n}\n"
            "#endif\nvoid F()\n{\n    FX_B.X;\n}\n",
            # a template class
            "class FX_T<Class T>\n{\n}\nvoid F()\n{\n    FX_T.X;\n}\n",
            # an enum, and a class that is also a typedef
            "enum FX_E\n{\n    A\n}\nclass FX_D\n{\n}\ntypedef FX_E FX_D;\n"
            "void F()\n{\n    FX_E.X;\n    FX_D.X;\n}\n",
            # a parent cycle
            "class FX_C1 : FX_C2\n{\n}\nclass FX_C2 : FX_C1\n{\n}\n"
            "void F()\n{\n    FX_C1.X;\n}\n",
            # a header whose body cannot be read
            "class FX_H\n{\n    static int A;\n}\nmodded class FX_H extends\n"
            "void F()\n{\n    FX_H.X;\n}\n",
            # a class-like name that is also a variable
            "class FX_V\n{\n}\nclass G\n{\n    FX_V FX_V;\n}\n"
            "void F()\n{\n    FX_V.X;\n}\n",
            # a method every class inherits from Class
            "class FX_R\n{\n}\nvoid F(Class c)\n{\n"
            "    FX_R.Cast(c);\n    FX_R r;\n    FX_R.CastTo(r, c);\n"
            "    typename t = FX_R.StaticType();\n"
            "    t = FX_R.StaticGetType();\n}\n",
            # the reference under #if 0, and after another dot
            "class FX_Z\n{\n}\nvoid F()\n{\n#if 0\n    FX_Z.X;\n#endif\n"
            "    g.FX_Z.X;\n}\n",
            # a forward declaration only
            "class FX_F;\nvoid F()\n{\n    FX_F.X;\n}\n",
        }
        for source in cases:
            self.assertEqual([], _static_member_errors(source), source)

    def test_the_methods_of_class_are_the_ten_of_enscript_c(self):
        # 1_core/proto/enscript.c:10-114, the same in 1.29 and 1.30.
        for member in (
            "IsInherited", "ClassName", "GetDebugName", "Type", "StaticType",
            "StaticGetType", "ToString", "Cast", "CastTo", "SafeCastType",
        ):
            source = "class FX_R\n{\n}\nvoid F()\n{\n    FX_R.%s();\n}\n" % member
            self.assertEqual([], _static_member_errors(source), member)
        # On the list from memory before; Class does not declare it.
        source = "class FX_R\n{\n}\nvoid F()\n{\n    FX_R.IsInstanceOf();\n}\n"
        self.assertEqual([6], [e["line"] for e in _static_member_errors(source)])

    def test_a_declaration_outside_the_addon_skips_the_class(self):
        source = "class FX_X\n{\n}\nvoid F()\n{\n    FX_X.Y;\n}\n"

        self.assertEqual([6], [e["line"] for e in _static_member_errors(source)])
        for external in ("modded class FX_X\n{\n}\n", "class FX_X\n{\n}\n"):
            self.assertEqual(
                [],
                _static_member_errors(source, [("scripts/4_World/e.c", external)]),
                external,
            )
        # The vanilla tree: Mission is declared there, and Class's own
        # methods come from its `class Class`.
        own_mission = (
            "class Mission\n{\n}\nvoid F()\n{\n    Mission.Y;\n}\n"
        )
        self.assertEqual([6], [e["line"] for e in _static_member_errors(own_mission)])
        self.assertEqual(
            [], _static_member_errors(own_mission, vanilla=CAST / "vanilla")
        )


PROTECTED_METHOD = FIXTURES / "protected_method_cross_class"
PROTECTED_METHOD_RULE = "ES-PROTECTED-METHOD-CROSS-CLASS"


def _protected_method_warnings(sources, external=()):
    from detectors.es_protected_method_cross_class import (
        check_es_protected_method_cross_class,
    )
    from stripper import strip_enforce_comments_and_strings

    def strip(text):
        return strip_enforce_comments_and_strings(text, "x.c")[0]

    if isinstance(sources, str):
        sources = [("scripts/4_World/x.c", sources)]
    return check_es_protected_method_cross_class(
        [(path, strip(text)) for path, text in sources],
        [(path, strip(text)) for path, text in external],
        None,
    )


_OWNER = (
    "class FX_Cmd : HumanCommandScript\n{\n"
    "    protected void FX_Hide()\n    {\n    }\n"
    "    private int FX_Own(int a = Math.Max(1, 2))\n    {\n        return a;\n    }\n"
    "}\n"
)


class TestProtectedMethodCrossClass(unittest.TestCase):
    """ES-PROTECTED-METHOD-CROSS-CLASS: a hidden method called from outside.

    `cmd.FX_OnServerState(...)` from
    PlayerBase.OnRPC on a local FX_RideCommand whose method is protected.
    WARN: the refusal is measured for fields, not for methods.
    """

    def test_ticket_repro_warns(self):
        exit_code, result = script_validator.run([str(PROTECTED_METHOD / "bad")])

        self.assertEqual(2, exit_code)
        warnings = [
            w for w in result["warnings"] if w["rule_id"] == PROTECTED_METHOD_RULE
        ]
        self.assertEqual([22], [w["line"] for w in warnings])
        self.assertEqual("WARN", warnings[0]["severity"])
        self.assertIn("'cmd.FX_OnServerState('", warnings[0]["message"])
        self.assertIn("class PlayerBase", warnings[0]["message"])
        assert_standard_findings(self, result)

    def test_calls_from_the_hierarchy_and_public_calls_pass(self):
        _code, result = script_validator.run([str(PROTECTED_METHOD / "ok")])

        self.assertEqual(
            [],
            [w for w in result["warnings"] if w["rule_id"] == PROTECTED_METHOD_RULE],
        )

    def test_private_parameter_member_and_free_function(self):
        source = _OWNER + (
            "class FX_Other\n{\n    FX_Cmd m_Cmd;\n"
            "    void F(FX_Cmd p)\n    {\n"
            "        p.FX_Own();\n        m_Cmd.FX_Hide();\n    }\n}\n"
            "void G(FX_Cmd c)\n{\n    c.FX_Hide();\n}\n"
        )

        found = _protected_method_warnings(source)
        self.assertEqual([16, 17, 22], [w["line"] for w in found])
        self.assertIn("is private in FX_Cmd", found[0]["message"])
        self.assertIn("code outside any class", found[2]["message"])

    def test_unknown_or_foreign_cases_are_skipped(self):
        call = "class FX_U\n{\n    void F(FX_Cmd c)\n    {\n        c.FX_Hide();\n    }\n}\n"
        cases = {
            # a public declaration of the same name in another addon declaration
            _OWNER + "modded class FX_Cmd\n{\n    void FX_Hide()\n    {\n    }\n}\n" + call,
            # the receiver's class is also declared outside the addon (below)
            # a template, a modded-only and an unreadable owner
            "class FX_Cmd<Class T>\n{\n    protected void FX_Hide();\n}\n" + call,
            "modded class FX_Cmd\n{\n    protected void FX_Hide();\n}\n" + call,
            "class FX_Cmd\n{\n    protected void FX_Hide();\n}\nmodded class FX_Cmd extends\n" + call,
            # the method only in a vanilla ancestor
            "class FX_Cmd : HumanCommandScript\n{\n}\n" + call,
            # a caller with two parents, and a parent cycle
            _OWNER + "class FX_P\n{\n}\nclass FX_U : FX_P\n{\n}\n"
            "#ifdef FX_X\nclass FX_U : FX_Cmd\n{\n}\n#endif\n" + call,
            _OWNER + "class FX_U : FX_V\n{\n}\nclass FX_V : FX_U\n{\n}\n" + call,
            # a parent that a directive in the header hides, in the caller
            # and in its parent
            _OWNER + "class FX_U\n#ifdef FX_X\n    : FX_Cmd\n#endif\n"
            "{\n    void F(FX_Cmd c)\n    {\n        c.FX_Hide();\n    }\n}\n",
            _OWNER + "class FX_P\n#ifdef FX_X\n    : FX_Cmd\n#endif\n{\n}\n"
            "class FX_U : FX_P\n{\n    void F(FX_Cmd c)\n    {\n"
            "        c.FX_Hide();\n    }\n}\n",
            # this, super, a field initialised by a call, and #if 0
            _OWNER + "class FX_W : FX_Cmd\n{\n    void F()\n    {\n"
            "        this.FX_Hide();\n        super.FX_Hide();\n    }\n}\n",
            "class FX_Cmd\n{\n    int m_N = FX_Hide();\n    protected int FX_Peek();\n}\n"
            "class FX_U\n{\n    void F(FX_Cmd c)\n    {\n        c.FX_Hide();\n    }\n}\n",
            _OWNER + "void G(FX_Cmd c)\n{\n#if 0\n    c.FX_Hide();\n#endif\n}\n",
            # an untyped or array-typed receiver
            _OWNER + "void G(array<FX_Cmd> a, FX_Cmd b[2])\n{\n    a.FX_Hide();\n"
            "    b.FX_Hide();\n    x.FX_Hide();\n}\n",
        }
        for source in cases:
            self.assertEqual([], _protected_method_warnings(source), source)
        outside = _protected_method_warnings(
            _OWNER + call, [("scripts/4_World/e.c", "modded class FX_Cmd\n{\n}\n")]
        )
        self.assertEqual([], outside)
        self.assertEqual([5 + 10], [w["line"] for w in _protected_method_warnings(_OWNER + call)])

    def test_a_receiver_declared_after_a_case_label_is_read(self):
        # The local on the line of its case label,
        # of a class whose FX_Hide is public, is the receiver, not the member
        # of that name.
        source = _OWNER + (
            "class FX_Open\n{\n    void FX_Hide()\n    {\n    }\n}\n"
            "class FX_U\n{\n    FX_Cmd c;\n    void F(int n)\n    {\n"
            "        switch (n)\n        {\n"
            "            case 0: FX_Open c = new FX_Open();\n"
            "                c.FX_Hide();\n                break;\n"
            "        }\n    }\n}\n"
        )
        line = source.count("\n", 0, source.index("c.FX_Hide")) + 1

        self.assertEqual([], _protected_method_warnings(source))
        # With the local named otherwise, the member is the receiver.
        renamed = source.replace("FX_Open c =", "FX_Open other =")
        self.assertEqual([line], [w["line"] for w in _protected_method_warnings(renamed)])

    def test_a_descendant_through_an_external_root_is_related(self):
        source = _OWNER + (
            "class FX_U : FX_Ext\n{\n    void F(FX_Cmd c)\n    {\n"
            "        c.FX_Hide();\n    }\n}\n"
        )
        external = [("scripts/4_World/e.c", "class FX_Ext : FX_Cmd\n{\n}\n")]

        self.assertEqual([], _protected_method_warnings(source, external))
        self.assertEqual([15], [w["line"] for w in _protected_method_warnings(source)])


MULTILINE_CONDITION = FIXTURES / "multiline_condition_operator"
MULTILINE_CONDITION_RULE = "ES-MULTILINE-CONDITION-OPERATOR"


def _multiline_condition_findings(source):
    from detectors.es_multiline_condition_operator import (
        check_es_multiline_condition_operator,
    )
    from stripper import strip_enforce_comments_and_strings

    stripped = strip_enforce_comments_and_strings(source, "x.c")[0]
    return check_es_multiline_condition_operator(stripped, "x.c")


def _multiline_condition_lines(source):
    return [w["line"] for w in _multiline_condition_findings(source)]


class TestMultilineConditionOperator(unittest.TestCase):
    """ES-MULTILINE-CONDITION-OPERATOR: `if (a ||` continued on the next line.

    DayZ 1.30.164014 server: "Invalid
    statement ')'" and "Syntax error" at the continuation. FAIL since the
    vanilla control found nothing for it on 1.29.0.163451 and 1.30.164078.
    """

    def test_ticket_repro_fails(self):
        exit_code, result = script_validator.run([str(MULTILINE_CONDITION / "bad")])

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, MULTILINE_CONDITION_RULE)
        self.assertEqual([10, 18], [e["line"] for e in errors])
        self.assertIn("trailing '||'", errors[0]["message"])
        self.assertIn("trailing '&&'", errors[1]["message"])
        self.assertEqual(["FAIL", "FAIL"], [e["severity"] for e in errors])
        self.assertTrue(errors[0]["message"].startswith("[FAIL] "))
        assert_standard_findings(self, result)

    def test_single_line_conditions_and_other_continuations_pass(self):
        _code, result = script_validator.run([str(MULTILINE_CONDITION / "ok")])

        # bool locals, an operator in a comment and in a string, a call's
        # argument list over two lines, and the failing shape under #if 0.
        self.assertEqual([], _errors_of(result, MULTILINE_CONDITION_RULE))

    def test_one_finding_per_header_and_its_line(self):
        source = (
            "void F(bool a, bool b, bool c)\n{\n"
            "    if (a &&\n        b ||\n        c)\n        return;\n"
            "    else if (F2(a,\n                b) && c ||   \n        a)\n        return;\n"
            "    if (a) { if (b ||\n        c) return; }\n"
            "    int x = (a &&\n        b);\n"
            "}\n"
        )

        findings = _multiline_condition_findings(source)
        self.assertEqual([3, 8, 11], [w["line"] for w in findings])
        # The message names the same line.
        for finding in findings:
            self.assertIn("x.c line %d: " % finding["line"], finding["message"])

    def test_an_unclosed_header_is_not_judged(self):
        self.assertEqual([], _multiline_condition_lines("if (a &&\n    b\n"))


PROTO = FIXTURES / "proto_argument_downcast"
PROTO_RULE = "ES-PROTO-ARGUMENT-DOWNCAST"


def _proto_findings(
    source, external=(), vanilla=PROTO / "vanilla", path="scripts/4_World/x.c"
):
    from detectors.es_proto_argument_downcast import (
        check_es_proto_argument_downcast,
    )
    from stripper import strip_enforce_comments_and_strings

    def strip(text):
        return strip_enforce_comments_and_strings(text, "x.c")[0]

    return check_es_proto_argument_downcast(
        [(path, strip(source))],
        [(rel_path, strip(text)) for rel_path, text in external],
        vanilla,
    )


def _proto_lines(
    source, external=(), vanilla=PROTO / "vanilla", path="scripts/4_World/x.c"
):
    """The lines of the FAILs and WARNs, in order."""
    errors, warnings = _proto_findings(source, external, vanilla, path)
    return sorted(finding["line"] for finding in errors + warnings)


class TestProtoArgumentDowncast(unittest.TestCase):
    """ES-PROTO-ARGUMENT-DOWNCAST: a base-class name passed where a proto takes a derived class.

    DayZ 1.30.164014 server: an IEntity at the
    Object argument 6 of DayZPhysics.RaycastRV, "Cannot convert 'IEntity' to
    'Object' for argument '6' to method 'RaycastRV'".
    DayZDiag 1.30.164289: an Object at the EntityAI argument 0 of
    ItemPreviewWidget.SetItem, "Cannot convert 'Object' to 'EntityAI' for
    argument '0' to method 'SetItem'".
    """

    RAYCAST_EVIDENCE = (
        "(DayZ 1.30, at DayZPhysics.RaycastRV, where it also said \"Types "
        "'IEntity' and 'Object' are unrelated\")"
    )
    SETITEM_EVIDENCE = (
        "(DayZDiag 1.30.164289, at ItemPreviewWidget.SetItem, argument '0', "
        "where it also said \"Types 'Object' and 'EntityAI' are unrelated\")"
    )

    def test_ticket_repro_fails(self):
        exit_code, result = script_validator.run(
            [str(PROTO / "bad"), "--vanilla-root", str(PROTO / "vanilla")]
        )

        self.assertEqual(1, exit_code)
        errors = [
            e for e in _errors_of(result, PROTO_RULE) if "fx_rider.c" in e["file"]
        ]
        self.assertEqual([19, 21], [e["line"] for e in errors])
        self.assertIn(
            "argument 6 (counted from 0), 'hitEntity', is declared as IEntity",
            errors[0]["message"],
        )
        self.assertIn(
            "\"Cannot convert 'IEntity' to 'Object' for argument '6' to method "
            "'FX_Raycast'\"",
            errors[0]["message"],
        )
        self.assertIn("(Object > IEntity > Managed)", errors[0]["message"])
        self.assertIn("Pass Object.Cast(hitEntity)", errors[0]["message"])
        self.assertIn("the proto Object.FX_SetOwner", errors[1]["message"])
        self.assertIn("fx_rider.c", errors[0]["file"])
        # The RaycastRV pair keeps its own evidence.
        for error in errors:
            self.assertIn(self.RAYCAST_EVIDENCE, error["message"])
            self.assertNotIn("SetItem", error["message"])
        assert_standard_findings(self, result)

    def test_an_object_where_setitem_takes_an_entityai_fails(self):
        # Case A: the shape the rule had found in a mod,
        # refused by DayZDiag 1.30.164289 at the probe's line 9.
        _code, result = script_validator.run(
            [str(PROTO / "bad"), "--vanilla-root", str(PROTO / "vanilla")]
        )

        errors = [
            e for e in _errors_of(result, PROTO_RULE) if "fx_preview.c" in e["file"]
        ]
        self.assertEqual([(9, "FAIL")], [(e["line"], e["severity"]) for e in errors])
        message = errors[0]["message"]
        self.assertIn(
            "argument 0 (counted from 0), 'obj', is declared as Object, and the "
            "proto FX_ItemPreview.FX_SetItem takes EntityAI there",
            message,
        )
        self.assertIn(
            "\"Cannot convert 'Object' to 'EntityAI' for argument '0' to method "
            "'FX_SetItem'\"",
            message,
        )
        self.assertIn(self.SETITEM_EVIDENCE, message)
        self.assertNotIn("RaycastRV", message)
        self.assertIn("Pass EntityAI.Cast(obj)", message)

    def test_only_the_two_measured_pairs_fail(self):
        # An IEntity where an Object is taken and an Object where an EntityAI
        # is are FAIL. A Managed where an Object is taken, and an IEntity
        # where an EntityAI is, are not measured.
        source = (
            "void F(EntityAI s, IEntity e, Managed m, Object o)\n{\n"
            "    s.FX_SetOwner(e);\n    s.FX_SetOwner(m);\n"
            "    FX_Physics.FX_Hold(o);\n    FX_Physics.FX_Hold(e);\n}\n"
        )

        errors, warnings = _proto_findings(source)
        self.assertEqual(
            [(3, "FAIL"), (5, "FAIL")],
            [(e["line"], e["severity"]) for e in errors],
        )
        self.assertEqual(
            [(4, "WARN"), (6, "WARN")],
            [(w["line"], w["severity"]) for w in warnings],
        )
        self.assertIn(self.RAYCAST_EVIDENCE, errors[0]["message"])
        self.assertIn(self.SETITEM_EVIDENCE, errors[1]["message"])
        message = warnings[1]["message"]
        self.assertTrue(message.startswith("[WARN] scripts/4_World/x.c line 6: "))
        self.assertIn(
            "'e', is declared as IEntity, and the proto FX_Physics.FX_Hold takes "
            "EntityAI there",
            message,
        )
        self.assertIn(
            "DayZ 1.30 refused two, an IEntity where DayZPhysics.RaycastRV takes "
            "an Object and an Object where ItemPreviewWidget.SetItem takes an "
            "EntityAI",
            message,
        )
        self.assertIn(
            "whether it refuses IEntity where EntityAI is taken is not measured",
            message,
        )
        self.assertIn("Pass EntityAI.Cast(e)", message)
        self.assertIn(
            "whether it refuses Managed where Object is taken is not measured",
            warnings[0]["message"],
        )
        # The validator counts the FAILs as errors and the rest as warnings.
        with tempfile.TemporaryDirectory() as temp_dir:
            path = pathlib.Path(temp_dir) / "x.c"
            path.write_text(source, encoding="utf-8")
            _code, result = script_validator.run(
                [str(path), "--vanilla-root", str(PROTO / "vanilla")]
            )
        self.assertEqual(
            [3, 5], [e["line"] for e in _errors_of(result, PROTO_RULE)]
        )
        self.assertEqual(
            [4, 6],
            [w["line"] for w in result["warnings"] if w["rule_id"] == PROTO_RULE],
        )

    def test_without_the_vanilla_tree_nothing_is_judged(self):
        _code, result = script_validator.run([str(PROTO / "bad")])

        self.assertEqual([], _errors_of(result, PROTO_RULE))

    def test_casts_upcasts_and_out_arguments_pass(self):
        _code, result = script_validator.run(
            [str(PROTO / "ok"), "--vanilla-root", str(PROTO / "vanilla")]
        )

        # An out argument, the entity cast first, an EntityAI and null where
        # an Object is taken, and the bad call in a comment, a string and
        # #if 0.
        self.assertEqual([], _errors_of(result, PROTO_RULE))

    def test_a_parameter_a_member_and_a_local_are_resolved(self):
        source = (
            "class FX_C\n{\n    IEntity m_Hit;\n    EntityAI m_Self;\n\n"
            "    void F(IEntity param, Managed any)\n    {\n"
            "        m_Self.FX_SetOwner(param);\n"
            "        m_Self.FX_SetOwner(m_Hit);\n"
            # two classes up
            "        m_Self.FX_SetOwner(any);\n"
            "        EntityAI own = m_Self;\n"
            "        own.FX_SetOwner(m_Hit);\n"
            "    }\n}\n"
        )

        self.assertEqual([8, 9, 10, 12], _proto_lines(source))

    def test_an_inherited_member_is_resolved(self):
        external = [(
            "scripts/3_Game/p.c",
            # m_Held once more on a line that never compiles; m_Two declared
            # twice across the class's bodies; m_Deep an array in the class
            # nearest to the user, which decides
            "class FX_Holder\n{\n    IEntity m_Held;\n    Object m_Kept;\n"
            "#if 0\n    Object m_Held;\n#endif\n"
            "    IEntity m_Two;\n    IEntity m_Deep;\n}\n"
            "modded class FX_Holder\n{\n    Managed m_Two;\n}\n"
            "class FX_Middle : FX_Holder\n{\n    IEntity m_Deep[2];\n}\n",
        )]
        source = (
            "class FX_Heir : FX_Middle\n{\n    void F(EntityAI s)\n    {\n"
            "        s.FX_SetOwner(m_Held);\n        s.FX_SetOwner(m_Kept);\n"
            "        s.FX_SetOwner(m_Two);\n        s.FX_SetOwner(m_Deep);\n"
            "    }\n}\n"
            # another body of the same class
            "modded class FX_Holder\n{\n    void G(EntityAI s)\n    {\n"
            "        s.FX_SetOwner(m_Held);\n    }\n}\n"
            # a chain that does not resolve
            "class FX_Lost : FX_Nowhere\n{\n    void K(EntityAI s)\n    {\n"
            "        s.FX_SetOwner(m_Held);\n    }\n}\n"
        )

        self.assertEqual([5, 15], _proto_lines(source, external))

    def test_a_call_outside_every_method_read_is_skipped(self):
        # shared/method_recognition.py reads no method whose return type has
        # template arguments, nor one whose `{` follows a default that calls
        # on the header's line: their parameters are unknown, so the member
        # of the same name must not be taken for them. H is read.
        source = (
            "class FX_T\n{\n    IEntity hit;\n"
            "    array<Object> F(Object hit)\n    {\n"
            "        FX_Physics.FX_Tag(hit);\n        return null;\n    }\n"
            "    void G(Object hit = FX_Make()) {\n"
            "        FX_Physics.FX_Tag(hit);\n    }\n"
            "    void H(Object e)\n    {\n        FX_Physics.FX_Tag(hit);\n    }\n}\n"
        )

        self.assertEqual([14], _proto_lines(source))

    def test_the_parameter_list_is_read_whole(self):
        # Template arguments, a default value with a call, an array, a
        # string and notnull keep the index of the Object after them, and
        # its own default is no part of its type.
        external = [(
            "scripts/3_Game/p.c",
            "class FX_P\n{\n    proto static void F(map<string, int> a, "
            "vector v = Vector(0, 1, 2), int b[2], string s = \"x, y\", "
            "notnull Object o = null);\n}\n",
        )]
        source = (
            "void G(IEntity e)\n{\n"
            "    FX_P.F(null, \"0 0 0\", null, \"a, b\", e);\n"
            "    FX_P.F(null, \"0 0 0\", null, e);\n"
            "}\n"
        )

        self.assertEqual([3], _proto_lines(source, external))

    def test_a_default_string_of_the_vanilla_tree_keeps_the_index(self):
        # FX_Tag takes `string tag = "a, b"`: the vanilla tree is read with
        # its strings blanked, so the comma in it splits nothing.
        source = (
            "void F(Object o, IEntity e)\n{\n"
            "    FX_Physics.FX_Tag(o, \"x\", e);\n}\n"
        )

        self.assertEqual([3], _proto_lines(source))

    def test_an_argument_that_holds_a_call_keeps_the_index(self):
        source = (
            "void F(Object o, IEntity e)\n{\n"
            "    FX_Physics.FX_Tag(FX_Pick(o, e), \"x\", e);\n"
            "    FX_Physics.FX_Tag(o, FX_Name(e)[0], FX_Pick(e, FX_Pick(o, e)));\n}\n"
        )

        self.assertEqual([3], _proto_lines(source))

    def test_the_first_class_that_declares_the_method_decides(self):
        external = [(
            "scripts/3_Game/p.c",
            "class FX_Base\n{\n    proto native void H(Object o);\n}\n"
            "class FX_Derived : FX_Base\n{\n"
            "    proto native void H(IEntity o);\n}\n"
            "class FX_Script : FX_Base\n{\n"
            "    void H(Object o)\n    {\n    }\n}\n"
            # a field set by a call to H, and a statement that declares
            # nothing: neither class declares H, so FX_Base decides
            "class FX_Field : FX_Base\n{\n    int m_N = H(null);\n}\n"
            "class FX_Paren : FX_Base\n{\n    (1);\n}\n",
        )]
        source = (
            "void F(FX_Base b, FX_Derived d, FX_Script s, FX_Field f, "
            "FX_Paren p, IEntity e)\n{\n"
            "    b.H(e);\n    d.H(e);\n    s.H(e);\n    f.H(e);\n    p.H(e);\n}\n"
        )

        self.assertEqual([3, 6, 7], _proto_lines(source, external))
        # Without the vanilla tree Object and IEntity are unknown.
        self.assertEqual([], _proto_lines(source, external, vanilla=None))

    def test_a_declaration_that_never_compiles_is_dropped(self):
        # FX_NO_PROTO is defined, so the #ifndef branches never compile: the
        # base decides, a proto for FX_Child and a script method for
        # FX_Hidden. Under #ifdef FX_OTHER a declaration may compile, so H is
        # unknown for FX_Maybe and FX_Perhaps.
        source = (
            "#define FX_NO_PROTO\n"
            "class FX_Base : EntityAI\n{\n    proto native void H(Object e);\n}\n"
            "class FX_Script : EntityAI\n{\n    void H(IEntity e)\n    {\n    }\n}\n"
            "class FX_Child : FX_Base\n{\n#ifndef FX_NO_PROTO\n"
            "    void H(IEntity e)\n    {\n    }\n#endif\n}\n"
            "class FX_Hidden : FX_Script\n{\n#ifndef FX_NO_PROTO\n"
            "    proto native void H(Object e);\n#endif\n}\n"
            "class FX_Maybe : FX_Base\n{\n#ifdef FX_OTHER\n"
            "    void H(IEntity e)\n    {\n    }\n#endif\n}\n"
            "class FX_Perhaps : FX_Script\n{\n#ifdef FX_OTHER\n"
            "    proto native void H(Object e);\n#endif\n}\n"
            "void F(FX_Child c, FX_Hidden h, FX_Maybe m, FX_Perhaps p, IEntity e)\n{\n"
            "    c.H(e);\n    h.H(e);\n    m.H(e);\n    p.H(e);\n}\n"
        )

        self.assertEqual([42], _proto_lines(source))

    def test_unjudged_shapes_are_skipped(self):
        cases = [
            # a script method: only a proto's refusal is measured
            "void F(EntityAI s, IEntity e)\n{\n    s.FX_Attach(e);\n}\n",
            # an unrelated class, an up-cast, Class, a typedef and an enum
            "class FX_U\n{\n}\ntypedef IEntity FX_Alias;\nenum FX_E\n{\n    A\n}\n"
            "void F(EntityAI s, FX_U u, Class c, FX_Alias a, FX_E n)\n{\n"
            "    s.FX_SetOwner(u);\n    s.FX_SetOwner(s);\n"
            "    s.FX_SetOwner(c);\n    s.FX_SetOwner(a);\n"
            "    s.FX_SetOwner(n);\n}\n",
            # an out argument, and an out, an inout and an array parameter
            # of a class above the argument's
            "void F(IEntity e)\n{\n    FX_Physics.FX_Probe(e);\n"
            "    FX_Physics.FX_Find(e, e);\n    FX_Physics.FX_Many(e);\n}\n",
            # a template argument, or a comparison, among the arguments
            "void F(vector a, int c, IEntity e)\n{\n"
            "    FX_Physics.FX_Raycast(a, a, a, a, c, new set<Object>, e, null, "
            "true, false, 0);\n"
            "    FX_Physics.FX_Raycast(a, a, a, a, c, null, e, null, c < 2, "
            "false, 0);\n}\n",
            # a directive among the arguments, which would put e at the
            # Object 6 when both branches count, and more arguments than
            # parameters
            "void F(EntityAI s, vector a, int c, IEntity e)\n{\n"
            "    FX_Physics.FX_Raycast(a, a, a,\n#ifdef FX_X\n        a,\n"
            "#else\n        a,\n#endif\n        c, e);\n"
            "    s.FX_SetOwner(e, e);\n}\n",
            # this, super, no receiver, a call's result and an unknown name
            "class FX_S : EntityAI\n{\n    void F(IEntity e)\n    {\n"
            "        this.FX_SetOwner(e);\n        super.FX_SetOwner(e);\n"
            "        FX_SetOwner(e);\n        GetSelf().FX_SetOwner(e);\n"
            "        g_Unknown.FX_SetOwner(e);\n    }\n}\n",
            # arguments that are no plain name (a member through this, an
            # element written as the array's declarator, `many[2]`, and the
            # text of a declarator, `x = m_E`), a later declarator
            # (`IEntity a, b;`), a template and an array, and a foreach
            # variable
            "class FX_C\n{\n    IEntity m_E;\n    void F(EntityAI s, "
            "array<IEntity> list, IEntity many[2])\n    {\n"
            "        s.FX_SetOwner(this.m_E);\n        s.FX_SetOwner(many[2]);\n"
            "        IEntity x = m_E;\n        s.FX_SetOwner(x = m_E);\n"
            "        IEntity a, b;\n"
            "        s.FX_SetOwner(b);\n        s.FX_SetOwner(list);\n"
            "        s.FX_SetOwner(many);\n"
            "        foreach (IEntity e : list)\n"
            "            s.FX_SetOwner(e);\n    }\n}\n",
            # an addon redeclaration of the method, in a derived class or a
            # modded one, that is no proto
            "class FX_Own : EntityAI\n{\n    void FX_SetOwner(Object o)\n    {\n"
            "    }\n}\nvoid F(FX_Own o, IEntity e)\n{\n    o.FX_SetOwner(e);\n}\n",
            "modded class EntityAI\n{\n    void FX_SetOwner(Object o)\n    {\n"
            "    }\n}\nvoid F(EntityAI s, IEntity e)\n{\n    s.FX_SetOwner(e);\n}\n",
            "class FX_Attr : EntityAI\n{\n#ifdef FX_X\n    [FX_Note(\"x\")]\n"
            "    void FX_SetOwner(Object o)\n    {\n    }\n#endif\n}\n"
            "void F(FX_Attr a, IEntity e)\n{\n    a.FX_SetOwner(e);\n}\n",
            # Class, the implicit root, also where a chain names it
            "class FX_Rooted : Class\n{\n    proto static void R(FX_Rooted r);\n}\n"
            "void F(Class c)\n{\n    FX_Rooted.R(c);\n}\n",
            # a receiver whose chain does not resolve
            "class FX_A : FX_Nowhere\n{\n}\n"
            "void F(FX_A a, IEntity e)\n{\n    a.FX_SetOwner(e);\n}\n",
            # the call under #if 0
            "void F(EntityAI s, IEntity e)\n{\n#if 0\n    s.FX_SetOwner(e);\n"
            "#endif\n}\n",
        ]
        for source in cases:
            self.assertEqual([], _proto_lines(source), source)

    def test_unread_declarations_are_skipped(self):
        external = [(
            "scripts/3_Game/p.c",
            # two parameter lists for one proto, even where they agree on
            # the first: under #ifdef and #else (a declaration under a block
            # leaves the method unknown), and in a class and a modded class
            "class FX_Two\n{\n#ifdef FX_A\n    proto static void G(Object o);\n"
            "#else\n    proto static void G(Object o, int i);\n#endif\n}\n"
            "class FX_Three\n{\n    proto static void G(Object o);\n}\n"
            "modded class FX_Three\n{\n    proto static void G(Object o, int i);\n}\n"
            # a parameter list that a directive splits
            "class FX_Split\n{\n    proto static void G(\n#ifdef FX_A\n"
            "        Object o\n#else\n        int i\n#endif\n    );\n}\n"
            # a parameter of an unknown modifier, one without a name, and
            # one of a class whose chain does not resolve
            "class FX_Orphan : FX_Nowhere\n{\n}\n"
            "class FX_Odd\n{\n    proto static void G(event Object o);\n"
            "    proto static void U(Object);\n"
            "    proto static void K(FX_Orphan o);\n}\n",
        ), (
            # a class body whose brackets do not close: what it declares is
            # unknown, so the proto of Object it may hide is not judged
            "scripts/3_Game/q.c",
            "class FX_Broken : EntityAI\n{\n    int m_X = (1;\n}\n",
        )]
        source = (
            "void F(IEntity e, Managed m, FX_Broken b)\n{\n    FX_Two.G(e);\n"
            "    FX_Three.G(e);\n"
            "    FX_Split.G(e);\n    FX_Odd.G(e);\n    FX_Odd.U(e);\n"
            "    FX_Odd.K(m);\n    b.FX_SetOwner(e);\n}\n"
        )

        self.assertEqual([], _proto_lines(source, external))

    def test_a_declaration_under_another_block_leaves_the_name_unknown(self):
        # Under #ifndef FX_MAYBE the call reaches
        # the Object of FX_B, so the IEntity under #ifdef FX_MAYBE is no type
        # of it, as a member of a class up the chain, of the enclosing body
        # or as a local; nor the Object where FX_Hold takes an EntityAI.
        base = "class FX_B\n{\n    Object hit;\n}\n"
        maybe = "#ifdef FX_MAYBE\n    IEntity hit;\n#endif\n"
        call = "#ifndef FX_MAYBE\n        FX_Physics.FX_Tag(hit);\n#endif\n"
        cases = [
            base + "class FX_C : FX_B\n{\n" + maybe + "}\n"
            "class FX_D : FX_C\n{\n    void F()\n    {\n" + call + "    }\n}\n",
            base + "class FX_D : FX_B\n{\n" + maybe
            + "    void F()\n    {\n" + call + "    }\n}\n",
            base + "class FX_D : FX_B\n{\n    void F()\n    {\n"
            + maybe.replace("    IEntity", "        IEntity") + call + "    }\n}\n",
            "class FX_B\n{\n    EntityAI hit;\n}\n"
            "class FX_C : FX_B\n{\n#ifdef FX_MAYBE\n    Object hit;\n#endif\n}\n"
            "class FX_D : FX_C\n{\n    void F()\n    {\n#ifndef FX_MAYBE\n"
            "        FX_Physics.FX_Hold(hit);\n#endif\n    }\n}\n",
        ]
        for source in cases:
            self.assertEqual([], _proto_lines(source), source)
        # Each without the block around its declaration.
        for source in cases:
            self.assertEqual(
                1,
                len(_proto_lines(source.replace("#ifdef FX_MAYBE\n", "", 1)
                                 .replace("#endif\n", "", 1))),
                source,
            )

    def test_a_declaration_under_the_blocks_around_the_call_is_read(self):
        # A file under one #ifdef, and calls under one more: a declaration
        # under blocks that are all around the call is read, also when the
        # call is under more of them. m_In, under the inner block, is
        # unknown for H, outside it.
        source = (
            "#ifdef FX_MOD\nclass FX_B\n{\n    IEntity m_Up;\n}\n"
            "class FX_D : FX_B\n{\n    IEntity m_Own;\n"
            "    void F(IEntity param)\n    {\n        IEntity local;\n"
            "        FX_Physics.FX_Tag(m_Up);\n        FX_Physics.FX_Tag(m_Own);\n"
            "        FX_Physics.FX_Tag(param);\n        FX_Physics.FX_Tag(local);\n"
            "    }\n}\n"
            "class FX_E : FX_B\n{\n    IEntity m_Out;\n    void H()\n    {\n"
            "        FX_Physics.FX_Tag(m_In);\n    }\n"
            "#ifdef FX_MORE\n    IEntity m_In;\n    void G()\n    {\n"
            "        FX_Physics.FX_Tag(m_In);\n        FX_Physics.FX_Tag(m_Out);\n"
            "        FX_Physics.FX_Tag(m_Up);\n    }\n#endif\n}\n#endif\n"
        )

        self.assertEqual([12, 13, 14, 15, 29, 30, 31], _proto_lines(source))
        # Block numbers are those of one file: a member under a block of
        # another file is unknown, even under a block of the same macro.
        external = [(
            "scripts/3_Game/p.c",
            "class FX_B\n{\n#ifdef FX_MOD\n    IEntity m_Up;\n#endif\n}\n",
        )]
        source = (
            "class FX_D : FX_B\n{\n    void F()\n    {\n#ifdef FX_MOD\n"
            "        FX_Physics.FX_Tag(m_Up);\n#endif\n    }\n}\n"
        )
        self.assertEqual([], _proto_lines(source, external))

    def test_a_member_of_a_later_module_is_not_seen(self):
        # World is compiled before the Mission
        # body that adds the member, so g_Hit is the global Object.
        base = ("scripts/3_Game/base.c", "Object g_Hit;\n\nclass FX_C\n{\n}\n")
        later = "modded class FX_C\n{\n    IEntity g_Hit;\n}\n"
        source = (
            "modded class FX_C\n{\n    void F()\n    {\n"
            "        FX_Physics.FX_Tag(g_Hit);\n    }\n}\n"
        )

        self.assertEqual(
            [], _proto_lines(source, [base, ("scripts/5_Mission/later.c", later)])
        )
        # One of the same module or of an earlier one is seen.
        for path in ("scripts/4_World/later.c", "scripts/3_Game/later.c"):
            self.assertEqual([5], _proto_lines(source, [base, (path, later)]), path)
        # A body or a call in a file under no N_Module folder may be seen or
        # not, so the name is unknown, even with a class up the chain that
        # declares it.
        up = (
            "scripts/3_Game/up.c",
            "class FX_Up\n{\n    IEntity g_Hit;\n}\nclass FX_C : FX_Up\n{\n}\n",
        )
        self.assertEqual([5], _proto_lines(source, [up]))
        self.assertEqual([], _proto_lines(source, [up], path="scripts/x.c"))
        self.assertEqual(
            [],
            _proto_lines(source, [up, ("later.c", later.replace("IEntity", "Object"))]),
        )
        self.assertEqual([], _proto_lines(source, [base, ("later.c", later)]))

    def test_a_member_of_the_vanilla_tree_is_read_with_its_module(self):
        # The vanilla files are under 1_core to 5_mission as the addon's are
        # under 1_Core to 5_Mission: a member of 3_game is seen from World
        # and not from GameLib.
        with tempfile.TemporaryDirectory() as temp_dir:
            vanilla = pathlib.Path(temp_dir)
            for path in (PROTO / "vanilla").rglob("*.c"):
                target = vanilla / path.relative_to(PROTO / "vanilla")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            (vanilla / "3_game" / "fx_holder.c").write_text(
                "class FX_VHolder\n{\n    IEntity m_V;\n}\n", encoding="utf-8"
            )
            source = (
                "class FX_VUser : FX_VHolder\n{\n    void F()\n    {\n"
                "        FX_Physics.FX_Tag(m_V);\n    }\n}\n"
            )

            self.assertEqual([5], _proto_lines(source, vanilla=vanilla))
            self.assertEqual(
                [], _proto_lines(source, vanilla=vanilla, path="scripts/2_GameLib/x.c")
            )

    def test_a_proto_word_that_never_compiles_makes_no_proto(self):
        # With `proto native` under #if 0 Take is
        # a script method. A word under #ifdef may compile, so the method is
        # unknown.
        source = (
            "class FX_API\n{\n#if 0\n    proto native\n#endif\n"
            "    void Take(Object value)\n    {\n    }\n}\n"
            "void F(FX_API a, IEntity e)\n{\n    a.Take(e);\n}\n"
        )
        maybe = (
            "class FX_API\n{\n    proto native\n#ifdef FX_X\n    static\n#endif\n"
            "    void Take(Object value);\n}\n"
            "void F(FX_API a, IEntity e)\n{\n    a.Take(e);\n}\n"
        )

        self.assertEqual([], _proto_lines(source))
        self.assertEqual([], _proto_lines(maybe))
        live = maybe.replace("#ifdef FX_X\n", "").replace("#endif\n", "")
        self.assertEqual([9], _proto_lines(live))

    def test_a_member_of_a_template_class_is_read(self):
        # The member read in the class's own body
        # was dropped for the lookup up a chain a template class has not.
        source = (
            "class FX_G<Class T>\n{\n    IEntity hit;\n    void F()\n    {\n"
            "        FX_Physics.FX_Tag(hit);\n    }\n}\n"
        )

        self.assertEqual([6], _proto_lines(source))

    def test_the_hook_is_asked_only_for_a_member_the_body_does_not_declare(self):
        from detectors.es_cast_unrelated_types import FileScopes, _argument_type

        stripped = (
            "class FX_H\n{\n    Object hit;\n    void F()\n    {\n"
            "        G(hit, miss);\n    }\n}\n"
        )
        scopes = FileScopes(stripped)
        asked = []

        def inherited(open_brace, name, blocks):
            asked.append((name, blocks))
            return "IEntity"

        at = stripped.index("G(")
        self.assertEqual(
            "Object", _argument_type(stripped, scopes, "hit", at, inherited)
        )
        self.assertEqual(
            "IEntity", _argument_type(stripped, scopes, "miss", at, inherited)
        )
        self.assertEqual([("miss", ())], asked)

    def test_a_class_body_is_read_once_per_name(self):
        # The class body was read again for
        # each set of blocks around a call, so over the mods the rule took 21 %
        # longer than the second version. These 400 calls, each under a block
        # of its own, in a class of 20 000 members, took 12.4 s, and take 0.3 s.
        source = (
            "class FX_D\n{\n    IEntity m_Hit;\n"
            + "".join("    Object m_X%d;\n" % i for i in range(20000))
            + "".join(
                "    void F%d()\n    {\n#ifdef FX_B%d\n"
                "        FX_Physics.FX_Tag(m_Hit);\n#endif\n    }\n" % (i, i)
                for i in range(400)
            )
            + "}\n"
        )

        start = time.perf_counter()
        lines = _proto_lines(source)

        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual(400, len(lines))

    def test_a_loop_variable_named_as_a_member_leaves_the_name_unknown(self):
        # The `(` of a foreach closes before a call
        # in the loop, so the lookup passed over the loop's Object and took
        # the member IEntity of that name, a false FAIL. A foreach variable,
        # also as the receiver, a for variable and a local of a block closed
        # before the call leave the name unknown where a member has it.
        cases = [
            ("class FX_L\n{\n    IEntity hit;\n    void F(array<Object> list)\n"
             "    {\n        foreach (Object hit : list)\n        {\n"
             "            FX_Physics.FX_Tag(hit);\n        }\n    }\n}\n",
             "Object hit :", [8]),
            ("class FX_L\n{\n    IEntity hit;\n    void F(Object o)\n    {\n"
             "        for (Object hit = o; hit != null; hit = null)\n"
             "            FX_Physics.FX_Tag(hit);\n    }\n}\n",
             "Object hit =", [7]),
            ("class FX_L\n{\n    Object item;\n    void F(array<EntityAI> list)\n"
             "    {\n        foreach (EntityAI item : list)\n"
             "            FX_Physics.FX_Hold(item);\n    }\n}\n",
             "EntityAI item :", [7]),
            ("class FX_L\n{\n    Object s;\n    void F(array<FX_L> list, IEntity e)\n"
             "    {\n        foreach (FX_L s : list)\n            s.FX_SetOwner(e);\n"
             "    }\n}\n",
             "FX_L s :", [7]),
            ("class FX_L\n{\n    IEntity hit;\n    void F(bool b, Object o)\n    {\n"
             "        if (b)\n        {\n            Object hit = o;\n        }\n"
             "        FX_Physics.FX_Tag(hit);\n    }\n}\n",
             "Object hit =", [10]),
        ]
        for source, local, member_lines in cases:
            self.assertEqual([], _proto_lines(source), source)
            # With the local named otherwise, the member is read.
            renamed = source.replace(local, local.split()[0] + " other " + local[-1])
            self.assertEqual(member_lines, _proto_lines(renamed), renamed)

    def test_a_member_on_a_line_that_never_compiles_is_no_second_type(self):
        # An Object member under #if 0 beside the
        # IEntity one leaves the IEntity the name's one type.
        source = (
            "class FX_D\n{\n    IEntity hit;\n#if 0\n    Object hit;\n#endif\n"
            "    void F()\n    {\n        FX_Physics.FX_Tag(hit);\n    }\n}\n"
        )

        self.assertEqual([9], _proto_lines(source))

    def test_a_declaration_after_a_case_label_is_read(self):
        # On the line of its `case` or `default`
        # label a declaration was none for the lookup, which took the member
        # of that name: an Object local beside an IEntity member was FAIL,
        # and an IEntity local beside an Object member passed. On a line of
        # its own the local was read. A case of an enum's value and a second
        # label on the line count too.
        for local, member, fails in (
            ("Object", "IEntity", False), ("IEntity", "Object", True)
        ):
            for label in ("case 0:", "default:", "case FX_Kind.FIRST:", "case 0: case 1:"):
                for apart in (" ", "\n            "):
                    source = (
                        "enum FX_Kind\n{\n    FIRST\n}\n"
                        "class FX_C\n{\n    %s hit;\n" % member
                        + "    void F(int n, vector a, int c)\n    {\n"
                        "        switch (n)\n        {\n"
                        "            %s%s%s hit;\n" % (label, apart, local)
                        + "                FX_Physics.FX_Raycast(a, a, a, a, c, null, "
                        "hit, null, true, false, 0);\n"
                        "                break;\n        }\n    }\n}\n"
                    )
                    line = source.count("\n", 0, source.index("FX_Physics")) + 1
                    self.assertEqual(
                        [line] if fails else [], _proto_lines(source), source
                    )

    def test_a_for_variable_is_read_in_its_own_header(self):
        # The header of a for is still open at a call
        # in its condition, so the variable is read there, not the member.
        source = (
            "class FX_F\n{\n    Object hit;\n    void F(IEntity e, vector a, int c)\n"
            "    {\n        for (IEntity hit = e; FX_Physics.FX_Raycast(a, a, a, a, "
            "c, null, hit, null, true, false, 0); hit = null)\n        {\n        }\n"
            "    }\n}\n"
        )

        self.assertEqual([6], _proto_lines(source))

    def test_a_long_line_before_a_colon_is_read_once(self):
        # Searched for, the label before a `:` took a
        # time that grew with the square of the text before it on the line.
        source = (
            "class FX_G\n{\n    IEntity hit;\n    void F()\n    {\n"
            "        " + "case x " * 20000 + "; not_a_label: Object hit;\n"
            "        FX_Physics.FX_Tag(hit);\n    }\n}\n"
        )

        start = time.perf_counter()
        lines = _proto_lines(source)
        self.assertLess(time.perf_counter() - start, 2)
        self.assertEqual([7], lines)

    def test_a_label_after_a_statement_on_its_line_is_read(self):
        # The label is read from the last `;`, `{`
        # or `}` before it on its line, so a statement, a `switch` head or a
        # closed block before the label leaves its declaration read; without
        # that boundary the lookup took the member of that name.
        for local, member, fails in (
            ("Object", "IEntity", False), ("IEntity", "Object", True)
        ):
            for switch in (
                "        switch (n)\n        {\n"
                "            case 0: break; case 1: %s hit;\n",
                "        switch (n) { case 0: %s hit;\n",
                "        switch (n)\n        {\n"
                "            case 0: if (n) {} case 1: %s hit;\n",
            ):
                source = (
                    "class FX_L\n{\n    %s hit;\n" % member
                    + "    void F(int n)\n    {\n"
                    + switch % local
                    + "                FX_Physics.FX_Tag(hit);\n"
                    "                break;\n        }\n    }\n}\n"
                )
                line = source.count("\n", 0, source.index("FX_Physics")) + 1
                self.assertEqual(
                    [line] if fails else [], _proto_lines(source), source
                )

    def test_a_label_indented_with_tabs_is_read(self):
        # A label indented with tabs is read like
        # one indented with spaces, so the Object local after it is read, not
        # the IEntity member of that name.
        source = (
            "class FX_T\n{\n    IEntity hit;\n    void F(int n)\n    {\n"
            "        switch (n)\n        {\n"
            "\t\t\tcase 0: Object hit;\n"
            "                FX_Physics.FX_Tag(hit);\n"
            "                break;\n        }\n    }\n}\n"
        )

        self.assertEqual([], _proto_lines(source))

    def test_a_name_that_begins_with_case_is_no_label(self):
        # `casework:` is no `case` label, so the
        # declaration after it is not read, as after `not_a_label:`, and the
        # IEntity member of that name is.
        source = (
            "class FX_W\n{\n    IEntity hit;\n    void F(int n)\n    {\n"
            "        switch (n)\n        {\n"
            "            casework: Object hit;\n"
            "                FX_Physics.FX_Tag(hit);\n"
            "                break;\n        }\n    }\n}\n"
        )

        self.assertEqual([9], _proto_lines(source))

    def test_a_template_with_a_comma_after_a_label_is_read(self):
        # The template part of a declaration after a
        # label runs past its comma, so the map local is read and the IEntity
        # member of that name is not.
        source = (
            "class FX_M\n{\n    IEntity hit;\n    void F(int n)\n    {\n"
            "        switch (n)\n        {\n"
            "            case 0: map<string, Object> hit;\n"
            "                FX_Physics.FX_Tag(hit);\n"
            "                break;\n        }\n    }\n}\n"
        )

        self.assertEqual([], _proto_lines(source))

    def test_a_long_line_of_template_or_array_parts_is_read_once(self):
        # From each `:` before a type the template
        # part of the declaration pattern, and its array part, ran on to the
        # end of the line, so a line of `: Object<` or `: Object[` took a time
        # that grew with its square.
        for part in ("<", "["):
            source = (
                "class FX_H\n{\n    IEntity hit;\n    void F()\n    {\n"
                "        " + (": Object" + part) * 20000 + "; Object hit;\n"
                "        FX_Physics.FX_Tag(hit);\n    }\n}\n"
            )

            start = time.perf_counter()
            lines = _proto_lines(source)
            self.assertLess(time.perf_counter() - start, 2, part)
            self.assertEqual([], lines, part)

    def test_a_closed_declaration_leaves_the_open_and_the_compiled_ones(self):
        # An IEntity local open at the call beside
        # an Object one of a block closed in the other branch of an #ifdef,
        # and an IEntity member beside an Object foreach variable under #if 0,
        # are FAIL: neither the closed declaration nor the one that never
        # compiles leaves the name unknown.
        cases = [
            ("class FX_K\n{\n    Object hit;\n    void F(bool b)\n    {\n"
             "#ifdef FX_FIRST\n        if (b)\n        {\n            Object hit;\n"
             "        }\n#else\n        IEntity hit;\n"
             "        FX_Physics.FX_Tag(hit);\n#endif\n    }\n}\n", [13]),
            ("class FX_K\n{\n    IEntity hit;\n    void F(array<Object> list)\n"
             "    {\n#if 0\n        foreach (Object hit : list)\n        {\n"
             "        }\n#endif\n        FX_Physics.FX_Tag(hit);\n    }\n}\n", [11]),
        ]
        for source, lines in cases:
            self.assertEqual(lines, _proto_lines(source), source)


BUILTIN = FIXTURES / "undefined_builtin_method"
BUILTIN_RULE = "ES-UNDEFINED-BUILTIN-METHOD"


def _builtin_check(source, external=(), vanilla=BUILTIN / "vanilla"):
    from detectors.es_undefined_builtin_method import (
        check_es_undefined_builtin_method,
    )
    from stripper import strip_enforce_comments_and_strings

    def strip(text):
        return strip_enforce_comments_and_strings(text, "x.c")[0]

    return check_es_undefined_builtin_method(
        [("scripts/4_World/x.c", strip(source))],
        [(path, strip(text)) for path, text in external],
        vanilla,
    )


def _builtin_errors(source, external=(), vanilla=BUILTIN / "vanilla"):
    return _builtin_check(source, external, vanilla)[0]


def _builtin_skips(result):
    return [
        s for s in result["info"].get("skipped_checks", [])
        if s["rule_id"] == BUILTIN_RULE
    ]


class TestUndefinedBuiltinMethod(unittest.TestCase):
    """ES-UNDEFINED-BUILTIN-METHOD: a method the built-in type does not declare.

    DayZDiag 1.30.164200 server: `gF.Cross(gR)`
    with vector locals stopped the World module with "Undefined function
    'vector.Cross'"; the 1.30.164014 Exp and 1.30.164078 scripts declare it.
    """

    def test_ticket_repro_fails(self):
        exit_code, result = script_validator.run(
            [str(BUILTIN / "bad"), "--vanilla-root", str(BUILTIN / "vanilla")]
        )

        self.assertEqual(1, exit_code)
        errors = _errors_of(result, BUILTIN_RULE)
        self.assertEqual([13, 15], [e["line"] for e in errors])
        self.assertIn("'forward.Cross('", errors[0]["message"])
        self.assertIn("'forward' is declared as vector", errors[0]["message"])
        self.assertIn("1_core/proto/fx_builtin.c:33", errors[0]["message"])
        self.assertIn("Undefined function 'vector.Cross'", errors[0]["message"])
        self.assertIn("'up.Cross('", errors[1]["message"])
        self.assertIn("fx_edge_glue.c", errors[0]["file"])
        self.assertEqual("FAIL", errors[0]["severity"])
        self.assertEqual([], _builtin_skips(result))
        assert_standard_findings(self, result)

    def test_without_the_vanilla_tree_the_rule_is_skipped(self):
        _code, result = script_validator.run([str(BUILTIN / "bad")])

        self.assertEqual([], _errors_of(result, BUILTIN_RULE))
        skips = _builtin_skips(result)
        self.assertEqual(1, len(skips))
        self.assertIn("vanilla tree", skips[0]["reason"])
        # A folder that is no DayZ scripts tree is no vanilla tree either.
        _code, result = script_validator.run(
            [str(BUILTIN / "bad"), "--vanilla-root", str(BUILTIN / "ok")]
        )
        self.assertEqual([], _errors_of(result, BUILTIN_RULE))
        self.assertIn("class Managed", _builtin_skips(result)[0]["reason"])

    def test_valid_and_unjudged_calls_pass(self):
        _code, result = script_validator.run(
            [str(BUILTIN / "ok"), "--vanilla-root", str(BUILTIN / "vanilla")]
        )

        # The fix written out; calls on vector, string, int, float, bool,
        # typename, array, set, map and a typedef of array, on a value and
        # on the type; Class's members; a call's result, a member access and
        # an index; the bad call in a comment and in a string.
        self.assertEqual([], _errors_of(result, BUILTIN_RULE))
        self.assertEqual([], _builtin_skips(result))

    def test_every_built_in_type_is_judged(self):
        source = "\n".join([
            "class C",
            "{",
            "    string m_S;",
            "    ref map<string, int> m_M;",
            "    void F(vector v, typename t, TStringArray labels)",
            "    {",
            "        int i = 1;",
            "        float f = 1.0;",
            "        bool b = true;",
            "        array<int> a = new array<int>;",
            "        set<int> s;",
            "        v.Cross(v);",
            "        vector.Cross(v, v);",
            "        m_S.Cross();",
            "        i.Cross();",
            "        f.Cross();",
            "        b.Cross();",
            "        t.Cross();",
            "        a.Cross();",
            "        s.Cross();",
            "        m_M.Cross();",
            "        labels.Cross();",
            "        TStringArray.Cross();",
            "    }",
            "}",
        ]) + "\n"

        errors = _builtin_errors(source)

        self.assertEqual(list(range(12, 24)), [e["line"] for e in errors])
        messages = {e["line"]: e["message"] for e in errors}
        self.assertIn("'vector' is a built-in type", messages[13])
        self.assertIn("'a' is declared as array", messages[19])
        self.assertIn("Undefined function 'map.Cross'", messages[21])
        self.assertIn(
            "'labels' is declared as TStringArray, a typedef of array", messages[22]
        )
        self.assertIn("'TStringArray' is a typedef of array", messages[23])

    def test_unresolvable_receivers_are_skipped(self):
        cases = [
            # auto, and a template parameter
            "class FX_T<Class T>\n{\n    T m_Item;\n    void F()\n    {\n"
            "        auto x = 1;\n        x.Cross();\n        m_Item.Cross();\n"
            "    }\n}\n",
            # two types in two branches
            "void F()\n{\n#ifdef FX_A\n    vector x;\n#else\n    FX_Other x;\n"
            "#endif\n    x.Cross();\n}\n",
            # a later declarator makes the name unknown
            "void F()\n{\n    vector a, x;\n    x.Cross();\n}\n",
            # an array of vectors, a typedef of int[], a typedef that is also
            # a class
            "void F(FX_Handle h, FX_ResourceName r)\n{\n    vector pts[2];\n"
            "    pts.Cross();\n    h.Cross();\n    r.Cross();\n}\n",
            # a foreach variable inside its loop
            "void F(TStringArray list)\n{\n    foreach (string s : list)\n    {\n"
            "        s.Cross();\n    }\n}\n",
            # a parameter of another method
            "class C\n{\n    void G(vector m_P)\n    {\n    }\n    void F()\n"
            "    {\n        m_P.Cross();\n    }\n}\n",
            # this and super
            "class C\n{\n    void F()\n    {\n        this.Cross();\n"
            "        super.Cross();\n    }\n}\n",
            # lines that never compile
            "void F(vector v)\n{\n#if 0\n    v.Cross(v);\n#endif\n}\n",
            "#define FX_ON\nvoid F(vector v)\n{\n#ifndef FX_ON\n    v.Cross(v);\n"
            "#endif\n}\n",
        ]
        for source in cases:
            self.assertEqual([], _builtin_errors(source), source)

    def test_any_declaration_of_the_type_counts(self):
        source = (
            "void F(vector v)\n{\n    v.Cross(v);\n    v.ToDebugString();\n"
            "    v.ClassName();\n    v.IsInherited(int);\n}\n"
        )

        # ToDebugString sits under #ifdef DIAG_DEVELOPER in the vanilla
        # class, ClassName and IsInherited in Class; Cross only in comments.
        self.assertEqual([3], [e["line"] for e in _builtin_errors(source)])
        modded = (
            "modded class vector\n{\n    vector Cross(vector v)\n    {\n"
            "        return v;\n    }\n}\n"
        )
        self.assertEqual([], _builtin_errors(modded + source))
        self.assertEqual(
            [], _builtin_errors(source, [("scripts/1_Core/m.c", modded)])
        )

    def test_a_template_list_read_across_parameters_is_unknown(self):
        # Measured on 2026-11-03: the lookup read `map<string, int> refunds`
        # from array's `<` to map's `>` and reported GetKey on an array.
        source = (
            "void F(array<ref FX_Claim> timeline, array<int> values, bool dirty, "
            "map<string, int> refunds)\n{\n    refunds.GetKey(0);\n"
            "    refunds.Contains(\"a\");\n}\n"
            "void G(map<string, int> counts, int n)\n{\n    counts.Contains(\"a\");\n"
            "    counts.Cross();\n}\n"
        )

        # G's map is read alone and still judged.
        self.assertEqual([9], [e["line"] for e in _builtin_errors(source)])

    def test_only_lines_for_one_dayz_build_are_left_out(self):
        # `#ifndef DAYZ_1_29` holds the code of every later build and is
        # judged; `#ifdef DAYZ_1_29` and the #else of `#ifndef` compile on
        # 1.29 alone, which the tree may not be.
        source = "\n".join([
            "void F(vector v)",
            "{",
            "#ifdef DAYZ_1_29",
            "    v.Cross(v);",
            "#else",
            "    v.Cross(v);",
            "#endif",
            "#ifndef DAYZ_1_29",
            "    v.Cross(v);",
            "#else",
            "    v.Cross(v);",
            "#endif",
            "#ifdef FX_OTHER_MOD",
            "    v.Cross(v);",
            "#endif",
            "}",
        ]) + "\n"

        self.assertEqual([6, 9, 14], [e["line"] for e in _builtin_errors(source)])

    def test_a_variable_that_never_compiles_hides_no_static_call(self):
        # `int vector` under `#if 0` left
        # `vector.Cross(` unjudged in the whole file.
        source = (
            "void F()\n{\n    vector.Cross(\"0 0 1\", \"0 1 0\");\n}\n"
            "#if 0\nint vector = 1;\n#endif\n"
        )

        self.assertEqual([3], [e["line"] for e in _builtin_errors(source)])

    def test_a_variable_named_as_the_type_is_no_static_call(self):
        # Measured on 2026-11-03: `Widget map = ...; map.ClearFlags(...)`. The
        # name fails as a variable (ES-VARIABLE-NAMED-AS-TYPE), not the call.
        source = (
            "void F(Widget root)\n{\n    Widget map = root;\n"
            "    map.ClearFlags(0);\n    vector.Cross(\"0 0 1\", \"0 1 0\");\n}\n"
        )

        self.assertEqual([5], [e["line"] for e in _builtin_errors(source)])

    def test_a_type_the_vanilla_tree_does_not_declare_is_not_judged(self):
        # The cast fixture's tree declares Class and Managed, no vector.
        source = "void F(vector v)\n{\n    v.Cross(v);\n}\n"

        errors, skipped = _builtin_check(source, vanilla=CAST / "vanilla")

        self.assertEqual([], errors)
        self.assertEqual([], skipped)


def _pbo_bytes(entries, properties=(("prefix", "scripts"), ("version", "4242"))):
    """An uncompressed PBO of (name, data[, packing]) entries."""
    header = bytearray(b"\x00" + struct.pack("<5I", 0x56657273, 0, 0, 0, 0))
    for key, value in properties:
        header.extend(key.encode("ascii") + b"\x00" + value.encode("ascii") + b"\x00")
    header.append(0)
    payload = bytearray()
    for item in entries:
        name, data = item[0], item[1]
        packing = item[2] if len(item) > 2 else 0
        header.extend(name.encode("ascii") + b"\x00")
        header.extend(struct.pack("<5I", packing, len(data), 0, 0, len(data)))
        payload.extend(data)
    header.extend(b"\x00" + struct.pack("<5I", 0, 0, 0, 0, 0))
    return bytes(header + payload + b"\x00" + b"\x5a" * 20)


BUILD_RULE = "VANILLA-ROOT-BUILD-MISMATCH"

# --game-root reads the game's scripts.pbo with the PBO reader of the sibling
# tool scripts/tools/dayz-vehicle-proxy-contract. Without that folder the
# validator reports the comparison as skipped, so the tests that need a PBO
# read are skipped too instead of failing.
_PBO_READER = vanilla_build._READER_ROOT / "vehicle_proxy" / "pbo.py"
needs_pbo_reader = unittest.skipUnless(
    _PBO_READER.is_file(),
    "needs scripts/tools/dayz-vehicle-proxy-contract/scripts/vehicle_proxy/pbo.py",
)


class TestVanillaRootBuild(unittest.TestCase):
    """--game-root: the vanilla tree against the game's own dta/scripts.pbo.

    The gate read the 1.30.164014 Exp extract
    while the game was 1.30.164200, and vector.Cross, which only the extract
    declares, passed.
    """

    FILES = {
        "1_Core/proto/fx_builtin.c": b"class Managed\n{\n}\n",
        "4_World/fx_world.c": b"class FX_World\n{\n}\n",
    }

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self._tmp.name)
        # Lower case on disk, as an extract can be; the PBO names keep theirs.
        self.vanilla = base / "scripts"
        for name, data in self.FILES.items():
            path = self.vanilla / name.lower()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (self.vanilla / "config.cpp").write_text("class CfgPatches\n{\n};\n")
        self.game = base / "DayZ"
        (self.game / "dta").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _install(self, files):
        """files: {name: data, or (data, packing)}."""
        entries = []
        for name, data in files.items():
            data = data if isinstance(data, tuple) else (data,)
            entries.append((name.replace("/", "\\"),) + data)
        (self.game / "dta" / "scripts.pbo").write_bytes(_pbo_bytes(entries))

    def _run(self, *extra):
        return script_validator.run(
            [str(FIXTURES / "empty"), "--vanilla-root", str(self.vanilla)] + list(extra)
        )

    def _build_warnings(self, result):
        return [w for w in result["warnings"] if w["rule_id"] == BUILD_RULE]

    def _build_skips(self, result):
        return [
            s for s in result["info"].get("skipped_checks", [])
            if s["rule_id"] == BUILD_RULE
        ]

    @needs_pbo_reader
    def test_the_game_scripts_match(self):
        self._install(self.FILES)

        code, result = self._run("--game-root", str(self.game))

        self.assertEqual(0, code)
        self.assertEqual([], self._build_warnings(result))
        build = result["info"]["vanilla_build"]
        self.assertTrue(build["matches"])
        self.assertEqual("4242", build["pbo_version"])
        self.assertEqual(2, build["files"])

    @needs_pbo_reader
    def test_another_tree_warns(self):
        changed = dict(self.FILES)
        changed["1_Core/proto/fx_builtin.c"] = b"class Managed\n{\n    int Cross();\n}\n"
        changed["4_World/fx_new.c"] = b"class FX_New\n{\n}\n"
        changed["config.bin"] = b"\x00raP"
        self._install(changed)

        code, result = self._run("--game-root", str(self.game))

        self.assertEqual(2, code)
        warnings = self._build_warnings(result)
        self.assertEqual(1, len(warnings))
        message = warnings[0]["message"]
        self.assertIn("1_Core/proto/fx_builtin.c", message)
        self.assertIn("4_World/fx_new.c", message)
        self.assertIn("header version 4242", message)
        self.assertIn("1 differ", message)
        self.assertEqual("WARN", warnings[0]["severity"])
        build = result["info"]["vanilla_build"]
        self.assertEqual(
            (3, 1, 1, 0, False),
            (build["files"], build["differ"], build["missing"], build["extra"],
             build["matches"]),
        )
        assert_standard_findings(self, result)

    @needs_pbo_reader
    def test_a_tree_with_files_the_game_lacks_warns(self):
        self._install({"4_World/fx_world.c": self.FILES["4_World/fx_world.c"]})

        _code, result = self._run("--game-root", str(self.game))

        self.assertEqual(1, len(self._build_warnings(result)))
        self.assertEqual(1, result["info"]["vanilla_build"]["extra"])

    @needs_pbo_reader
    def test_the_pbo_and_the_environment_name_the_game_too(self):
        self._install(self.FILES)
        pbo = self.game / "dta" / "scripts.pbo"

        _code, result = self._run("--game-root", str(pbo))
        self.assertTrue(result["info"]["vanilla_build"]["matches"])
        with mock.patch.dict(os.environ, {"DAYZ_GAME_ROOT": str(self.game)}):
            _code, result = self._run()
        self.assertTrue(result["info"]["vanilla_build"]["matches"])

    def test_without_a_game_nothing_is_compared(self):
        _code, result = self._run()

        self.assertNotIn("vanilla_build", result["info"])
        self.assertEqual([], self._build_warnings(result))
        self.assertEqual([], self._build_skips(result))

    @needs_pbo_reader
    def test_an_unreadable_game_is_skipped_not_judged(self):
        # No scripts.pbo under the folder.
        code, result = self._run("--game-root", str(self.game))
        self.assertEqual(0, code)
        self.assertIn("no dta/scripts.pbo under", self._build_skips(result)[0]["reason"])
        self.assertNotIn("vanilla_build", result["info"])
        # A compressed entry: the reader fails closed.
        self._install({"4_World/fx_world.c": (b"xx", 0x43707273)})
        _code, result = self._run("--game-root", str(self.game))
        self.assertIn("compressed", self._build_skips(result)[0]["reason"])
        self.assertEqual([], self._build_warnings(result))
        # No vanilla tree to compare.
        self._install(self.FILES)
        _code, result = script_validator.run(
            [str(FIXTURES / "empty"), "--game-root", str(self.game)]
        )
        self.assertIn("vanilla tree", self._build_skips(result)[0]["reason"])


if __name__ == "__main__":
    unittest.main()

