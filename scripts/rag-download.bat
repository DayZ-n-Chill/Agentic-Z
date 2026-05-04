@echo off
REM Thin wrapper around the /dayz-rag-download skill. Forwards all arguments.
REM See .claude\skills\dayz-rag-download\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-rag-download\download.py" %*
