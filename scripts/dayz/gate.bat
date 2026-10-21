@echo off
REM Build, in-game or behavior check with PASS/FAIL. Usage: gate.bat build <ModName> | gate.bat ingame <ModName> | gate.bat behavior <ModName>
REM See .claude\skills\dayz-gate\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-gate\gate.py" %*
