"""Tests for the search-index release check under network failures, and for
race-safe stale-lock takeover.

No real network: urllib.request.urlopen is replaced in every test that reaches it.
"""
import http.client
import importlib.util
import json
import os
import ssl
import sys
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "agentic_z_update_netlock", Path(__file__).resolve().parent / "update.py"
)
update = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(update)


class _Resp:
    """Minimal stand-in for an HTTP response used as a context manager."""

    def __init__(self, body=b"", read_error=None):
        self._body = body
        self._read_error = read_error

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        if self._read_error is not None:
            raise self._read_error
        return self._body


def _urlopen_raising(exc):
    def fake(req, timeout=None):
        raise exc
    return fake


def _urlopen_returning(resp):
    return lambda req, timeout=None: resp


# ---------- latest_search_index_tag never raises ----------

@pytest.mark.parametrize("exc", [
    http.client.RemoteDisconnected("Remote end closed connection without response"),
    ConnectionResetError(10054, "connection reset"),
    ssl.SSLError("handshake failed"),
    TimeoutError("timed out"),
    update.urllib.request.URLError("offline"),
], ids=["remote-disconnected", "connection-reset", "ssl", "timeout", "urlerror"])
def test_connect_failures_return_none(monkeypatch, exc):
    monkeypatch.setattr(update.urllib.request, "urlopen", _urlopen_raising(exc))
    assert update.latest_search_index_tag() is None


@pytest.mark.parametrize("exc", [
    http.client.IncompleteRead(b"{\"tag", 200),
    ssl.SSLError("bad record mac"),
    ConnectionResetError(10054, "connection reset"),
], ids=["incomplete-read", "ssl", "connection-reset"])
def test_read_failures_return_none(monkeypatch, exc):
    monkeypatch.setattr(update.urllib.request, "urlopen", _urlopen_returning(_Resp(read_error=exc)))
    assert update.latest_search_index_tag() is None


@pytest.mark.parametrize("body", [
    b"not json",
    b"\xff\xfe\x00",
    b"[]",
    b"null",
    b"{\"tag_name\": \"v2\", \"assets\": \"oops\"}",
    b"{\"tag_name\": 5, \"assets\": [{\"name\": \"dayz-search-index-x.zip\"}]}",
    b"{\"tag_name\": \"v2\", \"assets\": [\"dayz-search-index-x.zip\"]}",
], ids=["bad-json", "bad-utf8", "list", "null", "assets-not-list", "tag-not-str", "asset-not-dict"])
def test_malformed_replies_return_none(monkeypatch, body):
    monkeypatch.setattr(update.urllib.request, "urlopen", _urlopen_returning(_Resp(body)))
    assert update.latest_search_index_tag() is None


def test_matching_asset_returns_tag(monkeypatch):
    body = json.dumps({"tag_name": "v2.0", "assets": [{"name": "other.zip"}, {"name": "dayz-search-index-v2.0.zip"}]})
    monkeypatch.setattr(update.urllib.request, "urlopen", _urlopen_returning(_Resp(body.encode())))
    assert update.latest_search_index_tag() == "v2.0"


def test_no_matching_asset_returns_none(monkeypatch):
    body = json.dumps({"tag_name": "v2.0", "assets": [{"name": "other.zip"}]})
    monkeypatch.setattr(update.urllib.request, "urlopen", _urlopen_returning(_Resp(body.encode())))
    assert update.latest_search_index_tag() is None


# ---------- main() survives a dropped connection during the release check ----------

def _stub_remote_with_installed_index(monkeypatch, root, exc):
    monkeypatch.chdir(root)
    tag_file = root / "release-tag.txt"
    tag_file.write_text("v1.0\n", encoding="utf-8")
    monkeypatch.setattr(update, "SEARCH_INDEX_TAG_FILE", tag_file)
    monkeypatch.setattr(update, "repo_root", lambda: root)
    monkeypatch.setattr(update, "ensure_upstream", lambda: True)
    monkeypatch.setattr(update, "fetch_upstream", lambda: True)
    monkeypatch.setattr(update, "upstream_head_sha", lambda: "c" * 40)
    monkeypatch.setattr(update, "merge_base_sha", lambda: None)
    monkeypatch.setattr(update, "compute_drift", lambda baseline, ref: {})
    monkeypatch.setattr(update.urllib.request, "urlopen", _urlopen_raising(exc))
    update.write_baseline("b" * 40)


@pytest.mark.parametrize("exc", [
    http.client.RemoteDisconnected("Remote end closed connection without response"),
    http.client.IncompleteRead(b"", 10),
], ids=["remote-disconnected", "incomplete-read"])
def test_quiet_check_exits_0_and_stays_silent_on_dropped_connection(tmp_path, monkeypatch, capsys, exc):
    _stub_remote_with_installed_index(monkeypatch, tmp_path, exc)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check", "--quiet"])
    assert update.main() == 0
    assert capsys.readouterr().out.strip() == ""


