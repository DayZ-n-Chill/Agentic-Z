@echo off
REM Build, in-game, behavior or visual check with PASS/FAIL. Usage: gate.bat build <ModName> | gate.bat ingame <ModName> | gate.bat behavior <ModName> | gate.bat visual <ModName>
REM See .claude\skills\dayz-gate\SKILL.md for full usage.
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
REM setlocal keeps PY out of the terminal that ran this file.
setlocal
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0..\..\.claude\skills\dayz-gate\gate.py" %*
