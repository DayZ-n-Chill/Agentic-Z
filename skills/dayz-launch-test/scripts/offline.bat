@echo off
REM [DESIGN] Build + deploy + launch a single DayZDiag in OFFLINE mode (no server).
REM Not covered by the infrastructure note - validate in-game.
REM Works only inside a session started by dayz-mcp's managed launcher: dayz-test.ps1 stops with
REM "Managed lifecycle environment is incomplete" unless that launcher set DAYZ_MCP_CLIENT_ID_JSON
REM and DAYZ_MCP_LEASE_TOKEN, so a plain double-click fails. Without dayz-mcp, use /dayz-launch-test.
setlocal
set MOD=__MODNAME__
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dayz-test.ps1" -Mod %MOD% -Mode offline -Build %*
echo.
pause
