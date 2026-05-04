@echo off
REM Thin wrapper around the /dayz-build-pbo skill. Forwards all arguments.
REM See .claude\skills\dayz-build-pbo\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-build-pbo\build.py" %*
