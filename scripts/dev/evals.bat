@echo off
REM Thin wrapper around the answer tests (evals) runner. Forwards all arguments.
REM Usage:
REM   evals.bat --dry-run                check the question files, ask nothing
REM   evals.bat --agent dayz-mod-reviewer  ask one agent its questions
REM   evals.bat --baseline               fail if any score fell below evals\baseline.json
REM   evals.bat --update-baseline        record these scores in evals\baseline.json (refused on a drop or an error)
REM See docs\evals.md for the question format and how evals gate a change.
REM Uses python when it runs, otherwise the py launcher. Running it (not just
REM finding it) skips the Microsoft Store alias, which is on PATH but exits 9009.
REM "call" lets a python.bat or python.cmd shim (pyenv-win) return here.
REM setlocal keeps PY out of the terminal that ran this file.
setlocal
set "PY=python"
call python -c "" >nul 2>nul || set "PY=py"
%PY% "%~dp0run_evals.py" %*
