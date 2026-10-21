@echo off
REM Match log lines against known errors. Usage: triage.bat <log files...>
REM See .claude\skills\dayz-gate\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-gate\triage.py" %*
