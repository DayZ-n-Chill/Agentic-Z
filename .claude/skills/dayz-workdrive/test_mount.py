"""Tests for dayz-workdrive/mount.py: settings.ini parsing, resolution order, mount fallback."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "dayz_workdrive_mount", Path(__file__).resolve().parent / "mount.py"
)
mount = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mount)

# The real process check, kept before any fixture replaces it on the module.
_REAL_RUNNING_P_DRIVE_USERS = mount.running_p_drive_users


# ---------- read_settings_ini_path ----------

def _write_ini(tools: Path, text: str) -> None:
    tools.mkdir(parents=True, exist_ok=True)
    (tools / "settings.ini").write_text(text, encoding="utf-8")


def test_settings_ini_reads_projectdrive_path(tmp_path):
    _write_ini(tmp_path, "[Other]\npath=C:\\wrong\n[ProjectDrive]\npath=C:\\Work\\Drive\n")
    assert mount.read_settings_ini_path(tmp_path) == Path("C:\\Work\\Drive")


def test_settings_ini_is_case_insensitive_and_strips_quotes(tmp_path):
    _write_ini(tmp_path, '[projectdrive]\n  PATH = "D:\\P Drive"  \n')
    assert mount.read_settings_ini_path(tmp_path) == Path("D:\\P Drive")


def test_settings_ini_ignores_path_in_other_sections(tmp_path):
    _write_ini(tmp_path, "[Other]\npath=C:\\wrong\n")
    assert mount.read_settings_ini_path(tmp_path) is None


def test_settings_ini_empty_value_is_none(tmp_path):
    _write_ini(tmp_path, "[ProjectDrive]\npath=\n")
    assert mount.read_settings_ini_path(tmp_path) is None


def test_settings_ini_missing_file_is_none(tmp_path):
    assert mount.read_settings_ini_path(tmp_path) is None


# ---------- find_work_drive resolution order ----------

@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Point every source at nothing; each test turns on the sources it needs."""
    monkeypatch.delenv("DAYZ_WORK_DRIVE", raising=False)
    monkeypatch.setattr(mount, "CACHE", tmp_path / "cache" / "dayz-work-drive.json")
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(mount, "query_p_device", lambda: None)  # P: letter free, never the real machine's
    return tmp_path


def _dir(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir(parents=True)
    return d


def _tools_with_ini_and_default(root: Path, ini_target: Path | None) -> Path:
    """A DayZ Tools folder whose Bin/WorkDrive (the binaries folder) exists."""
    tools = _dir(root, "tools")
    _dir(tools, "Bin/WorkDrive")
    if ini_target is not None:
        _write_ini(tools, f"[ProjectDrive]\npath={ini_target}\n")
    return tools


def test_nothing_resolves_to_none(isolated):
    assert mount.find_work_drive() == (None, None)


def test_env_var_wins_over_everything(isolated, monkeypatch):
    env = _dir(isolated, "env")
    cached = _dir(isolated, "cached")
    mount.set_cached_path(cached)
    tools = _tools_with_ini_and_default(isolated, _dir(isolated, "ini"))
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(env))
    assert mount.find_work_drive() == (env.resolve(), "$DAYZ_WORK_DRIVE")


def test_cache_beats_settings_ini(isolated, monkeypatch):
    cached = _dir(isolated, "cached")
    mount.set_cached_path(cached)
    tools = _tools_with_ini_and_default(isolated, _dir(isolated, "ini"))
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == (cached, f"cache {mount.CACHE}")


def test_settings_ini_path_is_used_when_nothing_earlier_resolves(isolated, monkeypatch):
    ini = _dir(isolated, "ini")
    tools = _tools_with_ini_and_default(isolated, ini)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == (ini, str(tools / "settings.ini"))


def test_registry_is_not_a_source(isolated, monkeypatch):
    # The DayZ Tools registry keys hold the install path, never a work drive folder.
    tools = _tools_with_ini_and_default(isolated, None)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert not hasattr(mount, "read_registry_string")
    assert mount.find_work_drive() == (None, None)


