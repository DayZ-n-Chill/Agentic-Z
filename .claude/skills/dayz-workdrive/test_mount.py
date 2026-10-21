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
    monkeypatch.setattr(mount, "read_registry_string", lambda *a: None)
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
    assert mount.find_work_drive() is None


def test_env_var_wins_over_everything(isolated, monkeypatch):
    env = _dir(isolated, "env")
    cached = _dir(isolated, "cached")
    mount.set_cached_path(cached)
    tools = _tools_with_ini_and_default(isolated, _dir(isolated, "ini"))
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(env))
    assert mount.find_work_drive() == env


def test_cache_beats_settings_ini(isolated, monkeypatch):
    cached = _dir(isolated, "cached")
    mount.set_cached_path(cached)
    tools = _tools_with_ini_and_default(isolated, _dir(isolated, "ini"))
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == cached


def test_settings_ini_beats_registry_and_default(isolated, monkeypatch):
    ini = _dir(isolated, "ini")
    reg = _dir(isolated, "reg")
    tools = _tools_with_ini_and_default(isolated, ini)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setattr(mount, "read_registry_string", lambda *a: str(reg))
    assert mount.find_work_drive() == ini


@pytest.mark.skipif(mount.sys.platform != "win32", reason="registry lookup is Windows-only")
def test_registry_used_when_settings_ini_has_no_path(isolated, monkeypatch):
    reg = _dir(isolated, "reg")
    tools = _tools_with_ini_and_default(isolated, None)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    monkeypatch.setattr(mount, "read_registry_string", lambda *a: str(reg))
    assert mount.find_work_drive() == reg


def test_tools_binaries_folder_is_never_a_candidate(isolated, monkeypatch):
    tools = _tools_with_ini_and_default(isolated, None)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() is None


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


def test_candidates_that_do_not_exist_are_skipped(isolated, monkeypatch):
    real = _dir(isolated, "real")
    monkeypatch.setenv("DAYZ_WORK_DRIVE", str(isolated / "missing"))
    mount.CACHE.parent.mkdir(parents=True)
    mount.CACHE.write_text(json.dumps({"work_drive_path": str(isolated / "gone")}), encoding="utf-8")
    tools = _tools_with_ini_and_default(isolated, real)
    monkeypatch.setattr(mount, "find_dayz_tools", lambda: tools)
    assert mount.find_work_drive() == real


# ---------- invoke_mount subst fallback ----------

def test_subst_failure_reports_exit_code(monkeypatch, capsys, tmp_path):
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
    """
    exe = tmp_path / "WorkDrive.exe"
    state = {"mounted": False, "calls": [], "effects": {}}

    def fake_run(args, **kwargs):
        assert "shell" not in kwargs
        state["calls"].append(list(args))
        if args[0] in state["effects"]:
            state["mounted"] = state["effects"][args[0]]
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(mount, "find_workdrive_exe", lambda: exe)
    monkeypatch.setattr(mount, "is_p_mounted", lambda: state["mounted"])
    monkeypatch.setattr(mount.subprocess, "run", fake_run)
    return exe, state


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
