@echo off
REM Thin wrapper around the /agentic-z-update skill. Forwards all arguments.
REM See .claude\skills\agentic-z-update\SKILL.md for full usage.
python "%~dp0..\.claude\skills\agentic-z-update\update.py" %*
