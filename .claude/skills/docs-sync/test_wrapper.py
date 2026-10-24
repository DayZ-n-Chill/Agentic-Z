"""Tests that scripts/dev/docs-sync.bat forwards its arguments and exit code to sync.py,
and that the Stop hook in .claude/settings.json runs through it.

Runs against the real repository, read-only (--check and a usage error never write).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
REPO = HERE.parents[2]
BAT = REPO / "scripts" / "dev" / "docs-sync.bat"
SYNC = HERE / "sync.py"

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="the wrapper is a Windows .bat")


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=120)


def test_check_gives_the_same_exit_code_and_output_as_sync_py():
    via_bat = _run(["cmd", "/c", str(BAT), "--check"])
    direct = _run([sys.executable, str(SYNC), "--check"])
    assert via_bat.returncode == direct.returncode
    assert via_bat.stdout == direct.stdout


def test_usage_error_exits_2():
    result = _run(["cmd", "/c", str(BAT), "--dry-run"])
    assert result.returncode == 2
    assert "--dry-run" in result.stderr


def test_falls_back_to_py_when_python_is_not_on_path(tmp_path):
    # PATH holds System32 (for cmd) and a py.cmd stand-in, but no python.
    (tmp_path / "py.cmd").write_text("@echo off\r\necho py-called %*\r\nexit /b 3\r\n", encoding="utf-8")
    system32 = Path(os.environ["SystemRoot"]) / "System32"
    env = {**os.environ, "PATH": f"{tmp_path};{system32}"}
    result = subprocess.run(["cmd", "/c", str(BAT), "--map"], cwd=REPO, capture_output=True, text=True,
                            timeout=120, env=env)
    assert result.returncode == 3
    assert result.stdout.startswith("py-called ") and 'sync.py" --map' in result.stdout


def test_falls_back_to_py_when_python_is_the_store_alias(tmp_path):
    # The Microsoft Store alias is a python on PATH that only prints a hint and exits 9009.
    (tmp_path / "python.cmd").write_text("@echo off\r\necho Python was not found\r\nexit /b 9009\r\n", encoding="utf-8")
    (tmp_path / "py.cmd").write_text("@echo off\r\necho py-called %*\r\nexit /b 3\r\n", encoding="utf-8")
    system32 = Path(os.environ["SystemRoot"]) / "System32"
    env = {**os.environ, "PATH": f"{tmp_path};{system32}"}
    result = subprocess.run(["cmd", "/c", str(BAT), "--map"], cwd=REPO, capture_output=True, text=True,
                            timeout=120, env=env)
    assert result.returncode == 3
    assert result.stdout.startswith("py-called ") and 'sync.py" --map' in result.stdout


def _stop_hook_command() -> str:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    commands = [h["command"] for entry in settings["hooks"]["Stop"] for h in entry["hooks"]]
    docs_sync = [c for c in commands if "docs-sync" in c]
    assert len(docs_sync) == 1, commands
    return docs_sync[0]


def _git_bash():
    # Claude Code runs hooks with Git Bash. On PATH, System32's bash.exe (WSL) can come
    # first, and WSL drops CLAUDE_PROJECT_DIR, so prefer the bash that ships with Git.
    git = shutil.which("git")
    if git:
        candidate = Path(git).resolve().parents[1] / "bin" / "bash.exe"
        if candidate.is_file():
            return str(candidate)
    return shutil.which("bash")


BASH = _git_bash()


@pytest.mark.skipif(BASH is None, reason="Claude Code runs hook commands with Git Bash")
def test_stop_hook_runs_the_check_quietly_and_exits_0():
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(REPO)}
    result = subprocess.run([BASH, "-c", _stop_hook_command()], cwd=REPO, capture_output=True, text=True,
                            timeout=120, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "" or "systemMessage" in json.loads(result.stdout)


@pytest.mark.skipif(BASH is None, reason="Claude Code runs hook commands with Git Bash")
def test_stop_hook_falls_back_to_py_when_python_is_the_store_alias(tmp_path):
    # A bare `python` in the hook would hit the alias, print its hint and exit 9009 every Stop.
    (tmp_path / "python.cmd").write_text("@echo off\r\necho Python was not found\r\nexit /b 9009\r\n", encoding="utf-8")
    (tmp_path / "py.cmd").write_text("@echo off\r\necho py-called %*\r\nexit /b 0\r\n", encoding="utf-8")
    system32 = Path(os.environ["SystemRoot"]) / "System32"
    env = {**os.environ, "PATH": f"{tmp_path};{system32}", "CLAUDE_PROJECT_DIR": str(REPO)}
    result = subprocess.run([BASH, "-c", _stop_hook_command()], cwd=REPO, capture_output=True, text=True,
                            timeout=120, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("py-called ") and 'sync.py" --check --quiet' in result.stdout
