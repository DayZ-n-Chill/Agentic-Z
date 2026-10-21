@echo off
REM Copy a bundle's prebuilt PBOs into P:\Mods. Thin wrapper, forwards all arguments.
REM See .claude\skills\dayz-deploy-pbo\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-deploy-pbo\deploy.py" %*
