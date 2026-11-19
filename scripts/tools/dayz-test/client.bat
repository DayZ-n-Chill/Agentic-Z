@echo off
REM Launch only the DayZ Diag client, joining the server dayz_test.py started earlier (a fast reconnect).
REM Usage: client.bat <ModName> [more dayz_test.py options, e.g. --deps CF]
setlocal
if "%~1"=="" (
    echo Usage: %~nx0 ^<ModName^> [options]
    exit /b 2
)
python "%~dp0dayz_test.py" %* --mode client
exit /b %ERRORLEVEL%
