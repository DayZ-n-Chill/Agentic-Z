"""Tests for add_server.py: map aliases, mission refresh backups, serverDZ.cfg handling."""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_add_server_under_test", HERE / "add_server.py")
srv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(srv)


# --- map alias resolution ------------------------------------------------------

@pytest.mark.parametrize("instance", ["chernarus", "livonia", "sakhal"])
def test_instance_named_after_map_needs_no_flag(instance):
    assert srv.resolve_map_name(instance, None) == instance


def test_map_flag_wins_over_instance_name():
    assert srv.resolve_map_name("chernarus-hardcore", "chernarus") == "chernarus"


def test_free_form_instance_requires_map():
    with pytest.raises(SystemExit) as exc:
        srv.resolve_map_name("my-test-server", None)
    assert "--map" in str(exc.value.code)


@pytest.mark.parametrize(
    "alias, template",
    [
        ("chernarus", "dayzOffline.chernarusplus"),
        ("livonia", "dayzOffline.enoch"),
        ("sakhal", "dayzOffline.sakhal"),
        ("dayzOffline.namalsk", "dayzOffline.namalsk"),
    ],
)
def test_mission_template_resolution(alias, template):
    assert srv.resolve_mission_template(alias) == template


# --- ensure_mission / --refresh-mission ------------------------------------------

@pytest.fixture
def server_install(monkeypatch, tmp_path):
    root = tmp_path / "DayZServer"
    mission = root / "mpmissions" / "dayzOffline.chernarusplus"
    mission.mkdir(parents=True)
    (mission / "init.c").write_text("// vanilla", encoding="utf-8")
    monkeypatch.setattr(srv, "find_dayz_server", lambda: root)
    return root


def test_fresh_copy(server_install, tmp_path):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// vanilla"


def test_existing_mission_left_alone_without_refresh(server_install, tmp_path):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// my edits", encoding="utf-8")
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// my edits"


def test_refresh_renames_old_mission_instead_of_deleting(server_install, tmp_path):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// my edits", encoding="utf-8")

    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=True, project_dir=project)

    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// vanilla"
    backups = list(mission_dir.parent.glob("mission.bak-*"))
    assert len(backups) == 1
    assert (backups[0] / "init.c").read_text(encoding="utf-8") == "// my edits"


def test_empty_mission_folder_is_copied_not_backed_up(server_install, tmp_path, capsys):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.mkdir(parents=True)
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// vanilla"
    assert not list(mission_dir.parent.glob("mission.bak-*"))
    out = capsys.readouterr().out
    assert "Copied" in out and "Refreshed" not in out and "Kept previous" not in out


def test_backup_names_never_collide(tmp_path):
    first = tmp_path / "mission"
    first.mkdir()
    a = srv.backup_mission(first)
    first.mkdir()
    b = srv.backup_mission(first)
    assert a != b and a.exists() and b.exists()


def test_unknown_template_lists_available(server_install, tmp_path):
    project = tmp_path / "project"
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.namalsk", project / "m", refresh=False, project_dir=project)
    assert "dayzOffline.chernarusplus" in str(exc.value.code)


# --- serverDZ.cfg ------------------------------------------------------------------

def test_default_cfg_written(tmp_path):
    srv.setup_instance_dir("chernarus", "dayzOffline.chernarusplus", tmp_path)
    cfg = (tmp_path / ".server" / "chernarus" / "serverDZ.cfg").read_text(encoding="utf-8")
    assert 'template = "dayzOffline.chernarusplus";' in cfg
    assert "allowFilePatching = 1;" in cfg
    assert (tmp_path / ".server" / "chernarus" / "Profiles").is_dir()
    assert (tmp_path / ".server" / "!ClientDiagLogs").is_dir()


def test_allow_file_patching_appended_to_existing_cfg(tmp_path):
    cfg_path = tmp_path / ".server" / "test" / "serverDZ.cfg"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text('hostname = "mine";\nmaxPlayers = 10;\n', encoding="utf-8")

    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)

    text = cfg_path.read_text(encoding="utf-8")
    assert text.startswith('hostname = "mine";\nmaxPlayers = 10;')
    assert text.endswith("allowFilePatching = 1;\n")


def test_existing_cfg_with_setting_on_unchanged(tmp_path):
    cfg_path = tmp_path / ".server" / "test" / "serverDZ.cfg"
    cfg_path.parent.mkdir(parents=True)
    original = 'hostname = "mine";\nallowFilePatching = 1;   // keep\n'
    cfg_path.write_text(original, encoding="utf-8")
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert cfg_path.read_text(encoding="utf-8") == original


def test_explicit_allow_file_patching_zero_is_turned_back_on(tmp_path):
    cfg_path = tmp_path / ".server" / "test" / "serverDZ.cfg"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text('hostname = "mine";\nallowFilePatching = 0;   // mine\n', encoding="utf-8")
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert cfg_path.read_text(encoding="utf-8") == 'hostname = "mine";\nallowFilePatching = 1;   // mine\n'


