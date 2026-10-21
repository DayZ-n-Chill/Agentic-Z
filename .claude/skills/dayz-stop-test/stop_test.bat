@echo off
REM /dayz-stop-test - force-kill all DayZDiag_x64.exe processes (server + client).
REM No preflight gate: abort-only skills are the documented exception.
REM taskkill errorlevel 128 means "no such process", which is the desired end
REM state, so it maps to exit 0 and taskkill's "not found" ERROR line is dropped.
REM Any other failure, such as access denied, re-prints taskkill's own error
REM text on stderr and exits with its errorlevel.
REM `call` lets a taskkill.cmd stub (used by test_stop_test.py) return here;
REM it changes nothing for the real taskkill.exe.
setlocal
set "ERRFILE=%TEMP%\dayz-stop-test-%RANDOM%.err"
call taskkill /IM DayZDiag_x64.exe /F 2>"%ERRFILE%"
set "RC=%errorlevel%"
if not "%RC%"=="128" type "%ERRFILE%" 1>&2
del "%ERRFILE%" 2>nul
if "%RC%"=="0" exit /b 0
if "%RC%"=="128" (
    echo [OK]   No DayZDiag_x64.exe processes running.
    exit /b 0
)
echo [FAIL] taskkill failed with errorlevel %RC%. 1>&2
exit /b %RC%
