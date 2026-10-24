@echo off
REM Standalone CLI for the DayZ RAG index. Bypasses Claude / MCP entirely.
REM See scripts\dayz\dayz-search.py for full usage.
REM
REM PYTHONIOENCODING=utf-8 keeps a non-ASCII character in a vanilla snippet from
REM crashing the script when its output is redirected on a cp1252 console.
REM setlocal keeps the setting out of the terminal that ran this file.
setlocal
set PYTHONIOENCODING=utf-8
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0dayz-search.py" %*
