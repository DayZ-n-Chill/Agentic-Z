@echo off
REM Mount P:\ as the DayZ work drive. Pure PowerShell, no Python.
REM Usage:
REM   mount-p.bat                       resolve and mount
REM   mount-p.bat -Path "C:\Foo"        explicit work drive path
REM   mount-p.bat -Unmount              unmount P:\
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\.claude\skills\dayz-mount-p\mount.ps1" %*
