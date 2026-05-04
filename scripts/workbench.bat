@echo off
REM Open Enfusion Workbench. Thin wrapper around the dayz-launch-workbench skill.
REM Usage:
REM   workbench.bat                     open vanilla project
REM   workbench.bat --mod MyMod         open per-mod project file
REM   workbench.bat --gproj <path>      open arbitrary .gproj
python "%~dp0..\.claude\skills\dayz-launch-workbench\launch.py" %*
