@echo off
REM Thin wrapper around the /agentic-z-update skill. Forwards all arguments.
REM See .claude\skills\agentic-z-update\SKILL.md for full usage.
REM
REM PYTHONIOENCODING=utf-8 protects against Windows cp1252 console crashes
REM on Unicode output (relevant for legacy update.py versions that printed
REM box characters; harmless for current versions).
set PYTHONIOENCODING=utf-8
python "%~dp0..\..\.claude\skills\agentic-z-update\update.py" %*
