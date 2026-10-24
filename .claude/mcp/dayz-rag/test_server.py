"""Tests for the dayz-rag MCP server's pure functions.

The LanceDB table and the Voyage client are stubbed, so these run without an
index, an API key, or P:\\ mounted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from collections import OrderedDict
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
        self.searches = getattr(self, "searches", 0) + 1
        self.last_query = _FakeQuery(self.rows)
        return self.last_query


def _row(path, file_type, distance):
    return {"path": path, "file_type": file_type, "_distance": distance, "content": "x", "line_start": 1, "line_end": 2}


@pytest.fixture
def fake_table(monkeypatch, tmp_path):
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
    # Each test starts with an empty answer cache over its own (unbuilt) index.
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_search_cache", OrderedDict())
    monkeypatch.setattr(server, "_manifest_stamp", None)
    monkeypatch.setattr(server, "_index_built_at", None)
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


@pytest.mark.parametrize("bad", [0, 0.0, -1.5, float("nan")])
def test_non_positive_max_distance_is_rejected(fake_table, bad):
    # A cutoff of 0 or below can never pass a hit; it must be a bad-argument
    # error (isError over MCP), not a silent empty list.
    with pytest.raises(ValueError, match="max_distance"):
        server.search_dayz_source_impl("vest", max_distance=bad)
    with pytest.raises(ValueError, match="max_distance"):
        server.search_dayz_source_impl("   ", max_distance=bad)


def test_top_k_is_clamped(fake_table):
    assert len(server.search_dayz_source_impl("vest", top_k=0)) == 1
    server.search_dayz_source_impl("vest", top_k=999)
    assert fake_table.last_query.limit_value == server.MAX_TOP_K


def test_missing_index_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_table", None)
    with pytest.raises(RuntimeError, match="dayz-search-index") as err:
        server._get_table()
    assert "/dayz-search-download" in str(err.value)


# --------------- answer cache ---------------


def _write_manifest(root, indexed_at, mtime_ns):
    manifest = root / "manifest.json"
    manifest.write_text(json.dumps({"indexed_at": indexed_at}), encoding="utf-8")
    os.utime(manifest, ns=(mtime_ns, mtime_ns))


def test_repeated_search_is_answered_from_cache(fake_table):
    first = server.search_dayz_source_impl("vest", top_k=2)
    again = server.search_dayz_source_impl("  vest ", top_k=2)
    assert again == first
    assert fake_table.searches == 1


def test_cache_key_includes_filters(fake_table):
    server.search_dayz_source_impl("vest", top_k=2)
    server.search_dayz_source_impl("vest", top_k=3)
    server.search_dayz_source_impl("vest", top_k=2, file_type="cpp")
    server.search_dayz_source_impl("jacket", top_k=2)
    assert fake_table.searches == 4


def test_max_distance_applies_to_cached_rows(fake_table):
    server.search_dayz_source_impl("vest", top_k=5)
    hits = server.search_dayz_source_impl("vest", top_k=5, max_distance=0.7)
    assert [h["path"] for h in hits] == ["https://wiki/a", "https://wiki/b"]
    assert fake_table.searches == 1


def test_stale_flag_is_rechecked_on_cached_answers(fake_table, monkeypatch):
    server.search_dayz_source_impl("vest", top_k=1)
    monkeypatch.setattr(server, "_check_stale", lambda _p: (True, "modified"))
    assert server.search_dayz_source_impl("vest", top_k=1)[0]["is_stale"] is True
    assert fake_table.searches == 1


def test_reindex_empties_the_cache(fake_table, tmp_path):
    _write_manifest(tmp_path, 100, 1_000_000_000)
    server.search_dayz_source_impl("vest", top_k=2)
    _write_manifest(tmp_path, 200, 2_000_000_000)
    server.search_dayz_source_impl("vest", top_k=2)
    assert fake_table.searches == 2
    assert server._get_index_built_at() == 200.0
    assert [k[3] for k in server._search_cache] == [200.0]


def test_reindex_reopens_the_table(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_manifest_stamp", None)
    monkeypatch.setattr(server, "_table", "old table")
    _write_manifest(tmp_path, 100, 1_000_000_000)
    server._sync_with_index()
    assert server._table is None


def test_reindex_reloads_embed_model(monkeypatch, tmp_path):
    models = []

    class _Client:
        def embed(self, **kwargs):
            models.append(kwargs["model"])
            return SimpleNamespace(embeddings=[[0.1]])

    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_manifest_stamp", None)
    monkeypatch.setattr(server, "_embed_model", None)
    monkeypatch.setattr(server, "_get_client", lambda: _Client())
    (tmp_path / "config.json").write_text(json.dumps({"embed_model": "voyage-old"}), encoding="utf-8")
    _write_manifest(tmp_path, 100, 1_000_000_000)
    server._sync_with_index()
    server._embed_query("q")
    (tmp_path / "config.json").write_text(json.dumps({"embed_model": "voyage-new"}), encoding="utf-8")
    _write_manifest(tmp_path, 200, 2_000_000_000)
    server._sync_with_index()
    server._embed_query("q")
    assert models == ["voyage-old", "voyage-new"]


def test_cache_is_bounded(fake_table, monkeypatch):
    monkeypatch.setattr(server, "CACHE_MAX", 2)
    for q in ("a", "b", "c"):
        server.search_dayz_source_impl(q)
    assert [k[0] for k in server._search_cache] == ["b", "c"]
    server.search_dayz_source_impl("a")
    assert fake_table.searches == 4


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


def test_slice_splits_on_newline_only_like_the_indexer():
    # splitlines would also break at \f, making "b" line 2 instead of "c".
    text = "a\fb\nc"
    out = server._slice_lines("p", text, 2, 2)
    assert out["content"] == "c"
    assert server._slice_lines("p", text, None, None)["line_end"] == 2


def test_slice_empty_text_has_no_lines():
    assert server._slice_lines("p", "", None, None)["line_end"] == 0


@pytest.mark.parametrize("start,end", [(0, 2), (3, 2), (9, None)])
def test_slice_rejects_bad_ranges(start, end):
    with pytest.raises(ValueError):
        server._slice_lines("p", _TEXT, start, end)


# --------------- stale detection ---------------


def _fake_path(monkeypatch, mtime=None, content=b"class A {};", hashes=None):
    """Make server.Path(...).stat() return the given mtime, or raise if None.

    The file's bytes are `content`; `hashes` is the indexer's recorded map (none by default).
    """

    def stat():
        if mtime is None:
            raise FileNotFoundError("gone")
        return SimpleNamespace(st_mtime=mtime)

    monkeypatch.setattr(server, "Path", lambda _p: SimpleNamespace(stat=stat, read_bytes=lambda: content))
    monkeypatch.setattr(server, "_get_file_hashes", lambda: hashes or {})


def test_non_local_paths_are_never_stale():
    assert server._check_stale("https://community.bistudio.com/wiki/DayZ") == (False, None)


def test_file_newer_than_index_is_stale(monkeypatch):
    monkeypatch.setattr(server, "_get_index_built_at", lambda: 100.0)
    _fake_path(monkeypatch, mtime=200.0)
    assert server._check_stale(r"P:\scripts\a.c") == (True, "modified")


def test_newer_file_with_the_indexed_content_is_fresh(monkeypatch):
    """A re-extracted P:\\ gives every file a new mtime; unchanged content is not stale."""
    monkeypatch.setattr(server, "_get_index_built_at", lambda: 100.0)
    digest = hashlib.sha256(b"class A {};").hexdigest()
    _fake_path(monkeypatch, mtime=200.0, hashes={r"P:\scripts\a.c": digest})
    assert server._check_stale(r"P:\scripts\a.c") == (False, None)


def test_newer_file_with_changed_content_is_stale(monkeypatch):
    monkeypatch.setattr(server, "_get_index_built_at", lambda: 100.0)
    digest = hashlib.sha256(b"class A {};").hexdigest()
    _fake_path(monkeypatch, mtime=200.0, content=b"class B {};", hashes={r"P:\scripts\a.c": digest})
    assert server._check_stale(r"P:\scripts\a.c") == (True, "modified")


def test_file_hashes_load_from_the_index_and_reset_on_rebuild(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(server, "_file_hashes", None)
    monkeypatch.setattr(server, "_manifest_stamp", None)
    assert server._get_file_hashes() == {}  # an index built before hashes existed
    (tmp_path / "file_hashes.json").write_text(json.dumps({"P:\\a.c": "ab"}), encoding="utf-8")
    assert server._get_file_hashes() == {}  # cached until the index changes
    _write_manifest(tmp_path, 1, 1_000)
    server._sync_with_index()
    assert server._get_file_hashes() == {"P:\\a.c": "ab"}


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


# --------------- list_indexed_sources ---------------


def test_list_sources_reports_nulls_when_nothing_built(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    assert server.list_indexed_sources_impl() == {"source": None}


def test_list_sources_returns_source_manifest(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"files": 3}), encoding="utf-8")
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    assert server.list_indexed_sources_impl() == {"source": {"files": 3}}


def test_list_sources_raises_on_corrupt_manifest(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="unreadable"):
        server.list_indexed_sources_impl()


def test_list_sources_raises_rebuild_hint_on_non_utf8_manifest(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_bytes(b'{"files": "\xff\xfe"}')
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    with pytest.raises(RuntimeError, match="rebuild"):
        server.list_indexed_sources_impl()


# --------------- query retry ---------------


def _fake_voyage_errors(monkeypatch):
    """Install a stand-in voyageai.error module so the retry rule needs no real SDK."""
    errors = SimpleNamespace(
        **{name: type(name, (Exception,), {}) for name in server.voyage_common.TRANSIENT_ERROR_NAMES},
        AuthenticationError=type("AuthenticationError", (Exception,), {}),
    )
    monkeypatch.setitem(sys.modules, "voyageai.error", errors)
    return errors


class _FlakyClient:
    def __init__(self, failures):
        self.failures = list(failures)
        self.calls = 0

    def embed(self, **_kwargs):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return SimpleNamespace(embeddings=[[0.5, 0.5]])


@pytest.fixture
def no_sleep(monkeypatch):
    sleeps = []
    monkeypatch.setattr(server.time, "sleep", sleeps.append)
    return sleeps


def test_query_retries_transient_voyage_errors(monkeypatch, no_sleep):
    errors = _fake_voyage_errors(monkeypatch)
    client = _FlakyClient([errors.RateLimitError("429"), errors.Timeout("slow")])
    monkeypatch.setattr(server, "_get_client", lambda: client)
    assert server._embed_query("q") == [0.5, 0.5]
    assert client.calls == 3
    assert no_sleep == [1.0, 2.0]


def test_query_does_not_retry_auth_errors(monkeypatch, no_sleep):
    errors = _fake_voyage_errors(monkeypatch)
    client = _FlakyClient([errors.AuthenticationError("bad key")])
    monkeypatch.setattr(server, "_get_client", lambda: client)
    with pytest.raises(errors.AuthenticationError):
        server._embed_query("q")
    assert client.calls == 1 and no_sleep == []


def test_query_gives_up_after_last_attempt(monkeypatch, no_sleep):
    errors = _fake_voyage_errors(monkeypatch)
    client = _FlakyClient([errors.APIConnectionError("down")] * server.QUERY_ATTEMPTS)
    monkeypatch.setattr(server, "_get_client", lambda: client)
    with pytest.raises(errors.APIConnectionError):
        server._embed_query("q")
    assert client.calls == server.QUERY_ATTEMPTS


def test_valid_file_types_match_the_indexer():
    index_py = Path(__file__).resolve().parents[2] / "skills" / "dayz-search-index" / "index.py"
    spec = importlib.util.spec_from_file_location("dayz_search_index_for_server_test", index_py)
    index = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(index)
    assert set(index.EXT_TYPE_MAP.values()) == server.VALID_FILE_TYPES


def test_app_registers_three_read_only_tools():
    pytest.importorskip("mcp")
    import asyncio

    tools = {t.name: t for t in asyncio.run(server.build_app().list_tools())}
    assert set(tools) == {"search_dayz_source", "get_dayz_file", "list_indexed_sources"}
    for tool in tools.values():
        assert tool.annotations is not None and tool.annotations.readOnlyHint is True
    assert tools["search_dayz_source"].annotations.openWorldHint is True
    # The MCP spec defaults openWorldHint to true, so the local tools must say False.
    assert tools["get_dayz_file"].annotations.openWorldHint is False
    assert tools["list_indexed_sources"].annotations.openWorldHint is False


def test_tool_error_reaches_client_as_is_error_result():
    pytest.importorskip("mcp")
    import asyncio

    from mcp.shared.memory import create_connected_server_and_client_session

    async def call():
        app = server.build_app()
        async with create_connected_server_and_client_session(app._mcp_server) as client:
            return await client.call_tool("get_dayz_file", {"path": "C:\\Windows\\win.ini"})

    result = asyncio.run(call())
    assert result.isError is True
    assert "P:" in result.content[0].text


def test_slow_search_does_not_block_other_tools(monkeypatch, tmp_path):
    """A search stuck in Voyage retries must not freeze the other tools.

    The fake search waits up to 5 s for the other tool call to finish. If the
    tools ran on the event loop, list_indexed_sources could not run until the
    search gave up, so the search would see the wait time out.
    """
    pytest.importorskip("mcp")
    import asyncio
    import threading

    import anyio
    from mcp.shared.memory import create_connected_server_and_client_session

    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    started, other_done = threading.Event(), threading.Event()
    seen = {}

    def slow_search(*_args):
        started.set()
        seen["other_ran_meanwhile"] = other_done.wait(timeout=5)
        return []

    monkeypatch.setattr(server, "search_dayz_source_impl", slow_search)

    async def call():
        app = server.build_app()
        async with create_connected_server_and_client_session(app._mcp_server) as client:
            async with anyio.create_task_group() as tg:
                tg.start_soon(client.call_tool, "search_dayz_source", {"query": "vest"})
                await anyio.to_thread.run_sync(started.wait, 5)
                with anyio.fail_after(4):
                    listed = await client.call_tool("list_indexed_sources", {})
                other_done.set()
            return listed

    listed = asyncio.run(call())
    assert listed.isError is False
    assert seen["other_ran_meanwhile"] is True


# --------------- embed model after a rebuild ---------------


def test_embed_model_comes_from_the_manifest_over_config(monkeypatch, tmp_path):
    """A search between the manifest and config.json writes must use the new model."""
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    (tmp_path / "config.json").write_text(json.dumps({"embed_model": "voyage-old"}), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({"embed_model": "voyage-new"}), encoding="utf-8")
    assert server._load_embed_model_name() == "voyage-new"


def test_embed_model_falls_back_to_config_then_env(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "INDEX_ROOT", tmp_path)
    monkeypatch.setenv("VOYAGE_MODEL", "voyage-env")
    assert server._load_embed_model_name() == "voyage-env"
    (tmp_path / "manifest.json").write_text(json.dumps({"indexed_at": 1}), encoding="utf-8")
    (tmp_path / "config.json").write_text(json.dumps({"embed_model": "voyage-cfg"}), encoding="utf-8")
    assert server._load_embed_model_name() == "voyage-cfg"


# --------------- snippet length ---------------


def test_snippet_is_cut_to_the_documented_limit():
    hit = server._format_hit({"path": "x", "content": "a" * (server.SNIPPET_MAX_CHARS + 10)})
    assert len(hit["snippet"]) == server.SNIPPET_MAX_CHARS == 1500


# --------------- get_dayz_file reads ---------------


@pytest.fixture
def temp_drive(monkeypatch, tmp_path):
    """Let get_dayz_file read tmp_path's drive in place of P:."""
    monkeypatch.setattr(server, "ALLOWED_DRIVE", tmp_path.drive)
    return tmp_path


