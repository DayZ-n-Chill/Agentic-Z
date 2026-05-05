@echo off
REM Thin wrapper around the /dayz-split-types skill. Forwards all arguments.
REM See .claude\skills\dayz-split-types\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-split-types\split.py" %*
