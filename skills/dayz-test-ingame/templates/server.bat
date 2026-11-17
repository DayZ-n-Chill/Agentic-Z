@echo off
REM Build + deploy + launch SERVER and CLIENT (filepatching) for this mod.
REM Double-click to run. Pass extra args after the file, e.g.  server.bat -Mission livonia
setlocal
set MOD=__MODNAME__
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dayz-test.ps1" -Mod %MOD% -Mode all -Build %*
echo.
pause
