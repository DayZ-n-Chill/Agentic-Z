@echo off
REM Open Object Builder. Thin wrapper around the dayz-launch-objectbuilder skill.
REM Usage:
REM   objectbuilder.bat                 open last-used file
REM   objectbuilder.bat --file <p3d>    open specific .p3d
REM   objectbuilder.bat --mod MyMod     set working dir to P:\MyMod\
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
REM setlocal keeps PY out of the terminal that ran this file.
setlocal
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0..\..\.claude\skills\dayz-launch-objectbuilder\launch.py" %*
