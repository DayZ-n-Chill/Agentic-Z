@echo off
REM Answer a vanilla DayZ question with checked path:line citations. Usage: ask.bat "<question>" [--grep] [--json]
REM See .claude\skills\dayz-ask\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-ask\ask.py" %*
