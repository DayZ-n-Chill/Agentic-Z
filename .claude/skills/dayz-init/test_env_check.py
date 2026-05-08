"""Tests for env_check.py."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from env_check import (  # noqa: E402
    EnvIssue,
    Severity,
    check_python,
    check_p_drive,
    check_dayz_tools,
    classify,
)


class TestCheckPython(unittest.TestCase):
    def test_current_python_is_ok(self):
        # Whatever python is running this test is by definition >=3.8
        issue = check_python()
        self.assertIsNone(issue)


class TestCheckPDrive(unittest.TestCase):
    def test_returns_autofix_when_unmounted(self):
        with patch("env_check._p_drive_mounted", return_value=False):
            issue = check_p_drive()
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, Severity.AUTOFIX)
            self.assertIn("P:\\", issue.message)


class TestCheckDayzTools(unittest.TestCase):
    def test_returns_hard_stop_when_missing(self):
        with patch("env_check._dayz_tools_installed", return_value=False):
            issue = check_dayz_tools()
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, Severity.HARD_STOP)
            self.assertIn("steam://", issue.fix_link)


class TestClassify(unittest.TestCase):
    def test_groups_issues_by_severity(self):
        issues = [
            EnvIssue("p", Severity.AUTOFIX, "P: missing"),
            EnvIssue("tools", Severity.HARD_STOP, "Tools missing", fix_link="steam://x"),
        ]
        autofix, hard_stop = classify(issues)
        self.assertEqual(len(autofix), 1)
        self.assertEqual(len(hard_stop), 1)
        self.assertEqual(autofix[0].name, "p")
        self.assertEqual(hard_stop[0].name, "tools")


if __name__ == "__main__":
    unittest.main()