def test_cp1252_cfg_is_repaired_without_crashing_and_keeps_its_bytes(tmp_path):
    cfg_path = tmp_path / ".server" / "test" / "serverDZ.cfg"
    cfg_path.parent.mkdir(parents=True)
    hostname = 'hostname = "Café Zoë";'.encode("cp1252")
    cfg_path.write_bytes(hostname + b'\ntemplate = "dayzOffline.chernarusplus";\n')

    srv.gate_on_template_mismatch(cfg_path, "dayzOffline.chernarusplus", "test")
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)

    data = cfg_path.read_bytes()
    assert data.startswith(hostname)
    assert b"allowFilePatching = 1;" in data


def test_cp1252_cfg_still_refuses_a_template_mismatch(tmp_path):
    cfg_path = tmp_path / "serverDZ.cfg"
    cfg_path.write_bytes('hostname = "Zoë";\ntemplate = "dayzOffline.enoch";\n'.encode("cp1252"))
    with pytest.raises(SystemExit) as exc:
        srv.gate_on_template_mismatch(cfg_path, "dayzOffline.chernarusplus", "test")
    assert "dayzOffline.enoch" in str(exc.value.code)


def test_rerun_with_different_template_refuses(tmp_path):
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    cfg_path = tmp_path / ".server" / "test" / "serverDZ.cfg"
    with pytest.raises(SystemExit) as exc:
        srv.gate_on_template_mismatch(cfg_path, "dayzOffline.enoch", "test")
    msg = str(exc.value.code)
    assert "dayzOffline.chernarusplus" in msg and "--refresh-mission" in msg and "new instance" in msg


def test_rerun_with_same_template_or_no_cfg_passes(tmp_path):
    cfg_path = tmp_path / ".server" / "test" / "serverDZ.cfg"
    srv.gate_on_template_mismatch(cfg_path, "dayzOffline.enoch", "test")  # no cfg yet
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    srv.gate_on_template_mismatch(cfg_path, "dayzOffline.chernarusplus", "test")


def test_commented_template_line_is_ignored(tmp_path):
    cfg_path = tmp_path / "serverDZ.cfg"
    cfg_path.write_text('// template = "dayzOffline.enoch";\ntemplate = "dayzOffline.chernarusplus";\n', encoding="utf-8")
    srv.gate_on_template_mismatch(cfg_path, "dayzOffline.chernarusplus", "test")


