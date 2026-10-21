@echo off
REM Grant yourself COT admin on the test server. Thin wrapper, forwards all arguments.
REM See .claude\skills\dayz-cot-bootstrap\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-cot-bootstrap\bootstrap.py" %*
