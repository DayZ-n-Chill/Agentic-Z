@echo off
REM Compare a mod's item stats with similar vanilla items and flag outliers. Usage: balance.bat <ModName> | balance.bat --mod-dir <folder>
REM See .claude\skills\dayz-balance\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-balance\balance.py" %*
