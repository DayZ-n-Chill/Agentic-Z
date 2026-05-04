@echo off
REM Thin wrapper around the /dayz-add-map skill. Forwards all arguments.
REM See .claude\skills\dayz-add-map\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-add-map\add_map.py" %*
