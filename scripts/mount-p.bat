@echo off
REM Mount P:\ as the DayZ work drive. Thin wrapper around the dayz-mount-p skill.
REM Usage:
REM   mount-p.bat                       resolve and mount
REM   mount-p.bat --path "C:\Foo"       explicit work drive path
REM   mount-p.bat --unmount             unmount P:\
python "%~dp0..\.claude\skills\dayz-mount-p\mount.py" %*
