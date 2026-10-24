"""The scripts\\dayz Python wrappers must set PYTHONIOENCODING=utf-8.

Without it, Python writes redirected output in the console code page (cp1252), so
`ask.bat "..." > answer.txt` crashed with UnicodeEncodeError on any cited vanilla line
holding a character outside cp1252 (the arrow in bunkerbroadcastscheduler.c).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DAYZ = REPO / "scripts" / "dayz"
PY_WRAPPERS = sorted(p.name for p in DAYZ.glob("*.bat") if ".py" in p.read_text(encoding="utf-8", errors="replace"))
NO_ENCODING_ENV = ("PYTHONIOENCODING", "PYTHONUTF8", "PY")


def _clean_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k.upper() not in NO_ENCODING_ENV}


def test_every_python_wrapper_is_covered():
    # stop-test.bat (a taskkill .bat) is the only scripts\dayz wrapper without Python.
    assert len(PY_WRAPPERS) == len(list(DAYZ.glob("*.bat"))) - 1


@pytest.mark.skipif(sys.platform != "win32", reason="runs cmd.exe")
@pytest.mark.parametrize("name", PY_WRAPPERS)
def test_wrapper_sets_utf8_output_without_leaking(name, tmp_path):
    # A fake python.bat reports the encoding the real script would see; the caller's
    # terminal must not keep the setting after the wrapper returns (setlocal).
    (tmp_path / "python.bat").write_text("@echo off\r\necho ENC=%PYTHONIOENCODING%\r\n", encoding="ascii")
    system32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    env = _clean_env()
    env["PATH"] = f"{tmp_path};{system32}"
    line = f'call "{DAYZ / name}" --help & if defined PYTHONIOENCODING (echo ENC-LEAKED) else (echo ENC-CLEAN)'
    result = subprocess.run(f'cmd /d /s /c "{line}"', env=env, capture_output=True, text=True, timeout=30)
    lines = [out.strip() for out in result.stdout.splitlines()]
    assert "ENC=utf-8" in lines, f"{name} does not set PYTHONIOENCODING=utf-8: {result.stdout!r}"
    assert "ENC-CLEAN" in lines, f"{name} left PYTHONIOENCODING set in the calling terminal: {result.stdout!r}"


@pytest.mark.skipif(sys.platform != "win32", reason="runs cmd.exe")
@pytest.mark.skipif(not Path("P:/scripts/4_world/classes/bunkerbroadcastscheduler.c").is_file(),
                    reason="needs the vanilla scripts unpacked on P:")
def test_ask_bat_redirected_output_keeps_non_cp1252_line(tmp_path):
    # bunkerbroadcastscheduler.c:322 holds "→" (U+2192), which cp1252 cannot encode.
    out = tmp_path / "answer.txt"
    cmd = (f'"{DAYZ / "ask.bat"}" "minuteDiff wrap-around rollover" --grep --folder scripts --top-k 1'
           f' > "{out}" 2>&1')
    result = subprocess.run(f'cmd /d /s /c "{cmd}"', env=_clean_env(), timeout=300)
    text = out.read_text(encoding="utf-8")
    assert "UnicodeEncodeError" not in text, text[-800:]
    assert result.returncode == 0, text[-800:]
    assert "bunkerbroadcastscheduler.c" in text and "\u2192" in text, text[:1500]
