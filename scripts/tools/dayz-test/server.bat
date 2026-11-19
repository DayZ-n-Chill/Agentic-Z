@echo off
REM Build the mod, then launch the DayZ Diag server and client with file patching (/dayz-build-pbo, /dayz-launch-test).
REM Usage: server.bat <ModName> [more dayz_test.py options, e.g. --deps CF --server chernarus]
REM Stop it with: python "%~dp0dayz_test.py" --kill
setlocal
if "%~1"=="" (
    echo Usage: %~nx0 ^<ModName^> [options]
    exit /b 2
)
python "%~dp0dayz_test.py" %* --mode all --build
exit /b %ERRORLEVEL%
