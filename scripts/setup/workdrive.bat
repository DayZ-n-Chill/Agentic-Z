@echo off
REM Mount P:\ as the DayZ work drive (delegates to the Python skill).
REM Usage:
REM   workdrive.bat                       resolve and mount
REM   workdrive.bat --path "C:\Foo"       explicit work drive path
REM   workdrive.bat --unmount             unmount P:\
python "%~dp0..\..\.claude\skills\dayz-workdrive\mount.py" %*
