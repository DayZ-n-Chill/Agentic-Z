@echo off
REM Wipe ALL template-managed artifacts across every domain. Thin wrapper around
REM the clean-repo skill. Defaults to interactive confirmation; pass --yes to skip.
REM Usage:
REM   clean-repo.bat                 prompt then wipe everything
REM   clean-repo.bat --yes           wipe immediately (no prompt)
REM   clean-repo.bat --dry-run       list what would be removed, don't remove
REM   clean-repo.bat --keep-server   same, but keep .server/ configs and missions
REM   clean-repo.bat --yes --plan ID  wipe only if the plan still matches a dry run's Plan ID
REM   clean-repo.bat --other-project  allow cleaning a cached project that is not this checkout
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
REM setlocal keeps PY out of the terminal that ran this file.
setlocal
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0..\..\.claude\skills\clean-repo\clean.py" %*
