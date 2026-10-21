@echo off
REM Find errors that would stop a mod loading, with PASS/FAIL. Usage: lint.bat <ModName> | lint.bat --mod-dir <folder>
REM See .claude\skills\dayz-lint\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-lint\lint.py" %*
