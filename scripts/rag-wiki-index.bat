@echo off
REM Thin wrapper around the /dayz-rag-wiki-index skill. Forwards all arguments.
REM See .claude\skills\dayz-rag-wiki-index\SKILL.md for full usage.
python "%~dp0..\.claude\skills\dayz-rag-wiki-index\index.py" %*
