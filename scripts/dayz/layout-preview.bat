@echo off
REM Render a .layout to approximate PNGs at several screen sizes. Usage: layout-preview.bat <file.layout> [--sizes 1920x1080]
REM See .claude\skills\dayz-layout-preview\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-layout-preview\layout_preview.py" %*