def test_check_reports_up_to_date_on_dropped_connection(tmp_path, monkeypatch, capsys):
    _stub_remote_with_installed_index(
        monkeypatch, tmp_path, http.client.RemoteDisconnected("Remote end closed connection without response")
    )
    monkeypatch.setattr(update, "_QUIET", False)
    monkeypatch.setattr(sys, "argv", ["update.py", "--check"])
    assert update.main() == 0
    assert "Up to date." in capsys.readouterr().out


# ---------- lock creation and race-safe stale takeover ----------

@pytest.fixture
def in_tmp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(update, "_QUIET", False)
    return tmp_path


def _write_lock_for(pid: int, started: str = "2020-01-01T00:00:00+00:00") -> bytes:
    update.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps({"pid": pid, "started_at": started}).encode()
    update.LOCK_FILE.write_bytes(data)
    return data


def _live_other_pid() -> int:
    pid = os.getppid()
    assert update._pid_alive(pid), "parent process should be alive"
    return pid


def test_write_lock_leaves_no_temp_file_and_full_content(in_tmp):
    update.write_lock()
    assert json.loads(update.LOCK_FILE.read_text(encoding="utf-8"))["pid"] == os.getpid()
    leftovers = [p.name for p in update.LOCK_FILE.parent.iterdir() if p.name != update.LOCK_FILE.name]
    assert leftovers == []
    with pytest.raises(FileExistsError):
        update.write_lock()
    assert [p.name for p in update.LOCK_FILE.parent.iterdir()] == [update.LOCK_FILE.name]


def test_write_lock_without_hard_links_is_still_exclusive(in_tmp, monkeypatch):
    def no_links(src, dst):
        raise OSError(1, "hard links not supported")

    monkeypatch.setattr(update.os, "link", no_links)
    update.write_lock()
    assert json.loads(update.LOCK_FILE.read_text(encoding="utf-8"))["pid"] == os.getpid()
    with pytest.raises(FileExistsError):
        update.write_lock()


def test_second_run_does_not_delete_lock_a_competitor_just_took(in_tmp, monkeypatch, capsys):
    """Run B reads the dead-PID lock; before B removes it, run A replaces it with
    its own fresh lock. B must notice and refuse instead of deleting A's lock."""
    _write_lock_for(999999)
    competitor = _live_other_pid()
    real_remove = update._remove_stale_lock

    def competitor_wins_first(seen):
        update.LOCK_FILE.unlink()
        _write_lock_for(competitor, "2026-10-24T00:00:00+00:00")
        return real_remove(seen)

    monkeypatch.setattr(update, "_remove_stale_lock", competitor_wins_first)
    assert update.acquire_lock() is False
    assert json.loads(update.LOCK_FILE.read_text(encoding="utf-8"))["pid"] == competitor
    assert "Another update is running" in capsys.readouterr().out


def test_remove_stale_lock_refuses_when_lock_changed(in_tmp):
    stale = _write_lock_for(999999)
    fresh = _write_lock_for(_live_other_pid(), "2026-10-24T00:00:00+00:00")
    assert update._remove_stale_lock(stale) == "changed"
    assert update.LOCK_FILE.read_bytes() == fresh
    assert not update.LOCK_TAKEOVER_FILE.exists()


def test_takeover_in_progress_elsewhere_refuses(in_tmp, capsys):
    stale = _write_lock_for(999999)
    update.LOCK_TAKEOVER_FILE.write_text("12345", encoding="utf-8")
    assert update.acquire_lock() is False
    assert update.LOCK_FILE.read_bytes() == stale
    assert update.LOCK_TAKEOVER_FILE.exists()
    assert "taking over a stale lock" in capsys.readouterr().out


def test_stale_takeover_cleans_up_guard(in_tmp):
    _write_lock_for(999999)
    assert update.acquire_lock() is True
    assert json.loads(update.LOCK_FILE.read_text(encoding="utf-8"))["pid"] == os.getpid()
    assert not update.LOCK_TAKEOVER_FILE.exists()
    update.release_lock()


def test_lock_released_between_create_and_read_is_retried(in_tmp, monkeypatch):
    """If the holder releases the lock right after our create failed, we take it."""
    _write_lock_for(_live_other_pid())
    real_read = update._read_lock_bytes
    calls = {"n": 0}

    def released_once():
        calls["n"] += 1
        if calls["n"] == 1:
            update.LOCK_FILE.unlink()
            return None
        return real_read()

    monkeypatch.setattr(update, "_read_lock_bytes", released_once)
    assert update.acquire_lock() is True
    assert json.loads(update.LOCK_FILE.read_text(encoding="utf-8"))["pid"] == os.getpid()
    update.release_lock()
