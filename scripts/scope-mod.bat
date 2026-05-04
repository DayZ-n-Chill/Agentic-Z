@echo off
REM Thin wrapper around the /dayz-scope-mod skill. Forwards all arguments.
REM See .claude\skills\dayz-scope-mod\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-scope-mod\scope.py" %*
