"""Tests for stop_test.bat with a stub taskkill.cmd first on PATH (no real processes touched)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

BAT = Path(__file__).resolve().parent / "stop_test.bat"

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="stop_test.bat needs cmd.exe")


WRAPPER = Path(__file__).resolve().parents[3] / "scripts" / "dayz" / "stop-test.bat"


def _run_args(tmp_path: Path, bat: Path, *args: str) -> tuple[subprocess.CompletedProcess, Path]:
    """Run bat with args and a recording taskkill.cmd stub; returns the result and the stub's args file."""
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    (stub_dir / "taskkill.cmd").write_text(
        "@echo off\r\necho %* > \"%~dp0args.txt\"\r\nexit /b 128\r\n", encoding="ascii"
    )
    env = dict(os.environ, PATH=f"{stub_dir}{os.pathsep}{os.environ['PATH']}", TEMP=str(tmp_path))
    result = subprocess.run(["cmd", "/c", str(bat), *args], cwd=tmp_path, env=env, capture_output=True, text=True)
    return result, stub_dir / "args.txt"


@pytest.mark.parametrize("bat", [BAT, WRAPPER], ids=["skill", "wrapper"])
@pytest.mark.parametrize("flag", ["--help", "-h", "--HELP"])
def test_help_prints_usage_and_never_kills(tmp_path, bat, flag):
    # scripts/README.md promises --help on every wrapper; this one used to run taskkill instead.
    result, args_file = _run_args(tmp_path, bat, flag)
    assert result.returncode == 0
    assert "Usage: stop-test.bat" in result.stdout
    assert not args_file.exists(), "--help must not call taskkill"


def test_unknown_argument_is_refused_without_killing(tmp_path):
    result, args_file = _run_args(tmp_path, WRAPPER, "chernarus")
    assert result.returncode == 2
    assert "Unknown argument: chernarus" in result.stderr
    assert not args_file.exists()


def _run(tmp_path: Path, stub_rc: int, stub_err: str = "") -> subprocess.CompletedProcess:
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    lines = ["@echo off", "echo %* > \"%~dp0args.txt\""]
    if stub_rc == 0:
        lines.append("echo SUCCESS: The process \"DayZDiag_x64.exe\" with PID 1 has been terminated.")
    if stub_err:
        lines.append(f"echo {stub_err} 1>&2")
    lines.append(f"exit /b {stub_rc}")
    (stub_dir / "taskkill.cmd").write_text("\r\n".join(lines) + "\r\n", encoding="ascii")
    env = dict(os.environ, PATH=f"{stub_dir}{os.pathsep}{os.environ['PATH']}", TEMP=str(tmp_path))
    work = tmp_path / "cwd"
    work.mkdir()
    result = subprocess.run(
        ["cmd", "/c", str(BAT)], cwd=work, env=env, capture_output=True, text=True
    )
    assert (stub_dir / "args.txt").read_text().strip() == "/IM DayZDiag_x64.exe /F"
    return result


def test_processes_killed_exits_0(tmp_path):
    result = _run(tmp_path, 0)
    assert result.returncode == 0
    assert "SUCCESS:" in result.stdout
    assert "[FAIL]" not in result.stderr


def test_no_process_exits_0_and_drops_not_found_line(tmp_path):
    result = _run(tmp_path, 128, 'ERROR: The process "DayZDiag_x64.exe" not found.')
    assert result.returncode == 0
    assert "No DayZDiag_x64.exe processes running" in result.stdout
    assert "not found" not in result.stderr


def test_other_failure_reprints_error_and_returns_code(tmp_path):
    result = _run(tmp_path, 1, "ERROR: Access is denied.")
    assert result.returncode == 1
    assert "ERROR: Access is denied." in result.stderr
    assert "[FAIL] taskkill failed with errorlevel 1." in result.stderr


def test_temp_error_file_is_removed(tmp_path):
    _run(tmp_path, 1, "ERROR: Access is denied.")
    assert not list(tmp_path.glob("dayz-stop-test-*.err"))
