@echo off
REM Thin wrapper around the /dayz-scope-clear skill. Forwards all arguments.
REM See .claude\skills\dayz-scope-clear\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-scope-clear\clear.py" %*
