"""Tests for setup.apply_preferences with a fake winreg (no real registry access)."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _load_setup():
    spec = importlib.util.spec_from_file_location("dayz_setup_objectbuilder", HERE / "setup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup = _load_setup()


class _FakeKey:
    def __init__(self, store: dict):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_winreg(store: dict, writes: list):
    mod = types.ModuleType("winreg")
    mod.HKEY_CURRENT_USER = object()
    mod.KEY_READ = 1
    mod.KEY_SET_VALUE = 2
    mod.REG_SZ = 1

    def open_key(hive, subkey, reserved=0, access=0):
        assert hive is mod.HKEY_CURRENT_USER
        assert subkey == setup.REG_SUBKEY_CCONFIG
        return _FakeKey(store)

    def query_value_ex(key, name):
        if name not in key.store:
            raise OSError("missing")
        return key.store[name], mod.REG_SZ

    def set_value_ex(key, name, reserved, kind, value):
        assert kind == mod.REG_SZ
        key.store[name] = value
        writes.append((name, value))

    mod.OpenKey = open_key
    mod.QueryValueEx = query_value_ex
    mod.SetValueEx = set_value_ex
    return mod


@pytest.fixture
def fake_registry(monkeypatch):
    store: dict = {}
    writes: list = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winreg", _fake_winreg(store, writes))
    return store, writes


def test_writes_all_four_flags_when_absent(fake_registry):
    store, writes = fake_registry
    assert setup.apply_preferences() == 4
    assert len(writes) == 4
    for name, (on_value, _label) in setup.PREFERRED_FLAGS_ON.items():
        assert store[name] == on_value


def test_direct3d_flag_uses_on_string(fake_registry):
    store, _ = fake_registry
    setup.apply_preferences()
    assert store["#Use Direct3D renderer by default"] == "On"
    assert store["#View background LOD"] == "1"


def test_skips_values_already_on(fake_registry):
    store, writes = fake_registry
    store.update({name: on for name, (on, _l) in setup.PREFERRED_FLAGS_ON.items()})
    assert setup.apply_preferences() == 0
    assert writes == []


def test_rewrites_flags_switched_off(fake_registry):
    store, writes = fake_registry
    store.update({name: on for name, (on, _l) in setup.PREFERRED_FLAGS_ON.items()})
    store["#View background LOD"] = "0"
    store["#Use Direct3D renderer by default"] = "1"  # wrong "on" form for this flag
    assert setup.apply_preferences() == 2
    assert sorted(n for n, _ in writes) == ["#Use Direct3D renderer by default", "#View background LOD"]


def test_noop_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert setup.apply_preferences() == 0


# --- .reg safety check --------------------------------------------------------

HKCU_REG = (
    "Windows Registry Editor Version 5.00\r\n\r\n"
    "[HKEY_CURRENT_USER\\Software\\Bohemia Interactive\\DayZ Tools\\Object Builder\\CConfig]\r\n"
    '"#View background LOD"="0"\r\n\r\n'
    "[-HKEY_CURRENT_USER\\Software\\Bohemia Interactive\\DayZ Tools\\Object Builder\\Old]\r\n"
)


def test_hkcu_only_reg_passes_utf16(tmp_path):
    reg = tmp_path / "defaults.reg"
    reg.write_bytes(b"\xff\xfe" + HKCU_REG.encode("utf-16-le"))
    assert setup.foreign_reg_keys(reg) == []


def test_reg_touching_hklm_is_reported(tmp_path):
    reg = tmp_path / "defaults.reg"
    reg.write_text(HKCU_REG + "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Evil]\r\n", encoding="utf-8")
    assert setup.foreign_reg_keys(reg) == ["HKEY_LOCAL_MACHINE\\SOFTWARE\\Evil"]


def test_reg_without_keys_is_reported(tmp_path):
    reg = tmp_path / "defaults.reg"
    reg.write_text("Windows Registry Editor Version 5.00\r\n", encoding="utf-8")
    assert setup.foreign_reg_keys(reg) == ["<no registry keys found>"]


# --- main() -------------------------------------------------------------------

class _FakePreflight:
    def __init__(self, root):
        self.root = root

    def find_dayz_tools(self):
        return self.root


@pytest.fixture
def env(tmp_path, monkeypatch):
    """DayZ Tools tree in tmp_path with ObjectBuilder.exe and an HKCU-only .reg.

    Registry access, reg import and the preflight gate are all faked; `state`
    records what happened.
    """
    ob = tmp_path / "Bin" / "ObjectBuilder"
    ob.mkdir(parents=True)
    (ob / "ObjectBuilder.exe").write_bytes(b"")
    (ob / "ObjectBuilder_defaultSettings.reg").write_text(HKCU_REG, encoding="utf-8")
    state = {"configured": False, "import_rc": 0, "import_creates_keys": True, "imports": 0, "prefs": 0}

    def fake_import(path):
        state["imports"] += 1
        state["order"].append("import")
        if state["import_rc"] == 0 and state["import_creates_keys"]:
            state["configured"] = True
        return state["import_rc"]

    monkeypatch.setattr(setup.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(setup.h, "preflight", _FakePreflight(tmp_path), raising=False)
    monkeypatch.setattr(setup, "registry_has_objectbuilder_settings", lambda: state["configured"])
    monkeypatch.setattr(setup, "import_reg_file", fake_import)
    def fake_prefs():
        state["prefs"] += 1
        return 1

    def fake_backup(backup_dir):
        state["backups"] += 1
        state["order"].append("backup")
        return None if state["backup_fails"] else backup_dir / "objectbuilder-backup.reg"

    def fake_delete():
        state["order"].append("delete")
        if state["delete_rc"] == 0:
            state["configured"] = False
            state["partial"] = False
        return state["delete_rc"]

    # "partial": the parent Object Builder key exists without CConfig.
    state.update(backups=0, backup_fails=False, delete_rc=0, order=[], running=False, partial=False)
    monkeypatch.setattr(setup, "registry_has_objectbuilder_key",
                        lambda: state["configured"] or state["partial"])
    monkeypatch.setattr(setup, "objectbuilder_state", lambda: (state["running"], 0))
    monkeypatch.setattr(setup, "delete_objectbuilder_key", fake_delete)
    monkeypatch.setattr(setup, "apply_preferences", fake_prefs)
    monkeypatch.setattr(setup, "backup_registry", fake_backup)
    monkeypatch.setattr(setup, "BACKUP_DIR", tmp_path / "local-memory")
    return ob, state


def test_main_fresh_machine_imports_and_applies(env, capsys):
    _, state = env
    assert setup.main([]) == 0
    assert state["imports"] == 1 and state["prefs"] == 1
    assert "[INFO]  1 of 4 preferences changed." in capsys.readouterr().out


def test_main_already_configured_skips_import(env):
    _, state = env
    state["configured"] = True
    assert setup.main([]) == 0
    assert state["imports"] == 0 and state["prefs"] == 1


@pytest.mark.parametrize("configured, argv", [(False, []), (True, []), (True, ["--force", "--yes"])])
def test_main_refuses_while_objectbuilder_runs(env, capsys, configured, argv):
    _, state = env
    state.update(running=True, configured=configured)
    assert setup.main(argv) == 1
    assert "Close Object Builder first" in capsys.readouterr().err
    assert state["imports"] == 0 and state["prefs"] == 0 and state["order"] == []


@pytest.mark.parametrize("stdout, running", [
    ("ObjectBuilder.exe             1234 Console    1     85,000 K\n", True),
    ("INFO: No tasks are running which match the specified criteria.\n", False),
])
def test_objectbuilder_running_reads_tasklist(monkeypatch, stdout, running):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr(setup.sys, "platform", "win32")
    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    assert setup.objectbuilder_running() is running
    assert setup.objectbuilder_state() == (running, 0)
    assert calls == [["tasklist", "/FI", "IMAGENAME eq ObjectBuilder.exe", "/NH"]] * 2


def test_objectbuilder_state_unknown_when_tasklist_fails(monkeypatch):
    monkeypatch.setattr(setup.sys, "platform", "win32")
    monkeypatch.setattr(setup.subprocess, "run",
                        lambda cmd, **kw: types.SimpleNamespace(returncode=5, stdout="", stderr="ERROR"))
    assert setup.objectbuilder_state() == (None, 5)


@pytest.mark.parametrize("configured, argv", [(False, []), (True, []), (True, ["--force", "--yes"])])
def test_main_refuses_when_tasklist_fails(env, capsys, monkeypatch, configured, argv):
    """A failed tasklist must not be read as 'not running': an open Object Builder
    would write its old settings back on exit and undo the reset."""
    _, state = env
    state["configured"] = configured
    monkeypatch.setattr(setup, "objectbuilder_state", lambda: (None, 5))
    assert setup.main(argv) == 1
    err = capsys.readouterr().err
    assert "tasklist failed (exit code 5)" in err and "Close Object Builder" in err
    assert state["imports"] == 0 and state["prefs"] == 0 and state["order"] == []


def test_main_missing_exe_fails(env, capsys):
    ob, state = env
    (ob / "ObjectBuilder.exe").unlink()
    assert setup.main([]) == 1
    assert "ObjectBuilder.exe not found" in capsys.readouterr().err
    assert state["imports"] == 0


def test_main_missing_reg_fails(env, capsys):
    ob, state = env
    (ob / "ObjectBuilder_defaultSettings.reg").unlink()
    assert setup.main([]) == 1
    assert "Default settings .reg missing" in capsys.readouterr().err
    assert state["imports"] == 0


def test_main_reg_import_failure_returns_its_code(env, capsys):
    _, state = env
    state["import_rc"] = 5
    assert setup.main([]) == 5
    assert "reg import failed (exit 5)" in capsys.readouterr().err
    assert state["prefs"] == 0


def test_main_keys_missing_after_import_fails(env, capsys):
    _, state = env
    state["import_creates_keys"] = False
    assert setup.main([]) == 1
    assert "keys are still missing" in capsys.readouterr().err
    assert state["prefs"] == 0


def test_main_refuses_reg_outside_hkcu(env, capsys):
    ob, state = env
    (ob / "ObjectBuilder_defaultSettings.reg").write_text(
        HKCU_REG + "[HKEY_LOCAL_MACHINE\\SOFTWARE\\X]\r\n", encoding="utf-8"
    )
    assert setup.main([]) == 1
    assert "outside HKEY_CURRENT_USER" in capsys.readouterr().err
    assert state["imports"] == 0


def test_main_force_without_tty_needs_yes(env, monkeypatch, capsys):
    _, state = env
    state["configured"] = True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert setup.main(["--force"]) == 1
    assert "--force --yes" in capsys.readouterr().err
    assert state["imports"] == 0


def test_main_force_with_yes_reimports(env):
    _, state = env
    state["configured"] = True
    assert setup.main(["--force", "--yes"]) == 0
    assert state["imports"] == 1


@pytest.mark.parametrize("answer, rc, imports", [("y", 0, 1), ("n", 1, 0), ("", 1, 0)])
def test_main_force_prompts_on_tty(env, monkeypatch, answer, rc, imports):
    _, state = env
    state["configured"] = True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: answer)
    assert setup.main(["--force"]) == rc
    assert state["imports"] == imports


def test_main_force_backs_up_before_import(env, capsys):
    _, state = env
    state["configured"] = True
    assert setup.main(["--force", "--yes"]) == 0
    assert state["backups"] == 1 and state["imports"] == 1
    assert "backed up to" in capsys.readouterr().out


def test_main_force_aborts_when_backup_fails(env, capsys):
    _, state = env
    state["configured"] = True
    state["backup_fails"] = True
    assert setup.main(["--force", "--yes"]) == 1
    assert "reset not attempted" in capsys.readouterr().err
    assert state["imports"] == 0
    assert "delete" not in state["order"]


def test_main_force_deletes_key_after_backup_and_before_import(env, capsys):
    _, state = env
    state["configured"] = True
    assert setup.main(["--force", "--yes"]) == 0
    assert state["order"] == ["backup", "delete", "import"]
    assert "Deleted HKCU" in capsys.readouterr().out


def test_main_force_stops_when_delete_fails(env, capsys):
    _, state = env
    state["configured"] = True
    state["delete_rc"] = 1
    assert setup.main(["--force", "--yes"]) == 1
    assert "Could not delete" in capsys.readouterr().err
    assert state["order"] == ["backup", "delete"]


def _path_aware_import(monkeypatch, state, defaults_rc, defaults_creates_keys=True, backup_rc=0):
    """Fake `reg import` whose result depends on which file is imported."""
    imported = []

    def fake_import(path):
        imported.append(Path(path).name)
        state["order"].append("import")
        is_backup = Path(path).name == "objectbuilder-backup.reg"
        rc = backup_rc if is_backup else defaults_rc
        if rc == 0 and (is_backup or defaults_creates_keys):
            state["configured"] = True
        return rc

    monkeypatch.setattr(setup, "import_reg_file", fake_import)
    return imported


def test_main_force_restores_backup_when_import_fails_after_delete(env, monkeypatch, capsys):
    _, state = env
    state["configured"] = True
    imported = _path_aware_import(monkeypatch, state, defaults_rc=5)
    assert setup.main(["--force", "--yes"]) == 5
    assert imported == ["ObjectBuilder_defaultSettings.reg", "objectbuilder-backup.reg"]
    assert state["order"] == ["backup", "delete", "import", "delete", "import"]
    assert state["configured"] is True and state["prefs"] == 0
    captured = capsys.readouterr()
    assert "reg import failed (exit 5)" in captured.err
    assert "Previous settings restored" in captured.out


def test_main_force_restores_backup_when_keys_missing_after_import(env, monkeypatch, capsys):
    _, state = env
    state["configured"] = True
    imported = _path_aware_import(monkeypatch, state, defaults_rc=0, defaults_creates_keys=False)
    assert setup.main(["--force", "--yes"]) == 1
    assert imported == ["ObjectBuilder_defaultSettings.reg", "objectbuilder-backup.reg"]
    assert state["configured"] is True
    assert "Previous settings restored" in capsys.readouterr().out


def test_main_force_reports_manual_restore_when_restore_fails(env, monkeypatch, capsys):
    _, state = env
    state["configured"] = True
    _path_aware_import(monkeypatch, state, defaults_rc=5, backup_rc=7)
    assert setup.main(["--force", "--yes"]) == 5
    err = capsys.readouterr().err
    assert "Restore failed (exit 7)" in err
    assert 'reg import "' in err and "objectbuilder-backup.reg" in err


def test_main_fresh_import_failure_does_not_try_a_restore(env, monkeypatch):
    _, state = env
    imported = _path_aware_import(monkeypatch, state, defaults_rc=5)
    assert setup.main([]) == 5
    assert imported == ["ObjectBuilder_defaultSettings.reg"]
    assert state["order"] == ["import"]


def test_backup_dir_is_the_project_found_from_a_subfolder(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    (project / ".claude" / "local-memory").mkdir(parents=True)
    (project / ".claude" / "local-memory" / "dayz-current-project.txt").write_text("x", encoding="utf-8")
    sub = project / "workspace" / "MyMod"
    sub.mkdir(parents=True)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(sub)
    fresh = _load_setup()
    assert fresh.PROJECT_DIR == project.resolve()
    assert fresh.BACKUP_DIR == project.resolve() / ".claude" / "local-memory"


def test_main_force_declined_deletes_nothing(env, monkeypatch):
    _, state = env
    state["configured"] = True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    assert setup.main(["--force"]) == 1
    assert state["order"] == []


def test_main_force_refuses_foreign_reg_before_touching_registry(env, capsys):
    ob, state = env
    state["configured"] = True
    (ob / "ObjectBuilder_defaultSettings.reg").write_text(
        HKCU_REG + "[HKEY_LOCAL_MACHINE\\SOFTWARE\\X]\r\n", encoding="utf-8"
    )
    assert setup.main(["--force", "--yes"]) == 1
    assert "outside HKEY_CURRENT_USER" in capsys.readouterr().err
    assert state["order"] == []


def test_main_fresh_machine_does_not_delete(env):
    _, state = env
    assert setup.main([]) == 0
    assert state["order"] == ["import"]


def test_main_fresh_machine_skips_backup(env):
    _, state = env
    assert setup.main([]) == 0
    assert state["backups"] == 0


# --- backup_registry with a mocked reg export ----------------------------------

def test_backup_registry_runs_reg_export(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        Path(cmd[3]).write_text("exported", encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    dest = setup.backup_registry(tmp_path / "mem")
    assert dest is not None and dest.is_file()
    assert dest.parent == tmp_path / "mem"
    assert dest.name.startswith("objectbuilder-backup-") and dest.suffix == ".reg"
    assert calls == [["reg", "export", "HKCU\\" + setup.REG_KEY, str(dest), "/y"]]


def test_delete_objectbuilder_key_runs_reg_delete(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(setup.subprocess, "run", fake_run)
    assert setup.delete_objectbuilder_key() == 0
    assert calls == [["reg", "delete", "HKCU\\" + setup.REG_KEY, "/f"]]


def test_delete_objectbuilder_key_failure_returns_code(monkeypatch, capsys):
    monkeypatch.setattr(
        setup.subprocess, "run",
        lambda cmd, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="ERROR: access denied"),
    )
    assert setup.delete_objectbuilder_key() == 1
    assert "access denied" in capsys.readouterr().err


def test_backup_registry_failure_returns_none(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(
        setup.subprocess, "run",
        lambda cmd, **k: types.SimpleNamespace(returncode=1, stdout="", stderr="ERROR: access denied"),
    )
    assert setup.backup_registry(tmp_path) is None
    assert "access denied" in capsys.readouterr().err


# --- --no-prefs, preference write errors, partial trees ------------------------

@pytest.mark.parametrize("configured", [False, True])
def test_main_no_prefs_leaves_flags_alone(env, capsys, configured):
    _, state = env
    state["configured"] = configured
    assert setup.main(["--no-prefs"]) == 0
    assert state["prefs"] == 0
    assert "--no-prefs: preferred flags left as they are" in capsys.readouterr().out


def test_main_default_run_still_applies_prefs_and_names_opt_out(env, capsys):
    _, state = env
    state["configured"] = True
    assert setup.main([]) == 0
    assert state["prefs"] == 1
    assert "skip with --no-prefs" in capsys.readouterr().out


def test_main_returns_1_when_preferences_fail(env, monkeypatch):
    _, state = env
    state["configured"] = True
    monkeypatch.setattr(setup, "apply_preferences", lambda: None)
    assert setup.main([]) == 1


def _raising_winreg(monkeypatch, fail_on):
    store: dict = {}
    mod = _fake_winreg(store, [])

    def boom(*a, **k):
        raise PermissionError(5, "Access is denied")

    if fail_on == "open":
        mod.OpenKey = boom
    else:
        mod.SetValueEx = boom
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winreg", mod)


@pytest.mark.parametrize("fail_on", ["open", "set"])
def test_apply_preferences_reports_oserror_cleanly(monkeypatch, capsys, fail_on):
    _raising_winreg(monkeypatch, fail_on)
    assert setup.apply_preferences() is None
    err = capsys.readouterr().err
    assert "[FAIL]" in err and "Could not write preferences" in err and "Access is denied" in err
    assert "--no-prefs" in err


_REAL_APPLY_PREFERENCES = setup.apply_preferences  # captured before the env fixture fakes it


def test_main_preference_oserror_exits_1_without_traceback(env, monkeypatch, capsys):
    _, state = env
    state["configured"] = True
    monkeypatch.setattr(setup, "apply_preferences", _REAL_APPLY_PREFERENCES)
    _raising_winreg(monkeypatch, "open")
    assert setup.main([]) == 1
    assert "Could not write preferences" in capsys.readouterr().err


def test_main_partial_tree_is_backed_up_then_merged(env, capsys):
    _, state = env
    state["partial"] = True
    assert setup.main([]) == 0
    assert state["order"] == ["backup", "import"]
    assert "backed up to" in capsys.readouterr().out


def test_main_partial_tree_backup_failure_stops_before_import(env, capsys):
    _, state = env
    state.update(partial=True, backup_fails=True)
    assert setup.main([]) == 1
    assert "defaults not imported" in capsys.readouterr().err
    assert state["order"] == ["backup"] and state["prefs"] == 0


def test_main_partial_tree_restores_backup_when_import_fails(env, monkeypatch, capsys):
    _, state = env
    state["partial"] = True
    imported = []

    def fake_import(path):
        name = Path(path).name
        imported.append(name)
        state["order"].append("import")
        if name == "objectbuilder-backup.reg":
            state["partial"] = True  # the backup never had CConfig
            return 0
        return 5

    monkeypatch.setattr(setup, "import_reg_file", fake_import)
    assert setup.main([]) == 5
    assert imported == ["ObjectBuilder_defaultSettings.reg", "objectbuilder-backup.reg"]
    assert state["order"] == ["backup", "import", "delete", "import"]
    assert state["partial"] is True and state["configured"] is False
    assert "Previous settings restored" in capsys.readouterr().out


def test_main_empty_registry_takes_no_backup(env):
    _, state = env
    assert setup.main([]) == 0
    assert state["backups"] == 0 and state["order"] == ["import"]


def test_registry_key_checks_use_the_right_subkeys(monkeypatch):
    present: set = set()
    mod = types.ModuleType("winreg")
    mod.HKEY_CURRENT_USER = object()

    def open_key(hive, subkey, *a):
        if subkey not in present:
            raise FileNotFoundError(subkey)
        return _FakeKey({})

    mod.OpenKey = open_key
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setitem(sys.modules, "winreg", mod)
    assert not setup.registry_has_objectbuilder_key()
    present.add(setup.REG_KEY)
    assert setup.registry_has_objectbuilder_key()
    assert not setup.registry_has_objectbuilder_settings()
    present.add(setup.REG_SUBKEY_CCONFIG)
    assert setup.registry_has_objectbuilder_settings()
