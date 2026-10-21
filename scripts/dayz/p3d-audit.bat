@echo off
REM Audit a .p3d model and its config. Thin wrapper, forwards all arguments.
REM See .claude\skills\dayz-p3d-audit\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-p3d-audit\scripts\audit_p3d.py" %*
