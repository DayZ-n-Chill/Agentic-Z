"""Tests for add_server.py: map aliases, mission refresh backups, serverDZ.cfg handling."""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
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


def make_junction(link: Path, target: Path) -> None:
    """A real junction (mklink /J needs no admin rights)."""
    srv.subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, capture_output=True)
    assert srv.h.is_link(link)


def test_existing_template_junction_reported_present(monkeypatch, tmp_path, capsys):
    inst = tmp_path / ".server" / "test"
    (inst / "mission").mkdir(parents=True)
    make_junction(inst / "dayzOffline.chernarusplus", inst / "mission")
    monkeypatch.setattr(srv.subprocess, "run", lambda *a, **k: pytest.fail("must not recreate the junction"))
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert "Junction dayzOffline.chernarusplus/ -> mission/ already present" in capsys.readouterr().out


def test_dangling_junction_after_project_move_is_replaced(tmp_path, capsys):
    # The project used to live in old/; its junction now points at a folder that is gone.
    old_mission = tmp_path / "old" / "mission"
    old_mission.mkdir(parents=True)
    inst = tmp_path / "new" / ".server" / "test"
    (inst / "mission").mkdir(parents=True)
    (inst / "mission" / "init.c").write_text("// new", encoding="utf-8")
    junction = inst / "dayzOffline.chernarusplus"
    make_junction(junction, old_mission)
    old_mission.rmdir()
    assert not junction.exists() and srv.h.is_link(junction)  # dangling

    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path / "new")

    assert srv.h.paths_equal(srv.h.link_target(junction), inst / "mission")
    assert (junction / "init.c").read_text(encoding="utf-8") == "// new"
    out = capsys.readouterr().out
    assert "Removed stale junction" in out and "(template handshake)" in out


def test_junction_to_another_copy_is_replaced_and_the_copy_is_kept(tmp_path, capsys):
    other = tmp_path / "other-clone" / "mission"
    other.mkdir(parents=True)
    (other / "init.c").write_text("// other", encoding="utf-8")
    inst = tmp_path / ".server" / "test"
    (inst / "mission").mkdir(parents=True)
    junction = inst / "dayzOffline.chernarusplus"
    make_junction(junction, other)

    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)

    assert srv.h.paths_equal(srv.h.link_target(junction), inst / "mission")
    assert (other / "init.c").read_text(encoding="utf-8") == "// other"
    assert "already present" not in capsys.readouterr().out


def test_real_folder_at_template_name_is_refused_and_kept(monkeypatch, tmp_path):
    inst = tmp_path / ".server" / "test"
    (inst / "mission").mkdir(parents=True)
    real = inst / "dayzOffline.chernarusplus"
    real.mkdir()
    (real / "mine.txt").write_text("keep", encoding="utf-8")
    monkeypatch.setattr(srv.subprocess, "run", lambda *a, **k: pytest.fail("must not run mklink over a real folder"))
    with pytest.raises(SystemExit) as exc:
        srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert "real folder or file" in str(exc.value.code)
    assert (real / "mine.txt").read_text(encoding="utf-8") == "keep"


def test_stale_junction_that_cannot_be_removed_exits_non_zero(monkeypatch, tmp_path):
    inst = tmp_path / ".server" / "test"
    (inst / "mission").mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    make_junction(inst / "dayzOffline.chernarusplus", tmp_path / "elsewhere")

    def locked(path):
        raise PermissionError("in use")

    monkeypatch.setattr(srv, "remove_link", locked)
    with pytest.raises(SystemExit) as exc:
        srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert "could not be removed" in str(exc.value.code)


def test_refresh_with_locked_mission_exits_cleanly(monkeypatch, tmp_path):
    mission = tmp_path / "mission"
    mission.mkdir()
    (mission / "init.c").write_text("x", encoding="utf-8")

    def locked(self, target):
        raise PermissionError("The process cannot access the file")

    monkeypatch.setattr(srv.Path, "rename", locked)
    with pytest.raises(SystemExit) as exc:
        srv.backup_mission(mission)
    assert "/dayz-stop-test" in str(exc.value.code)
    assert (mission / "init.c").exists()


# --- failed mission copy never leaves a partial mission/ ---------------------------

def _failing_copytree(src, dst, *a, **k):
    Path(dst).mkdir(parents=True)
    (Path(dst) / "half.c").write_text("partial", encoding="utf-8")
    raise shutil.Error([(str(src), str(dst), "No space left on device")])


