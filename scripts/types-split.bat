@echo off
REM Thin wrapper around the /dayz-types-split skill. Forwards all arguments.
REM See .claude\skills\dayz-types-split\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-types-split\split.py" %*
