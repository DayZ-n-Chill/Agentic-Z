from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "dayz_ui_lab" / "corpus.py"
MANIFEST_PATH = Path(__file__).parents[1] / "corpora" / "manifest.json"
SPEC = importlib.util.spec_from_file_location("dayz_ui_lab_corpus", MODULE_PATH)
assert SPEC is not None
assert SPEC.loader is not None
corpus = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = corpus
SPEC.loader.exec_module(corpus)

LEAF_LAYOUT = (
    "FrameWidgetClass Root {\n"
    "    {\n"
    "        ButtonWidgetClass Leaf {\n"
    '            text "Leaf"\n'
    "        }\n"
    "    }\n"
    "}\n"
)
BROKEN_LAYOUT = "FrameWidgetClass Root {\n    position 0 0\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def codes(findings: list[dict[str, str]]) -> set[str]:
    return {item["code"] for item in findings}


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_every_corpus_declares_identity_and_licence(self) -> None:
        required = {
            "corpus_id",
            "name",
            "role",
            "local_root_id",
            "pin",
            "expected_layout_count",
            "expected_parse_ok",
            "license",
            "redistributed_in_pack",
        }
        for entry in self.manifest["corpora"]:
            with self.subTest(corpus=entry.get("corpus_id")):
                self.assertTrue(required.issubset(entry), sorted(required - set(entry)))
                self.assertIn("kind", entry["pin"])
                self.assertIn("redistribution", entry["license"])

    def test_no_corpus_is_marked_as_redistributed(self) -> None:
        # C5: the pack ships identity, never payload.
        for entry in self.manifest["corpora"]:
            with self.subTest(corpus=entry["corpus_id"]):
                self.assertFalse(entry["redistributed_in_pack"])

    def test_the_public_corpus_still_sums_to_the_pinned_319(self) -> None:
        public = {"vpp-admin-tools", "dayz-expansion", "traderplus-v1"}
        total = sum(
            int(e["expected_parse_ok"])
            for e in self.manifest["corpora"]
            if e["corpus_id"] in public
        )
        self.assertEqual(total, 319)
        traderx = next(e for e in self.manifest["corpora"] if e["corpus_id"] == "traderx")
        self.assertEqual(int(traderx["expected_parse_ok"]), 46)


