@echo off
REM Show who should handle a request. Usage: route.bat "build MyVest"
REM See .claude\skills\dayz-route\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-route\route.py" %*
