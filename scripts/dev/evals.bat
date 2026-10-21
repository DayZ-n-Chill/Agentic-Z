@echo off
REM Thin wrapper around the answer tests (evals) runner. Forwards all arguments.
REM Usage:
REM   evals.bat --dry-run                check the question files, ask nothing
REM   evals.bat --agent dayz-mod-reviewer  ask one agent its questions
REM   evals.bat --baseline               fail if any score fell below evals\baseline.json
REM See docs\evals.md for the question format and how evals gate a change.
python "%~dp0run_evals.py" %*
