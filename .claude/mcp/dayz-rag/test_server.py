"""Tests for the dayz-rag MCP server's pure functions.

The LanceDB table and the Voyage client are stubbed, so these run without an
index, an API key, or P:\\ mounted.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

_spec = importlib.util.spec_from_file_location("dayz_rag_server", Path(__file__).parent / "server.py")
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


class _FakeQuery:
    """Mimics LanceDB's vector query builder: rows come back nearest first."""

    _WHERE = re.compile(r"^file_type = '(\w+)'$")

    def __init__(self, rows):
        self._rows = sorted(rows, key=lambda r: r["_distance"])
        self.limit_value = None
        self.where_clause = None
        self.prefilter = None

    def where(self, clause, prefilter=None):
        m = self._WHERE.match(clause)
        assert m, f"unexpected where clause {clause!r}"
        self.where_clause, self.prefilter = clause, prefilter
        self._rows = [r for r in self._rows if r["file_type"] == m.group(1)]
        return self

    def limit(self, n):
        self.limit_value = n
        return self

    def to_list(self):
        return self._rows[: self.limit_value]


class _FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.last_query = None

    def search(self, _vec):
        self.last_query = _FakeQuery(self.rows)
        return self.last_query


def _row(path, file_type, distance):
    return {"path": path, "file_type": file_type, "_distance": distance, "content": "x", "line_start": 1, "line_end": 2}


@pytest.fixture
def fake_table(monkeypatch):
    rows = [
        _row("https://wiki/a", "c", 0.5),
        _row("https://wiki/b", "cpp", 0.6),
        _row("https://wiki/c", "c", 0.9),
        _row("https://wiki/d", "cpp", 1.2),
    ]
    table = _FakeTable(rows)
    monkeypatch.setattr(server, "DEFAULT_MAX_DISTANCE", None)  # ignore a developer's env override
    monkeypatch.setattr(server, "_get_table", lambda: table)
    monkeypatch.setattr(server, "_embed_query", lambda _q: [0.0])
    return table


# --------------- source search ---------------


def test_blank_query_returns_nothing_without_touching_index(monkeypatch):
    monkeypatch.setattr(server, "_get_table", lambda: pytest.fail("index should not be opened"))
    assert server.search_dayz_source_impl("   ") == []


def test_unknown_file_type_is_rejected():
    with pytest.raises(ValueError):
        server.search_dayz_source_impl("vest", file_type="config.cpp")


def test_file_type_filter_is_a_lancedb_prefilter(fake_table):
    hits = server.search_dayz_source_impl("vest", top_k=1, file_type="cpp")
    # The nearest row overall is a "c" row; the prefilter still yields a cpp hit.
    assert [h["path"] for h in hits] == ["https://wiki/b"]
    q = fake_table.last_query
    assert (q.where_clause, q.prefilter, q.limit_value) == ("file_type = 'cpp'", True, 1)


def test_no_where_clause_without_file_type(fake_table):
    server.search_dayz_source_impl("vest", top_k=3)
    assert fake_table.last_query.where_clause is None
    assert fake_table.last_query.limit_value == 3


def test_hits_report_distance(fake_table):
    hit = server.search_dayz_source_impl("vest", top_k=1)[0]
    assert hit["distance"] == 0.5
    assert "score" not in hit


def test_max_distance_drops_far_hits(fake_table):
    hits = server.search_dayz_source_impl("vest", top_k=5, max_distance=0.7)
    assert [h["path"] for h in hits] == ["https://wiki/a", "https://wiki/b"]
    assert fake_table.last_query.limit_value == 5  # no over-fetch: farther rows can't pass


def test_top_k_is_clamped(fake_table):
    assert len(server.search_dayz_source_impl("vest", top_k=0)) == 1
    server.search_dayz_source_impl("vest", top_k=999)
    assert fake_table.last_query.limit_value == server.MAX_TOP_K


