@echo off
REM Snapshot vanilla classes and list mod classes a DayZ update affects. Usage: upgrade-guard.bat snapshot | upgrade-guard.bat check [ModName]
REM See .claude\skills\dayz-upgrade-guard\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-upgrade-guard\upgrade_guard.py" %*
