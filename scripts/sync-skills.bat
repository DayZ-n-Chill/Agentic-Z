@echo off
REM Thin wrapper around the /sync-skills skill. Forwards all arguments.
REM See .claude\skills\sync-skills\SKILL.md for full usage.
python "%~dp0..\.claude\skills\sync-skills\sync.py" %*
