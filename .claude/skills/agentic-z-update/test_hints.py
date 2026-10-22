"""Tests for the user-facing hints update.py prints: the quiet hook nudge and the resolve command."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent))

import update  # noqa: E402
from update import FileStatus  # noqa: E402


class TestQuietNudgeNamesOnlyWhatApplies(unittest.TestCase):
    def _quiet(self, drift, sidx):
        with mock.patch.object(update, "search_index_update_available", return_value=sidx):
            return update.format_preview(drift, None, "a" * 40, quiet=True)

    def test_template_only(self):
        line = self._quiet({"x.md": FileStatus.SAFE_OVERWRITE}, None)
        self.assertIn("Run /agentic-z-update.", line)
        self.assertNotIn("/dayz-search-download", line)

    def test_index_only(self):
        line = self._quiet({}, ("v1", "v2"))
        self.assertIn("Run /dayz-search-download.", line)
        self.assertNotIn("/agentic-z-update", line)

    def test_both(self):
        line = self._quiet({"x.md": FileStatus.SAFE_OVERWRITE}, ("v1", "v2"))
        self.assertIn("Run /agentic-z-update and /dayz-search-download.", line)


class TestPerFileCommandRunsFromRepoRoot(unittest.TestCase):
    def test_path_resolves_from_repo_root(self):
        orig = os.getcwd()
        root = Path(update.__file__).resolve().parents[3]
        try:
            os.chdir(root)
            cmd = update.per_file_command()
            path = cmd.split('"')[1]
            self.assertTrue((root / path).is_file(), cmd)
            self.assertTrue(cmd.endswith("--per-file"))
        finally:
            os.chdir(orig)


if __name__ == "__main__":
    unittest.main()