class MissingRootTests(unittest.TestCase):
    def test_absent_local_roots_file_is_a_finding_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            roots, findings = corpus.resolve_roots(Path(temp_dir))
            self.assertEqual(roots, {})
            self.assertIn("CORPUS-LOCAL-ROOTS-MISSING", codes(findings))

    def test_an_unconfigured_corpus_is_reported_not_silently_skipped(self) -> None:
        # "not measured" and "passed" must not look alike.
        entry = {
            "corpus_id": "absent",
            "local_root_id": "nowhere",
            "expected_layout_count": 3,
            "expected_parse_ok": 3,
        }
        result, findings = corpus.measure_corpus(entry, {}, None)
        self.assertFalse(result["measured"])
        self.assertEqual(result["parse_ok"], 0)
        self.assertIn("CORPUS-ROOT-MISSING", codes(findings))

    def test_only_roots_this_manifest_uses_are_reported_unset(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write(
                root / "sources" / "local-roots.json",
                json.dumps(
                    {
                        "schema_version": 1,
                        "roots": {
                            "used_by_corpus": {"path_env": "PACK_TEST_UNSET_A"},
                            "unrelated": {"path_env": "PACK_TEST_UNSET_B"},
                        },
                    }
                ),
            )
            _, findings = corpus.resolve_roots(root, required={"used_by_corpus"})
            evidence = {item["evidence"] for item in findings}
            self.assertIn("used_by_corpus", evidence)
            self.assertNotIn("unrelated", evidence)


class ExpectationTests(unittest.TestCase):
    def _parser(self):
        return corpus._load_parser()

    def test_count_and_parse_mismatches_produce_distinct_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus"
            write(root / "a.layout", LEAF_LAYOUT)
            write(root / "b.layout", BROKEN_LAYOUT)

            entry = {
                "corpus_id": "synthetic",
                "local_root_id": "synthetic",
                "expected_layout_count": 5,
                "expected_parse_ok": 5,
            }
            result, findings = corpus.measure_corpus(
                entry, {"synthetic": root}, self._parser()
            )

            self.assertTrue(result["measured"])
            self.assertEqual(result["layouts_found"], 2)
            self.assertEqual(result["parse_ok"], 1)
            self.assertEqual(result["parse_failed"], 1)
            self.assertIn("CORPUS-COUNT-MISMATCH", codes(findings))
            self.assertIn("CORPUS-PARSE-REGRESSION", codes(findings))

    def test_meeting_the_expectation_produces_no_finding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "corpus"
            write(root / "a.layout", LEAF_LAYOUT)
            entry = {
                "corpus_id": "synthetic",
                "local_root_id": "synthetic",
                "expected_layout_count": 1,
                "expected_parse_ok": 1,
            }
            _, findings = corpus.measure_corpus(entry, {"synthetic": root}, self._parser())
            self.assertEqual(findings, [])


class ProvenanceAuditTests(unittest.TestCase):
    """The audit must be able to go RED; a green-only gate proves nothing."""

    def _pack(self, temp_dir: str) -> tuple[Path, Path]:
        pack = Path(temp_dir) / "pack"
        third_party = Path(temp_dir) / "third-party"
        write(pack / corpus.FIRST_PARTY_LAYOUT_DIR / "leaf.layout", LEAF_LAYOUT)
        write(third_party / "vendor.layout", "FrameWidgetClass Vendor {\n    {\n    }\n}\n")
        return pack, third_party

    def _entries(self) -> list[dict[str, object]]:
        return [
            {
                "corpus_id": "vendor",
                "role": "positive-external",
                "local_root_id": "vendor",
            }
        ]

    def test_clean_pack_passes_and_actually_counts_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack, third_party = self._pack(temp_dir)
            audit, findings = corpus.audit_redistribution(
                pack, self._entries(), {"vendor": third_party}
            )
            self.assertEqual(findings, [])
            # The count is the point: an audit that measures zero files reports
            # success for the wrong reason.
            self.assertEqual(audit["tracked_layouts"], 1)
            self.assertEqual(audit["third_party_layouts_compared"], 1)

    def test_a_planted_third_party_layout_is_caught_by_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack, third_party = self._pack(temp_dir)
            leaked = (third_party / "vendor.layout").read_text(encoding="utf-8")
            # Renamed and moved: the audit compares hashes, not paths.
            write(pack / corpus.FIRST_PARTY_LAYOUT_DIR / "innocent_name.layout", leaked)

            audit, findings = corpus.audit_redistribution(
                pack, self._entries(), {"vendor": third_party}
            )
            self.assertIn("CORPUS-THIRD-PARTY-REDISTRIBUTED", codes(findings))
            self.assertEqual(len(audit["leaked"]), 1)

    def test_a_layout_outside_the_first_party_directory_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack, third_party = self._pack(temp_dir)
            write(pack / "skills" / "dayz-ui" / "stray.layout", LEAF_LAYOUT)
            _, findings = corpus.audit_redistribution(
                pack, self._entries(), {"vendor": third_party}
            )
            self.assertIn("CORPUS-LAYOUT-OUTSIDE-FIRST-PARTY", codes(findings))

    def test_a_layout_under_the_scenario_fixture_directory_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack, third_party = self._pack(temp_dir)
            write(
                pack / "tools/dayz-ui-lab/fixtures/scenarios/green/card.layout",
                LEAF_LAYOUT,
            )
            _, findings = corpus.audit_redistribution(
                pack, self._entries(), {"vendor": third_party}
            )
            self.assertNotIn("CORPUS-LAYOUT-OUTSIDE-FIRST-PARTY", codes(findings))

    def test_a_layout_under_an_unlisted_third_directory_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack, third_party = self._pack(temp_dir)
            write(
                pack / "tools/dayz-ui-lab/fixtures/unlisted/stray.layout",
                LEAF_LAYOUT,
            )
            _, findings = corpus.audit_redistribution(
                pack, self._entries(), {"vendor": third_party}
            )
            self.assertIn("CORPUS-LAYOUT-OUTSIDE-FIRST-PARTY", codes(findings))

    def test_exclusions_apply_to_the_relative_path_not_the_absolute_one(self) -> None:
        # Regression: filtering on absolute path parts matched every file when the
        # pack itself lives under a directory named like an exclusion, so the audit
        # measured nothing while reporting success.
        with tempfile.TemporaryDirectory() as temp_dir:
            nested = Path(temp_dir) / "reports" / "pack"
            write(nested / corpus.FIRST_PARTY_LAYOUT_DIR / "leaf.layout", LEAF_LAYOUT)
            audit, _ = corpus.audit_redistribution(nested, [], {})
            self.assertEqual(audit["tracked_layouts"], 1)

    def test_generated_report_directories_are_still_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = Path(temp_dir) / "pack"
            write(pack / corpus.FIRST_PARTY_LAYOUT_DIR / "leaf.layout", LEAF_LAYOUT)
            write(pack / "reports" / "staged" / "generated.layout", LEAF_LAYOUT)
            audit, findings = corpus.audit_redistribution(pack, [], {})
            self.assertEqual(audit["tracked_layouts"], 1)
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
