"""Tests for the Workbench launcher: flags, mod name and gproj resolution, exit paths, the single-instance guard and the startup check."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_launch_workbench_under_test", HERE / "launch.py")
wb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wb)


@pytest.fixture
def p_drive(monkeypatch, tmp_path):
    drive = tmp_path / "P"
    drive.mkdir()
    monkeypatch.setattr(wb, "P_DRIVE", drive)
    return drive


def _fake_exe(root, bundled_gproj=True):
    r"""workbenchApp.exe under <root>\Bin\Workbench, with the dayz.gproj DayZ Tools ships beside it."""
    exe = root / "Bin" / "Workbench" / "workbenchApp.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    if bundled_gproj:
        (exe.parent / "dayz.gproj").write_text("")
    return exe


def test_mod_and_gproj_are_mutually_exclusive():
    with pytest.raises(SystemExit) as exc:
        wb.build_parser().parse_args(["--mod", "MyMod", "--gproj", "x.gproj"])
    assert exc.value.code == 2


def test_no_flags_means_bundled_gproj():
    assert wb.resolve_gproj(None, None) is None


def test_mod_resolves_to_workbench_gproj(p_drive):
    gproj = p_drive / "MyMod" / "workbench" / "dayz.gproj"
    gproj.parent.mkdir(parents=True)
    gproj.write_text("", encoding="utf-8")
    assert wb.resolve_gproj("MyMod", None) == gproj


def test_missing_mod_folder_points_at_new_mod(p_drive):
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj("MyMod", None)
    assert "/dayz-new-mod MyMod" in str(exc.value.code)


def test_missing_gproj_points_at_add_scaffold(p_drive):
    (p_drive / "MyMod").mkdir()
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj("MyMod", None)
    assert "/dayz-add-scaffold MyMod --piece workbench" in str(exc.value.code)


def test_relative_gproj_resolves_against_project(tmp_path, monkeypatch):
    monkeypatch.setattr(wb, "PROJECT_DIR", tmp_path)
    (tmp_path / "custom.gproj").write_text("", encoding="utf-8")
    assert wb.resolve_gproj(None, "custom.gproj") == (tmp_path / "custom.gproj").resolve()


def test_missing_gproj_path_exits(tmp_path):
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj(None, str(tmp_path / "nope.gproj"))
    assert "does not exist" in str(exc.value.code)


def test_wrong_extension_warns(tmp_path, capsys):
    other = tmp_path / "project.txt"
    other.write_text("", encoding="utf-8")
    assert wb.resolve_gproj(None, str(other)) == other
    assert "not a .gproj" in capsys.readouterr().out


def test_launch_uses_shared_detach_flags_and_workbench_cwd(tmp_path, monkeypatch):
    exe = _fake_exe(tmp_path)
    spawned = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            spawned.update(cmd=cmd, **kwargs)

        def poll(self):
            return None  # still running

    class FakePreflight:
        @staticmethod
        def find_dayz_tools():
            return tmp_path

    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", FakePreflight, raising=False)
    monkeypatch.setattr(wb, "running_workbench_pids", lambda: [])
    monkeypatch.setattr(wb.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 0
    assert spawned["cmd"] == [str(exe)]
    assert spawned["creationflags"] == wb.h.DETACH_FLAGS
    assert spawned["cwd"] == str(exe.parent)


def test_launch_passes_mod_gproj_through_gproj_switch(tmp_path, monkeypatch):
    exe = _fake_exe(tmp_path)
    gproj = tmp_path / "P" / "MyMod" / "workbench" / "dayz.gproj"
    gproj.parent.mkdir(parents=True)
    gproj.write_text("")
    spawned = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            spawned.update(cmd=cmd, **kwargs)

        def poll(self):
            return None  # still running

    class FakePreflight:
        @staticmethod
        def find_dayz_tools():
            return tmp_path

    monkeypatch.setattr(wb, "P_DRIVE", tmp_path / "P")
    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", FakePreflight, raising=False)
    monkeypatch.setattr(wb, "running_workbench_pids", lambda: [])
    monkeypatch.setattr(wb.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py", "--mod", "MyMod"])
    assert wb.main() == 0
    assert spawned["cmd"] == [str(exe), f"-gproj={gproj}"]


def _no_spawn(*args, **kwargs):
    pytest.fail("spawned workbenchApp.exe")


def _tools_at(root):
    class FakePreflight:
        @staticmethod
        def find_dayz_tools():
            return root

    return FakePreflight


def test_failed_preflight_stops_the_launch(monkeypatch):
    def preflight_fails():
        raise SystemExit(1)

    class NoTools:
        @staticmethod
        def find_dayz_tools():
            pytest.fail("looked for DayZ Tools after a failed preflight")

    monkeypatch.setattr(wb.h, "gate_on_preflight", preflight_fails)
    monkeypatch.setattr(wb.h, "preflight", NoTools, raising=False)
    monkeypatch.setattr(wb.subprocess, "Popen", _no_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py", "--mod", "MyMod"])
    with pytest.raises(SystemExit) as exc:
        wb.main()
    assert exc.value.code == 1


def test_missing_dayz_tools_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(None), raising=False)
    monkeypatch.setattr(wb.subprocess, "Popen", _no_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 1
    assert "DayZ Tools not found" in capsys.readouterr().err


def test_missing_workbench_exe_exits_1(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(tmp_path), raising=False)
    monkeypatch.setattr(wb.subprocess, "Popen", _no_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 1
    err = capsys.readouterr().err
    assert "workbenchApp.exe not found" in err
    assert str(tmp_path / "Bin" / "Workbench" / "workbenchApp.exe") in err


def test_running_workbench_refuses_a_second_launch(tmp_path, monkeypatch, capsys):
    exe = _fake_exe(tmp_path)
    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(tmp_path), raising=False)
    monkeypatch.setattr(wb, "running_workbench_pids", lambda: [1234])
    monkeypatch.setattr(wb.subprocess, "Popen", _no_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 1
    assert "already running (PID 1234)" in capsys.readouterr().err


def test_running_workbench_pids_parses_tasklist(monkeypatch):
    out = (
        '"WorkbenchApp.exe","1234","Console","1","500,000 K"\n'
        '"workbenchApp.exe","5678","Console","1","400,000 K"\n'
    )
    seen = {}

    def fake_check_output(cmd, **kwargs):
        seen["cmd"] = cmd
        return out

    monkeypatch.setattr(wb.subprocess, "check_output", fake_check_output)
    assert wb.running_workbench_pids() == [1234, 5678]
    assert "IMAGENAME eq workbenchApp.exe" in seen["cmd"]


def test_running_workbench_pids_empty_when_none_match(monkeypatch):
    monkeypatch.setattr(
        wb.subprocess,
        "check_output",
        lambda cmd, **kw: "INFO: No tasks are running which match the specified criteria.\n",
    )
    assert wb.running_workbench_pids() == []


def test_process_that_exits_at_once_is_reported_as_failure(tmp_path, monkeypatch, capsys):
    """A workbenchApp.exe that dies on start (bad gproj, missing DLL) must not report success."""
    exe = _fake_exe(tmp_path)

    class DiesAtOnce:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            pass

        def poll(self):
            return 3

    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(tmp_path), raising=False)
    monkeypatch.setattr(wb, "running_workbench_pids", lambda: [])
    monkeypatch.setattr(wb.subprocess, "Popen", DiesAtOnce)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 1
    out = capsys.readouterr()
    assert "exited right after starting (exit code 3)" in out.err
    assert "Workbench launched" not in out.out


def test_wait_for_early_exit_polls_until_exit_within_window(monkeypatch):
    monkeypatch.setattr(wb, "STARTUP_POLL_INTERVAL", 0)
    results = iter([None, None, 5])

    class ExitsLater:
        polls = 0

        def poll(self):
            ExitsLater.polls += 1
            return next(results)

    assert wb.wait_for_early_exit(ExitsLater()) == 5
    assert ExitsLater.polls == 3


def test_wait_for_early_exit_returns_none_when_still_running(monkeypatch):
    clock = iter([0.0, 0.5, 1.5])  # deadline set at 0.0; second check passes it
    monkeypatch.setattr(wb.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(wb.time, "sleep", lambda s: None)

    class Running:
        def poll(self):
            return None

    assert wb.wait_for_early_exit(Running()) is None


@pytest.mark.parametrize(
    "bad", [r"..\Windows", "../etc", "1Mod", "My Mod", "My-Mod", r"C:\Mod", "Mod\n", "A" * 65]
)
def test_invalid_mod_name_is_refused_before_touching_p_drive(bad, p_drive):
    # Without the check, r"..\Windows" would resolve outside P:\ and report a "missing mod".
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj(bad, None)
    assert "Invalid mod name" in str(exc.value.code)


def test_mod_name_rule_comes_from_new_mod():
    r"""One mod name rule, owned by /dayz-new-mod, which creates P:\<ModName>\."""
    new_mod_py = HERE.parent / "dayz-new-mod" / "new_mod.py"
    assert Path(wb._new_mod.__file__).resolve() == new_mod_py
    assert wb.MOD_NAME_PATTERN is wb._new_mod.NAME_PATTERN




def test_invalid_mod_name_fails_before_preflight(monkeypatch, capsys):
    def no_preflight():
        pytest.fail("ran preflight for a mod name that was never valid")

    monkeypatch.setattr(wb.h, "gate_on_preflight", no_preflight)
    monkeypatch.setattr(wb.subprocess, "Popen", _no_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py", "--mod", "My-Mod"])
    with pytest.raises(SystemExit) as exc:
        wb.main()
    assert "Invalid mod name" in str(exc.value.code)


def test_missing_mod_gproj_is_reported_before_dayz_tools_lookup(p_drive, monkeypatch):
    class NoToolsLookup:
        @staticmethod
        def find_dayz_tools():
            pytest.fail("looked for DayZ Tools before checking the --mod target")

    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", NoToolsLookup, raising=False)
    monkeypatch.setattr(wb.subprocess, "Popen", _no_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py", "--mod", "MyMod"])
    with pytest.raises(SystemExit) as exc:
        wb.main()
    assert "/dayz-new-mod MyMod" in str(exc.value.code)


@pytest.mark.parametrize("name", ["dz", "DZ", "scripts", "gui", "languagecore", "system", "Mods"])
def test_reserved_p_folder_is_refused_as_mod(name, p_drive):
    # P:\dz exists on every set-up machine; without the check the user was told
    # to run /dayz-add-scaffold dz --piece workbench.
    (p_drive / name).mkdir()
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj(name, None)
    msg = str(exc.value.code)
    assert "not a mod" in msg
    assert "Run without --mod" in msg
    assert "/dayz-add-scaffold" not in msg


def test_ordinary_mod_name_is_not_reserved(p_drive):
    (p_drive / "DZ_Extra" / "workbench").mkdir(parents=True)
    (p_drive / "DZ_Extra" / "workbench" / "dayz.gproj").write_text("", encoding="utf-8")
    assert wb.resolve_gproj("DZ_Extra", None) == p_drive / "DZ_Extra" / "workbench" / "dayz.gproj"


@pytest.mark.parametrize(
    "error",
    [FileNotFoundError("tasklist"), wb.subprocess.CalledProcessError(1, ["tasklist"])],
)
def test_tasklist_failure_warns_instead_of_silently_skipping_the_guard(error, monkeypatch, capsys):
    def broken(cmd, **kwargs):
        raise error

    monkeypatch.setattr(wb.subprocess, "check_output", broken)
    assert wb.running_workbench_pids() == []
    err = capsys.readouterr().err
    assert "tasklist failed" in err
    assert "cannot check for a running Workbench" in err


def test_spawn_oserror_exits_1(tmp_path, monkeypatch, capsys):
    _fake_exe(tmp_path)

    def cannot_spawn(cmd, **kwargs):
        raise OSError(193, "%1 is not a valid Win32 application")

    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(tmp_path), raising=False)
    monkeypatch.setattr(wb, "running_workbench_pids", lambda: [])
    monkeypatch.setattr(wb.subprocess, "Popen", cannot_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 1
    out = capsys.readouterr()
    assert "Failed to spawn workbenchApp.exe" in out.err
    assert "not a valid Win32 application" in out.err
    assert "Workbench launched" not in out.out


def test_gproj_path_with_spaces_is_refused(tmp_path):
    # Workbench is not confirmed to open a quoted "-gproj=<path with spaces>",
    # so such a path must fail clearly instead of being handed over.
    gproj = tmp_path / "My Path" / "my project.gproj"
    gproj.parent.mkdir()
    gproj.write_text("")
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj(None, str(gproj))
    msg = str(exc.value.code)
    assert "contains a space" in msg
    assert "P:\\" in msg


def test_gproj_directory_is_refused(tmp_path):
    # A folder such as P:\MyMod\workbench passed Path.exists() and was handed
    # to Workbench as -gproj=<folder>.
    folder = tmp_path / "workbench"
    folder.mkdir()
    with pytest.raises(SystemExit) as exc:
        wb.resolve_gproj(None, str(folder))
    assert "is a folder, not a project file" in str(exc.value.code)


def test_vanilla_launch_without_bundled_gproj_exits_1(tmp_path, monkeypatch, capsys):
    # On a partial DayZ Tools install Workbench reports "cannot find file
    # dayz.gproj", possibly in a dialog that outlives the startup check.
    exe = _fake_exe(tmp_path, bundled_gproj=False)
    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(tmp_path), raising=False)
    monkeypatch.setattr(wb, "running_workbench_pids", lambda: [])
    monkeypatch.setattr(wb.subprocess, "Popen", _no_spawn)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 1
    err = capsys.readouterr().err
    assert f"Bundled dayz.gproj not found at {exe.parent / 'dayz.gproj'}" in err
    assert "Verify" in err and "Steam" in err


def test_mod_launch_does_not_need_bundled_gproj(tmp_path, monkeypatch):
    exe = _fake_exe(tmp_path, bundled_gproj=False)
    gproj = tmp_path / "P" / "MyMod" / "workbench" / "dayz.gproj"
    gproj.parent.mkdir(parents=True)
    gproj.write_text("")
    spawned = {}

    class FakePopen:
        pid = 4242

        def __init__(self, cmd, **kwargs):
            spawned["cmd"] = cmd

        def poll(self):
            return None

    monkeypatch.setattr(wb, "P_DRIVE", tmp_path / "P")
    monkeypatch.setattr(wb.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(tmp_path), raising=False)
    monkeypatch.setattr(wb, "running_workbench_pids", lambda: [])
    monkeypatch.setattr(wb.subprocess, "Popen", FakePopen)
    monkeypatch.setattr("sys.argv", ["launch.py", "--mod", "MyMod"])
    assert wb.main() == 0
    assert spawned["cmd"] == [str(exe), f"-gproj={gproj}"]


def test_stdout_is_line_buffered_so_output_keeps_order_with_preflight(monkeypatch):
    # Preflight is a child process writing to the console directly; with a
    # block-buffered pipe the "DayZ Workbench launcher" header printed after it.
    import io
    import sys

    stream = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    seen = {}

    def preflight():
        seen["header_flushed"] = b"DayZ Workbench launcher" in stream.buffer.getvalue()

    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(wb.h, "gate_on_preflight", preflight)
    monkeypatch.setattr(wb.h, "preflight", _tools_at(None), raising=False)
    monkeypatch.setattr("sys.argv", ["launch.py"])
    assert wb.main() == 1
    assert seen["header_flushed"]
