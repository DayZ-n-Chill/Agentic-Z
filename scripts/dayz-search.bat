@echo off
REM Standalone CLI for the DayZ RAG index. Bypasses Claude / MCP entirely.
REM See scripts\dayz-search.py for full usage.
python "%~dp0dayz-search.py" %*
