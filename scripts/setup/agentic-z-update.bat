@echo off
REM Thin wrapper around the /agentic-z-update skill. Forwards all arguments.
REM See .claude\skills\agentic-z-update\SKILL.md for full usage.
REM
REM PYTHONIOENCODING=utf-8 keeps any non-ASCII output (a file name, a git
REM message) from crashing the script on a cp1252 console.
set PYTHONIOENCODING=utf-8
python "%~dp0..\..\.claude\skills\agentic-z-update\update.py" %*
