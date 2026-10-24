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


def test_build_server_cmd_puts_server_only_mods_on_server_mod():
    cmd = launch.build_server_cmd(
        DIAG, "P:\\Mods\\@A", 2302,
        Path("cfg/serverDZ.cfg"), Path("inst/Profiles"), Path("inst/dayzOffline.chernarusplus"),
        server_mod_arg="P:\\Mods\\@S",
    )
    assert "-mod=P:\\Mods\\@A" in cmd
    assert "-serverMod=P:\\Mods\\@S" in cmd
    assert not any(a.startswith("-mod=") and "@S" in a for a in cmd)


def test_main_keeps_server_only_mods_off_mod_list(monkeypatch, tmp_path, capsys):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--server-only", "SrvMod", "--dry-run"])
    assert launch.main() == 0
    server_line = next(l for l in capsys.readouterr().out.splitlines() if "Server cmd:" in l)
    assert f"-mod={launch.MODS_ROOT / '@MyMod'} " in server_line
    assert f"-serverMod={launch.MODS_ROOT / '@SrvMod'} " in server_line


@pytest.mark.parametrize("argv", [
    ["CF", "--server-only", "Srv", "MyMod"],  # nargs="+" put MyMod on -serverMod= only
    ["CF", "--port", "2402", "MyMod"],
])
def test_main_refuses_mod_name_after_an_option(monkeypatch, tmp_path, capsys, argv):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, argv + ["--dry-run"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "unexpected arguments: MyMod" in captured.err
    assert "Server cmd:" not in captured.out


def test_server_only_takes_one_name_per_flag(monkeypatch, tmp_path, capsys):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, [
        "CF", "MyMod", "--server-only", "SrvA", "--server-only", "SrvB", "--dry-run",
    ])
    assert launch.main() == 0
    out = capsys.readouterr().out
    server_line = next(l for l in out.splitlines() if "Server cmd:" in l)
    client_line = next(l for l in out.splitlines() if "Client cmd:" in l)
    shared = f"-mod={launch.MODS_ROOT / '@CF'};{launch.MODS_ROOT / '@MyMod'} "
    assert shared in server_line and shared in client_line
    assert f"-serverMod={launch.MODS_ROOT / '@SrvA'};{launch.MODS_ROOT / '@SrvB'} " in server_line
    assert "@Srv" not in client_line


def test_main_refuses_mod_named_shared_and_server_only(monkeypatch, tmp_path, capsys):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "SrvMod", "--server-only", "SrvMod", "--dry-run"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "mod named both as shared and --server-only: SrvMod" in captured.err
    assert "Server cmd:" not in captured.out


def test_main_refuses_shared_and_server_only_differing_in_case(monkeypatch, tmp_path, capsys):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["CF", "--server-only", "cf", "--dry-run"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "mod named both as shared and --server-only: cf" in captured.err
    assert "Server cmd:" not in captured.out


@pytest.mark.parametrize("argv", [
    ["CF", "CF", "MyMod"],
    ["CF", "@cf", "MyMod"],
    ["MyMod", "--server-only", "Srv", "--server-only", "srv"],
])
def test_main_refuses_duplicate_mod_names(monkeypatch, tmp_path, capsys, argv):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, argv + ["--dry-run"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2
    captured = capsys.readouterr()
    assert "mod named more than once" in captured.err
    assert "Server cmd:" not in captured.out

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


def test_verify_instance_reads_ansi_cfg(tmp_path):
    inst = _instance(tmp_path)
    (inst / "serverDZ.cfg").write_bytes(
        ('hostname = "Café Server";\npassword = "été";\n' + CFG + FP).encode("cp1252")
    )
    _, _, mission, _ = launch.verify_instance_environment("chernarus", tmp_path)
    assert mission == inst / "dayzOffline.chernarusplus"


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
    monkeypatch.setattr(launch.h, "udp_port_free", lambda port: True)
    monkeypatch.setattr(launch.h, "steam_running", lambda: True)
    monkeypatch.setattr(launch, "verify_built_mods", lambda names: None)
    monkeypatch.setattr(launch, "resolve_diag_client", lambda: DIAG)
    monkeypatch.setattr(launch.sys, "argv", ["launch.py", *argv])


def test_launch_refuses_without_steam_before_spawning(monkeypatch, tmp_path):
    # The live AZTestVest run: Steam was closed, the client crashed at start
    # (a crash dump in !ClientDiagLogs) and the in-game gate only saw an early exit.
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod"])
    monkeypatch.setattr(launch.h, "steam_running", lambda: False)
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("launched without Steam"))
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert "Steam is not running" in str(exc.value.code)


def test_dry_run_does_not_need_steam(monkeypatch, tmp_path):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--dry-run"])
    monkeypatch.setattr(launch.h, "steam_running", lambda: pytest.fail("dry run checked Steam"))
    assert launch.main() == 0


def _snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None) for p in root.rglob("*")}