def test_failed_fresh_copy_leaves_no_partial_mission(server_install, tmp_path, monkeypatch):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    monkeypatch.setattr(srv.shutil, "copytree", _failing_copytree)
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert str(exc.value.code).startswith(srv.FAIL)
    assert not mission_dir.exists()
    assert not list(mission_dir.parent.glob("mission.tmp-*"))
    # A rerun must copy again, not report a broken mission as present.
    monkeypatch.undo()
    monkeypatch.setattr(srv, "find_dayz_server", lambda: server_install)
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// vanilla"


def test_failed_refresh_copy_keeps_existing_mission_in_place(server_install, tmp_path, monkeypatch):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// my edits", encoding="utf-8")
    monkeypatch.setattr(srv.shutil, "copytree", _failing_copytree)
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=True, project_dir=project)
    assert str(exc.value.code).startswith(srv.FAIL)
    assert "was not touched" in str(exc.value.code)
    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// my edits"
    assert not (mission_dir / "half.c").exists()
    assert not list(mission_dir.parent.glob("mission.tmp-*"))
    assert not list(mission_dir.parent.glob("mission.bak-*"))


def test_failed_swap_after_backup_names_the_backup(server_install, tmp_path, monkeypatch):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// my edits", encoding="utf-8")
    real_rename = srv.Path.rename

    def rename(self, target):
        if self.name.startswith("mission.tmp-"):
            raise PermissionError("Access is denied")
        return real_rename(self, target)

    monkeypatch.setattr(srv.Path, "rename", rename)
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=True, project_dir=project)
    backups = list(mission_dir.parent.glob("mission.bak-*"))
    assert len(backups) == 1
    assert (backups[0] / "init.c").read_text(encoding="utf-8") == "// my edits"
    assert backups[0].name in str(exc.value.code)
    assert not mission_dir.exists()
    assert not list(mission_dir.parent.glob("mission.tmp-*"))


def test_locked_empty_mission_exits_cleanly_and_removes_staged_copy(server_install, tmp_path, monkeypatch):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.mkdir(parents=True)  # empty: treated as missing, removed before the swap
    real_rmdir = srv.Path.rmdir

    def rmdir(self):
        if self.name == "mission":
            raise PermissionError("The process cannot access the file")
        return real_rmdir(self)

    monkeypatch.setattr(srv.Path, "rmdir", rmdir)
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert str(exc.value.code).startswith(srv.FAIL)
    assert "/dayz-stop-test" in str(exc.value.code)
    assert mission_dir.is_dir() and not any(mission_dir.iterdir())
    assert not list(mission_dir.parent.glob("mission.tmp-*"))


def test_locked_mission_on_refresh_removes_staged_copy(server_install, tmp_path, monkeypatch):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// my edits", encoding="utf-8")
    real_rename = srv.Path.rename

    def rename(self, target):
        if self.name == "mission":
            raise PermissionError("The process cannot access the file")
        return real_rename(self, target)

    monkeypatch.setattr(srv.Path, "rename", rename)
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=True, project_dir=project)
    assert "/dayz-stop-test" in str(exc.value.code)
    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// my edits"
    assert not list(mission_dir.parent.glob("mission.tmp-*"))


# --- interrupted copy, leftovers, mission/ that is not a folder ----------------------

def test_interrupted_copy_removes_the_staged_folder(server_install, tmp_path, monkeypatch):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"

    def interrupted(src, dst, *a, **k):
        Path(dst).mkdir(parents=True)
        (Path(dst) / "half.c").write_text("partial", encoding="utf-8")
        raise KeyboardInterrupt

    monkeypatch.setattr(srv.shutil, "copytree", interrupted)
    with pytest.raises(KeyboardInterrupt):
        srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert not list(mission_dir.parent.glob("mission.tmp-*"))
    assert not mission_dir.exists()


def test_leftover_staging_folder_is_reported(server_install, tmp_path, capsys):
    project = tmp_path / "project"
    inst = project / ".server" / "chernarus"
    leftover = inst / "mission.tmp-20260101-000000"
    leftover.mkdir(parents=True)
    srv.ensure_mission("dayzOffline.chernarusplus", inst / "mission", refresh=False, project_dir=project)
    out = capsys.readouterr().out
    assert srv.WARN in out and "mission.tmp-20260101-000000" in out and "interrupted run" in out
    assert leftover.is_dir()  # reported, never deleted


