@echo off
REM Thin wrapper around the /dayz-launch-test skill. Forwards all arguments.
REM See .claude\skills\dayz-launch-test\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-launch-test\launch.py" %*
