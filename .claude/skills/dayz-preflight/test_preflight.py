"""Tests for preflight.py: Steam library parsing, vanilla data lookup and the P:\\Mods junction rules.

No real P:\\ drive, registry or junctions: paths point at tmp_path and the junction
helpers are replaced with fakes.
"""
from __future__ import annotations

import importlib.util
import os
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
    assert preflight.find_vanilla_data() is None


def test_vanilla_data_ignores_dta(p_drive):
    # P:\dta is not a vanilla data folder; it used to count as one.
    (p_drive / "dta" / "data").mkdir(parents=True)
    assert preflight.find_vanilla_data() is None


def test_vanilla_scripts_found(p_drive):
    (p_drive / "scripts" / "3_game").mkdir(parents=True)
    assert preflight.find_vanilla_scripts() == p_drive / "scripts"


def test_vanilla_scripts_empty_or_missing(p_drive):
    assert preflight.find_vanilla_scripts() is None
    (p_drive / "scripts").mkdir()
    assert preflight.find_vanilla_scripts() is None


def test_check_vanilla_data_warns_when_scripts_missing(p_drive, capsys):
    # A partial extraction with P:\dz but no P:\scripts used to pass silently.
    (p_drive / "dz" / "data").mkdir(parents=True)
    preflight.check_vanilla_data()
    out = capsys.readouterr().out
    assert "[OK]    Vanilla data found" in out
    assert "[WARN]  Vanilla scripts not detected" in out


def test_check_vanilla_data_ok_with_scripts(p_drive, capsys):
    (p_drive / "dz" / "data").mkdir(parents=True)
    (p_drive / "scripts" / "3_game").mkdir(parents=True)
    preflight.check_vanilla_data()
    out = capsys.readouterr().out
    assert "[WARN]" not in out
    assert "Vanilla scripts found" in out


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
    monkeypatch.setattr(
        preflight, "link_target", lambda p: Path(links[str(p)]) if str(p) in links else None
    )
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
    assert preflight.main([]) == 1


def test_link_target_of_plain_folder_is_none(tmp_path):
    assert preflight.link_target(tmp_path) is None


def test_paths_equal_ignores_case_and_trailing_separator(tmp_path):
    assert preflight.paths_equal(tmp_path / "A" / "", tmp_path / "a") is (os.name == "nt")
    assert preflight.paths_equal(tmp_path / "x" / ".." / "y", tmp_path / "y")


# --- install resolution order ----------------------------------------------


def _make_tools(root: Path) -> Path:
    exe = root / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    return root


@pytest.fixture
def no_installs(monkeypatch):
    for var in ("DAYZ_TOOLS_PATH", "DAYZ_GAME_PATH", "DAYZ_DIAG_PATH", "DAYZ_SERVER_PATH"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(preflight, "read_registry_string", lambda *a: None)
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [])


def test_find_dayz_tools_env_beats_steam(no_installs, monkeypatch, tmp_path):
    env_root = _make_tools(tmp_path / "env")
    common = tmp_path / "common"
    _make_tools(common / "DayZ Tools")
    monkeypatch.setenv("DAYZ_TOOLS_PATH", str(env_root))
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [common])
    assert preflight.find_dayz_tools() == env_root


def test_find_dayz_tools_falls_back_to_steam_when_env_is_invalid(no_installs, monkeypatch, tmp_path):
    common = tmp_path / "common"
    steam_root = _make_tools(common / "DayZ Tools")
    monkeypatch.setenv("DAYZ_TOOLS_PATH", str(tmp_path / "missing"))
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [common])
    assert preflight.find_dayz_tools() == steam_root


def test_find_dayz_tools_none_when_nothing_matches(no_installs):
    assert preflight.find_dayz_tools() is None


