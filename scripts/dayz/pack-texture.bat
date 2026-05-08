@echo off
REM Thin wrapper around the /dayz-pack-texture skill. Forwards all arguments.
REM See .claude\skills\dayz-pack-texture\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-pack-texture\pack_texture.py" %*