def test_get_file_reads_whole_file_and_range(temp_drive):
    f = temp_drive / "a.c"
    f.write_text(_TEXT, encoding="utf-8")
    assert server.get_dayz_file_impl(str(f))["content"] == _TEXT
    out = server.get_dayz_file_impl(str(f), 2, 3)
    assert (out["path"], out["content"]) == (str(f), "two\nthree")


def test_get_file_normalises_dot_dot(temp_drive):
    sub = temp_drive / "sub"
    sub.mkdir()
    (temp_drive / "a.c").write_text(_TEXT, encoding="utf-8")
    out = server.get_dayz_file_impl(str(sub / ".." / "a.c"))
    assert out["path"] == str(temp_drive / "a.c")


def test_dot_dot_above_the_drive_root_stays_on_p():
    # normpath clamps `..` at the root, so the read stays on P: (and P:\Windows
    # does not exist), never reaching C:\Windows.
    with pytest.raises(FileNotFoundError, match=r"P:\\Windows"):
        server.get_dayz_file_impl(r"P:\..\..\Windows\win.ini")


def test_get_file_over_size_limit_needs_a_range(temp_drive, monkeypatch):
    monkeypatch.setattr(server, "MAX_FILE_BYTES", 10)
    f = temp_drive / "big.c"
    f.write_text(_TEXT * 3, encoding="utf-8")
    with pytest.raises(ValueError, match="line_start/line_end"):
        server.get_dayz_file_impl(str(f))
    assert server.get_dayz_file_impl(str(f), 1, 1)["content"] == "one"


def test_get_file_over_size_limit_refuses_open_ended_range(temp_drive, monkeypatch):
    # Only line_start set used to skip the cap and return the whole tail.
    monkeypatch.setattr(server, "MAX_FILE_BYTES", 10)
    f = temp_drive / "big.c"
    f.write_text(_TEXT * 3, encoding="utf-8")
    with pytest.raises(ValueError, match="narrower"):
        server.get_dayz_file_impl(str(f), line_start=1)
    with pytest.raises(ValueError, match="narrower"):
        server.get_dayz_file_impl(str(f), line_end=12)
    with pytest.raises(ValueError, match="narrower"):
        server.get_dayz_file_impl(str(f), 1, 12)


def test_get_file_missing_file_raises(temp_drive):
    with pytest.raises(FileNotFoundError):
        server.get_dayz_file_impl(str(temp_drive / "nope.c"))
