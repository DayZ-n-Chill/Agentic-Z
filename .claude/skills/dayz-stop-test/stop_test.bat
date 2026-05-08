@echo off
REM /dayz-stop-test - force-kill all DayZDiag_x64.exe processes (server + client).
REM
REM Counterpart to /dayz-launch-test. NO preflight gate - this skill must work
REM even when the env is half-broken (P:\ unmounted, etc.). Always exits 0:
REM "no diag running" is a desired end state too.
taskkill /IM DayZDiag_x64.exe /F 2>nul
if %errorlevel% EQU 128 echo [OK]   No DayZDiag_x64.exe processes running.
exit /b 0
