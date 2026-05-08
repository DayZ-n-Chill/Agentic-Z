@echo off
REM Thin wrapper around the /dayz-search-download skill. Forwards all arguments.
REM See .claude\skills\dayz-search-download\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-search-download\download.py" %*