def test_missing_index_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_table", None)
    with pytest.raises(RuntimeError, match="dayz-search-index"):
        server._get_table()


# --------------- get_dayz_file ---------------


@pytest.mark.parametrize("path", ["relative/file.c", r"C:\Windows\win.ini", r"D:\dz\x.c"])
def test_get_file_refuses_paths_outside_p(path):
    with pytest.raises(ValueError):
        server.get_dayz_file_impl(path)


_TEXT = "one\ntwo\nthree\nfour\n"


def test_slice_whole_file_when_no_range():
    out = server._slice_lines(r"P:\a.c", _TEXT, None, None)
    assert out == {"path": r"P:\a.c", "line_start": 1, "line_end": 4, "content": _TEXT}


def test_slice_inclusive_range():
    out = server._slice_lines("p", _TEXT, 2, 3)
    assert (out["line_start"], out["line_end"], out["content"]) == (2, 3, "two\nthree")


def test_slice_open_ended_ranges():
    assert server._slice_lines("p", _TEXT, 3, None)["content"] == "three\nfour"
    assert server._slice_lines("p", _TEXT, None, 1)["content"] == "one"


def test_slice_clamps_end_past_eof():
    out = server._slice_lines("p", _TEXT, 3, 99)
    assert (out["line_end"], out["content"]) == (4, "three\nfour")


@pytest.mark.parametrize("start,end", [(0, 2), (3, 2), (9, None)])
def test_slice_rejects_bad_ranges(start, end):
    with pytest.raises(ValueError):
        server._slice_lines("p", _TEXT, start, end)


# --------------- stale detection ---------------


def _fake_path(monkeypatch, mtime=None):
    """Make server.Path(...).stat() return the given mtime, or raise if None."""

    def stat():
        if mtime is None:
            raise FileNotFoundError("gone")
        return SimpleNamespace(st_mtime=mtime)

    monkeypatch.setattr(server, "Path", lambda _p: SimpleNamespace(stat=stat))


def test_non_local_paths_are_never_stale():
    assert server._check_stale("https://community.bistudio.com/wiki/DayZ") == (False, None)


def test_file_newer_than_index_is_stale(monkeypatch):
    monkeypatch.setattr(server, "_get_index_built_at", lambda: 100.0)
    _fake_path(monkeypatch, mtime=200.0)
    assert server._check_stale(r"P:\scripts\a.c") == (True, "modified")


def test_file_older_than_index_is_fresh(monkeypatch):
    monkeypatch.setattr(server, "_get_index_built_at", lambda: 100.0)
    _fake_path(monkeypatch, mtime=50.0)
    assert server._check_stale("P:/scripts/a.c") == (False, None)


def test_missing_file_is_stale(monkeypatch):
    monkeypatch.setattr(server, "_get_index_built_at", lambda: 100.0)
    _fake_path(monkeypatch, mtime=None)
    assert server._check_stale(r"P:\scripts\gone.c") == (True, "missing")


def test_unknown_build_time_is_never_stale(monkeypatch):
    monkeypatch.setattr(server, "_get_index_built_at", lambda: None)
    _fake_path(monkeypatch, mtime=200.0)
    assert server._check_stale(r"P:\scripts\a.c") == (False, None)


def test_stale_flag_appears_on_search_hits(fake_table, monkeypatch):
    monkeypatch.setattr(server, "_check_stale", lambda _p: (True, "modified"))
    hit = server.search_dayz_source_impl("vest", top_k=1)[0]
    assert (hit["is_stale"], hit["stale_reason"]) == (True, "modified")


def test_index_build_time_read_from_manifest(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"indexed_at": 1234}), encoding="utf-8")
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_index_built_at", None)
    assert server._get_index_built_at() == 1234.0


# --------------- wiki search ---------------