def test_mission_that_is_a_file_fails_cleanly(server_install, tmp_path):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    mission_dir.parent.mkdir(parents=True)
    mission_dir.write_text("not a folder", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    msg = str(exc.value.code)
    assert msg.startswith(srv.FAIL) and "not a folder" in msg
    assert mission_dir.read_text(encoding="utf-8") == "not a folder"


# --- the mission remembers which template it came from ---------------------------------

def test_copy_and_refresh_record_the_source_template(server_install, tmp_path):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "chernarus" / "mission"
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert srv.recorded_mission_template(mission_dir) == "dayzOffline.chernarusplus"

    enoch = server_install / "mpmissions" / "dayzOffline.enoch"
    enoch.mkdir()
    (enoch / "init.c").write_text("// enoch", encoding="utf-8")
    srv.ensure_mission("dayzOffline.enoch", mission_dir, refresh=True, project_dir=project)
    assert srv.recorded_mission_template(mission_dir) == "dayzOffline.enoch"
    backup = next(mission_dir.parent.glob("mission.bak-*"))
    assert srv.recorded_mission_template(backup) == "dayzOffline.chernarusplus"


def test_template_switch_without_refresh_is_refused(server_install, tmp_path, capsys):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "test" / "mission"
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.enoch", mission_dir, refresh=False, project_dir=project)
    msg = str(exc.value.code)
    assert "dayzOffline.chernarusplus" in msg and "--refresh-mission" in msg
    assert "Mission already present" not in capsys.readouterr().out


def test_same_template_rerun_is_accepted(server_install, tmp_path, capsys):
    project = tmp_path / "project"
    mission_dir = project / ".server" / "test" / "mission"
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=project)
    assert "Mission already present" in capsys.readouterr().out


def test_unmarked_mission_is_identified_by_its_old_junction(tmp_path):
    inst = tmp_path / ".server" / "test"
    mission_dir = inst / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// chernarus, copied before markers existed", encoding="utf-8")
    make_junction(inst / "dayzOffline.chernarusplus", mission_dir)
    with pytest.raises(SystemExit) as exc:
        srv.ensure_mission("dayzOffline.enoch", mission_dir, refresh=False, project_dir=tmp_path)
    assert "dayzOffline.chernarusplus/ junction" in str(exc.value.code)
    srv.ensure_mission("dayzOffline.chernarusplus", mission_dir, refresh=False, project_dir=tmp_path)


def test_hand_filled_mission_without_marker_or_junction_is_accepted(tmp_path, capsys):
    mission_dir = tmp_path / ".server" / "test" / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// mine", encoding="utf-8")
    srv.ensure_mission("dayzOffline.namalsk", mission_dir, refresh=False, project_dir=tmp_path)
    assert "Mission already present" in capsys.readouterr().out


def test_main_refuses_edited_cfg_template_without_refresh(server_install, monkeypatch, tmp_path):
    # The reviewer's case: cfg hand-edited to enoch, mission/ still holds Chernarus.
    inst = tmp_path / ".server" / "test"
    srv.ensure_mission("dayzOffline.chernarusplus", inst / "mission", refresh=False, project_dir=tmp_path)
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    cfg_path = inst / "serverDZ.cfg"
    cfg_path.write_text(
        cfg_path.read_text(encoding="utf-8").replace("dayzOffline.chernarusplus", "dayzOffline.enoch"),
        encoding="utf-8",
    )
    monkeypatch.setattr(srv.h, "resolve_project_dir", lambda: tmp_path)
    monkeypatch.setattr(srv.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(srv.sys, "argv", ["add_server.py", "test", "--map", "livonia"])
    with pytest.raises(SystemExit) as exc:
        srv.main()
    assert "--refresh-mission" in str(exc.value.code)
    assert not os.path.lexists(inst / "dayzOffline.enoch")


def test_template_switch_removes_the_old_junction(tmp_path, capsys):
    inst = tmp_path / ".server" / "test"
    mission_dir = inst / "mission"
    mission_dir.mkdir(parents=True)
    (mission_dir / "init.c").write_text("// enoch", encoding="utf-8")
    make_junction(inst / "dayzOffline.chernarusplus", mission_dir)

    srv.setup_instance_dir("test", "dayzOffline.enoch", tmp_path)

    assert srv.h.paths_equal(srv.h.link_target(inst / "dayzOffline.enoch"), mission_dir)
    assert not os.path.lexists(inst / "dayzOffline.chernarusplus")
    assert (mission_dir / "init.c").read_text(encoding="utf-8") == "// enoch"
    assert "Removed junction dayzOffline.chernarusplus/" in capsys.readouterr().out


def test_junction_to_another_folder_is_not_treated_as_an_old_template(tmp_path):
    inst = tmp_path / ".server" / "test"
    (inst / "mission").mkdir(parents=True)
    (tmp_path / "elsewhere").mkdir()
    make_junction(inst / "my-link", tmp_path / "elsewhere")
    make_junction(inst / "dayzOffline.chernarusplus", inst / "mission")
    srv.setup_instance_dir("test", "dayzOffline.chernarusplus", tmp_path)
    assert srv.h.is_link(inst / "my-link")