def test_dry_run_is_side_effect_free(monkeypatch, tmp_path):
    _instance(tmp_path)
    before = _snapshot(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--dry-run"])
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("dry run spawned a process"))
    assert launch.main() == 0
    assert _snapshot(tmp_path) == before  # no Profiles/, no prefs file


SPACED_DIAG = Path("C:/Program Files (x86)/Steam/steamapps/common/DayZ/DayZDiag_x64.exe")


@pytest.mark.parametrize("dry_run", [True, False])
def test_printed_commands_quote_paths_with_spaces(monkeypatch, tmp_path, capsys, dry_run):
    project = tmp_path / "DayZ n Chill"
    project.mkdir()
    _instance(project)
    _patch_main(monkeypatch, project, ["MyMod", *(["--dry-run"] if dry_run else [])])
    monkeypatch.setattr(launch, "resolve_diag_client", lambda: SPACED_DIAG)
    spawned = []
    monkeypatch.setattr(launch.subprocess, "Popen", lambda cmd, **k: spawned.append(cmd) or _FakeProc())
    monkeypatch.setattr(launch, "wait_for_server_port", lambda port, proc, timeout_s: True)
    assert launch.main() == 0
    prefix = "[DRY-RUN] Server cmd: " if dry_run else "[Launch] Server: "
    lines = [l for l in capsys.readouterr().out.splitlines() if "Server" in l and l.startswith(prefix)]
    assert len(lines) == 1
    printed = lines[0][len(prefix):]
    assert printed.startswith(f'"{SPACED_DIAG}" ')  # exe path quoted, so the line pastes as is
    assert f'"-config={project}' in printed  # cfg path under a spaced folder stays one argument
    if not dry_run:
        assert printed == launch.subprocess.list2cmdline(spawned[0])


@pytest.mark.parametrize("extra", [[], ["--dry-run"]])
def test_port_out_of_range_exits_2(monkeypatch, tmp_path, capsys, extra):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--port", "70000", *extra])
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned with a bad port"))
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2
    assert "port must be 1-65535" in capsys.readouterr().err


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
    monkeypatch.setattr(launch.subprocess, "Popen", lambda cmd, **k: procs.append(_FakeProc()) or procs[-1])
    monkeypatch.setattr(launch, "wait_for_server_port", lambda port, proc, timeout_s: False)
    assert launch.main() == 1
    assert len(procs) == 1 and procs[0].killed  # server killed, client never started


