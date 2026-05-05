@echo off
REM Thin wrapper around the /dayz-search-index skill. Forwards all arguments.
REM See .claude\skills\dayz-search-index\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-search-index\index.py" %*
