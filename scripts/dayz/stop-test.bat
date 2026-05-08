@echo off
REM Kill any running DayZDiag_x64.exe processes (server + client).
REM Thin wrapper around the dayz-stop-test skill (which is itself a .bat
REM since the operation is a single taskkill call).
call "%~dp0..\..\.claude\skills\dayz-stop-test\stop_test.bat" %*
