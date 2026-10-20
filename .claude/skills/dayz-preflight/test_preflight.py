"""Tests for preflight.py: Steam library parsing, vanilla data lookup and the P:\\Mods junction rules.

No real P:\\ drive, registry or junctions: paths point at tmp_path and the junction
helpers are replaced with fakes.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_preflight_under_test", HERE / "preflight.py")
preflight = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(preflight)


# --- libraryfolders.vdf ----------------------------------------------------

VDF = r'''"libraryfolders"
{
	"0"
	{
		"path"		"C:\\Program Files (x86)\\Steam"
		"label"		""
		"apps"
		{
			"221100"		"15000000000"
		}
	}
	"1"
	{
		"path"		"D:\\SteamLibrary"
	}
}
'''


def test_parse_library_folders_unescapes_backslashes():
    assert preflight.parse_library_folders(VDF) == [
        Path(r"C:\Program Files (x86)\Steam"),
        Path(r"D:\SteamLibrary"),
    ]


def test_parse_library_folders_ignores_other_keys():
    assert preflight.parse_library_folders('"label" "x"\n"contentid" "123"') == []


def test_registry_alias_kept():
    assert preflight._read_registry_string is preflight.read_registry_string


# --- find_vanilla_data -----------------------------------------------------

@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    drive.mkdir()
    monkeypatch.setattr(preflight, "P_DRIVE", drive)
    monkeypatch.setattr(preflight, "MODS_LINK", drive / "Mods")
    monkeypatch.delenv("DAYZ_VANILLA_DATA_PATH", raising=False)
    return drive


def test_vanilla_data_found_under_canonical_name(p_drive):
    (p_drive / "dz" / "data").mkdir(parents=True)
    assert preflight.find_vanilla_data() == p_drive / "dz"


def test_vanilla_data_skips_empty_dir(p_drive):
    (p_drive / "dz").mkdir()
    (p_drive / "dta" / "scripts").mkdir(parents=True)
    assert preflight.find_vanilla_data() == p_drive / "dta"


def test_vanilla_data_env_override_wins(p_drive, monkeypatch, tmp_path):
    (p_drive / "dz" / "data").mkdir(parents=True)
    custom = tmp_path / "custom"
    (custom / "data").mkdir(parents=True)
    monkeypatch.setenv("DAYZ_VANILLA_DATA_PATH", str(custom))
    assert preflight.find_vanilla_data() == custom


def test_vanilla_data_missing(p_drive):
    assert preflight.find_vanilla_data() is None


# --- validate_p_mods -------------------------------------------------------

@pytest.fixture
def game(monkeypatch, tmp_path):
    root = tmp_path / "DayZ"
    (root / "!Workshop").mkdir(parents=True)
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: root)
    return root


@pytest.fixture
def fake_junctions(monkeypatch):
    """Record junction creation and serve link targets from a dict."""
    links: dict[str, str] = {}
    created: list[tuple[Path, Path]] = []

    def create(link: Path, target: Path) -> None:
        created.append((link, target))
        link.mkdir()
        links[str(link)] = str(target)

    monkeypatch.setattr(preflight, "_create_junction", create)
    monkeypatch.setattr(preflight, "_read_link", lambda p: links.get(str(p)))
    return links, created


def test_absent_mods_is_created_to_workshop(p_drive, game, fake_junctions, capsys):
    links, created = fake_junctions
    assert preflight.validate_p_mods() is None
    assert created == [(p_drive / "Mods", game / "!Workshop")]
    assert "Created junction" in capsys.readouterr().out


def test_absent_mods_without_game_is_not_created(p_drive, monkeypatch, fake_junctions):
    _, created = fake_junctions
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    err = preflight.validate_p_mods()
    assert err and "does not exist" in err and "DAYZ_GAME_PATH" in err
    assert created == []


def test_absent_mods_create_failure_is_reported(p_drive, game, monkeypatch):
    def boom(link, target):
        raise OSError("Access is denied.")

    monkeypatch.setattr(preflight, "_create_junction", boom)
    err = preflight.validate_p_mods()
    assert err and "Access is denied." in err and "mklink /J" in err


def test_regular_folder_fails_and_is_left_alone(p_drive, game, fake_junctions):
    _, created = fake_junctions
    (p_drive / "Mods" / "@Something").mkdir(parents=True)
    err = preflight.validate_p_mods()
    assert err and "regular folder" in err
    assert created == []
    assert (p_drive / "Mods" / "@Something").is_dir()


def test_junction_to_workshop_passes(p_drive, game, fake_junctions):
    links, _ = fake_junctions
    (p_drive / "Mods").mkdir()
    links[str(p_drive / "Mods")] = str(game / "!Workshop")
    assert preflight.validate_p_mods() is None


def test_junction_elsewhere_fails(p_drive, game, fake_junctions, tmp_path):
    links, created = fake_junctions
    other = tmp_path / "Other" / "!Workshop"
    other.mkdir(parents=True)
    (p_drive / "Mods").mkdir()
    links[str(p_drive / "Mods")] = str(other)
    err = preflight.validate_p_mods()
    assert err and "points to" in err and str(game / "!Workshop") in err
    assert created == []


def test_dangling_junction_fails(p_drive, game, fake_junctions, tmp_path):
    links, _ = fake_junctions
    (p_drive / "Mods").mkdir()
    links[str(p_drive / "Mods")] = str(tmp_path / "gone")
    err = preflight.validate_p_mods()
    assert err and "dangling" in err


def test_unknown_game_accepts_workshop_named_target(p_drive, monkeypatch, fake_junctions, tmp_path):
    links, _ = fake_junctions
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    target = tmp_path / "Elsewhere" / "!Workshop"
    target.mkdir(parents=True)
    (p_drive / "Mods").mkdir()
    links[str(p_drive / "Mods")] = str(target)
    assert preflight.validate_p_mods() is None

    links[str(p_drive / "Mods")] = str(tmp_path / "Elsewhere")
    assert "points to" in preflight.validate_p_mods()


def test_check_workshop_deploy_prints_target(p_drive, game, fake_junctions, capsys):
    preflight.check_workshop_deploy()
    out = capsys.readouterr().out
    assert f"P:\\Mods -> {game / '!Workshop'}" in out


def test_main_fails_without_p_drive(monkeypatch, tmp_path):
    monkeypatch.setattr(preflight, "P_DRIVE", tmp_path / "missing")
    assert preflight.main() == 1