@pytest.fixture
def fake_wiki_table(monkeypatch):
    rows = [
        _row("https://community.bistudio.com/wiki/A", "wiki", 0.4),
        _row("https://community.bistudio.com/wiki/B", "wiki", 0.8),
        _row("https://community.bistudio.com/wiki/C", "wiki", 1.1),
    ]
    rows[0]["parent_context"] = "A > Intro"
    table = _FakeTable(rows)
    monkeypatch.setattr(server, "DEFAULT_MAX_DISTANCE", None)
    monkeypatch.setattr(server, "_get_wiki_table", lambda: table)
    monkeypatch.setattr(server, "_get_table", lambda: pytest.fail("wiki search must not open the source table"))
    monkeypatch.setattr(server, "_embed_query", lambda _q: [0.0])
    return table


def test_wiki_search_returns_formatted_hits(fake_wiki_table):
    hits = server.search_dayz_wiki_impl("how do RPCs work", top_k=2)
    assert [h["path"] for h in hits] == [
        "https://community.bistudio.com/wiki/A",
        "https://community.bistudio.com/wiki/B",
    ]
    assert hits[0]["parent_context"] == "A > Intro"
    assert all(h["is_stale"] is False and "stale_reason" not in h for h in hits)
    assert fake_wiki_table.last_query.limit_value == 2


def test_wiki_search_max_distance_filters(fake_wiki_table):
    hits = server.search_dayz_wiki_impl("rpc", top_k=3, max_distance=0.9)
    assert len(hits) == 2
    assert fake_wiki_table.last_query.limit_value == 3


def test_wiki_blank_query_returns_nothing(monkeypatch):
    monkeypatch.setattr(server, "_get_wiki_table", lambda: pytest.fail("index should not be opened"))
    assert server.search_dayz_wiki_impl("") == []


def test_missing_wiki_table_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_wiki_table", None)
    with pytest.raises(RuntimeError, match="dayz-search-wiki-index"):
        server._get_wiki_table()


# --------------- list_indexed_sources ---------------


def test_list_sources_reports_nulls_when_nothing_built(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    assert server.list_indexed_sources_impl() == {"source": None, "wiki": None}


def test_list_sources_source_only(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"files": 3}), encoding="utf-8")
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    assert server.list_indexed_sources_impl() == {"source": {"files": 3}, "wiki": None}


def test_list_sources_returns_both_when_wiki_present(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"files": 3}), encoding="utf-8")
    (tmp_path / "wiki-manifest.json").write_text(json.dumps({"pages": 9}), encoding="utf-8")
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    assert server.list_indexed_sources_impl() == {"source": {"files": 3}, "wiki": {"pages": 9}}


def test_list_sources_raises_on_corrupt_manifest(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="unreadable"):
        server.list_indexed_sources_impl()


# --------------- .env discovery ---------------


def test_dotenv_paths_finds_cwd_parent_then_repo_root(monkeypatch, tmp_path):
    work = tmp_path / "work"
    (work / "sub").mkdir(parents=True)
    (work / ".env").write_text("A=1\n", encoding="utf-8")
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text("B=2\n", encoding="utf-8")
    monkeypatch.chdir(work / "sub")
    monkeypatch.setattr(server, "REPO_ROOT", repo)
    assert server._dotenv_paths() == [work / ".env", repo / ".env"]


def test_dotenv_paths_uses_repo_root_when_cwd_has_none(monkeypatch, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text("B=2\n", encoding="utf-8")
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(server, "REPO_ROOT", repo)
    assert server._dotenv_paths() == [repo / ".env"]


def test_dotenv_paths_no_duplicate_when_cwd_is_repo_root(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("B=2\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(server, "REPO_ROOT", tmp_path)
    assert server._dotenv_paths() == [tmp_path / ".env"]


def test_repo_root_is_three_levels_above_server_dir():
    assert (server.REPO_ROOT / ".claude" / "mcp" / "dayz-rag" / "server.py").is_file()
