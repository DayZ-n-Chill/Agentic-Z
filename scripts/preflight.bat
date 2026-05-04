@echo off
REM Thin wrapper around the /dayz-preflight skill. Forwards all arguments.
REM See .claude\skills\dayz-preflight\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-preflight\preflight.py" %*
