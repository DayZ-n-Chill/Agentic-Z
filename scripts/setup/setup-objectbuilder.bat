@echo off
REM Thin wrapper around the /dayz-setup-objectbuilder skill. Forwards all arguments.
REM See .claude\skills\dayz-setup-objectbuilder\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-setup-objectbuilder\setup.py" %*
