@echo off
REM Write a mod's health page from stored gate results. Usage: health.bat <ModName> | health.bat --all | health.bat record <ModName> <kind> [FILE]
REM See .claude\skills\dayz-health\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-health\health.py" %*
