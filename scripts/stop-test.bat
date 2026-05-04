@echo off
REM Kill any running DayZDiag_x64.exe processes (server + client).
REM Thin wrapper around the dayz-stop-test skill.
python "%~dp0..\.claude\skills\dayz-stop-test\stop_test.py" %*
