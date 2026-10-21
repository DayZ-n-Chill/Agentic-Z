"""Tests for the dayz-search-index chunkers and batch packing.

Pure functions only: no P:\\ drive, no Voyage key, no LanceDB.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_spec = importlib.util.spec_from_file_location("dayz_search_index", Path(__file__).parent / "index.py")
index = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(index)


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# --------------- class-block chunker ---------------


def test_block_chunks_one_per_top_level_class(tmp_path):
    src = (
        "// header\n"
        "class Foo\n{\n  void A() { if (x) { y(); } }\n}\n"
        "modded class Bar\n{\n  int b;\n}\n"
    )
    chunks = index._block_chunks(_write(tmp_path, "a.c", src), "c")
    assert [c["parent_context"] for c in chunks] == ["Foo", "Bar"]
    assert (chunks[0]["line_start"], chunks[0]["line_end"]) == (2, 5)
    assert (chunks[1]["line_start"], chunks[1]["line_end"]) == (6, 9)
    assert chunks[1]["content"].startswith("modded class Bar")
    assert all(c["file_type"] == "c" for c in chunks)


def test_block_chunks_config_inheritance_syntax(tmp_path):
    src = "class CfgVehicles\n{\n  class Vest_Base;\n  class MyVest: Vest_Base { scope = 2; };\n};\n"
    chunks = index._block_chunks(_write(tmp_path, "config.cpp", src), "cpp")
    assert [c["parent_context"] for c in chunks] == ["CfgVehicles"]


def test_block_chunks_falls_back_to_whole_file(tmp_path):
    src = "int g_Value = 1;\nvoid Helper() {}\n"
    chunks = index._block_chunks(_write(tmp_path, "b.c", src), "c")
    assert len(chunks) == 1
    assert chunks[0]["parent_context"] == ""
    assert chunks[0]["content"] == src


def test_block_chunks_stops_at_unbalanced_braces(tmp_path):
    src = "class Good { }\nclass Broken {\n"
    chunks = index._block_chunks(_write(tmp_path, "c.c", src), "c")
    assert [c["parent_context"] for c in chunks] == ["Good"]


def test_block_chunks_default_window_is_embed_limit(tmp_path):
    methods = "".join(f"  void M{i}()\n  {{\n    Print({i});\n  }}\n" for i in range(600))
    src = "class Big\n{\n" + methods + "}\n"
    chunks = index._block_chunks(_write(tmp_path, "big.c", src), "c")
    assert len(chunks) > 1
    assert all(len(c["content"]) <= index.EMBED_MAX_CHARS for c in chunks)
    assert all(c["parent_context"] == "Big" for c in chunks)
    assert "".join(c["content"] for c in chunks) == src.rstrip("\n")


def test_oversize_class_splits_at_method_boundaries(tmp_path):
    methods = "".join(f"  void M{i}()\n  {{\n    Print({i});\n  }}\n" for i in range(10))
    src = "// header\nclass Big\n{\n" + methods + "}\n"
    chunks = index._block_chunks(_write(tmp_path, "m.c", src), "c", max_chars=120)
    lines = src.splitlines()
    # Every window fits, keeps the class name, and no text is lost.
    assert all(len(c["content"]) <= 120 for c in chunks)
    assert {c["parent_context"] for c in chunks} == {"Big"}
    assert "".join(c["content"] for c in chunks) == src[len("// header\n"):].rstrip("\n")
    # Line ranges are real, contiguous, and cover the whole class.
    assert chunks[0]["line_start"] == 2
    assert chunks[-1]["line_end"] == len(lines)
    for prev, nxt in zip(chunks, chunks[1:]):
        assert nxt["line_start"] == prev["line_end"] + 1
    for c in chunks:
        expected = "\n".join(lines[c["line_start"] - 1 : c["line_end"]])
        assert c["content"].rstrip("\n") == expected
    # Windows after the first start on a method signature, not mid-method.
    assert all(c["content"].startswith("  void M") for c in chunks[1:])


def test_oversize_method_without_boundaries_splits_by_lines(tmp_path):
    stmts = "".join(f"    Print({i});\n" for i in range(40))
    src = "class Flat\n{\n  void M()\n  {\n" + stmts + "  }\n}\n"
    chunks = index._block_chunks(_write(tmp_path, "f.c", src), "c", max_chars=60)
    assert len(chunks) > 1
    assert all(len(c["content"]) <= 60 for c in chunks)
    assert "".join(c["content"] for c in chunks) == src.rstrip("\n")


def test_overlong_single_line_is_sliced_not_dropped(tmp_path):
    src = "class Big {\n" + "x" * 100 + "\n}\n"
    chunks = index._block_chunks(_write(tmp_path, "d.c", src), "c", max_chars=20)
    assert all(len(c["content"]) <= 20 for c in chunks)
    assert "".join(c["content"] for c in chunks) == src.rstrip("\n")
    assert {(c["line_start"], c["line_end"]) for c in chunks if "x" in c["content"]} == {(2, 2)}


def test_oversize_file_without_classes_is_windowed(tmp_path):
    src = "".join(f"int g_V{i} = {i};\n" for i in range(50))
    chunks = index._block_chunks(_write(tmp_path, "g.c", src), "c", max_chars=100)
    assert len(chunks) > 1
    assert {c["parent_context"] for c in chunks} == {""}
    assert "".join(c["content"] for c in chunks) == src


def test_empty_file_produces_no_chunks(tmp_path):
    assert index._block_chunks(_write(tmp_path, "e.c", ""), "c") == []
    assert index.chunk_whole_file(_write(tmp_path, "e.json", ""), "json") == []


# --------------- rvmat dedup ---------------


def test_rvmat_dedup_by_content(tmp_path):
    body = 'class Stage1 { texture = "x_nohq.paa"; };\n'
    a = _write(tmp_path, "a.rvmat", body)
    b = _write(tmp_path, "b.rvmat", body)
    c = _write(tmp_path, "c.rvmat", body + "// different\n")
    seen: set[str] = set()

    first = index.chunk_rvmat(a, seen)
    assert first is not None and first[0]["file_type"] == "rvmat"
    assert len(first[0]["parent_context"]) == 12  # short content hash
    assert index.chunk_rvmat(b, seen) is None  # same bytes, different path
    assert index.chunk_rvmat(c, seen) is not None
    assert len(seen) == 2


def test_rvmat_unreadable_file_is_skipped(tmp_path):
    assert index.chunk_rvmat(tmp_path / "missing.rvmat", set()) is None


# --------------- xml chunker ---------------


def _types_xml(n: int) -> str:
    items = "\n".join(
        f'  <type name="Item{i:03d}"><nominal>{i}</nominal><lifetime>3600</lifetime></type>' for i in range(n)
    )
    return f"<types>\n{items}\n</types>\n"


def test_small_xml_is_one_chunk(tmp_path):
    chunks = index.chunk_xml(_write(tmp_path, "s.xml", _types_xml(3)))
    assert len(chunks) == 1
    assert chunks[0]["parent_context"] == ""


def test_large_xml_batches_top_level_elements(tmp_path):
    text = _types_xml(120)
    assert len(text) >= 4000
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", text))
    assert len(chunks) == 3  # 50 + 50 + 20
    assert chunks[0]["parent_context"] == "types > Item000..Item049 (50 items)"
    assert chunks[2]["parent_context"] == "types > Item100..Item119 (20 items)"
    assert 'name="Item049"' in chunks[0]["content"]
    assert 'name="Item050"' not in chunks[0]["content"]


def test_unparseable_large_xml_falls_back_to_whole_file(tmp_path):
    text = _types_xml(120).replace("</types>", "")  # unclosed root
    chunks = index.chunk_xml(_write(tmp_path, "bad.xml", text))
    assert len(chunks) == 1
    assert chunks[0]["parent_context"] == ""


# --------------- batch packing ---------------


def test_pack_batches_respects_text_limit():
    texts = ["a"] * (index.TEXT_LIMIT_PER_BATCH * 2 + 5)
    sizes = [len(b) for b in index._pack_batches(texts)]
    assert sizes == [index.TEXT_LIMIT_PER_BATCH, index.TEXT_LIMIT_PER_BATCH, 5]


def test_pack_batches_respects_token_budget():
    # Each text is estimated at 40% of the budget, so two fit and the third spills.
    chars = int(index.TOKEN_BUDGET_PER_BATCH * 0.4 * index.CHARS_PER_TOKEN_EST)
    texts = ["x" * chars] * 5
    sizes = [len(b) for b in index._pack_batches(texts)]
    assert sizes == [2, 2, 1]


def test_pack_batches_oversize_text_goes_alone_and_order_is_kept():
    huge = "h" * int(index.TOKEN_BUDGET_PER_BATCH * index.CHARS_PER_TOKEN_EST * 2)
    texts = ["a", huge, "b"]
    batches = list(index._pack_batches(texts))
    assert batches == [["a"], [huge], ["b"]]
    assert [t for b in batches for t in b] == texts


def test_pack_batches_empty_input():
    assert list(index._pack_batches([])) == []


def test_private_embed_alias_kept_for_wiki_indexer():
    assert index._embed_all is index.embed_all


def test_large_xml_batches_record_real_line_ranges(tmp_path):
    # _types_xml puts the root on line 1 and item i on line i + 2.
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", _types_xml(120)))
    assert [(c["line_start"], c["line_end"]) for c in chunks] == [(2, 51), (52, 101), (102, 121)]


def test_xml_line_ranges_cover_multiline_elements(tmp_path):
    items = "\n".join(
        f'  <type name="Item{i:03d}">\n    <nominal>{i}</nominal>\n    <lifetime>3600</lifetime>\n  </type>'
        for i in range(60)
    )
    text = f'<?xml version="1.0" encoding="UTF-8"?>\n<types>\n{items}\n</types>\n'
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", text), batch_size=50)
    # Item i spans lines 3 + 4i .. 6 + 4i.
    assert (chunks[0]["line_start"], chunks[0]["line_end"]) == (3, 6 + 4 * 49)
    assert (chunks[1]["line_start"], chunks[1]["line_end"]) == (3 + 4 * 50, 6 + 4 * 59)


# --------------- --status, gate, ceiling ---------------


def test_status_without_index_creates_nothing(tmp_path, monkeypatch, capsys):
    root = tmp_path / "no-index-here"
    monkeypatch.setattr(index, "INDEX_ROOT", root)
    monkeypatch.setattr(index.h, "gate_on_preflight", lambda: (_ for _ in ()).throw(AssertionError("no gate for --status")))
    assert index.main(["--status"]) == 1
    assert not root.exists()
    assert "No index" in capsys.readouterr().err


def test_status_prints_manifest(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    (tmp_path / "manifest.json").write_text('{"total_chunks": 3}', encoding="utf-8")
    assert index.main(["--status"]) == 0
    assert '"total_chunks": 3' in capsys.readouterr().out


def test_build_gates_on_preflight(tmp_path, monkeypatch):
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path / "idx")

    def failing_gate():
        raise SystemExit(1)

    monkeypatch.setattr(index.h, "gate_on_preflight", failing_gate)
    with pytest.raises(SystemExit) as exc:
        index.main(["--full"])
    assert exc.value.code == 1
    assert not (tmp_path / "idx").exists()


def test_chunk_ceiling_is_a_module_constant():
    assert index.CHUNK_CEILING == 150_000


# --------------- tier check overage uses the model rate ---------------


def test_tier_overage_uses_model_rate(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    monkeypatch.setenv("VOYAGE_FREE_TIER_TOKENS", "1000000")
    # 2M tokens past a 1M budget = 1M over.
    assert index._check_voyage_tier(2_000_000, True, "voyage-4-lite")
    assert "estimated overage: $0.02" in capsys.readouterr().out
    assert index._check_voyage_tier(2_000_000, True, "voyage-code-3")
    assert "estimated overage: $0.18" in capsys.readouterr().out
    assert index._check_voyage_tier(2_000_000, True, "some-new-model")
    assert "no local rate for some-new-model" in capsys.readouterr().out


# --------------- staged table write ---------------


class _FakeTable:
    def __init__(self, rows):
        self.rows = list(rows)

    def to_arrow(self):
        return list(self.rows)


class _FakeDb:
    def __init__(self, tables=None, fail_on=None):
        self.tables = {k: _FakeTable(v) for k, v in (tables or {}).items()}
        self.fail_on = fail_on
        self.log = []

    def table_names(self):
        return list(self.tables)

    def drop_table(self, name):
        self.log.append(("drop", name))
        del self.tables[name]

    def create_table(self, name, data, mode="create"):
        self.log.append(("create", name, mode))
        if name == self.fail_on:
            raise OSError("disk full")
        if name in self.tables and mode != "overwrite":
            raise ValueError(f"table {name} exists")
        self.tables[name] = _FakeTable(data)
        return self.tables[name]


def test_write_table_swaps_new_rows_in_and_drops_staging():
    db = _FakeDb({index.TABLE_NAME: [{"v": "old"}]})
    index.write_table(db, [{"v": "new"}])
    assert db.tables[index.TABLE_NAME].rows == [{"v": "new"}]
    assert index.STAGING_TABLE_NAME not in db.tables


def test_write_table_failed_staging_leaves_live_table():
    db = _FakeDb({index.TABLE_NAME: [{"v": "old"}]}, fail_on=index.STAGING_TABLE_NAME)
    with pytest.raises(OSError):
        index.write_table(db, [{"v": "new"}])
    assert db.tables[index.TABLE_NAME].rows == [{"v": "old"}]
    assert ("drop", index.TABLE_NAME) not in db.log


def test_write_table_clears_leftover_staging_and_works_on_empty_db():
    db = _FakeDb({index.STAGING_TABLE_NAME: [{"v": "stale"}]})
    index.write_table(db, [{"v": "new"}])
    assert db.tables == {index.TABLE_NAME: db.tables[index.TABLE_NAME]}
    assert db.tables[index.TABLE_NAME].rows == [{"v": "new"}]


# --------------- token estimate ---------------


def test_estimate_tokens_uses_chars_per_token_constant():
    text = "x" * int(index.CHARS_PER_TOKEN_EST * 1000)
    assert index._estimate_tokens(text) == 1000
    assert index._estimate_tokens("") == 1


# --------------- embed retry ---------------


class _FakeBar:
    def __init__(self, *args, **kwargs):
        self.lines = []

    def write(self, line):
        self.lines.append(line)

    def set_postfix_str(self, _s):
        pass

    def update(self, _n):
        pass

    def close(self):
        pass


@pytest.fixture
def fake_voyage(monkeypatch):
    """Stand-in voyageai + tqdm modules; returns (errors, scripted failures list, call log)."""
    names = index.voyage_common.TRANSIENT_ERROR_NAMES + ("AuthenticationError",)
    errors = SimpleNamespace(**{n: type(n, (Exception,), {}) for n in names})
    failures: list[Exception] = []
    calls: list[list[str]] = []

    class Client:
        def __init__(self, **_kwargs):
            pass

        def embed(self, texts, **_kwargs):
            calls.append(texts)
            if failures:
                raise failures.pop(0)
            return SimpleNamespace(embeddings=[[0.0] for _ in texts], total_tokens=len(texts))

    monkeypatch.setitem(sys.modules, "voyageai", SimpleNamespace(Client=Client, error=errors))
    monkeypatch.setitem(sys.modules, "voyageai.error", errors)
    monkeypatch.setitem(sys.modules, "tqdm", SimpleNamespace(tqdm=_FakeBar))
    monkeypatch.setattr(index.time, "sleep", lambda _s: None)
    return errors, failures, calls


def test_embed_all_retries_transient_errors(fake_voyage):
    errors, failures, calls = fake_voyage
    failures += [errors.RateLimitError("429"), errors.ServiceUnavailableError("503")]
    vectors, tokens = index.embed_all(["a", "b"], "voyage-code-3", "pa-test")
    assert len(vectors) == 2 and tokens == 2
    assert len(calls) == 3


def test_embed_all_does_not_retry_auth_errors(fake_voyage):
    errors, failures, calls = fake_voyage
    failures.append(errors.AuthenticationError("bad key"))
    with pytest.raises(errors.AuthenticationError):
        index.embed_all(["a"], "voyage-code-3", "pa-test")
    assert len(calls) == 1


def test_embed_all_gives_up_after_last_attempt(fake_voyage):
    errors, failures, calls = fake_voyage
    failures += [errors.Timeout("slow")] * index.EMBED_ATTEMPTS
    with pytest.raises(errors.Timeout):
        index.embed_all(["a"], "voyage-code-3", "pa-test")
    assert len(calls) == index.EMBED_ATTEMPTS


# --------------- API key ---------------


def test_missing_key_exits_1_with_fail_line(monkeypatch, capsys):
    monkeypatch.setattr(index.voyage_common, "dotenv_paths", lambda: [])
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        index._load_env_and_key()
    assert exc.value.code == 1
    assert "VOYAGE_API_KEY not set" in capsys.readouterr().err
