"""Tests for prompts.py."""
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import ask_text, ask_yes_no, ask_select  # noqa: E402


class TestAskText(unittest.TestCase):
    def test_returns_user_input(self):
        with patch("builtins.input", return_value="MyMod"):
            self.assertEqual(ask_text("Mod name?"), "MyMod")

    def test_returns_default_on_empty(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(ask_text("Mod name?", default="Foo"), "Foo")

    def test_returns_input_when_default_provided(self):
        with patch("builtins.input", return_value="Bar"):
            self.assertEqual(ask_text("Mod name?", default="Foo"), "Bar")


class TestAskYesNo(unittest.TestCase):
    def test_y_is_yes(self):
        with patch("builtins.input", return_value="y"):
            self.assertTrue(ask_yes_no("ok?", default=False))

    def test_n_is_no(self):
        with patch("builtins.input", return_value="n"):
            self.assertFalse(ask_yes_no("ok?", default=True))

    def test_empty_uses_default_true(self):
        with patch("builtins.input", return_value=""):
            self.assertTrue(ask_yes_no("ok?", default=True))

    def test_empty_uses_default_false(self):
        with patch("builtins.input", return_value=""):
            self.assertFalse(ask_yes_no("ok?", default=False))


class TestAskSelect(unittest.TestCase):
    def test_picks_by_number(self):
        with patch("builtins.input", return_value="2"):
            self.assertEqual(
                ask_select("pick", ["alpha", "beta", "gamma"]), "beta"
            )

    def test_default_on_empty(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(
                ask_select("pick", ["alpha", "beta"], default="beta"), "beta"
            )

    def test_rejects_out_of_range_then_accepts_valid(self):
        with patch("builtins.input", side_effect=["9", "1"]):
            self.assertEqual(
                ask_select("pick", ["alpha", "beta"]), "alpha"
            )


if __name__ == "__main__":
    unittest.main()
