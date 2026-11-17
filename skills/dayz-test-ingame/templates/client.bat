@echo off
REM Launch only the CLIENT, connecting to a server already running on 127.0.0.1.
REM Use when the server is up and you only need to reconnect (faster iteration).
REM dayz-test.ps1 refuses client mode without the run to join: client.bat -RunId <run_id>
setlocal
set MOD=__MODNAME__
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dayz-test.ps1" -Mod %MOD% -Mode client %*
echo.
pause
