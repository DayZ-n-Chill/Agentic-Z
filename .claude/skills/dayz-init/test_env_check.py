"""Tests for dayz-init/env_check.py. The preflight resolvers are mocked."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_check  # noqa: E402
from env_check import EnvIssue, Severity, classify  # noqa: E402


def _env(monkeypatch, mounted=True, tools=True, vanilla=True, p_mods_problem=None, mods_exists=False, game=True):
    monkeypatch.setattr(env_check, "p_drive_mounted", lambda: mounted)
    pf = env_check.preflight
    monkeypatch.setattr(pf, "find_dayz_tools", lambda: Path("C:/Tools") if tools else None)
    monkeypatch.setattr(pf, "find_vanilla_data", lambda: Path("P:/dz") if vanilla else None)
    monkeypatch.setattr(pf, "validate_p_mods", lambda: p_mods_problem)
    monkeypatch.setattr(pf, "find_dayz_game", lambda: Path("C:/DayZ") if game else None)
    monkeypatch.setattr(env_check.os.path, "lexists", lambda p: mods_exists)


def _names(issues):
    return [(i.name, i.severity) for i in issues]


def test_all_good(monkeypatch):
    _env(monkeypatch)
    assert env_check.run_all() == []


def test_unmounted_p_is_autofix_and_skips_p_checks(monkeypatch):
    _env(monkeypatch, mounted=False, vanilla=False, p_mods_problem="missing")
    assert _names(env_check.run_all()) == [("p_drive", Severity.AUTOFIX)]


def test_missing_tools_is_hard_stop_with_steam_link(monkeypatch):
    _env(monkeypatch, tools=False)
    [issue] = env_check.run_all()
    assert (issue.name, issue.severity) == ("dayz_tools", Severity.HARD_STOP)
    assert issue.fix_link.startswith("steam://")


def test_missing_vanilla_data_is_hard_stop(monkeypatch):
    _env(monkeypatch, vanilla=False)
    assert _names(env_check.run_all()) == [("vanilla_data", Severity.HARD_STOP)]


def test_absent_mods_junction_with_game_is_autofix(monkeypatch):
    _env(monkeypatch, p_mods_problem="P:\\Mods\\ does not exist", mods_exists=False, game=True)
    assert _names(env_check.run_all()) == [("mods_junction", Severity.AUTOFIX)]


def test_absent_mods_junction_without_game_is_hard_stop(monkeypatch):
    _env(monkeypatch, p_mods_problem="P:\\Mods\\ does not exist", mods_exists=False, game=False)
    assert _names(env_check.run_all()) == [("mods_junction", Severity.HARD_STOP)]


def test_wrong_shape_mods_folder_is_hard_stop_with_preflight_message(monkeypatch):
    _env(monkeypatch, p_mods_problem="P:\\Mods\\ exists as a regular folder", mods_exists=True)
    [issue] = env_check.run_all()
    assert issue.severity == Severity.HARD_STOP
    assert "regular folder" in issue.message


def test_classify_preserves_order():
    issues = [
        EnvIssue("a", Severity.AUTOFIX, "a"),
        EnvIssue("b", Severity.HARD_STOP, "b"),
        EnvIssue("c", Severity.AUTOFIX, "c"),
    ]
    autofix, hard = classify(issues)
    assert [i.name for i in autofix] == ["a", "c"]
    assert [i.name for i in hard] == ["b"]
