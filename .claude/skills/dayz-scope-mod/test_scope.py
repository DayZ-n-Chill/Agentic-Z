"""Tests for dayz-scope-mod/scope.py: scope, re-scope and clear round trips
against a temporary project directory (never the real settings file)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent / "scope.py"


@pytest.fixture
def scope(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("dayz_scope_mod", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(mod, "WORKSPACE", tmp_path / "workspace")
    monkeypatch.setattr(mod, "SETTINGS_LOCAL", tmp_path / ".claude" / "settings.local.json")
    monkeypatch.setattr(
        mod, "SCOPE_STATE", tmp_path / ".claude" / "local-memory" / "dayz-active-scope.json"
    )
    monkeypatch.setattr(mod, "_game_workshop_dir", lambda: None)
    for name in ("ModA", "ModB", "ModC", ".hidden"):
        (tmp_path / "workspace" / name).mkdir(parents=True)
    return mod


def _deny(mod) -> list[str]:
    data = json.loads(mod.SETTINGS_LOCAL.read_text(encoding="utf-8"))
    return data.get("permissions", {}).get("deny", [])


def test_scope_writes_edit_rules_in_permission_syntax(scope):
    assert scope.main(["ModA"]) == 0
    deny = _deny(scope)
    assert deny == [
        "Edit(/workspace/ModB/**)",
        "Edit(//p/ModB/**)",
        "Edit(//p/Mods/@ModB/**)",
        "Edit(/workspace/ModC/**)",
        "Edit(//p/ModC/**)",
        "Edit(//p/Mods/@ModC/**)",
    ]
    # Write(path) rules are never consulted by Claude Code; Windows-style
    # backslash paths never match. Neither may appear.
    assert not any(r.startswith("Write(") or "\\" in r for r in deny)
    state = json.loads(scope.SCOPE_STATE.read_text(encoding="utf-8"))
    assert state["active_mod"] == "ModA"
    assert state["denied_rules"] == deny


def test_rescope_replaces_prior_rules_and_keeps_user_rules(scope):
    scope.SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    scope.SETTINGS_LOCAL.write_text(
        json.dumps({"permissions": {"deny": ["Read(./.env)"], "allow": ["Bash(ls)"]}}),
        encoding="utf-8",
    )
    assert scope.main(["ModA"]) == 0
    assert scope.main(["ModB"]) == 0
    deny = _deny(scope)
    assert "Read(./.env)" in deny
    assert not any("ModB" in r for r in deny)
    assert "Edit(/workspace/ModA/**)" in deny
    assert len(deny) == 1 + 6
    data = json.loads(scope.SETTINGS_LOCAL.read_text(encoding="utf-8"))
    assert data["permissions"]["allow"] == ["Bash(ls)"]


def test_clear_round_trip_restores_settings(scope):
    scope.SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    original = {"permissions": {"deny": ["Read(./.env)"]}}
    scope.SETTINGS_LOCAL.write_text(json.dumps(original), encoding="utf-8")
    assert scope.main(["ModA"]) == 0
    assert scope.main(["--clear"]) == 0
    assert json.loads(scope.SETTINGS_LOCAL.read_text(encoding="utf-8")) == original
    assert not scope.SCOPE_STATE.exists()
    # A second clear is a no-op.
    assert scope.main(["--clear"]) == 0


def test_single_mod_records_empty_scope(scope, tmp_path):
    for name in ("ModB", "ModC"):
        (tmp_path / "workspace" / name).rmdir()
    assert scope.main(["ModA"]) == 0
    assert _deny(scope) == []
    assert json.loads(scope.SCOPE_STATE.read_text(encoding="utf-8"))["denied_rules"] == []


def test_unknown_mod_fails_without_writing(scope, capsys):
    assert scope.main(["NoSuchMod"]) == 1
    assert "Known mods" in capsys.readouterr().err
    assert not scope.SETTINGS_LOCAL.exists()


@pytest.mark.parametrize("argv", [[], ["--clear", "--status"], ["ModA", "--clear"]])
def test_arguments_are_mutually_exclusive_and_required(scope, argv):
    with pytest.raises(SystemExit) as exc:
        scope.main(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize("name", ["Mod*", "Mod?", "Mod[1]", "!Mod", "#Mod"])
def test_mod_name_with_gitignore_metacharacter_is_refused(scope, capsys, name):
    assert scope.main([name]) == 1
    assert "pattern syntax" in capsys.readouterr().err
    assert not scope.SETTINGS_LOCAL.exists()


def test_sibling_with_metacharacter_is_refused(scope, tmp_path, capsys):
    (tmp_path / "workspace" / "Mod[old]").mkdir()
    assert scope.main(["ModA"]) == 1
    assert "Mod[old]" in capsys.readouterr().err
    assert not scope.SETTINGS_LOCAL.exists()


def test_real_workshop_folder_is_denied_in_posix_form(scope, monkeypatch):
    workshop = Path(r"C:\Program Files (x86)\Steam\steamapps\common\DayZ\!Workshop")
    monkeypatch.setattr(scope, "_game_workshop_dir", lambda: workshop)
    assert scope.main(["ModA"]) == 0
    deny = _deny(scope)
    assert "Edit(//c/Program Files (x86)/Steam/steamapps/common/DayZ/!Workshop/@ModB/**)" in deny
    assert "Edit(//c/Program Files (x86)/Steam/steamapps/common/DayZ/!Workshop/@ModC/**)" in deny
    assert len(deny) == 8
    assert scope.main(["--clear"]) == 0
    assert _deny(scope) == []


def test_posix_rule_path(scope):
    assert scope._posix_rule_path(Path(r"D:\Games\DayZ\!Workshop")) == "//d/Games/DayZ/!Workshop"
