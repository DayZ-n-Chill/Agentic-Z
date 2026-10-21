@echo off
REM Print the active mod, PBO age, servers, DayZ Diag and search status.
REM See .claude\skills\dayz-init\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-init\hub_status.py" %*