def test_tools_binaries_folder_is_never_a_candidate(isolated, monkeypatch):
    tools = _tools_with_ini_and_default(isolated, None)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == (None, None)


def test_main_unresolved_fails_with_path_hint(isolated, monkeypatch, capsys):
    tools = _tools_with_ini_and_default(isolated, None)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setattr(mount, "is_p_mounted", lambda: False)
    monkeypatch.setattr(mount, "invoke_mount", lambda target: pytest.fail("must not mount"))
    monkeypatch.setattr("sys.argv", ["mount.py"])
    assert mount.main() == 1
    err = capsys.readouterr().err
    assert "Could not resolve a work drive folder" in err
    assert "--path" in err
    assert "Bin" not in err


def test_candidates_that_do_not_exist_are_skipped_with_a_warning(isolated, monkeypatch, capsys):
    real = _dir(isolated, "real")
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(isolated / "missing"))
    mount.CACHE.parent.mkdir(parents=True)
    mount.CACHE.write_text(json.dumps({"work_drive_path": str(isolated / "gone")}), encoding="utf-8")
    tools = _tools_with_ini_and_default(isolated, real)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == (real, str(tools / "settings.ini"))
    out = capsys.readouterr().out
    assert f"[WARN] $DAYZ_WORK_DRIVE is set to {isolated / 'missing'}, which is not a folder" in out


def test_settings_ini_path_that_is_not_a_folder_warns(isolated, monkeypatch, capsys):
    tools = _tools_with_ini_and_default(isolated, isolated / "typo")
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == (None, None)
    out = capsys.readouterr().out
    assert "[WARN]" in out and f"path={isolated / 'typo'}, which is not a folder" in out


def test_relative_env_var_is_made_absolute(isolated, monkeypatch):
    work = _dir(isolated, "PDrive")
    run_dir = _dir(isolated, "scripts")
    monkeypatch.chdir(run_dir)
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(Path("..") / "PDrive"))
    found, source = mount.find_work_drive()
    assert found.is_absolute() and found == work.resolve()
    assert source == "$DAYZ_WORK_DRIVE"


# ---------- invoke_mount subst fallback ----------

def test_subst_failure_reports_exit_code(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(mount, "find_workdrive_exe", lambda: None)
    monkeypatch.setattr(mount, "is_p_mounted", lambda: False)
    monkeypatch.setattr(mount.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=5))
    assert mount.invoke_mount(tmp_path) is False
    assert "exited with code 5" in capsys.readouterr().err


def test_subst_success_returns_true(monkeypatch, tmp_path):
    state = {"mounted": False}

    def fake_run(*a, **k):
        state["mounted"] = True
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(mount, "find_dayz_tools", lambda: None)
    monkeypatch.setattr(mount, "find_workdrive_exe", lambda: None)
    monkeypatch.setattr(mount, "is_p_mounted", lambda: state["mounted"])
    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    assert mount.invoke_mount(tmp_path) is True


# ---------- WorkDrive.exe and --unmount ----------

@pytest.fixture
def fake_drive(monkeypatch, tmp_path):
    """Fake P:\\ state plus a recorder for every command run.

    `effects` maps the first argument of a command (the exe path, or "subst")
    to the mounted state it leaves behind; commands not listed change nothing.
    The P: device follows the mounted state (a folder mapping while mounted, the
    letter free otherwise) unless a test sets state["device"]; `device_effects`
    maps a command to the device it leaves behind.
    """
    exe = tmp_path / "WorkDrive.exe"
    state = {"mounted": False, "calls": [], "effects": {}, "device_effects": {}}

    def fake_run(args, **kwargs):
        assert "shell" not in kwargs
        state["calls"].append(list(args))
        if args[0] in state["effects"]:
            state["mounted"] = state["effects"][args[0]]
            if state["mounted"] and len(args) == 3 and args[2] != "/D":
                state["target"] = args[2]  # WorkDrive.exe /Mount <folder> or subst P: <folder>
        if args[0] in state["device_effects"]:
            state["device"] = state["device_effects"][args[0]]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_device():
        if "device" in state:
            return state["device"]
        return "\\??\\" + state.get("target", "C:\\Fake\\Work") if state["mounted"] else None

    monkeypatch.setattr(mount, "find_workdrive_exe", lambda: exe)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: None)  # no settings.ini, so Letter= is P
    monkeypatch.setattr(mount, "is_p_mounted", lambda: state["mounted"])
    monkeypatch.setattr(mount, "query_p_device", fake_device)
    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    state["running"] = []  # processes the unmount guard sees; none by default
    monkeypatch.setattr(mount, "running_p_drive_users", lambda: state["running"])
    return exe, state


