@echo off
REM Thin wrapper around the /dayz-add-scaffold skill. Forwards all arguments.
REM See .claude\skills\dayz-add-scaffold\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-add-scaffold\add_scaffold.py" %*
