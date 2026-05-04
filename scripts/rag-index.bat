@echo off
REM Thin wrapper around the /dayz-rag-index skill. Forwards all arguments.
REM See .claude\skills\dayz-rag-index\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-rag-index\index.py" %*
