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
CFG = 'class Missions { class DayZ { template = "dayzOffline.chernarusplus"; }; };\n'


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

FP = "allowFilePatching = 1;\n"


def _instance(project: Path, name: str = "chernarus") -> Path:
    inst = project / ".server" / name
    (inst / "mission").mkdir(parents=True)
    (inst / "dayzOffline.chernarusplus").mkdir()  # stands in for the junction
    (inst / "serverDZ.cfg").write_text(CFG + FP, encoding="utf-8")
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
    assert "serverDZ.cfg" in msg and "mission folder" in msg and "/dayz-add-server livonia" in msg


def test_verify_instance_missing_template_junction(tmp_path):
    inst = _instance(tmp_path)
    (inst / "dayzOffline.chernarusplus").rmdir()
    with pytest.raises(SystemExit) as exc:
        launch.verify_instance_environment("chernarus", tmp_path)
    assert "template junction" in str(exc.value.code)


@pytest.mark.parametrize("tail", ["", "allowFilePatching = 0;\n", "// allowFilePatching = 1;\n"])
def test_verify_instance_refuses_without_active_file_patching(tmp_path, tail):
    inst = _instance(tmp_path)
    (inst / "serverDZ.cfg").write_text(CFG + tail, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        launch.verify_instance_environment("chernarus", tmp_path)
    msg = str(exc.value.code)
    assert "allowFilePatching = 1;" in msg and "/dayz-add-server chernarus" in msg
    assert (inst / "serverDZ.cfg").read_text(encoding="utf-8") == CFG + tail  # never rewritten


def test_mission_path_follows_cfg_template_not_glob(tmp_path):
    inst = _instance(tmp_path)
    (inst / "dayzOffline.enoch").mkdir()  # sorts first; the cfg must still decide
    (inst / "serverDZ.cfg").write_text(CFG.replace("chernarusplus", "enoch") + FP, encoding="utf-8")
    _, _, mission, _ = launch.verify_instance_environment("chernarus", tmp_path)
    assert mission == inst / "dayzOffline.enoch"
    (inst / "serverDZ.cfg").write_text(CFG + FP, encoding="utf-8")
    _, _, mission, _ = launch.verify_instance_environment("chernarus", tmp_path)
    assert mission == inst / "dayzOffline.chernarusplus"


def test_custom_template_junction_is_found(tmp_path):
    inst = _instance(tmp_path)
    (inst / "namalsk.custom").mkdir()
    (inst / "serverDZ.cfg").write_text(CFG.replace("dayzOffline.chernarusplus", "namalsk.custom") + FP, encoding="utf-8")
    assert launch.verify_instance_environment("chernarus", tmp_path)[2] == inst / "namalsk.custom"


def test_cfg_without_template_line_refuses(tmp_path):
    inst = _instance(tmp_path)
    (inst / "serverDZ.cfg").write_text("allowFilePatching = 1;\n", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        launch.verify_instance_environment("chernarus", tmp_path)
    assert "template" in str(exc.value.code)


def test_read_cfg_template():
    assert launch.read_cfg_template('  template = "dayzOffline.sakhal";   // map\n') == "dayzOffline.sakhal"
    assert launch.read_cfg_template('hostname = "x";\n') is None


def test_verify_instance_dry_run_changes_nothing(tmp_path):
    inst = _instance(tmp_path)
    launch.verify_instance_environment("chernarus", tmp_path, dry_run=True)
    assert not (inst / "Profiles").exists()
    assert not (tmp_path / ".server" / "!ClientDiagLogs").exists()


# --- main ---------------------------------------------------------------------------

def _patch_main(monkeypatch, tmp_path, argv):
    monkeypatch.setattr(launch.h, "resolve_project_dir", lambda: tmp_path)
    monkeypatch.setattr(launch.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(launch, "verify_built_mods", lambda names: None)
    monkeypatch.setattr(launch, "resolve_diag_client", lambda: DIAG)
    monkeypatch.setattr(launch.sys, "argv", ["launch.py", *argv])


def _snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None) for p in root.rglob("*")}


def test_dry_run_is_side_effect_free(monkeypatch, tmp_path):
    _instance(tmp_path)
    before = _snapshot(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--dry-run"])
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("dry run spawned a process"))
    assert launch.main() == 0
    assert _snapshot(tmp_path) == before  # no Profiles/, no prefs file


class _FakeProc:
    def __init__(self):
        self.pid = 4242
        self.killed = False

    def poll(self):
        return -9 if self.killed else None

    def kill(self):
        self.killed = True


def test_server_killed_on_bind_timeout(monkeypatch, tmp_path):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod"])
    procs = []
    monkeypatch.setattr(launch.subprocess, "Popen", lambda cmd: procs.append(_FakeProc()) or procs[-1])
    monkeypatch.setattr(launch, "wait_for_server_port", lambda port, proc, timeout_s: False)
    assert launch.main() == 1
    assert len(procs) == 1 and procs[0].killed  # server killed, client never started


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
