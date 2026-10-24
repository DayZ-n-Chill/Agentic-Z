@echo off
REM Open Enfusion Workbench. Thin wrapper around the dayz-launch-workbench skill.
REM Usage:
REM   workbench.bat                     open vanilla project
REM   workbench.bat --mod MyMod         open per-mod project file
REM   workbench.bat --gproj <path>      open arbitrary .gproj
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
REM setlocal keeps PY out of the terminal that ran this file.
setlocal
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0..\..\.claude\skills\dayz-launch-workbench\launch.py" %*
