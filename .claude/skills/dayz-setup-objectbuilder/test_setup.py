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