@pytest.mark.skipif(os.name != "nt", reason="registry lookup only runs on Windows")
def test_find_dayz_tools_tries_every_registry_key(no_installs, monkeypatch, tmp_path):
    """A stale first registry entry must not stop later registry entries being tried."""
    good = _make_tools(tmp_path / "good")
    values = iter([str(tmp_path / "stale"), str(good), None])
    monkeypatch.setattr(preflight, "read_registry_string", lambda *a: next(values))
    assert preflight.find_dayz_tools() == good


def test_find_dayz_game_env_then_steam(no_installs, monkeypatch, tmp_path):
    env_root = tmp_path / "env"
    env_root.mkdir()
    (env_root / "DayZ_x64.exe").write_bytes(b"")
    common = tmp_path / "common"
    (common / "DayZ").mkdir(parents=True)
    (common / "DayZ" / "DayZ_x64.exe").write_bytes(b"")
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [common])

    assert preflight.find_dayz_game() == common / "DayZ"
    monkeypatch.setenv("DAYZ_GAME_PATH", str(env_root))
    assert preflight.find_dayz_game() == env_root


def test_find_dayz_diag_order(no_installs, monkeypatch, tmp_path):
    env_exe = tmp_path / "env" / "DayZDiag_x64.exe"
    game = tmp_path / "game"
    common = tmp_path / "common"
    for exe in (env_exe, game / "DayZDiag_x64.exe", common / "DayZ" / "DayZDiag_x64.exe"):
        exe.parent.mkdir(parents=True, exist_ok=True)
        exe.write_bytes(b"")
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [common])

    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    assert preflight.find_dayz_diag() == common / "DayZ" / "DayZDiag_x64.exe"

    monkeypatch.setattr(preflight, "find_dayz_game", lambda: game)
    assert preflight.find_dayz_diag() == game / "DayZDiag_x64.exe"

    monkeypatch.setenv("DAYZ_DIAG_PATH", str(env_exe))
    assert preflight.find_dayz_diag() == env_exe


def test_find_dayz_diag_env_folder_resolves_to_exe_inside(no_installs, monkeypatch, tmp_path):
    # A folder-valued DAYZ_DIAG_PATH used to be returned as-is, so /dayz-launch-test
    # tried to run a directory.
    folder = tmp_path / "DayZ"
    folder.mkdir()
    (folder / "DayZDiag_x64.exe").write_bytes(b"")
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    monkeypatch.setenv("DAYZ_DIAG_PATH", str(folder))
    assert preflight.find_dayz_diag() == folder / "DayZDiag_x64.exe"


def test_find_dayz_diag_ignores_env_folder_without_exe(no_installs, monkeypatch, tmp_path, capsys):
    folder = tmp_path / "DayZ"
    folder.mkdir()
    game = tmp_path / "game"
    game.mkdir()
    (game / "DayZDiag_x64.exe").write_bytes(b"")
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: game)
    monkeypatch.setenv("DAYZ_DIAG_PATH", str(folder))
    assert preflight.find_dayz_diag() == game / "DayZDiag_x64.exe"
    preflight.check_dayz_diag()
    out = capsys.readouterr().out
    assert f"[WARN]  DAYZ_DIAG_PATH ignored: {folder}" in out
    assert f"[OK]    DayZ Diag found: {game / 'DayZDiag_x64.exe'}" in out


def test_find_dayz_diag_ignores_env_file_with_wrong_name(no_installs, monkeypatch, tmp_path, capsys):
    retail = tmp_path / "DayZ_x64.exe"
    retail.write_bytes(b"")
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    monkeypatch.setenv("DAYZ_DIAG_PATH", str(retail))
    assert preflight.find_dayz_diag() is None
    preflight.check_dayz_diag()
    out = capsys.readouterr().out
    assert "DAYZ_DIAG_PATH ignored" in out
    assert "DayZ Diag (DayZDiag_x64.exe) not detected" in out


