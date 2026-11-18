@echo off
REM Build the mod, then launch one DayZ Diag in offline mode (-mission, no server) with file patching.
REM Measured once on 1.30: the world loads, but whether a player spawns is not known. Use it to look around,
REM not to judge a mod; /dayz-gate ingame needs the server and client.
REM Usage: offline.bat <ModName> [more dayz_test.py options]
setlocal
if "%~1"=="" (
    echo Usage: %~nx0 ^<ModName^> [options]
    exit /b 2
)
python "%~dp0dayz_test.py" %* --mode offline --build
exit /b %ERRORLEVEL%