def test_settings_ini_reads_projectdrive_letter(tmp_path):
    _write_ini(tmp_path, "[ProjectDrive]\npath=C:\\Work\nLetter=q:\n")
    assert mount.read_settings_ini_letter(tmp_path) == "Q"


def test_letter_other_than_p_skips_workdrive_exe(fake_drive, monkeypatch, tmp_path, capsys):
    exe, state = fake_drive
    tools = tmp_path / "tools"
    _write_ini(tools, "[ProjectDrive]\npath=C:\\Work\nLetter=Q\n")
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    state["effects"]["subst"] = True
    assert mount.invoke_mount(tmp_path) is True
    assert state["calls"] == [["subst", "P:", str(tmp_path)]]
    out = capsys.readouterr().out
    assert "[WARN]" in out and "[ProjectDrive] Letter=Q," in out
    assert "would mount Q: instead of P:\\. Using subst P: instead." in out
    assert "(" not in out.split("[WARN]")[1].splitlines()[0]  # no tangled parenthetical


def test_letter_p_still_uses_workdrive_exe(fake_drive, monkeypatch, tmp_path):
    exe, state = fake_drive
    tools = tmp_path / "tools"
    _write_ini(tools, "[ProjectDrive]\npath=C:\\Work\nLetter=P\n")
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    state["effects"][str(exe)] = True
    assert mount.invoke_mount(tmp_path) is True
    assert state["calls"] == [[str(exe), "/Mount", str(tmp_path)]]


def test_unmount_with_letter_other_than_p_uses_subst_d(fake_drive, monkeypatch, tmp_path):
    exe, state = fake_drive
    tools = tmp_path / "tools"
    _write_ini(tools, "[ProjectDrive]\nLetter=Q\n")
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    state["mounted"] = True
    state["effects"]["subst"] = False
    assert mount.invoke_unmount() == 0
    assert state["calls"] == [["subst", "P:", "/D"]]


def test_workdrive_exe_success_skips_subst(fake_drive, tmp_path):
    exe, state = fake_drive
    state["effects"][str(exe)] = True
    assert mount.invoke_mount(tmp_path) is True
    assert state["calls"] == [[str(exe), "/Mount", str(tmp_path)]]


def test_workdrive_exe_no_mount_falls_back_to_subst(fake_drive, tmp_path, capsys):
    exe, state = fake_drive
    state["effects"]["subst"] = True
    assert mount.invoke_mount(tmp_path) is True
    assert state["calls"] == [[str(exe), "/Mount", str(tmp_path)], ["subst", "P:", str(tmp_path)]]
    assert "falling back to subst" in capsys.readouterr().out


def test_main_success_caches_folder(fake_drive, monkeypatch, tmp_path):
    exe, state = fake_drive
    state["effects"][str(exe)] = True
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(mount, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", str(work)])
    assert mount.main() == 0
    assert mount.get_cached_path() == work


def test_main_names_the_source_on_the_mounting_line(fake_drive, monkeypatch, tmp_path, capsys):
    exe, state = fake_drive
    state["effects"][str(exe)] = True
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(mount, "CACHE", tmp_path / "cache.json")
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(work))
    monkeypatch.setattr("sys.argv", ["mount.py"])
    assert mount.main() == 0
    assert f"[INFO] Mounting P: -> {work.resolve()} (from $DAYZ_WORK_DRIVE)" in capsys.readouterr().out