def test_find_dayz_diag_env_exe_name_is_case_insensitive(no_installs, monkeypatch, tmp_path):
    exe = tmp_path / "dayzdiag_x64.EXE"
    exe.write_bytes(b"")
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    monkeypatch.setenv("DAYZ_DIAG_PATH", str(exe))
    assert preflight.find_dayz_diag() == exe


def test_find_dayz_server_env_then_steam(no_installs, monkeypatch, tmp_path):
    env_root = tmp_path / "env"
    common = tmp_path / "common"
    for root in (env_root, common / "DayZServer"):
        root.mkdir(parents=True)
        (root / "DayZServer_x64.exe").write_bytes(b"")
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [common])

    assert preflight.find_dayz_server() == common / "DayZServer"
    monkeypatch.setenv("DAYZ_SERVER_PATH", str(env_root))
    assert preflight.find_dayz_server() == env_root


def test_check_dayz_diag_warns_when_missing(no_installs, monkeypatch, capsys):
    # Preflight used to pass silently without Diag; /dayz-launch-test then failed with
    # "DayZDiag_x64.exe not found".
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    preflight.check_dayz_diag()
    out = capsys.readouterr().out
    assert "[WARN]  DayZ Diag (DayZDiag_x64.exe) not detected" in out
    assert "DAYZ_DIAG_PATH" in out


def test_check_dayz_diag_ok(no_installs, monkeypatch, tmp_path, capsys):
    exe = tmp_path / "DayZDiag_x64.exe"
    exe.write_bytes(b"")
    monkeypatch.setenv("DAYZ_DIAG_PATH", str(exe))
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: None)
    preflight.check_dayz_diag()
    assert capsys.readouterr().out.strip() == f"[OK]    DayZ Diag found: {exe}"


def test_check_dayz_server_warns_when_missing(no_installs, capsys):
    # Preflight used to pass silently without DayZ Server; /dayz-add-server then failed with
    # "DayZ Server install not found".
    preflight.check_dayz_server()
    out = capsys.readouterr().out
    assert "[WARN]  DayZ Server (DayZServer_x64.exe) not detected" in out
    assert "223350" in out and "DAYZ_SERVER_PATH" in out


def test_check_dayz_server_ok(no_installs, monkeypatch, tmp_path, capsys):
    (tmp_path / "DayZServer_x64.exe").write_bytes(b"")
    monkeypatch.setenv("DAYZ_SERVER_PATH", str(tmp_path))
    preflight.check_dayz_server()
    assert capsys.readouterr().out.strip() == f"[OK]    DayZ Server found: {tmp_path}"


def test_main_runs_every_check_and_warnings_do_not_fail(monkeypatch):
    ran = []
    monkeypatch.setattr(preflight, "check_p_drive", lambda: ran.append("p") or True)
    for name in ("check_dayz_tools", "check_dayz_diag", "check_dayz_server",
                 "check_vanilla_data", "check_workshop_deploy"):
        monkeypatch.setattr(preflight, name, lambda n=name: ran.append(n))
    assert preflight.main([]) == 0
    assert ran == ["p", "check_dayz_tools", "check_dayz_diag", "check_dayz_server",
                   "check_vanilla_data", "check_workshop_deploy"]


def test_help_prints_usage_and_runs_no_check(monkeypatch, capsys):
    # scripts/README.md promises --help on preflight.bat; main() used to ignore it and run every
    # check, including check_workshop_deploy(), which can create the P:\Mods junction.
    for name in ("check_p_drive", "check_dayz_tools", "check_dayz_diag", "check_dayz_server",
                 "check_vanilla_data", "check_workshop_deploy"):
        monkeypatch.setattr(preflight, name, lambda n=name: pytest.fail(f"--help ran {n}"))
    with pytest.raises(SystemExit) as exc:
        preflight.main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "usage:" in out
    assert "DayZ preflight" not in out


# --- ignored *_PATH overrides and a missing !Workshop folder ----------------
# A wrong override used to be skipped silently (only DAYZ_DIAG_PATH warned), so the
# user saw "[OK] ... found: <Steam path>" and could not tell their setting had no effect.


