@echo off
REM Pre-fill a mod plan from a recipe (weapon, vest, craftable). Usage: recipe.bat vest MyVest [--parent SmershVest]
REM See .claude\skills\dayz-recipe\SKILL.md for full usage.
python "%~dp0..\..\.claude\skills\dayz-recipe\recipe.py" %*
