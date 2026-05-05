@echo off
REM Mount P:\ as the DayZ work drive. Pure PowerShell, no Python.
REM Usage:
REM   workdrive.bat                       resolve and mount
REM   workdrive.bat -Path "C:\Foo"        explicit work drive path
REM   workdrive.bat -Unmount              unmount P:\
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\.claude\skills\dayz-workdrive\mount.ps1" %*
