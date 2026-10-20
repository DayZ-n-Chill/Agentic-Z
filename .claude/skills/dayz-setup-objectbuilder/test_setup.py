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
        if state["import_rc"] == 0 and state["import_creates_keys"]:
            state["configured"] = True
        return state["import_rc"]

    monkeypatch.setattr(setup.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(setup.h, "preflight", _FakePreflight(tmp_path), raising=False)
    monkeypatch.setattr(setup, "registry_has_objectbuilder_settings", lambda: state["configured"])
    monkeypatch.setattr(setup, "import_reg_file", fake_import)
    monkeypatch.setattr(setup, "apply_preferences", lambda: state.__setitem__("prefs", state["prefs"] + 1))
    return ob, state


def test_main_fresh_machine_imports_and_applies(env):
    _, state = env
    assert setup.main([]) == 0
    assert state["imports"] == 1 and state["prefs"] == 1


def test_main_already_configured_skips_import(env):
    _, state = env
    state["configured"] = True
    assert setup.main([]) == 0
    assert state["imports"] == 0 and state["prefs"] == 1


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