def test_main_fails_and_does_not_cache_when_p_shows_another_folder(fake_drive, monkeypatch, tmp_path, capsys):
    exe, state = fake_drive
    state["effects"][str(exe)] = True
    state["device_effects"][str(exe)] = "\\??\\C:\\Somewhere\\Else"
    work = tmp_path / "work"
    work.mkdir()
    cache = tmp_path / "cache.json"
    monkeypatch.setattr(mount, "CACHE", cache)
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", str(work)])
    assert mount.main() == 1
    captured = capsys.readouterr()
    assert "points to C:\\Somewhere\\Else, not" in captured.err and "--unmount" in captured.err
    assert "[OK]   P:\\ mounted" not in captured.out
    assert not cache.exists()


def test_main_warns_and_exits_0_when_cache_cannot_be_written(fake_drive, monkeypatch, tmp_path, capsys):
    exe, state = fake_drive
    state["effects"][str(exe)] = True
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr(mount, "CACHE", tmp_path / "cache.json")

    def read_only(_p):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(mount, "set_cached_path", read_only)
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", str(work)])
    assert mount.main() == 0
    out = capsys.readouterr().out
    assert f"[OK]   P:\\ mounted -> {work}" in out
    assert "[WARN]" in out and "was not cached" in out and "Permission denied" in out


