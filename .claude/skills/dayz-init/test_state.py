"""Tests for state.py."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from state import (  # noqa: E402
    cached_project_root,
    write_cached_project_root,
    is_setup_complete,
    read_state,
    write_state,
)


class TestCachedProjectRoot(unittest.TestCase):
    def test_returns_none_when_cache_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(cached_project_root(home=Path(d)))

    def test_returns_path_when_cache_present(self):
        with tempfile.TemporaryDirectory() as home:
            write_cached_project_root(Path("G:/repos/MyMod"), home=Path(home))
            result = cached_project_root(home=Path(home))
            self.assertEqual(result, Path("G:/repos/MyMod"))


class TestIsSetupComplete(unittest.TestCase):
    def test_false_for_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(is_setup_complete(Path(d)))

    def test_true_when_required_markers_present(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            (project / "$PBOPREFIX$").write_text("MyMod")
            (project / "config.cpp").write_text("class CfgPatches {};")
            (project / ".agentic-z").mkdir()
            (project / ".agentic-z" / "state.json").write_text("{}")
            self.assertTrue(is_setup_complete(project))


class TestReadWriteState(unittest.TestCase):
    def test_read_returns_empty_dict_when_missing(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(read_state(Path(d)), {})

    def test_write_then_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            write_state(project, {"rag": "skip", "last_build": "ok"})
            self.assertEqual(
                read_state(project),
                {"rag": "skip", "last_build": "ok"},
            )

    def test_write_creates_agentic_z_dir(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            write_state(project, {})
            self.assertTrue((project / ".agentic-z").is_dir())


if __name__ == "__main__":
    unittest.main()
