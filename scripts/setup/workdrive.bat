@echo off
REM Mount P:\ as the DayZ work drive (delegates to the Python skill).
REM Usage:
REM   workdrive.bat                       resolve and mount
REM   workdrive.bat --path "C:\Foo"       explicit work drive path
REM   workdrive.bat --unmount             unmount P:\ (refuses while DayZ Tools or DayZDiag runs)
REM   workdrive.bat --unmount --force     unmount anyway
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
REM setlocal keeps PY out of the terminal that ran this file.
setlocal
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0..\..\skills\dayz-workdrive\mount.py" %*
