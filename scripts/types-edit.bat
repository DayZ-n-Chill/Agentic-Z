@echo off
REM Thin wrapper around the /dayz-types-edit skill. Forwards all arguments.
REM See .claude\skills\dayz-types-edit\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-types-edit\types_edit.py" %*
