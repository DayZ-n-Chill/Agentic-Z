@echo off
REM Thin wrapper around the /agentic-z-update skill. Forwards all arguments.
REM See .claude\skills\agentic-z-update\SKILL.md for full usage.
REM
REM PYTHONIOENCODING=utf-8 keeps any non-ASCII output (a file name, a git
REM message) from crashing the script on a cp1252 console. setlocal keeps the
REM setting out of the terminal that ran this file.
setlocal
set PYTHONIOENCODING=utf-8
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0..\..\.claude\skills\agentic-z-update\update.py" %*
