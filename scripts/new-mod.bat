@echo off
REM Thin wrapper around the /dayz-new-mod skill. Forwards all arguments.
REM See .claude\skills\dayz-new-mod\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-new-mod\new_mod.py" %*
