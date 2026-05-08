@echo off
REM Open Object Builder. Thin wrapper around the dayz-launch-objectbuilder skill.
REM Usage:
REM   objectbuilder.bat                 open last-used file
REM   objectbuilder.bat --file <p3d>    open specific .p3d
REM   objectbuilder.bat --mod MyMod     set working dir to P:\MyMod\
python "%~dp0..\..\.claude\skills\dayz-launch-objectbuilder\launch.py" %*
