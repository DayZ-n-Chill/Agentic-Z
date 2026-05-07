"""Tests for detect.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from detect import (  # noqa: E402
    cwd,
    mod_name_from_cwd,
    mod_name_from_config_cpp,
    is_mod_dir,
)


class TestCwd(unittest.TestCase):
    def test_returns_path_object(self):
        self.assertIsInstance(cwd(), Path)

    def test_is_absolute(self):
        self.assertTrue(cwd().is_absolute())


class TestModNameFromCwd(unittest.TestCase):
    def test_returns_basename(self):
        with tempfile.TemporaryDirectory() as d:
            mod_dir = Path(d) / "MyTestMod"
            mod_dir.mkdir()
            self.assertEqual(mod_name_from_cwd(mod_dir), "MyTestMod")


class TestModNameFromConfigCpp(unittest.TestCase):
    def test_extracts_first_cfgpatches_class(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.cpp"
            cfg.write_text(
                'class CfgPatches {\n'
                '    class MyAwesomeMod {\n'
                '        units[] = {};\n'
                '    };\n'
                '};\n'
            )
            self.assertEqual(mod_name_from_config_cpp(Path(d)), "MyAwesomeMod")

    def test_returns_none_when_no_config(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(mod_name_from_config_cpp(Path(d)))

    def test_returns_none_when_config_has_no_cfgpatches(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config.cpp"
            cfg.write_text("// empty")
            self.assertIsNone(mod_name_from_config_cpp(Path(d)))


class TestIsModDir(unittest.TestCase):
    def test_true_when_config_cpp_exists(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "config.cpp").write_text("")
            self.assertTrue(is_mod_dir(Path(d)))

    def test_true_when_pboprefix_exists(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "$PBOPREFIX$").write_text("MyMod")
            self.assertTrue(is_mod_dir(Path(d)))

    def test_false_when_neither(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(is_mod_dir(Path(d)))


if __name__ == "__main__":
    unittest.main()
