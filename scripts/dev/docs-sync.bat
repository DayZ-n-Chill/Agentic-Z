@echo off
REM Thin wrapper around the /docs-sync skill. Forwards all arguments.
REM See .claude\skills\docs-sync\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\docs-sync\sync.py" %*