def test_server_and_client_spawn_detached(monkeypatch, tmp_path):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod"])
    spawns = []

    def fake_popen(cmd, **kwargs):
        spawns.append(kwargs)
        return _FakeProc()

    monkeypatch.setattr(launch.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(launch, "wait_for_server_port", lambda port, proc, timeout_s: True)
    assert launch.main() == 0
    assert len(spawns) == 2  # server, then client
    for kwargs in spawns:
        assert kwargs["creationflags"] == launch.h.DETACH_FLAGS
        assert kwargs["close_fds"] is True


def test_client_spawn_failure_kills_server(monkeypatch, tmp_path, capsys):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod"])
    procs = []

    def fake_popen(cmd, **kwargs):
        if procs:
            raise OSError("access denied")
        procs.append(_FakeProc())
        return procs[-1]

    monkeypatch.setattr(launch.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(launch, "wait_for_server_port", lambda port, proc, timeout_s: True)
    assert launch.main() == 1
    assert procs[0].killed
    out = capsys.readouterr().out
    assert launch.FAIL in out and "Failed to spawn DayZDiag_x64.exe: access denied" in out


def test_server_spawn_failure_exits_1(monkeypatch, tmp_path, capsys):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod"])

    def fake_popen(cmd, **kwargs):
        raise OSError("not found")

    monkeypatch.setattr(launch.subprocess, "Popen", fake_popen)
    assert launch.main() == 1
    assert "Failed to spawn DayZDiag_x64.exe: not found" in capsys.readouterr().out


def test_wait_for_port_defaults_to_bind_timeout():
    import inspect

    default = inspect.signature(launch.wait_for_server_port).parameters["timeout_s"].default
    assert default == launch.SERVER_BIND_TIMEOUT_S


def test_port_in_use_refuses_before_spawning(monkeypatch, tmp_path):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--port", "2402"])
    checked = []
    monkeypatch.setattr(launch.h, "udp_port_free", lambda port: checked.append(port) or False)
    monkeypatch.setattr(launch.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned despite a taken port"))
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert checked == [2402]
    assert "port 2402 in use; run /dayz-stop-test or pass --port" in str(exc.value.code)


# --- argument validation ---------------------------------------------------------------

@pytest.mark.parametrize("bad", ["..\\x", "../x", "a/b", "C:x", "..", ".", "", "!ClientDiagLogs"])
def test_server_rejects_paths_and_shared_folders(monkeypatch, tmp_path, capsys, bad):
    # '..\\x' was joined onto .server/ and looked outside the project.
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--server", bad, "--dry-run"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2
    assert "instance" in capsys.readouterr().err


def test_server_accepts_gate_behavior_copy(monkeypatch, tmp_path):
    # /dayz-gate behavior launches its <instance>-behavior copy through this script.
    _instance(tmp_path, "chernarus-behavior")
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--server", "chernarus-behavior", "--dry-run"])
    assert launch.main() == 0


@pytest.mark.parametrize("bad", ["..\\x", "a/b", "@", "..", "P:\\Mods\\@CF"])
def test_mod_name_rejects_paths(monkeypatch, tmp_path, capsys, bad):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, [bad, "--dry-run"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 2
    assert "is not a mod name" in capsys.readouterr().err


def test_mod_name_drops_leading_at(monkeypatch, tmp_path, capsys):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["@CF", "MyMod", "--dry-run"])
    assert launch.main() == 0
    server_line = next(l for l in capsys.readouterr().out.splitlines() if "Server cmd:" in l)
    assert f"-mod={launch.MODS_ROOT / '@CF'};{launch.MODS_ROOT / '@MyMod'} " in server_line


# --- requiredAddons dependency gate ------------------------------------------------------

def _source_mod(project: Path, name: str, config: str, rel: str = "config.cpp") -> Path:
    mod = project / "workspace" / name
    (mod / rel).parent.mkdir(parents=True, exist_ok=True)
    (mod / rel).write_text(config, encoding="utf-8")
    return mod


NEEDS_CF = """class CfgPatches
{
    class MyMod
    {
        requiredAddons[] =
        {
            "DZ_Data",
            "JM_CF_Scripts"
        };
    };
};
"""


def test_config_patches_reads_names_and_required_addons():
    text = NEEDS_CF + 'class CfgVehicles { class MyVest { displayName = "a { b"; }; };\n'
    patches, required = launch.config_patches(text)
    assert patches == {"MyMod"}  # CfgVehicles classes and string braces do not count
    assert required == ["DZ_Data", "JM_CF_Scripts"]


def test_config_patches_reads_appended_required_addons():
    text = 'class CfgPatches { class MyMod { requiredAddons[] += {"JM_CF_Scripts"}; }; };\n'
    assert launch.config_patches(text) == ({"MyMod"}, ["JM_CF_Scripts"])


def test_config_patches_reads_vanilla_ai_config():
    vanilla = Path("P:/DZ/AI/config.cpp")
    if not vanilla.is_file():
        pytest.skip("P:\\ not mounted")
    patches, required = launch.config_patches(vanilla.read_text(encoding="utf-8", errors="replace"))
    assert "DZ_AI" in patches and "DZ_Data" in required


def test_launch_refuses_mod_whose_required_addon_is_not_loaded(monkeypatch, tmp_path):
    # Run directly, `/dayz-launch-test MyMod` for a mod that needs CF started a
    # session in which the mod failed to load; only /dayz-init checked this.
    _instance(tmp_path)
    _source_mod(tmp_path, "MyMod", NEEDS_CF)
    _patch_main(monkeypatch, tmp_path, ["MyMod", "--dry-run"])
    with pytest.raises(SystemExit) as exc:
        launch.main()
    msg = str(exc.value.code)
    assert "MyMod requires JM_CF_Scripts" in msg and "/dayz-launch-test CF MyMod" in msg
    assert "DZ_Data" not in msg


def test_required_addon_in_subfolder_config_is_checked(tmp_path):
    _source_mod(tmp_path, "MyMod", "class CfgPatches { class MyMod { requiredAddons[] = {}; }; };\n")
    _source_mod(tmp_path, "MyMod", NEEDS_CF.replace("class MyMod", "class MyMod_Data"), "data/config.cpp")
    assert launch.missing_dependencies(["MyMod"], [], tmp_path) == {"MyMod": ["JM_CF_Scripts"]}


def test_dependency_listed_first_satisfies_gate(monkeypatch, tmp_path):
    _instance(tmp_path)
    _source_mod(tmp_path, "MyMod", NEEDS_CF)
    _patch_main(monkeypatch, tmp_path, ["CF", "MyMod", "--dry-run"])
    assert launch.main() == 0


def test_dependency_listed_after_the_mod_does_not_count(tmp_path):
    _source_mod(tmp_path, "MyMod", NEEDS_CF)
    assert launch.missing_dependencies(["MyMod", "CF"], [], tmp_path) == {"MyMod": ["JM_CF_Scripts"]}


def test_workspace_dependency_must_declare_the_patch(tmp_path):
    _source_mod(tmp_path, "MyMod", NEEDS_CF.replace("JM_CF_Scripts", "MyBase"))
    _source_mod(tmp_path, "Other", "class CfgPatches { class OtherPatch {}; };\n")
    assert launch.missing_dependencies(["Other", "MyMod"], [], tmp_path) == {"MyMod": ["MyBase"]}
    _source_mod(tmp_path, "Base", "class CfgPatches { class mybase { requiredAddons[] = {}; }; };\n")
    assert launch.missing_dependencies(["Base", "MyMod"], [], tmp_path) == {}  # case-insensitive


def test_mod_can_require_its_own_patch(tmp_path):
    cfg = "class CfgPatches { class A { }; class B { requiredAddons[] = {\"A\"}; }; };\n"
    _source_mod(tmp_path, "MyMod", cfg)
    assert launch.missing_dependencies(["MyMod"], [], tmp_path) == {}


def test_prebuilt_bundle_and_unknown_mods_are_not_checked(tmp_path):
    mod = _source_mod(tmp_path, "Bundle", NEEDS_CF)
    (mod / "Addons").mkdir()
    (mod / "Addons" / "Bundle.pbo").write_bytes(b"")
    assert launch.missing_dependencies(["Bundle", "NotInWorkspace"], [], tmp_path) == {}


def test_shared_mod_cannot_rely_on_server_only_mod(tmp_path):
    _source_mod(tmp_path, "MyMod", NEEDS_CF)
    assert launch.missing_dependencies(["MyMod"], ["CF"], tmp_path) == {"MyMod": ["JM_CF_Scripts"]}
    _source_mod(tmp_path, "SrvMod", NEEDS_CF)
    assert launch.missing_dependencies(["CF"], ["SrvMod"], tmp_path) == {}  # shared mods load first


def test_addons_and_keys_configs_are_skipped(tmp_path):
    _source_mod(tmp_path, "MyMod", "class CfgPatches { class MyMod {}; };\n")
    _source_mod(tmp_path, "MyMod", NEEDS_CF, "Keys/config.cpp")
    assert launch.missing_dependencies(["MyMod"], [], tmp_path) == {}


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


@pytest.mark.parametrize("content", ['[1920, 1080]', '"windowed"', '{"windowed": "yes"}',
                                     '{"width": "1920"}', '{"height": 0}', '{"width": true}', "{not json"])
def test_display_prefs_bad_shape_falls_back_with_warning(tmp_path, capsys, content):
    prefs = tmp_path / ".claude" / "local-memory" / launch.CLIENT_DISPLAY_PREFS_NAME
    prefs.parent.mkdir(parents=True)
    prefs.write_text(content, encoding="utf-8")
    assert launch.read_client_display_prefs(tmp_path) == launch.DEFAULT_CLIENT_DISPLAY
    assert "Falling back to defaults" in capsys.readouterr().out


# --- wait_for_server_port -------------------------------------------------------------

class _ServerProc:
    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        return self.returncode


@pytest.fixture
def fake_clock(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(launch.time, "time", lambda: now[0])
    monkeypatch.setattr(launch.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))
    return now


def test_wait_for_port_stops_when_server_exits(monkeypatch, fake_clock, capsys):
    monkeypatch.setattr(launch.h, "udp_port_free", lambda port: pytest.fail("probed after the server exited"))
    assert launch.wait_for_server_port(2302, _ServerProc(returncode=3), timeout_s=60) is False
    assert "exited unexpectedly (rc=3)" in capsys.readouterr().out


def test_wait_for_port_succeeds_once_server_binds(monkeypatch, fake_clock):
    probes = iter([True, True, False])  # free, free, then held by the server
    monkeypatch.setattr(launch.h, "udp_port_free", lambda port: next(probes))
    assert launch.wait_for_server_port(2302, _ServerProc(), timeout_s=60) is True
    assert fake_clock[0] == 2  # slept once per free probe


def _interrupt(port):
    raise KeyboardInterrupt


def test_wait_for_port_ctrl_c_kills_server_and_exits_130(monkeypatch, fake_clock, capsys):
    # Before the fix Ctrl+C printed a traceback and left the detached server
    # holding the port, so the next launch was refused with "port in use".
    monkeypatch.setattr(launch.h, "udp_port_free", _interrupt)
    server = _FakeProc()
    with pytest.raises(SystemExit) as exc:
        launch.wait_for_server_port(2302, server, timeout_s=60)
    assert exc.value.code == 130
    assert server.killed
    assert "Interrupted while waiting for the server; killed it (PID 4242)" in capsys.readouterr().out


def test_main_ctrl_c_during_bind_wait_never_starts_client(monkeypatch, tmp_path):
    _instance(tmp_path)
    _patch_main(monkeypatch, tmp_path, ["MyMod"])
    procs = []
    monkeypatch.setattr(launch.subprocess, "Popen", lambda cmd, **k: procs.append(_FakeProc()) or procs[-1])
    monkeypatch.setattr(launch.time, "sleep", lambda s: None)
    probes = iter([True])  # the port gate sees it free, then Ctrl+C during the wait

    def probe(port):
        if next(probes, False):
            return True
        raise KeyboardInterrupt

    monkeypatch.setattr(launch.h, "udp_port_free", probe)
    with pytest.raises(SystemExit) as exc:
        launch.main()
    assert exc.value.code == 130
    assert len(procs) == 1 and procs[0].killed


def test_wait_for_port_times_out(monkeypatch, fake_clock):
    monkeypatch.setattr(launch.h, "udp_port_free", lambda port: True)
    assert launch.wait_for_server_port(2302, _ServerProc(), timeout_s=10) is False
    assert fake_clock[0] >= 10
