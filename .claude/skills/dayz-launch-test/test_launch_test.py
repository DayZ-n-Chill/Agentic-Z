"""Tests for launch.py: server/client command lines and instance verification."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_launch_test_under_test", HERE / "launch.py")
launch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(launch)

DIAG = Path("C:/DayZ/DayZDiag_x64.exe")


# --- command builders -----------------------------------------------------------

def test_build_server_cmd():
    cmd = launch.build_server_cmd(
        DIAG, "P:\\Mods\\@A;P:\\Mods\\@B", 2402,
        Path("cfg/serverDZ.cfg"), Path("inst/Profiles"), Path("inst/dayzOffline.chernarusplus"),
    )
    assert cmd == [
        str(DIAG),
        "-server",
        f"-config={Path('cfg/serverDZ.cfg')}",
        f"-profiles={Path('inst/Profiles')}",
        f"-mission={Path('inst/dayzOffline.chernarusplus')}",
        "-mod=P:\\Mods\\@A;P:\\Mods\\@B",
        "-filePatching",
        "-port=2402",
    ]


def test_build_client_cmd_with_display_prefs():
    cmd = launch.build_client_cmd(
        DIAG, "P:\\Mods\\@A", 2302, Path("logs"), {"windowed": True, "width": 2560, "height": 1440}
    )
    assert cmd[:6] == [
        str(DIAG),
        f"-profiles={Path('logs')}",
        "-mod=P:\\Mods\\@A",
        "-connect=127.0.0.1",
        "-port=2302",
        "-filePatching",
    ]
    assert cmd[6:] == ["-window", "-x=2560", "-y=1440"]
    assert "-server" not in cmd


def test_build_client_cmd_fullscreen_without_size():
    cmd = launch.build_client_cmd(DIAG, "m", 2302, Path("logs"), {"windowed": False})
    assert not any(a in cmd for a in ("-window",)) and not any(a.startswith(("-x=", "-y=")) for a in cmd)


# --- verify_instance_environment ------------------------------------------------

def _instance(project: Path, name: str = "chernarus") -> Path:
    inst = project / ".server" / name
    (inst / "mission").mkdir(parents=True)
    (inst / "dayzOffline.chernarusplus").mkdir()  # stands in for the junction
    (inst / "serverDZ.cfg").write_text("allowFilePatching = 1;\n", encoding="utf-8")
    return inst


def test_verify_instance_returns_paths(tmp_path):
    inst = _instance(tmp_path)
    cfg, server_profiles, mission, client_profiles = launch.verify_instance_environment("chernarus", tmp_path)
    assert cfg == inst / "serverDZ.cfg"
    assert mission == inst / "dayzOffline.chernarusplus"
    assert server_profiles == inst / "Profiles" and server_profiles.is_dir()
    assert client_profiles == tmp_path / ".server" / "!ClientDiagLogs" and client_profiles.is_dir()


def test_verify_instance_missing_entirely(tmp_path):
    with pytest.raises(SystemExit) as exc:
        launch.verify_instance_environment("livonia", tmp_path)
    msg = str(exc.value.code)
    assert "serverDZ.cfg" in msg and "mission folder" in msg and "add_server.py livonia" in msg


def test_verify_instance_missing_template_junction(tmp_path):
    inst = _instance(tmp_path)
    (inst / "dayzOffline.chernarusplus").rmdir()
    with pytest.raises(SystemExit) as exc:
        launch.verify_instance_environment("chernarus", tmp_path)
    assert "template junction" in str(exc.value.code)


def test_verify_instance_appends_allow_file_patching(tmp_path):
    inst = _instance(tmp_path)
    (inst / "serverDZ.cfg").write_text('hostname = "x";\n', encoding="utf-8")
    launch.verify_instance_environment("chernarus", tmp_path)
    assert (inst / "serverDZ.cfg").read_text(encoding="utf-8").endswith("allowFilePatching = 1;\n")


# --- built mods and display prefs -------------------------------------------------

def test_verify_built_mods_requires_a_pbo(monkeypatch, tmp_path):
    monkeypatch.setattr(launch, "MODS_ROOT", tmp_path)
    (tmp_path / "@MyMod" / "Addons").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        launch.verify_built_mods(["MyMod"])
    assert "no .pbo" in str(exc.value.code)
    (tmp_path / "@MyMod" / "Addons" / "Other.pbo").write_bytes(b"")
    launch.verify_built_mods(["MyMod"])  # any .pbo name is accepted


def test_display_prefs_created_then_read(tmp_path):
    assert launch.read_client_display_prefs(tmp_path) == launch.DEFAULT_CLIENT_DISPLAY
    prefs = tmp_path / ".claude" / "local-memory" / launch.CLIENT_DISPLAY_PREFS_NAME
    prefs.write_text(json.dumps({"windowed": False}), encoding="utf-8")
    assert launch.read_client_display_prefs(tmp_path) == {"windowed": False}
