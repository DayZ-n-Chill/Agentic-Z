@echo off
REM Find class name and path collisions with CF, COT, Expansion or other mods. Usage: conflict-check.bat <ModName> [--against CF ...] [--ingame]
REM See .claude\skills\dayz-conflict-check\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-conflict-check\conflict_check.py" %*
