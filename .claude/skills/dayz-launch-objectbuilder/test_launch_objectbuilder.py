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


def test_folder_passed_as_file_exits(tmp_path, capsys):
    """A folder must never reach ObjectBuilder.exe: it opens model files, not folders."""
    folder = tmp_path / "models"
    folder.mkdir()
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(str(folder), None)
    msg = str(exc.value.code)
    assert "--file is a folder" in msg and "Pass a .p3d file" in msg
    assert "not a .p3d" not in capsys.readouterr().out  # no misleading extension warning


def test_main_with_file_passes_the_resolved_p3d_to_objectbuilder(tmp_path, monkeypatch):
    exe = _fake_exe(tmp_path / "tools")
    _fake_launch_env(tmp_path / "tools", monkeypatch)
    monkeypatch.setattr(ob, "PROJECT_DIR", tmp_path)
    model = tmp_path / "data" / "model.p3d"
    model.parent.mkdir()
    model.write_bytes(b"")
    spawned = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            spawned["cmd"] = cmd

        def poll(self):
            return None

    monkeypatch.setattr(ob.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py", "--file", "data/model.p3d"])
    assert ob.main() == 0
    assert spawned["cmd"] == [str(exe), str(model.resolve())]


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


def test_mod_without_p3d_opens_the_editor_empty(tmp_path, monkeypatch, capsys):
    """A fresh scaffold has no model yet: no target, not a failure."""
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    (tmp_path / "MyMod" / "data").mkdir(parents=True)
    assert ob.resolve_target(None, "MyMod") is None
    out = capsys.readouterr().out
    assert "No .p3d under" in out and "opening Object Builder with no model" in out


def test_main_with_mod_without_p3d_launches_with_no_model(tmp_path, monkeypatch, capsys):
    exe = _fake_exe(tmp_path / "tools")
    _fake_launch_env(tmp_path / "tools", monkeypatch)
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    (tmp_path / "MyMod" / "data").mkdir(parents=True)
    spawned = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            spawned["cmd"] = cmd

        def poll(self):
            return None

    monkeypatch.setattr(ob.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py", "--mod", "MyMod"])
    assert ob.main() == 0
    assert spawned["cmd"] == [str(exe)]
    out = capsys.readouterr().out
    assert "No --file/--mod given" not in out  # --mod was given; say why there is no model instead
    assert "Object Builder launched" in out


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


def test_failed_tasklist_warns_instead_of_silently_saying_not_running(monkeypatch, capsys):
    import subprocess as sp

    monkeypatch.setattr(ob._setup.sys, "platform", "win32")
    monkeypatch.setattr(
        ob._setup.subprocess, "run",
        lambda cmd, **kw: sp.CompletedProcess(cmd, 1, stdout="", stderr="ERROR"),
    )
    assert ob.objectbuilder_running() is False
    err = capsys.readouterr().err
    assert "tasklist failed (exit code 1)" in err and "treating it as not running" in err


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


def test_mod_without_p3d_names_the_whole_mod_tree(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    (tmp_path / "MyMod" / "models").mkdir(parents=True)
    assert ob.resolve_target(None, "MyMod") is None
    assert f"No .p3d under {tmp_path / 'MyMod'} yet (searched every subfolder)" in capsys.readouterr().out


def _load_fresh_launcher():
    spec = importlib.util.spec_from_file_location("dayz_launch_objectbuilder_fresh", HERE / "launch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_project_dir_is_found_from_a_subfolder(tmp_path, monkeypatch):
    r"""Run from workspace\<mod>\, a relative --file resolves against the cached
    project, as in the sibling DayZ skills, not against the subfolder."""
    project = tmp_path / "proj"
    (project / ".claude" / "local-memory").mkdir(parents=True)
    (project / ".claude" / "local-memory" / "dayz-current-project.txt").write_text("x", encoding="utf-8")
    sub = project / "workspace" / "MyMod"
    sub.mkdir(parents=True)
    model = project / "data" / "model.p3d"
    model.parent.mkdir()
    model.write_bytes(b"")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(sub)
    fresh = _load_fresh_launcher()
    assert fresh.PROJECT_DIR == project.resolve()
    assert fresh.resolve_target("data/model.p3d", None) == model.resolve()


def test_project_dir_prefers_claude_project_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert _load_fresh_launcher().PROJECT_DIR == tmp_path.resolve()


@pytest.mark.parametrize(
    "bad", [r"..\Windows", "../etc", "1Mod", "My Mod", "My-Mod", r"C:\Mod", "Mod\n", "A" * 65]
)
def test_invalid_mod_name_is_refused_before_touching_p_drive(bad, tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    # Without the check, r"..\Windows" would resolve outside P:\ and report a "missing mod".
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, bad)
    assert "Invalid mod name" in str(exc.value.code)


def test_relative_file_falls_back_to_current_folder(tmp_path, monkeypatch):
    r"""`--file data\model.p3d` run from workspace\<mod>\ used to fail with
    "does not exist" because only the project root was tried."""
    project = tmp_path / "proj"
    project.mkdir()
    sub = project / "workspace" / "MyMod"
    model = sub / "data" / "model.p3d"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"")
    monkeypatch.setattr(ob, "PROJECT_DIR", project)
    monkeypatch.chdir(sub)
    assert ob.resolve_target("data/model.p3d", None) == model.resolve()


def test_relative_file_prefers_project_root_over_current_folder(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    sub = project / "workspace" / "MyMod"
    for base in (project, sub):
        (base / "data").mkdir(parents=True)
        (base / "data" / "model.p3d").write_bytes(b"")
    monkeypatch.setattr(ob, "PROJECT_DIR", project)
    monkeypatch.chdir(sub)
    assert ob.resolve_target("data/model.p3d", None) == (project / "data" / "model.p3d").resolve()


def test_missing_relative_file_names_every_base_folder_tried(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    sub = tmp_path / "elsewhere"
    project.mkdir()
    sub.mkdir()
    monkeypatch.setattr(ob, "PROJECT_DIR", project)
    monkeypatch.chdir(sub)
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target("data/model.p3d", None)
    msg = str(exc.value.code)
    assert "does not exist: data/model.p3d" in msg
    assert str((project / "data" / "model.p3d").resolve()) in msg
    assert str((sub / "data" / "model.p3d").resolve()) in msg


def test_many_p3d_listing_is_capped_with_a_count(tmp_path, monkeypatch):
    r"""A big tree used to print every path (8,256 for P:\DZ) before asking for --file."""
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    data = tmp_path / "MyMod" / "data"
    data.mkdir(parents=True)
    total = ob.MAX_LISTED_MODELS + 5
    names = [f"m{i:03d}.p3d" for i in range(total)]
    for name in names:
        (data / name).write_bytes(b"")
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, "MyMod")
    msg = str(exc.value.code)
    assert f"{total} .p3d files" in msg
    assert str(data / names[ob.MAX_LISTED_MODELS - 1]) in msg
    assert str(data / names[ob.MAX_LISTED_MODELS]) not in msg
    assert "... and 5 more" in msg


def test_exactly_the_cap_lists_all_without_a_count(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    data = tmp_path / "MyMod" / "data"
    data.mkdir(parents=True)
    for i in range(ob.MAX_LISTED_MODELS):
        (data / f"m{i:03d}.p3d").write_bytes(b"")
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, "MyMod")
    assert "more" not in str(exc.value.code)


@pytest.mark.parametrize("name", ["DZ", "dz", "scripts", "gui", "Mods"])
def test_vanilla_p_folder_is_refused_as_mod_without_scanning(name, tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    (tmp_path / name / "data").mkdir(parents=True)
    (tmp_path / name / "data" / "a.p3d").write_bytes(b"")
    (tmp_path / name / "data" / "b.p3d").write_bytes(b"")
    with pytest.raises(SystemExit) as exc:
        ob.resolve_target(None, name)
    msg = str(exc.value.code)
    assert "not a mod" in msg and "--file" in msg
    assert ".p3d files under" not in msg  # refused before the tree was scanned


def test_mod_name_starting_like_a_vanilla_folder_is_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(ob, "P_DRIVE", tmp_path)
    model = tmp_path / "DZ_Extra" / "data" / "a.p3d"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"")
    assert ob.resolve_target(None, "DZ_Extra") == model


def test_reserved_folders_come_from_launch_workbench():
    wb_py = Path(ob.__file__).resolve().parents[1] / "dayz-launch-workbench" / "launch.py"
    assert Path(ob._workbench.__file__).resolve() == wb_py
    assert ob.RESERVED_P_FOLDERS is ob._workbench.RESERVED_P_FOLDERS


def test_mod_name_rule_comes_from_new_mod():
    r"""One mod name rule, owned by /dayz-new-mod, which creates P:\<ModName>\."""
    new_mod_py = Path(ob.__file__).resolve().parents[1] / "dayz-new-mod" / "new_mod.py"
    assert Path(ob._new_mod.__file__).resolve() == new_mod_py
    assert ob.MOD_NAME_PATTERN is ob._new_mod.NAME_PATTERN
