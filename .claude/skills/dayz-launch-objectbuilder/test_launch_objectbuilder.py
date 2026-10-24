"""Tests for the Object Builder launcher: flags, target resolution, the running-instance guard and the startup check."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_launch_objectbuilder_under_test", HERE / "launch.py")
ob = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ob)


def test_file_and_mod_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit) as exc:
        ob.build_parser().parse_args(["--file", "a.p3d", "--mod", "MyMod"])
    assert exc.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [[], ["--file", "a.p3d"], ["--mod", "MyMod"]])
def test_one_or_neither_flag_parses(argv):
    ob.build_parser().parse_args(argv)


def test_no_flags_means_no_target():
    assert ob.resolve_target(None, None) is None


def test_absolute_file_target(tmp_path):
    model = tmp_path / "model.p3d"
    model.write_bytes(b"")
    assert ob.resolve_target(str(model), None) == model


def test_relative_file_resolves_against_project(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "PROJECT_DIR", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "model.p3d").write_bytes(b"")
    assert ob.resolve_target("data/model.p3d", None) == (tmp_path / "data" / "model.p3d").resolve()


def test_missing_file_exits(tmp_path):
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(str(tmp_path / "nope.p3d"), None)
    assert "does not exist" in str(exc.value.code)


def test_non_p3d_file_warns(tmp_path, capsys):
    other = tmp_path / "model.obj"
    other.write_bytes(b"")
    assert ob.resolve_target(str(other), None) == other
    assert "not a .p3d" in capsys.readouterr().out


def test_mod_target_is_the_one_p3d_in_data(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    model = tmp_path / "MyMod" / "data" / "vest" / "vest.p3d"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"")
    (tmp_path / "MyMod" / "data" / "vest" / "vest.rvmat").write_text("")
    target = ob.resolve_target(None, "MyMod")
    assert target == model and target.is_file()  # a file, never the mod folder


def test_mod_without_p3d_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    (tmp_path / "MyMod" / "data").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, "MyMod")
    assert "No .p3d under" in str(exc.value.code) and "--file" in str(exc.value.code)


def test_mod_with_several_p3d_lists_them_and_asks_for_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    data = tmp_path / "MyMod" / "data"
    data.mkdir(parents=True)
    for name in ("a.p3d", "b.p3d"):
        (data / name).write_bytes(b"")
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, "MyMod")
    msg = str(exc.value.code)
    assert "2 .p3d files" in msg and "--file" in msg
    assert str(data / "a.p3d") in msg and str(data / "b.p3d") in msg


def test_missing_mod_folder_exits(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, "MyMod")
    assert "/dayz-new-mod MyMod" in str(exc.value.code)


def test_preflight_runs_before_target_resolution(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(ob.h, "gate_on_preflight", lambda: calls.append("preflight"))
    real_resolve = ob.resolve_target
    monkeypatch.setattr(ob, "resolve_target", lambda f, m: calls.append("resolve") or real_resolve(f, m))
    monkeypatch.setattr(ob, "registry_has_objectbuilder_settings", lambda: calls.append("registry") or True)
    monkeypatch.setattr("sys.argv", ["launch.py", "--file", str(tmp_path / "missing.p3d")])
    with pytest.raises(SystemExit) as exc:
        ob.main()
    assert "does not exist" in str(exc.value.code)
    assert calls == ["preflight", "resolve"]


def test_failed_preflight_stops_before_target_resolution(monkeypatch):
    def preflight_fails():
        raise SystemExit(1)

    monkeypatch.setattr(ob.h, "gate_on_preflight", preflight_fails)
    monkeypatch.setattr(ob, "resolve_target", lambda f, m: pytest.fail("resolved a P:\\ target before preflight"))
    monkeypatch.setattr("sys.argv", ["launch.py", "--mod", "MyMod"])
    with pytest.raises(SystemExit) as exc:
        ob.main()
    assert exc.value.code == 1


def _fake_launch_env(tmp_path, monkeypatch, running=False):
    """Stub preflight, DayZ Tools, the registry check and the running check."""

    class FakePreflight:
        @staticmethod
        def find_dayz_tools():
            return tmp_path

    monkeypatch.setattr(ob.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(ob.h, "preflight", FakePreflight, raising=False)
    monkeypatch.setattr(ob, "registry_has_objectbuilder_settings", lambda: True)
    monkeypatch.setattr(ob, "objectbuilder_running", lambda: running)
    monkeypatch.setattr(ob, "STARTUP_CHECK_SECONDS", 0)


def _fake_exe(tmp_path):
    exe = tmp_path / "Bin" / "ObjectBuilder" / "ObjectBuilder.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    return exe


def test_launch_uses_shared_detach_flags(tmp_path, monkeypatch):
    exe = _fake_exe(tmp_path)
    spawned = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            spawned.update(cmd=cmd, **kwargs)

        def poll(self):
            return None  # still running

    _fake_launch_env(tmp_path, monkeypatch)
    monkeypatch.setattr(ob.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert ob.main() == 0
    assert spawned["cmd"] == [str(exe)]
    assert spawned["creationflags"] == ob.h.DETACH_FLAGS
    assert spawned["cwd"] == str(exe.parent)


def test_registry_check_comes_from_setup_objectbuilder():
    """One definition of the key and the check, owned by the skill that writes the key."""
    setup_py = Path(ob.__file__).resolve().parents[1] / "dayz-setup-objectbuilder" / "setup.py"
    assert Path(ob._setup.__file__).resolve() == setup_py
    assert ob.REG_KEY == ob._setup.REG_KEY
    assert ob.registry_has_objectbuilder_settings is ob._setup.registry_has_objectbuilder_settings


def test_refuses_when_objectbuilder_already_running(tmp_path, monkeypatch, capsys):
    _fake_exe(tmp_path)
    _fake_launch_env(tmp_path, monkeypatch, running=True)
    monkeypatch.setattr(ob.subprocess, "Popen", lambda *a, **k: pytest.fail("spawned a second ObjectBuilder.exe"))
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert ob.main() == 1
    err = capsys.readouterr().err
    assert "already running" in err and "Switch to its window" in err


def test_running_check_is_reused_from_setup_objectbuilder():
    assert ob.objectbuilder_running is ob._setup.objectbuilder_running


def test_process_that_exits_at_once_is_reported_as_failure(tmp_path, monkeypatch, capsys):
    _fake_exe(tmp_path)
    _fake_launch_env(tmp_path, monkeypatch)

    class DiesAtOnce:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            pass

        def poll(self):
            return 3

    monkeypatch.setattr(ob.subprocess, "Popen", DiesAtOnce)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert ob.main() == 1
    out = capsys.readouterr()
    assert "exited right after starting (exit code 3)" in out.err
    assert "launched" not in out.out


def test_wait_for_early_exit_polls_until_exit_within_window(monkeypatch):
    monkeypatch.setattr(ob, "STARTUP_POLL_INTERVAL", 0)
    results = iter([None, None, 5])

    class ExitsLater:
        polls = 0

        def poll(self):
            ExitsLater.polls += 1
            return next(results)

    assert ob.wait_for_early_exit(ExitsLater()) == 5
    assert ExitsLater.polls == 3


def test_wait_for_early_exit_returns_none_when_still_running(monkeypatch):
    clock = iter([0.0, 0.5, 1.5])  # deadline set at 0.0; second check passes it
    monkeypatch.setattr(ob.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(ob.time, "sleep", lambda s: None)

    class Running:
        def poll(self):
            return None

    assert ob.wait_for_early_exit(Running()) is None


def test_mod_finds_p3d_outside_data(tmp_path, monkeypatch):
    r"""A mod that keeps its models in models\ (not data\) still resolves."""
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    model = tmp_path / "MyMod" / "models" / "crate.p3d"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"")
    (tmp_path / "MyMod" / "data").mkdir()
    assert ob.resolve_target(None, "MyMod") == model


def test_mod_without_p3d_names_the_whole_mod_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    (tmp_path / "MyMod" / "models").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, "MyMod")
    msg = str(exc.value.code)
    assert f"No .p3d under {tmp_path / 'MyMod'} (searched every subfolder)" in msg


@pytest.mark.parametrize(
    "bad", [r"..\Windows", "../etc", "1Mod", "My Mod", "My-Mod", r"C:\Mod", "Mod\n", "A" * 65]
)
def test_invalid_mod_name_is_refused_before_touching_p_drive(bad, tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    # Without the check, r"..\Windows" would resolve outside P:\ and report a "missing mod".
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, bad)
    assert "Invalid mod name" in str(exc.value.code)


def test_mod_name_rule_comes_from_new_mod():
    r"""One mod name rule, owned by /dayz-new-mod, which creates P:\<ModName>\."""
    new_mod_py = Path(ob.__file__).resolve().parents[1] / "dayz-new-mod" / "new_mod.py"
    assert Path(ob._new_mod.__file__).resolve() == new_mod_py
    assert ob.MOD_NAME_PATTERN is ob._new_mod.NAME_PATTERN