def test_check_dayz_tools_warns_on_ignored_override(no_installs, monkeypatch, tmp_path, capsys):
    common = tmp_path / "common"
    steam_root = _make_tools(common / "DayZ Tools")
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [common])
    bad = tmp_path / "nope"
    monkeypatch.setenv("DAYZ_TOOLS_PATH", str(bad))
    preflight.check_dayz_tools()
    out = capsys.readouterr().out
    assert f"[WARN]  DAYZ_TOOLS_PATH ignored: {bad}" in out
    assert "AddonBuilder.exe" in out
    assert f"[OK]    DayZ Tools found: {steam_root}" in out


def test_check_dayz_tools_valid_override_does_not_warn(no_installs, monkeypatch, tmp_path, capsys):
    root = _make_tools(tmp_path / "tools")
    monkeypatch.setenv("DAYZ_TOOLS_PATH", str(root))
    preflight.check_dayz_tools()
    assert capsys.readouterr().out.strip() == f"[OK]    DayZ Tools found: {root}"


def test_check_dayz_server_warns_on_ignored_override(no_installs, monkeypatch, tmp_path, capsys):
    bad = tmp_path / "empty"
    bad.mkdir()
    monkeypatch.setenv("DAYZ_SERVER_PATH", str(bad))
    preflight.check_dayz_server()
    out = capsys.readouterr().out
    assert f"[WARN]  DAYZ_SERVER_PATH ignored: {bad}" in out
    assert "DayZServer_x64.exe" in out
    assert "DayZ Server (DayZServer_x64.exe) not detected" in out


def test_check_vanilla_data_warns_on_ignored_override(p_drive, monkeypatch, tmp_path, capsys):
    (p_drive / "dz" / "data").mkdir(parents=True)
    (p_drive / "scripts" / "3_game").mkdir(parents=True)
    bad = tmp_path / "empty_data"
    bad.mkdir()
    monkeypatch.setenv("DAYZ_VANILLA_DATA_PATH", str(bad))
    preflight.check_vanilla_data()
    out = capsys.readouterr().out
    assert f"[WARN]  DAYZ_VANILLA_DATA_PATH ignored: {bad}" in out
    assert f"[OK]    Vanilla data found: {p_drive / 'dz'}" in out


def test_check_workshop_deploy_warns_on_ignored_game_override(
    no_installs, p_drive, fake_junctions, monkeypatch, tmp_path, capsys
):
    common = tmp_path / "common"
    (common / "DayZ" / "!Workshop").mkdir(parents=True)
    (common / "DayZ" / "DayZ_x64.exe").write_bytes(b"")
    monkeypatch.setattr(preflight, "_steam_common_dirs", lambda: [common])
    bad = tmp_path / "nope"
    monkeypatch.setenv("DAYZ_GAME_PATH", str(bad))
    preflight.check_workshop_deploy()
    out = capsys.readouterr().out
    assert f"[WARN]  DAYZ_GAME_PATH ignored: {bad}" in out
    assert "DayZ_x64.exe" in out
    assert f"P:\\Mods -> {common / 'DayZ' / '!Workshop'}" in out


def test_absent_mods_with_game_but_no_workshop_names_the_folder(
    p_drive, monkeypatch, fake_junctions, tmp_path
):
    # Used to say "!Workshop folder was not found (set DAYZ_GAME_PATH ...)" although the
    # game path was right, and suggested an mklink that would fail on the missing target.
    _, created = fake_junctions
    root = tmp_path / "DayZ"
    root.mkdir()
    monkeypatch.setattr(preflight, "find_dayz_game", lambda: root)
    err = preflight.validate_p_mods()
    assert err and "does not exist yet" in err
    assert f'mkdir "{root / "!Workshop"}"' in err
    assert "DAYZ_GAME_PATH" not in err
    assert "mklink" not in err
    assert created == []
