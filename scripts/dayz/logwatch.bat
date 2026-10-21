@echo off
REM Watch a test session's logs and triage each new error line. Usage: logwatch.bat [--server chernarus] [--until-closed]
REM See .claude\skills\dayz-logwatch\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-logwatch\logwatch.py" %*
