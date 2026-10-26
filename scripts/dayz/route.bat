@echo off
REM Show who should handle a request. Usage: route.bat "build MyVest"
REM See skills\dayz-route\SKILL.md for full usage.
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM If neither runs it prints one [FAIL] line and exits 9009. (call ) clears the
REM 9009 the python probe left, so a py.bat shim that sets no exit code still counts.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
REM PYTHONIOENCODING=utf-8 keeps a non-ASCII character in the output (a vanilla
REM line, a mod path) from crashing the script when its output is redirected.
REM setlocal keeps PY and PYTHONIOENCODING out of the terminal that ran this file.
setlocal
set PYTHONIOENCODING=utf-8
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
if "%PY%"=="py" ((call ) & call py -c "" >nul 2>nul || (>&2 echo [FAIL] Python 3 not found: install it from python.org or add python/py to PATH& exit /b 9009))
%PY% "%~dp0..\..\skills\dayz-route\route.py" %*
