@echo off
REM Thin wrapper around the /dayz-add-server skill. Forwards all arguments.
REM See .claude\skills\dayz-add-server\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-add-server\add_server.py" %*
