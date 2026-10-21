@echo off
REM Pack GUI sprites into an imageset. Thin wrapper, forwards all arguments.
REM See .claude\skills\dayz-build-imageset\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-build-imageset\build_imageset.py" %*
