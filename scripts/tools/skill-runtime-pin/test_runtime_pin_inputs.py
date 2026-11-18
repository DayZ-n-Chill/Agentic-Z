"""Unreadable grade and inspect-prompt inputs end in a FAIL JSON report, not a traceback."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent / "runtime_pin.py"

SKILL = """---
name: dayz-mod-workflow
description: Fixture workflow.
---

# Fixture body
"""

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is not on PATH")


def run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def run_pin(*args: str) -> subprocess.CompletedProcess[str]:
    if args and args[0] == "materialize" and "--skill" not in args:
        args = (*args, "--skill", "dayz-mod-workflow")
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@pytest.fixture
def task_root(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    skill = source / "skills" / "dayz-mod-workflow" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(SKILL, encoding="utf-8", newline="\n")
    run_git(source, "init", "-q")
    run_git(source, "config", "user.email", "fixture@example.invalid")
    run_git(source, "config", "user.name", "Fixture")
    run_git(source, "config", "core.autocrlf", "false")
    run_git(source, "add", "-A")
    run_git(source, "commit", "-qm", "fixture")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, check=True, capture_output=True, text=True
    ).stdout.strip()
    task = tmp_path / "task"
    result = run_pin("materialize", "--source", str(source), "--commit", commit, "--task-root", str(task))
    assert result.returncode == 0, result.stdout + result.stderr
    return task


def assert_fail_report(result: subprocess.CompletedProcess[str], code: str) -> None:
    assert result.returncode == 1, result.stderr
    assert "Traceback" not in result.stderr
    report = json.loads(result.stdout)
    assert report["verdict"] == "FAIL"
    assert [item["code"] for item in report["findings"]] == [code]


def test_grade_missing_transcript_is_a_fail_report(task_root: Path, tmp_path: Path) -> None:
    result = run_pin("grade", "--task-root", str(task_root), "--transcript", str(tmp_path / "missing.json"))
    assert_fail_report(result, "TRANSCRIPT-INVALID")


def test_grade_invalid_json_is_a_fail_report(task_root: Path, tmp_path: Path) -> None:
    transcript = tmp_path / "bad.json"
    transcript.write_text("{not json", encoding="utf-8")
    result = run_pin("grade", "--task-root", str(task_root), "--transcript", str(transcript))
    assert_fail_report(result, "TRANSCRIPT-INVALID")


def test_grade_string_injected_body_is_a_fail_report(task_root: Path, tmp_path: Path) -> None:
    transcript = tmp_path / "strings.json"
    transcript.write_text(
        json.dumps({"consumer": "codex", "exit_code": 0, "stdout": "", "injected_bodies": ["x"]}),
        encoding="utf-8",
    )
    result = run_pin("grade", "--task-root", str(task_root), "--transcript", str(transcript))
    assert_fail_report(result, "TRANSCRIPT-INVALID")


def test_inspect_prompt_missing_input_is_a_fail_report(task_root: Path, tmp_path: Path) -> None:
    result = run_pin(
        "inspect-prompt", "--task-root", str(task_root), "--prompt-input", str(tmp_path / "missing.txt")
    )
    assert_fail_report(result, "PROMPT-INPUT-INVALID")
