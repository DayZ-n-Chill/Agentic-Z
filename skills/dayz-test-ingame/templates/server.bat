@echo off
REM Build + deploy + launch SERVER and CLIENT (filepatching) for this mod.
REM Works only inside a session started by dayz-mcp's managed launcher: dayz-test.ps1 stops with
REM "Managed lifecycle environment is incomplete" unless that launcher set DAYZ_MCP_CLIENT_ID_JSON
REM and DAYZ_MCP_LEASE_TOKEN, so a plain double-click fails. Without dayz-mcp, use /dayz-launch-test.
REM Pass extra args after the file, e.g.  server.bat -Mission livonia
setlocal
set MOD=__MODNAME__
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dayz-test.ps1" -Mod %MOD% -Mode all -Build %*
echo.
pause
