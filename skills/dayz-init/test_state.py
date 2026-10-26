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


def test_linked_import_without_scaffold_files_counts_as_set_up(tmp_path):
    # A --no-scaffold import links a source that may lack config.cpp / $PBOPREFIX$.
    (tmp_path / "workspace" / "Linked").mkdir(parents=True)
    state.write_state(tmp_path, {"last_intent": {"mod_name": "Linked"}})
    assert state.mod_exists(tmp_path, "Linked")
    assert state.is_setup_complete(tmp_path)


def test_mod_exists_counts_a_dangling_link(tmp_path, monkeypatch):
    # new-mod and import-mod refuse any existing path, so the plan must skip them.
    monkeypatch.setattr(state.os.path, "lexists", lambda p: Path(p).name == "Gone")
    assert state.mod_exists(tmp_path, "Gone")
    assert not state.mod_exists(tmp_path, "Other")


def _seed_cache(project: Path) -> Path:
    cache = project / ".claude" / "local-memory" / state.CACHE_FILENAME
    cache.parent.mkdir(parents=True)
    cache.write_text(str(project), encoding="utf-8")
    return project


def test_find_project_dir_walks_up_to_the_cache(tmp_path, monkeypatch):
    project = _seed_cache(tmp_path.resolve() / "project")
    sub = project / "workspace" / "MyMod" / "scripts"
    sub.mkdir(parents=True)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(sub)
    assert state.find_project_dir() == project


def test_find_project_dir_prefers_env_then_falls_back_to_cwd(tmp_path, monkeypatch):
    monkeypatch.setattr(state.Path, "home", classmethod(lambda cls: tmp_path.resolve()))
    monkeypatch.setattr(state, "SCRIPT_CLONE", tmp_path / "no-clone")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "env"))
    assert state.find_project_dir() == (tmp_path / "env").resolve()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    assert state.find_project_dir() == tmp_path.resolve()


def test_find_project_dir_ignores_a_cache_in_home(tmp_path, monkeypatch):
    home = _seed_cache(tmp_path.resolve() / "home")
    sub = home / "repos" / "Other"
    sub.mkdir(parents=True)
    monkeypatch.setattr(state.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(state, "SCRIPT_CLONE", tmp_path / "no-clone")
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(sub)
    assert state.find_project_dir() == sub


def test_find_project_dir_outside_any_project_uses_the_scripts_clone(tmp_path, monkeypatch):
    # The live AZTestVest run: a worker's shell started in the home folder, which
    # holds a stray cache pointing at another clone, and its build went there.
    home = _seed_cache(tmp_path.resolve() / "home")
    clone = _seed_cache(tmp_path.resolve() / "clone")
    monkeypatch.setattr(state.Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(state, "SCRIPT_CLONE", clone)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(home)
    assert state.find_project_dir() == clone
