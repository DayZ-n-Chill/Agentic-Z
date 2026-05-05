@echo off
REM Thin wrapper around the /dayz-search-wiki-index skill. Forwards all arguments.
REM See .claude\skills\dayz-search-wiki-index\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-search-wiki-index\index.py" %*
