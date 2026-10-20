@echo off
REM /dayz-stop-test - force-kill all DayZDiag_x64.exe processes (server + client).
REM No preflight gate: abort-only skills are the documented exception.
REM taskkill errorlevel 128 means "no such process", which is the desired end
REM state, so it maps to exit 0. Any other failure, such as access denied,
REM keeps taskkill's own error text and exits with its errorlevel.
taskkill /IM DayZDiag_x64.exe /F
set "RC=%errorlevel%"
if "%RC%"=="0" exit /b 0
if "%RC%"=="128" (
    echo [OK]   No DayZDiag_x64.exe processes running.
    exit /b 0
)
echo [FAIL] taskkill failed with errorlevel %RC%. 1>&2
exit /b %RC%
