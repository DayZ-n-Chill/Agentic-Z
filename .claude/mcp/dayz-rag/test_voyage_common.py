"""Tests for voyage_common: .env discovery, API-key loading and the retry rule."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_spec = importlib.util.spec_from_file_location("voyage_common", Path(__file__).parent / "voyage_common.py")
vc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vc)


# --------------- .env discovery ---------------


def test_dotenv_paths_finds_cwd_parent_then_repo_root(monkeypatch, tmp_path):
    work = tmp_path / "work"
    (work / "sub").mkdir(parents=True)
    (work / ".env").write_text("A=1\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text("B=2\n", encoding="utf-8")
    monkeypatch.chdir(work / "sub")
    monkeypatch.setattr(vc, "REPO_ROOT", repo)
    assert vc.dotenv_paths() == [work / ".env", repo / ".env"]


def test_dotenv_paths_uses_repo_root_when_cwd_has_none(monkeypatch, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text("B=2\n", encoding="utf-8")
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(vc, "REPO_ROOT", repo)
    assert vc.dotenv_paths() == [repo / ".env"]


def test_dotenv_paths_no_duplicate_when_cwd_is_repo_root(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("B=2\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(vc, "REPO_ROOT", tmp_path)
    assert vc.dotenv_paths() == [tmp_path / ".env"]


def test_repo_root_is_three_levels_above_module_dir():
    assert (vc.REPO_ROOT / ".claude" / "mcp" / "dayz-rag" / "voyage_common.py").is_file()


# --------------- API key ---------------


@pytest.fixture
def no_env_files(monkeypatch):
    monkeypatch.setattr(vc, "dotenv_paths", lambda: [])


def test_key_from_environment(monkeypatch, no_env_files):
    monkeypatch.setenv("VOYAGE_API_KEY", "  pa-abc  ")
    assert vc.load_api_key() == "pa-abc"


def test_pasted_export_line_is_unwrapped(monkeypatch, no_env_files):
    monkeypatch.setenv("VOYAGE_API_KEY", 'export VOYAGE_API_KEY="pa-xyz"')
    assert vc.load_api_key() == "pa-xyz"


def test_missing_key_raises(monkeypatch, no_env_files):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="VOYAGE_API_KEY not set"):
        vc.load_api_key()


# --------------- retry rule ---------------


@pytest.fixture
def errors(monkeypatch):
    names = vc.TRANSIENT_ERROR_NAMES + ("AuthenticationError", "InvalidRequestError")
    mod = SimpleNamespace(**{n: type(n, (Exception,), {}) for n in names})
    monkeypatch.setitem(sys.modules, "voyageai.error", mod)
    return mod


@pytest.mark.parametrize("name", vc.TRANSIENT_ERROR_NAMES)
def test_transient_classes_are_retried(errors, name):
    assert vc.is_transient(getattr(errors, name)("x"))


@pytest.mark.parametrize("name", ["AuthenticationError", "InvalidRequestError"])
def test_request_errors_are_not_retried(errors, name):
    assert not vc.is_transient(getattr(errors, name)("rate limit"))


def test_unrelated_exception_mentioning_timeout_is_not_retried(errors):
    assert not vc.is_transient(ValueError("connection timeout"))


def test_names_exist_in_installed_sdk():
    verr = pytest.importorskip("voyageai.error")
    assert all(hasattr(verr, n) for n in vc.TRANSIENT_ERROR_NAMES)
