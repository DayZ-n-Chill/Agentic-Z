"""Tests for dayz-scope-mod/scope.py: scope, re-scope and clear round trips
against a temporary project directory (never the real settings file)."""
from __future__ import annotations

import importlib.util
import json
import shutil
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
        _make_mod(tmp_path / "workspace" / name)
    return mod


def _make_mod(folder: Path) -> None:
    """A workspace folder with the $PBOPREFIX$ marker that makes it count as a mod."""
    folder.mkdir(parents=True)
    (folder / "$PBOPREFIX$").write_text(folder.name, encoding="utf-8")


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
        shutil.rmtree(tmp_path / "workspace" / name)
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
    _make_mod(tmp_path / "workspace" / "Mod[old]")
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


@pytest.mark.parametrize("name", ["Mod!Fix", "Mod#2"])
def test_bang_and_hash_mid_name_are_allowed(scope, tmp_path, name):
    _make_mod(tmp_path / "workspace" / name)
    assert scope.main([name]) == 0
    assert scope.main(["ModA"]) == 0
    assert f"Edit(/workspace/{name}/**)" in _deny(scope)


def test_preexisting_rule_is_not_recorded_and_survives_clear(scope):
    scope.SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    mine = "Edit(//p/ModB/**)"
    scope.SETTINGS_LOCAL.write_text(json.dumps({"permissions": {"deny": [mine]}}), encoding="utf-8")
    assert scope.main(["ModA"]) == 0
    state = json.loads(scope.SCOPE_STATE.read_text(encoding="utf-8"))
    assert mine not in state["denied_rules"]
    assert len(state["denied_rules"]) == 5
    assert _deny(scope).count(mine) == 1
    assert scope.main(["--clear"]) == 0
    assert _deny(scope) == [mine]


def test_status_reports_scope_and_rules(scope, capsys):
    assert scope.main(["--status"]) == 0
    assert "No active scope" in capsys.readouterr().out
    assert scope.main(["ModA"]) == 0
    capsys.readouterr()
    assert scope.main(["--status"]) == 0
    out = capsys.readouterr().out
    assert "Active scope: ModA" in out
    assert "Deny rules:   6" in out
    assert "  - Edit(/workspace/ModB/**)" in out


def test_unknown_mod_lists_known_mods_on_their_own_lines(scope, capsys):
    assert scope.main(["NoSuchMod"]) == 1
    lines = capsys.readouterr().err.splitlines()
    assert lines[0].endswith("NoSuchMod does not exist.")
    assert lines[1].strip() == "Known mods:"
    assert lines[2].strip() == "- ModA"


