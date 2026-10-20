"""Tests for the dayz-search-index chunkers and batch packing.

Pure functions only: no P:\\ drive, no Voyage key, no LanceDB.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

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


def test_block_chunks_truncates_long_blocks(tmp_path):
    src = "class Big {\n" + "x" * 100 + "\n}\n"
    chunks = index._block_chunks(_write(tmp_path, "d.c", src), "c", max_chars=20)
    assert len(chunks[0]["content"]) == 20


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
