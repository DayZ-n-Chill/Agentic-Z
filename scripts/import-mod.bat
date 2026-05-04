@echo off
REM Thin wrapper around the /dayz-import-mod skill. Forwards all arguments.
REM See .claude\skills\dayz-import-mod\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-import-mod\import_mod.py" %*
