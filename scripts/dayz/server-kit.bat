@echo off
REM Zip types entries, cfgeconomycore lines, load order and the public key. Usage: server-kit.bat <ModName> [--mission chernarus] [--deps CF]
REM See .claude\skills\dayz-server-kit\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-server-kit\server_kit.py" %*