def test_main_relative_path_is_mounted_and_cached_absolute(fake_drive, monkeypatch, tmp_path):
    exe, state = fake_drive
    state["effects"][str(exe)] = True
    work = tmp_path / "PDrive"
    work.mkdir()
    run_dir = tmp_path / "scripts"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)
    monkeypatch.setattr(mount, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", "..\\PDrive" if mount.sys.platform == "win32" else "../PDrive"])
    assert mount.main() == 0
    expected = work.resolve()
    assert state["calls"] == [[str(exe), "/Mount", str(expected)]]
    cached = json.loads((tmp_path / "cache.json").read_text(encoding="utf-8"))["work_drive_path"]
    assert Path(cached).is_absolute() and Path(cached) == expected
    monkeypatch.chdir(tmp_path)  # a later run from another folder still finds it
    assert mount.get_cached_path() == expected


def test_run_workdrive_passes_a_timeout(monkeypatch):
    seen = {}

    def fake_run(args, **kwargs):
        seen.update(kwargs)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    mount._run_workdrive(["WorkDrive.exe", "/Mount", "C:\\Work"])
    assert seen["timeout"] == mount.WORKDRIVE_TIMEOUT


def test_hung_workdrive_exe_falls_through_to_subst(fake_drive, monkeypatch, tmp_path, capsys):
    exe, state = fake_drive
    calls = state["calls"]

    def fake_run(args, **kwargs):
        calls.append(list(args))
        if args[0] == str(exe):
            raise mount.subprocess.TimeoutExpired(args, kwargs.get("timeout"))
        state["mounted"] = True
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    assert mount.invoke_mount(tmp_path) is True
    assert calls == [[str(exe), "/Mount", str(tmp_path)], ["subst", "P:", str(tmp_path)]]
    captured = capsys.readouterr()
    assert "rc=-1" in captured.out and "falling back to subst" in captured.out
    assert "did not exit within" in captured.err


def test_main_already_mounted_runs_nothing(fake_drive, monkeypatch):
    _, state = fake_drive
    state["mounted"] = True
    monkeypatch.setattr("sys.argv", ["mount.py"])
    assert mount.main() == 0
    assert state["calls"] == []


def test_unmount_when_not_mounted_is_noop(fake_drive, monkeypatch):
    _, state = fake_drive
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 0
    assert state["calls"] == []


def test_unmount_via_workdrive_exe(fake_drive, monkeypatch):
    exe, state = fake_drive
    state["mounted"] = True
    state["effects"][str(exe)] = False
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 0
    assert state["calls"] == [[str(exe), "/Dismount"]]


def test_unmount_falls_back_to_subst_d(fake_drive, monkeypatch):
    exe, state = fake_drive
    state["mounted"] = True
    state["effects"]["subst"] = False
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 0
    assert state["calls"] == [[str(exe), "/Dismount"], ["subst", "P:", "/D"]]


def test_unmount_fails_when_drive_stays(fake_drive, monkeypatch, capsys):
    _, state = fake_drive
    state["mounted"] = True
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 1
    assert "still mounted=True" in capsys.readouterr().err


# ---------- --unmount guard against running DayZ Tools / DayZDiag ----------

TASKLIST_CSV = (
    '"System Idle Process","0","Services","0","8 K"\n'
    '"WorkbenchApp.exe","4120","Console","1","812,004 K"\n'
    '"notepad.exe","5000","Console","1","9,000 K"\n'
    '"DayZDiag_x64.exe","6100","Console","1","2,100,000 K"\n'
    '"DayZDiag_x64.exe","6200","Console","1","1,900,000 K"\n'
)


def test_parse_tasklist_images_reads_first_column():
    assert mount.parse_tasklist_images(TASKLIST_CSV) == [
        "System Idle Process", "WorkbenchApp.exe", "notepad.exe", "DayZDiag_x64.exe", "DayZDiag_x64.exe",
    ]


def test_running_p_drive_users_matches_case_insensitively_and_dedupes(monkeypatch):
    calls = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        return SimpleNamespace(returncode=0, stdout=TASKLIST_CSV.replace("WorkbenchApp", "workbenchapp"), stderr="")

    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    assert mount.running_p_drive_users() == ["DayZDiag_x64.exe", "workbenchapp.exe"]
    assert calls == [["tasklist", "/FO", "CSV", "/NH"]]


@pytest.mark.parametrize("name", ["WorkbenchApp.exe", "ObjectBuilder.exe", "AddonBuilder.exe",
                                  "binarize.exe", "DayZDiag_x64.exe"])
def test_unmount_refuses_while_p_drive_user_runs(fake_drive, monkeypatch, capsys, name):
    exe, state = fake_drive
    state["mounted"] = True
    state["effects"][str(exe)] = False
    state["running"] = [name]
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 1
    assert state["calls"] == []  # nothing dismounted
    assert state["mounted"] is True
    err = capsys.readouterr().err
    assert name in err and "--force" in err


def test_unmount_force_proceeds_with_warning(fake_drive, monkeypatch, capsys):
    exe, state = fake_drive
    state["mounted"] = True
    state["effects"][str(exe)] = False
    state["running"] = ["ObjectBuilder.exe"]
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount", "--force"])
    assert mount.main() == 0
    assert state["calls"] == [[str(exe), "/Dismount"]]
    assert "--force" in capsys.readouterr().out


@pytest.mark.parametrize("result", [
    SimpleNamespace(returncode=1, stdout="", stderr="ERROR: Access denied"),
    SimpleNamespace(returncode=0, stdout="", stderr=""),
    SimpleNamespace(returncode=0, stdout="  \r\n", stderr=""),
], ids=["nonzero-exit", "empty-output", "blank-output"])
def test_running_p_drive_users_unknown_when_tasklist_fails(monkeypatch, result):
    monkeypatch.setattr(mount.subprocess, "run", lambda *a, **k: result)
    assert mount.running_p_drive_users() is None


def test_running_p_drive_users_unknown_when_tasklist_cannot_start(monkeypatch):
    def fake_run(*a, **k):
        raise FileNotFoundError("tasklist")

    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    assert mount.running_p_drive_users() is None


def test_unmount_refuses_when_process_list_is_unknown(fake_drive, monkeypatch, capsys):
    exe, state = fake_drive
    state["mounted"] = True
    state["effects"][str(exe)] = False
    state["running"] = None  # tasklist failed
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 1
    assert state["calls"] == []
    assert state["mounted"] is True
    err = capsys.readouterr().err
    assert "tasklist failed" in err and "--force" in err


def test_unmount_force_proceeds_when_process_list_is_unknown(fake_drive, monkeypatch, capsys):
    exe, state = fake_drive
    state["mounted"] = True
    state["effects"][str(exe)] = False
    state["running"] = None
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount", "--force"])
    assert mount.main() == 0
    assert state["calls"] == [[str(exe), "/Dismount"]]
    assert "could not list running processes" in capsys.readouterr().out


def test_unmount_with_real_tasklist_failure_refuses(fake_drive, monkeypatch, capsys):
    # End to end through the real running_p_drive_users: a failing tasklist must not
    # read as "nothing running".
    exe, state = fake_drive
    state["mounted"] = True
    monkeypatch.setattr(mount, "running_p_drive_users", _REAL_RUNNING_P_DRIVE_USERS)

    def fake_run(args, **kwargs):
        state["calls"].append(list(args))
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 1
    assert state["calls"] == [["tasklist", "/FO", "CSV", "/NH"]]  # no dismount ran


@pytest.mark.parametrize("argv", [["--force"], ["--path", "C:\\Work", "--force"], ["--unmount", "--path", "C:\\Work"]])
def test_flags_that_would_be_ignored_are_rejected(fake_drive, monkeypatch, capsys, argv):
    _, state = fake_drive
    monkeypatch.setattr("sys.argv", ["mount.py", *argv])
    with pytest.raises(SystemExit) as exc:
        mount.main()
    assert exc.value.code == 2
    assert state["calls"] == []
    err = capsys.readouterr().err
    assert "--force only applies to --unmount" in err or "--path cannot be combined with --unmount" in err


def test_unmount_guard_not_checked_when_not_mounted(fake_drive, monkeypatch):
    _, state = fake_drive
    state["running"] = ["DayZDiag_x64.exe"]
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 0
    assert state["calls"] == []


# ---------- --path while already mounted ----------

def test_main_warns_when_path_differs_from_current_target(fake_drive, monkeypatch, tmp_path, capsys):
    _, state = fake_drive
    state["mounted"] = True
    monkeypatch.setattr(mount, "current_p_target", lambda: tmp_path / "current")
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", str(tmp_path / "other")])
    assert mount.main() == 0
    out = capsys.readouterr().out
    assert "--path was not used" in out and str(tmp_path / "current") in out
    assert state["calls"] == []


def test_main_no_warning_when_path_matches_ignoring_case(fake_drive, monkeypatch, tmp_path, capsys):
    _, state = fake_drive
    state["mounted"] = True
    monkeypatch.setattr(mount, "current_p_target", lambda: Path(r"C:\Work\Drive"))
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", "c:\\work\\drive\\"])
    assert mount.main() == 0
    assert "--path was not used" not in capsys.readouterr().out


def test_main_warns_when_p_is_not_a_folder_mapping(fake_drive, monkeypatch, tmp_path, capsys):
    _, state = fake_drive
    state["mounted"] = True
    monkeypatch.setattr(mount, "current_p_target", lambda: None)
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", str(tmp_path / "other")])
    assert mount.main() == 0
    out = capsys.readouterr().out
    assert "--path was not used" in out and "not a folder mapping" in out and "--unmount" in out
    assert state["calls"] == []


def test_current_p_target_none_off_windows(monkeypatch):
    monkeypatch.setattr(mount.sys, "platform", "linux")
    assert mount.current_p_target() is None


def test_cache_follows_claude_project_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("dayz_workdrive_mount_env", Path(mount.__file__))
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    assert fresh.CACHE == tmp_path.resolve() / ".claude" / "local-memory" / "dayz-work-drive.json"


def test_cache_from_a_subfolder_goes_to_the_project_root(monkeypatch, tmp_path):
    project = tmp_path / "project"
    memory = project / ".claude" / "local-memory"
    memory.mkdir(parents=True)
    (memory / "dayz-current-project.txt").write_text(str(project), encoding="utf-8")
    sub = project / "scripts" / "setup"
    sub.mkdir(parents=True)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(sub)
    spec = importlib.util.spec_from_file_location("dayz_workdrive_mount_sub", Path(mount.__file__))
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    assert fresh.CACHE == project.resolve() / ".claude" / "local-memory" / "dayz-work-drive.json"


# ---------- stale mappings, volumes and network drives on P: ----------

STALE = r"\??\C:\Gone\Work"
VOLUME = r"\Device\HarddiskVolume3"


def test_current_p_target_reads_folder_mappings_only(monkeypatch):
    monkeypatch.setattr(mount, "query_p_device", lambda: STALE)
    assert mount.current_p_target() == Path(r"C:\Gone\Work")
    monkeypatch.setattr(mount, "query_p_device", lambda: VOLUME)
    assert mount.current_p_target() is None
    monkeypatch.setattr(mount, "query_p_device", lambda: None)
    assert mount.current_p_target() is None


def test_query_p_device_none_off_windows(monkeypatch):
    monkeypatch.setattr(mount.sys, "platform", "linux")
    assert mount.query_p_device() is None


def test_unmount_removes_stale_mapping(fake_drive, monkeypatch, capsys):
    # The folder behind P: is gone: P:\ is not a directory, but the mapping still holds the letter.
    _, state = fake_drive
    state["device"] = STALE
    state["device_effects"]["subst"] = None
    state["running"] = ["WorkbenchApp.exe"]  # nothing can work from an invisible P:\, so no guard
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 0
    assert state["calls"] == [["subst", "P:", "/D"]]
    out = capsys.readouterr().out
    assert r"C:\Gone\Work" in out and "stale mapping" in out
    assert "not currently mounted" not in out


def test_unmount_stale_mapping_that_stays_fails(fake_drive, monkeypatch, capsys):
    _, state = fake_drive
    state["device"] = STALE
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 1
    assert "stale P: mapping" in capsys.readouterr().err


def test_mount_with_stale_mapping_names_folder_and_fix(fake_drive, monkeypatch, tmp_path, capsys):
    _, state = fake_drive
    state["device"] = STALE
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", str(work)])
    assert mount.main() == 1
    err = capsys.readouterr().err
    assert r"mapped to a missing folder C:\Gone\Work" in err and "--unmount" in err
    assert state["calls"] == []


def test_mount_with_unreachable_device_on_p_fails_clearly(fake_drive, monkeypatch, tmp_path, capsys):
    _, state = fake_drive
    state["device"] = r"\Device\LanmanRedirector\;P:0000\server\share"
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setattr("sys.argv", ["mount.py", "--path", str(work)])
    assert mount.main() == 1
    err = capsys.readouterr().err
    assert "LanmanRedirector" in err and "net use P: /delete" in err
    assert state["calls"] == []


def test_unmount_refuses_on_a_volume(fake_drive, monkeypatch, capsys):
    _, state = fake_drive
    state["mounted"] = True
    state["device"] = VOLUME
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount", "--force"])
    assert mount.main() == 1
    err = capsys.readouterr().err
    assert VOLUME in err and "not a folder mapping" in err
    assert "still mounted" not in err
    assert state["calls"] == []


def test_unmount_refuses_on_unreachable_non_folder_device(fake_drive, monkeypatch, capsys):
    _, state = fake_drive
    state["device"] = VOLUME
    monkeypatch.setattr("sys.argv", ["mount.py", "--unmount"])
    assert mount.main() == 1
    assert "cannot remove it" in capsys.readouterr().err
    assert state["calls"] == []


# ---------- cache contents and platform ----------

@pytest.mark.parametrize("text", ["[]", r'"C:\\Work"', "42", "null", '{"work_drive_path": 5}', "{not json"])
def test_cache_that_is_not_the_expected_object_is_no_cache(isolated, text):
    mount.CACHE.parent.mkdir(parents=True)
    mount.CACHE.write_text(text, encoding="utf-8")
    assert mount.get_cached_path() is None
    assert mount.find_work_drive() == (None, None)


def test_main_off_windows_fails_with_windows_only(monkeypatch, capsys):
    monkeypatch.setattr(mount.sys, "platform", "linux")
    monkeypatch.setattr(mount.subprocess, "run", lambda *a, **k: pytest.fail("must not run anything"))
    for argv in (["mount.py"], ["mount.py", "--unmount"]):
        monkeypatch.setattr("sys.argv", argv)
        assert mount.main() == 1
        assert "[FAIL] Windows-only" in capsys.readouterr().err
