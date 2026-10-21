@echo off
REM Write the Workshop text, changelog, classname list and install notes. Usage: release-pack.bat <ModName> [--version 1.2.0] [--deps CF]
REM See .claude\skills\dayz-release-pack\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-release-pack\release_pack.py" %*
