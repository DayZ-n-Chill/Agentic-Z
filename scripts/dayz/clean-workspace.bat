@echo off
REM Thin wrapper around the /dayz-clean-workspace skill. Forwards all arguments.
REM See .claude\skills\dayz-clean-workspace\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-clean-workspace\clean.py" %*
