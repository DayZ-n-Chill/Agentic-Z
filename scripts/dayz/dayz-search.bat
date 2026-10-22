@echo off
REM Standalone CLI for the DayZ RAG index. Bypasses Claude / MCP entirely.
REM See scripts\dayz\dayz-search.py for full usage.
REM
REM PYTHONIOENCODING=utf-8 keeps a non-ASCII character in a vanilla snippet from
REM crashing the script when its output is redirected on a cp1252 console.
REM setlocal keeps the setting out of the terminal that ran this file.
setlocal
set PYTHONIOENCODING=utf-8
python "%~dp0dayz-search.py" %*
