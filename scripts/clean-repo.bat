@echo off
REM Wipe ALL template-managed artifacts across every domain. Thin wrapper around
REM the clean-repo skill. Defaults to interactive confirmation; pass --yes to skip.
REM Usage:
REM   clean-repo.bat                 prompt then wipe everything
REM   clean-repo.bat --yes           wipe immediately (no prompt)
REM   clean-repo.bat --dry-run       list what would be removed, don't remove
python "%~dp0..\.claude\skills\clean-repo\clean.py" %*