def test_main_refuses_mismatch_before_copying(monkeypatch, tmp_path):
    srv.setup_instance_dir("chernarus", "dayzOffline.chernarusplus", tmp_path)
    monkeypatch.setattr(srv.h, "resolve_project_dir", lambda: tmp_path)
    monkeypatch.setattr(srv.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(srv, "ensure_mission", lambda *a, **k: pytest.fail("mission copied despite mismatch"))
    monkeypatch.setattr(srv.sys, "argv", ["add_server.py", "chernarus", "--map", "livonia"])
    with pytest.raises(SystemExit) as exc:
        srv.main()
    assert "dayzOffline.enoch" in str(exc.value.code)


def test_template_junction_failure_exits_non_zero(monkeypatch, tmp_path):
    (tmp_path / ".server" / "test" / "mission").mkdir(parents=True)
    monkeypatch.setattr(
        srv.subprocess, "run",
        lambda cmd, **k: srv.subprocess.CompletedProcess(cmd, 1, stdout="", stderr="Access is denied."),
    )
    with pytest.raises(SystemExit) as exc:
        srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert "Access is denied." in str(exc.value.code)


def test_template_junction_created_when_mission_present(monkeypatch, tmp_path):
    (tmp_path / ".server" / "test" / "mission").mkdir(parents=True)
    calls = []
    monkeypatch.setattr(
        srv.subprocess, "run",
        lambda cmd, **k: calls.append(cmd) or srv.subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert calls[0][:4] == ["cmd", "/c", "mklink", "/J"]
    assert calls[0][4].endswith("dayzOffline.chernarusplus")


@pytest.mark.parametrize("bad", ["", ".", "..", "..\\..\\x", "../x", "a/b", "C:x", "a*b", 'a"b'])
def test_map_rejects_paths(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError):
        srv.validate_map(bad)


@pytest.mark.parametrize("good", ["chernarus", "dayzOffline.namalsk", "dayzOffline.chernarusplus"])
def test_map_accepts_aliases_and_folder_names(good):
    assert srv.validate_map(good) == good


def test_main_rejects_map_path_before_any_work(monkeypatch, capsys):
    monkeypatch.setattr(srv.sys, "argv", ["add_server.py", "test", "--map", "..\\..\\x"])

    def must_not_run(*a, **k):
        raise AssertionError("nothing may run with a bad --map")

    monkeypatch.setattr(srv.h, "resolve_project_dir", must_not_run)
    with pytest.raises(SystemExit) as exc:
        srv.main()
    assert exc.value.code == 2
    assert "not a valid map" in capsys.readouterr().err


@pytest.mark.parametrize("bad", ["", ".", "..", "../x", "a/b", "a\\b", "C:x"])
def test_instance_name_rejects_paths(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError):
        srv.validate_instance(bad)


@pytest.mark.parametrize("bad", ["a*b", "a?b", 'a"b', "a<b", "a>b", "a|b"])
def test_instance_name_rejects_windows_forbidden_chars(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError, match="Windows forbids"):
        srv.validate_instance(bad)


@pytest.mark.parametrize("bad", ["!ClientDiagLogs", "!Health", "!mine"])
def test_instance_name_rejects_shared_bang_folders(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError, match="reserved"):
        srv.validate_instance(bad)


@pytest.mark.parametrize("bad", ["chernarus-behavior", "x-behavior"])
def test_instance_name_rejects_gate_behavior_copies(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError, match="dayz-gate"):
        srv.validate_instance(bad)


@pytest.mark.parametrize("good", ["chernarus", "chernarus-hardcore", "loot_test.2"])
def test_instance_name_accepts_folder_names(good):
    assert srv.validate_instance(good) == good


@pytest.mark.parametrize("bad", ["con", "NUL", "Aux", "prn", "com1", "LPT9", "nul.txt", "con.chernarus"])
def test_instance_name_rejects_windows_device_names(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError, match="reserved device name"):
        srv.validate_instance(bad)


@pytest.mark.parametrize("bad", ["chernarus.", "chernarus ", "test. "])
def test_instance_name_rejects_trailing_dot_or_space(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError, match="trailing dot or space"):
        srv.validate_instance(bad)


@pytest.mark.parametrize("bad", ["con", "COM3", "aux.enoch", "dayzOffline.namalsk.", "dayzOffline.namalsk "])
def test_map_rejects_windows_device_names_and_trailing_dot_or_space(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError, match="not a valid map"):
        srv.validate_map(bad)


@pytest.mark.parametrize("good", ["console", "nullmap", "com10", "auxiliary", "dayzOffline.con"])
def test_device_name_check_does_not_catch_lookalikes(good):
    assert srv.validate_instance(good) == good
    assert srv.validate_map(good) == good


@pytest.mark.parametrize("instance", ["Chernarus", "CHERNARUS", "Livonia"])
def test_instance_named_after_map_matches_any_case(instance):
    assert srv.resolve_map_name(instance, None) == instance.lower()


def test_map_alias_matches_any_case():
    assert srv.resolve_map_name("hardcore", "Sakhal") == "sakhal"
    assert srv.resolve_mission_template(srv.resolve_map_name("hardcore", "Sakhal")) == "dayzOffline.sakhal"


def test_custom_mission_folder_keeps_its_case():
    assert srv.resolve_map_name("ns", "dayzOffline.Namalsk") == "dayzOffline.Namalsk"


def test_shard_id_is_six_chars():
    cfg = srv.default_server_cfg("ab", "t")
    assert 'shardId = "abshar";' in cfg


def test_shard_id_keeps_only_alphanumerics():
    cfg = srv.default_server_cfg("a-b_c.d", "t")
    assert 'shardId = "abcdsh";' in cfg


@pytest.mark.parametrize("bad", ["-", "__", "-._"])
def test_instance_name_needs_a_letter_or_digit(bad):
    with pytest.raises(srv.argparse.ArgumentTypeError, match="letter or digit"):
        srv.validate_instance(bad)


@pytest.mark.parametrize("instance", ["-", "a", "abcdefgh"])
def test_shard_id_is_always_six_chars(instance):
    cfg = srv.default_server_cfg(instance, "t")
    shard = re.search(r'shardId = "([^"]*)";', cfg).group(1)
    assert len(shard) == 6 and shard.isalnum()


def test_commented_out_allow_file_patching_counts_as_missing(tmp_path):
    cfg_path = tmp_path / ".server" / "test" / "serverDZ.cfg"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text("// allowFilePatching = 1;\n", encoding="utf-8")
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert cfg_path.read_text(encoding="utf-8") == "// allowFilePatching = 1;\nallowFilePatching = 1;\n"


def test_existing_template_junction_reported_present(monkeypatch, tmp_path, capsys):
    inst = tmp_path / ".server" / "test"
    (inst / "mission").mkdir(parents=True)
    (inst / "dayzOffline.chernarusplus").mkdir()  # stands in for the junction
    monkeypatch.setattr(srv.subprocess, "run", lambda *a, **k: pytest.fail("must not recreate the junction"))
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert "Junction dayzOffline.chernarusplus/ -> mission/ already present" in capsys.readouterr().out
