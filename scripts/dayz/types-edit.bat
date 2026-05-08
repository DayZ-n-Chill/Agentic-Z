@echo off
REM Thin wrapper around the /dayz-edit-types skill. Forwards all arguments.
REM See .claude\skills\dayz-edit-types\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-edit-types\types_edit.py" %*