def _load_fresh():
    spec = importlib.util.spec_from_file_location("dayz_scope_mod_fresh", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_run_from_a_mod_subfolder_finds_the_project(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    memory = project / ".claude" / "local-memory"
    memory.mkdir(parents=True)
    (memory / "dayz-current-project.txt").write_text(str(project), encoding="utf-8")
    sub = project / "workspace" / "MyVest"
    sub.mkdir(parents=True)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(sub)
    mod = _load_fresh()
    assert mod.PROJECT_DIR == project.resolve()
    assert mod.WORKSPACE == project.resolve() / "workspace"
    assert mod.SETTINGS_LOCAL == project.resolve() / ".claude" / "settings.local.json"


@pytest.mark.parametrize("bad", ["{not json", '["a list"]', '{"denied_rules": "Edit(x)"}'])
@pytest.mark.parametrize("argv", [["ModA"], ["--clear"], ["--status"]])
def test_corrupt_scope_record_fails_and_changes_nothing(scope, capsys, bad, argv):
    scope.SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    original = json.dumps({"permissions": {"deny": ["Edit(/workspace/ModB/**)"]}})
    scope.SETTINGS_LOCAL.write_text(original, encoding="utf-8")
    scope.SCOPE_STATE.parent.mkdir(parents=True, exist_ok=True)
    scope.SCOPE_STATE.write_text(bad, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        scope.main(argv)
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "scope record" in captured.err
    assert "Nothing to clear" not in captured.out
    assert scope.SETTINGS_LOCAL.read_text(encoding="utf-8") == original
    assert scope.SCOPE_STATE.read_text(encoding="utf-8") == bad


@pytest.mark.parametrize(
    "bad", ['["a list"]', '{"permissions": []}', '{"permissions": {"deny": "Edit(x)"}}']
)
def test_settings_with_wrong_shape_fails_and_changes_nothing(scope, capsys, bad):
    scope.SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    scope.SETTINGS_LOCAL.write_text(bad, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        scope.main(["ModA"])
    assert exc.value.code == 1
    assert "permissions" in capsys.readouterr().err
    assert scope.SETTINGS_LOCAL.read_text(encoding="utf-8") == bad
    assert not scope.SCOPE_STATE.exists()


def _backups(mod) -> list[Path]:
    return sorted(mod.SCOPE_STATE.parent.glob("settings.local.json.*.bak"))


def test_settings_are_backed_up_before_each_change_without_replacing_older_backups(scope):
    scope.SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    original = json.dumps({"permissions": {"deny": ["Read(./.env)"]}})
    scope.SETTINGS_LOCAL.write_text(original, encoding="utf-8")
    assert scope.main(["ModA"]) == 0
    first = _backups(scope)
    assert len(first) == 1
    assert first[0].read_text(encoding="utf-8") == original
    scoped_a = scope.SETTINGS_LOCAL.read_text(encoding="utf-8")
    assert scope.main(["ModB"]) == 0
    both = _backups(scope)
    assert len(both) == 2
    assert first[0].read_text(encoding="utf-8") == original
    assert {b.read_text(encoding="utf-8") for b in both} == {original, scoped_a}


def test_unchanged_settings_are_not_rewritten_or_backed_up(scope):
    assert scope.main(["ModA"]) == 0
    assert _backups(scope) == []  # no file existed before the first run
    before = scope.SETTINGS_LOCAL.read_text(encoding="utf-8")
    assert scope.main(["ModA"]) == 0
    assert scope.SETTINGS_LOCAL.read_text(encoding="utf-8") == before
    assert _backups(scope) == []


@pytest.mark.parametrize("typed", ["moda", "MODA", "modA"])
def test_mod_name_matches_folder_case_insensitively(scope, capsys, typed):
    assert scope.main([typed]) == 0
    deny = _deny(scope)
    assert not any("ModA" in r or typed in r for r in deny)
    assert "Edit(/workspace/ModB/**)" in deny and "Edit(/workspace/ModC/**)" in deny
    state = json.loads(scope.SCOPE_STATE.read_text(encoding="utf-8"))
    assert state["active_mod"] == "ModA"
    out = capsys.readouterr().out
    assert "DayZ scope: ModA" in out
    assert "Sibling mods detected: 2 (ModB, ModC)" in out


def test_non_mod_folders_get_no_rules_and_do_not_block(scope, tmp_path, capsys):
    (tmp_path / "workspace" / "_archive").mkdir()
    (tmp_path / "workspace" / "old[1]").mkdir()
    (tmp_path / "workspace" / "CfgOnly").mkdir()
    (tmp_path / "workspace" / "CfgOnly" / "config.cpp").write_text("", encoding="utf-8")
    assert scope.main(["ModA"]) == 0
    deny = _deny(scope)
    assert not any("_archive" in r or "old[1]" in r for r in deny)
    assert "Edit(/workspace/CfgOnly/**)" in deny
    assert "left writable: _archive, old[1]" in capsys.readouterr().out


def test_clear_with_missing_settings_does_not_create_them_and_warns(scope, capsys):
    assert scope.main(["ModA"]) == 0
    scope.SETTINGS_LOCAL.unlink()
    capsys.readouterr()
    assert scope.main(["--clear"]) == 0
    out = capsys.readouterr().out
    assert not scope.SETTINGS_LOCAL.exists()
    assert not scope.SCOPE_STATE.exists()
    assert "Removed 0 deny rule(s)" in out
    assert "[WARN]" in out and "6 recorded rule(s)" in out and "does not exist" in out


def test_clear_warns_when_recorded_rules_were_removed_by_hand(scope, capsys):
    assert scope.main(["ModA"]) == 0
    data = json.loads(scope.SETTINGS_LOCAL.read_text(encoding="utf-8"))
    data["permissions"]["deny"] = data["permissions"]["deny"][2:]
    scope.SETTINGS_LOCAL.write_text(json.dumps(data), encoding="utf-8")
    capsys.readouterr()
    assert scope.main(["--clear"]) == 0
    out = capsys.readouterr().out
    assert "Removed 4 deny rule(s)" in out
    assert "2 recorded rule(s) were not in" in out
    assert _deny(scope) == []


def test_clear_with_all_rules_present_does_not_warn(scope, capsys):
    assert scope.main(["ModA"]) == 0
    capsys.readouterr()
    assert scope.main(["--clear"]) == 0
    assert "[WARN]" not in capsys.readouterr().out


def _fail_replace_into(monkeypatch, scope, target_name: str, *, after: int = 0) -> dict:
    """Make os.replace raise OSError when it moves a temp file onto target_name.

    The first `after` such calls still succeed, so a later write can be failed.
    Returns a switch: set ["on"] = False to let writes through again.
    """
    real_replace = scope.os.replace
    seen = {"n": 0, "on": True}

    def replace(src, dst):
        if seen["on"] and Path(dst).name == target_name:
            seen["n"] += 1
            if seen["n"] > after:
                raise PermissionError(13, "The process cannot access the file", str(dst))
        return real_replace(src, dst)

    monkeypatch.setattr(scope.os, "replace", replace)
    return seen


def _leftover_tmp(scope) -> list[Path]:
    """Temp files next to the settings file or in local-memory."""
    found = list(scope.SETTINGS_LOCAL.parent.glob("*.tmp"))
    if scope.SCOPE_STATE.parent.exists():
        found += list(scope.SCOPE_STATE.parent.glob("*.tmp"))
    return found


def test_failed_state_write_leaves_settings_untouched(scope, monkeypatch, capsys):
    _fail_replace_into(monkeypatch, scope, scope.SCOPE_STATE.name)
    assert scope.main(["ModA"]) == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err and str(scope.SCOPE_STATE) in err
    assert "Nothing was changed" in err
    assert not scope.SETTINGS_LOCAL.exists()
    assert not scope.SCOPE_STATE.exists()
    assert _leftover_tmp(scope) == []


def test_failed_settings_write_keeps_every_rule_recorded(scope, monkeypatch, capsys):
    assert scope.main(["ModA"]) == 0
    in_settings = _deny(scope)
    capsys.readouterr()
    switch = _fail_replace_into(monkeypatch, scope, scope.SETTINGS_LOCAL.name)
    assert scope.main(["ModB"]) == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err and str(scope.SETTINGS_LOCAL) in err
    assert "--clear" in err
    assert _leftover_tmp(scope) == []
    # The ModA-scope rules are still in settings and must still be recorded,
    # so --clear can remove them.
    assert _deny(scope) == in_settings
    recorded = json.loads(scope.SCOPE_STATE.read_text(encoding="utf-8"))["denied_rules"]
    assert set(in_settings) <= set(recorded)
    switch["on"] = False  # the cause is fixed
    assert scope.main(["--clear"]) == 0
    assert _deny(scope) == []


def test_failed_backup_leaves_settings_untouched(scope, monkeypatch, capsys):
    assert scope.main(["ModA"]) == 0
    before = scope.SETTINGS_LOCAL.read_text(encoding="utf-8")
    capsys.readouterr()

    def copy_fails(*_args, **_kwargs):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(scope.shutil, "copy2", copy_fails)
    assert scope.main(["ModB"]) == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "Could not back up" in err
    assert scope.SETTINGS_LOCAL.read_text(encoding="utf-8") == before
    assert _leftover_tmp(scope) == []


def test_failed_final_state_write_says_clear_still_works(scope, monkeypatch, capsys):
    assert scope.main(["ModA"]) == 0
    capsys.readouterr()
    # Let the first record write of the ModB run through, fail the second.
    _fail_replace_into(monkeypatch, scope, scope.SCOPE_STATE.name, after=1)
    assert scope.main(["ModB"]) == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "settings.local.json was updated" in err
    assert _leftover_tmp(scope) == []
    recorded = set(json.loads(scope.SCOPE_STATE.read_text(encoding="utf-8"))["denied_rules"])
    assert set(_deny(scope)) <= recorded


def test_failed_clear_write_keeps_rules_and_record(scope, monkeypatch, capsys):
    assert scope.main(["ModA"]) == 0
    in_settings = _deny(scope)
    capsys.readouterr()
    _fail_replace_into(monkeypatch, scope, scope.SETTINGS_LOCAL.name)
    assert scope.main(["--clear"]) == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "run --clear again" in err
    assert _deny(scope) == in_settings
    assert scope.SCOPE_STATE.exists()
    assert _leftover_tmp(scope) == []


def test_failed_record_delete_on_clear_fails_loudly(scope, monkeypatch, capsys):
    assert scope.main(["ModA"]) == 0
    capsys.readouterr()

    def unlink_fails():
        raise PermissionError(13, "Access is denied", str(scope.SCOPE_STATE))

    monkeypatch.setattr(scope, "_clear_state", unlink_fails)
    assert scope.main(["--clear"]) == 1
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "Delete the" in err
    assert _deny(scope) == []


def test_scope_record_is_written_atomically(scope):
    assert scope.main(["ModA"]) == 0
    leftovers = list(scope.SCOPE_STATE.parent.glob("*.tmp"))
    assert leftovers == []
