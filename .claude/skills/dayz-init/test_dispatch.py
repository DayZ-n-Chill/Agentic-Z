"""Tests for dayz-init/dispatch.py: every action maps to a real sibling entry point."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dispatch  # noqa: E402
from dispatch import DispatchError, command_for  # noqa: E402

SKILLS = Path(__file__).resolve().parents[1]


def _script(argv):
    """The entry-point path in an argv (python <script> ... or cmd /c <bat>)."""
    return Path(argv[1]) if argv[0] == sys.executable else Path(argv[2])


@pytest.mark.parametrize("action,kwargs,tail", [
    ("mount-p", {}, []),
    ("new-mod", {"mod": "MyMod"}, ["MyMod"]),
    ("new-mod", {"mod": "MyMod", "author": "Me"}, ["MyMod", "--author", "Me"]),
    ("import-mod", {"mod": "M", "source": "D:/src"}, ["--source", "D:/src", "--name", "M"]),
    ("import-mod", {"mod": "M", "source": "D:/src", "scaffold": True},
     ["--source", "D:/src", "--name", "M", "--scaffold"]),
    ("import-mod", {"mod": "M", "source": "D:/src", "scaffold": False},
     ["--source", "D:/src", "--name", "M", "--no-scaffold"]),
    ("import-mod", {"mod": "M", "source": "D:/src", "scaffold": True, "author": "Me"},
     ["--source", "D:/src", "--name", "M", "--scaffold", "--author", "Me"]),
    ("add-server", {"server": "livonia"}, ["livonia", "--map", "livonia"]),
    ("build", {"mod": "MyMod"}, ["MyMod"]),
    ("launch", {"mod": "MyMod", "server": "chernarus"}, ["MyMod", "--server", "chernarus"]),
    ("workbench", {"mod": "MyMod"}, ["--mod", "MyMod"]),
    ("search-download", {}, []),
    ("launch", {"mod": "MyMod", "server": "chernarus", "deps": ["@CF", "COT"]},
     ["CF", "COT", "MyMod", "--server", "chernarus"]),
    ("lint", {"mod": "MyMod"}, ["MyMod"]),
    ("gate-build", {"mod": "MyMod"}, ["build", "MyMod"]),
    ("gate-ingame", {"mod": "MyMod", "server": "chernarus"}, ["ingame", "MyMod", "--server", "chernarus"]),
    ("gate-ingame", {"mod": "MyMod", "server": "chernarus", "deps": ["CF"]},
     ["ingame", "MyMod", "--server", "chernarus", "--deps", "CF"]),
    ("health", {"mod": "MyMod"}, ["MyMod"]),
    ("gate-build", {"mod": "MyMod", "yes": True}, ["build", "MyMod", "--yes"]),
    ("gate-ingame", {"mod": "MyMod"}, ["ingame", "MyMod"]),
    ("gate-ingame", {"mod": "MyMod", "server": "livonia", "deps": ["CF"], "yes": True},
     ["ingame", "MyMod", "--server", "livonia", "--deps", "CF", "--yes"]),
])
def test_python_actions_point_at_existing_scripts(action, kwargs, tail):
    argv = command_for(action, **kwargs)
    assert argv[0] == sys.executable
    assert _script(argv).is_file(), f"{action} -> missing {argv[1]}"
    assert _script(argv).parent.parent == SKILLS
    assert argv[2:] == tail


OBJECTBUILDER = SKILLS / "dayz-launch-objectbuilder" / "launch.py"


@pytest.mark.parametrize("model", [True, False])
def test_objectbuilder_always_passes_mod(monkeypatch, tmp_path, model):
    # launch.py --mod opens the editor empty itself when the mod has no .p3d,
    # so dispatch passes --mod whether or not a model exists.
    (tmp_path / "MyMod").mkdir()
    if model:
        (tmp_path / "MyMod" / "vest.p3d").write_bytes(b"")
    monkeypatch.chdir(tmp_path)
    argv = command_for("objectbuilder", mod="MyMod")
    assert Path(argv[1]) == OBJECTBUILDER and OBJECTBUILDER.is_file()
    assert argv[2:] == ["--mod", "MyMod"]


def test_stop_runs_the_stop_test_batch_file():
    argv = command_for("stop")
    assert argv[:2] == ["cmd", "/c"]
    assert _script(argv) == SKILLS / "dayz-stop-test" / "stop_test.bat"
    assert _script(argv).is_file()


def test_mods_junction_is_not_an_action():
    # /dayz-preflight creates P:\Mods; dayz-init has no action of its own for it.
    with pytest.raises(DispatchError):
        command_for("mods-junction")


@pytest.mark.parametrize("action,kwargs", [
    ("new-mod", {}),
    ("import-mod", {"mod": "M"}),
    ("add-server", {}),
    ("build", {}),
    ("launch", {"mod": "M"}),
    ("workbench", {}),
    ("objectbuilder", {}),
    ("lint", {}),
    ("gate-ingame", {}),
    ("health", {}),
    ("build", {"mod": "M", "yes": True}),
    ("launch", {"mod": "M", "server": "chernarus", "yes": True}),
    ("unknown-thing", {}),
])
def test_missing_values_raise(action, kwargs):
    with pytest.raises(DispatchError):
        command_for(action, **kwargs)


def test_hub_action_defaults_to_active_mod(monkeypatch):
    seen = []

    def fake_run(argv):
        seen.append(argv)
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr(dispatch, "active_mod", lambda project: "ActiveMod")
    monkeypatch.setattr(dispatch.subprocess, "run", fake_run)
    assert dispatch.main(["build"]) == 7
    assert seen[0][-1] == "ActiveMod"


def test_hub_action_missing_value_exits_2(monkeypatch):
    monkeypatch.setattr(dispatch, "active_mod", lambda project: None)
    assert dispatch.main(["build"]) == 2


def test_known_maps_come_from_add_server():
    import importlib.util
    spec = importlib.util.spec_from_file_location("add_server_for_test", SKILLS / "dayz-add-server" / "add_server.py")
    add_server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(add_server)
    assert dispatch.KNOWN_MAPS == tuple(add_server.KNOWN_MAPS)


def _mod_needing_cf(project: Path, name: str = "CfMod") -> Path:
    mod_dir = project / "workspace" / name
    mod_dir.mkdir(parents=True)
    (mod_dir / "config.cpp").write_text(
        'class CfgPatches { class CfMod { requiredAddons[] = {"DZ_Data", "JM_CF_Scripts"}; }; };\n',
        encoding="utf-8",
    )
    return mod_dir


def test_hub_launch_refuses_missing_deps_before_running(monkeypatch, tmp_path, capsys):
    _mod_needing_cf(tmp_path)
    monkeypatch.setattr(dispatch, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(dispatch, "active_mod", lambda project: "CfMod")
    monkeypatch.setattr(dispatch.subprocess, "run", lambda argv: pytest.fail("nothing may launch"))
    assert dispatch.main(["launch", "--server", "chernarus"]) == 2
    assert "JM_CF_Scripts" in capsys.readouterr().err


def test_hub_launch_with_deps_or_a_prebuilt_bundle_runs(monkeypatch, tmp_path):
    mod_dir = _mod_needing_cf(tmp_path)
    seen = []
    monkeypatch.setattr(dispatch, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(dispatch, "active_mod", lambda project: "CfMod")
    monkeypatch.setattr(dispatch.subprocess, "run", lambda argv: seen.append(argv) or SimpleNamespace(returncode=0))
    assert dispatch.main(["launch", "--server", "chernarus", "--deps", "CF"]) == 0
    (mod_dir / "Addons").mkdir()
    (mod_dir / "Addons" / "CfMod.pbo").write_bytes(b"")
    assert dispatch.main(["launch", "--server", "chernarus"]) == 0
    assert len(seen) == 2


def test_hub_launch_passes_deps_before_the_mod(monkeypatch):
    seen = []
    monkeypatch.setattr(dispatch, "active_mod", lambda project: "ActiveMod")
    monkeypatch.setattr(dispatch.subprocess, "run", lambda argv: seen.append(argv) or SimpleNamespace(returncode=0))
    assert dispatch.main(["launch", "--server", "chernarus", "--deps", "CF"]) == 0
    assert seen[0][2:] == ["CF", "ActiveMod", "--server", "chernarus"]


GATE = SKILLS / "dayz-gate" / "gate.py"


@pytest.mark.parametrize("action,sub", [("gate-build", "build"), ("gate-ingame", "ingame")])
def test_hub_yes_reaches_gate(monkeypatch, action, sub):
    # gate.py stops a running DayZ Diag only with --yes; an agent has no terminal to answer.
    seen = []
    monkeypatch.setattr(dispatch, "active_mod", lambda project: "ActiveMod")
    monkeypatch.setattr(dispatch.subprocess, "run", lambda argv: seen.append(argv) or SimpleNamespace(returncode=0))
    assert dispatch.main([action, "--yes"]) == 0
    assert Path(seen[0][1]) == GATE and GATE.is_file()
    assert seen[0][2:4] == [sub, "ActiveMod"]
    assert seen[0][-1] == "--yes"


def test_gate_accepts_the_yes_dispatch_passes():
    # The flag dispatch forwards must be one gate.py's parser takes for both subcommands.
    import subprocess
    for sub in ("build", "ingame"):
        out = subprocess.run([sys.executable, str(GATE), sub, "--help"],
                             capture_output=True, text=True, timeout=60)
        assert out.returncode == 0, out.stderr
        assert "--yes" in out.stdout


def test_hub_yes_on_other_actions_exits_2(monkeypatch, capsys):
    monkeypatch.setattr(dispatch, "active_mod", lambda project: "ActiveMod")
    monkeypatch.setattr(dispatch.subprocess, "run", lambda argv: pytest.fail("nothing may run"))
    assert dispatch.main(["build", "--yes"]) == 2
    assert "--yes" in capsys.readouterr().err


def test_hub_gate_ingame_without_server_uses_gate_default(monkeypatch):
    seen = []
    monkeypatch.setattr(dispatch, "active_mod", lambda project: "ActiveMod")
    monkeypatch.setattr(dispatch.subprocess, "run", lambda argv: seen.append(argv) or SimpleNamespace(returncode=0))
    assert dispatch.main(["gate-ingame"]) == 0
    assert seen[0][2:] == ["ingame", "ActiveMod"]


@pytest.mark.parametrize("action,kwargs", [
    ("build", {"mod": "X", "deps": ["CF"]}),
    ("build", {"mod": "X", "server": "livonia"}),
    ("lint", {"mod": "X", "server": "livonia"}),
    ("gate-build", {"mod": "X", "deps": ["CF"]}),
    ("add-server", {"server": "livonia", "deps": ["CF"]}),
    ("workbench", {"mod": "X", "server": "chernarus"}),
])
def test_options_an_action_cannot_use_raise(action, kwargs):
    with pytest.raises(DispatchError):
        command_for(action, **kwargs)


@pytest.mark.parametrize("argv,flag", [
    (["build", "--deps", "CF"], "--deps"),
    (["lint", "--server", "livonia"], "--server"),
])
def test_hub_unusable_option_exits_2(monkeypatch, capsys, argv, flag):
    # A dropped flag would run the action without what the user asked for.
    monkeypatch.setattr(dispatch, "active_mod", lambda project: "ActiveMod")
    monkeypatch.setattr(dispatch.subprocess, "run", lambda argv: pytest.fail("nothing may run"))
    assert dispatch.main(argv) == 2
    assert flag in capsys.readouterr().err
