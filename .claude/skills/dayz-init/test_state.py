"""Tests for dayz-init/state.py (per-clone cache and state)."""
import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "dayz_init_state_under_test", Path(__file__).resolve().parent / "state.py"
)
state = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(state)


def _scaffold(project: Path, mod: str) -> None:
    mod_dir = project / "workspace" / mod
    mod_dir.mkdir(parents=True)
    (mod_dir / "config.cpp").write_text("class CfgPatches {};")
    (mod_dir / "$PBOPREFIX$").write_text(mod)


def test_cache_missing_returns_none(tmp_path):
    assert state.cached_project_root(memory_dir=tmp_path) is None


def test_cache_roundtrip(tmp_path):
    state.write_cached_project_root(Path("G:/repos/Clone"), memory_dir=tmp_path / "mem")
    assert state.cached_project_root(memory_dir=tmp_path / "mem") == Path("G:/repos/Clone")


def test_cache_defaults_to_per_clone_local_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "PROJECT_DIR", tmp_path)
    state.write_cached_project_root(tmp_path)
    assert (tmp_path / ".claude" / "local-memory" / state.CACHE_FILENAME).is_file()
    assert state.cached_project_root() == tmp_path


def test_state_lives_in_project_local_memory(tmp_path):
    state.write_state(tmp_path, {"rag_choice": "skip"})
    assert (tmp_path / ".claude" / "local-memory" / state.STATE_FILENAME).is_file()
    assert state.read_state(tmp_path) == {"rag_choice": "skip"}


def test_read_state_missing_or_corrupt_is_empty(tmp_path):
    assert state.read_state(tmp_path) == {}
    path = tmp_path / ".claude" / "local-memory" / state.STATE_FILENAME
    path.parent.mkdir(parents=True)
    path.write_text("{not json")
    assert state.read_state(tmp_path) == {}


def test_setup_incomplete_for_empty_project(tmp_path):
    assert not state.is_setup_complete(tmp_path)


def test_setup_incomplete_when_active_mod_missing_from_workspace(tmp_path):
    state.write_state(tmp_path, {"last_intent": {"mod_name": "MyMod"}})
    assert not state.is_setup_complete(tmp_path)


def test_setup_complete_when_active_mod_scaffolded(tmp_path):
    _scaffold(tmp_path, "MyMod")
    state.write_state(tmp_path, {"last_intent": {"mod_name": "MyMod"}})
    assert state.active_mod(tmp_path) == "MyMod"
    assert state.is_setup_complete(tmp_path)
