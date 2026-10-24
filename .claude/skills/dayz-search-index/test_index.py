"""Tests for the dayz-search-index chunkers, embed loop, checkpoint and index write.

Everything external is faked:no P:\\ drive, no Voyage key, no LanceDB.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
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


def test_block_chunks_keeps_unclosed_class_as_file_scope_text(tmp_path):
    src = "class Good { }\nclass Broken {\n  int x;\n"
    chunks = index._block_chunks(_write(tmp_path, "c.c", src), "c")
    assert [c["parent_context"] for c in chunks] == ["Good", ""]
    assert chunks[1]["content"] == "class Broken {\n  int x;\n"
    assert chunks[1]["line_start"] == 2


def test_braces_in_comments_and_strings_do_not_end_a_class(tmp_path):
    src = (
        "class A\n{\n"
        "  // a stray } in a comment\n"
        "  /* and { another */\n"
        '  string s = "}}";\n'
        '  string t = "say \\"}\\" here";\n'
        "  void M() { }\n"
        "}\n"
        "// class Fake {\n"
        "class B { }\n"
    )
    chunks = index._block_chunks(_write(tmp_path, "s.c", src), "c")
    assert [c["parent_context"] for c in chunks] == ["A", "B"]
    assert (chunks[0]["line_start"], chunks[0]["line_end"]) == (1, 8)
    assert chunks[0]["content"].rstrip().endswith("void M() { }\n}")


def test_config_backslash_is_not_an_escape(tmp_path):
    # The closing brace shares the line with the path, so an escaping
    # backslash would swallow it and run class A on into class B.
    src = 'class A { file = "MyMod\\"; };\nclass B { };\n'
    chunks = index._block_chunks(_write(tmp_path, "config.cpp", src), "cpp")
    assert [c["parent_context"] for c in chunks if c["parent_context"]] == ["A", "B"]
    assert (chunks[0]["line_start"], chunks[0]["line_end"]) == (1, 1)
    # In a .c file the same backslash is an escape.
    escaped = index._block_chunks(_write(tmp_path, "a.c", src), "c")
    assert [c["parent_context"] for c in escaped] != ["A", "B"]


def test_code_between_classes_is_indexed(tmp_path):
    src = (
        "// file header\n"
        "enum EColor\n{\n  RED,\n  BLUE\n}\n\n"
        "class A { }\n"
        "\n"
        "typedef array<int> TIntArray;\n"
        "void GlobalHelper()\n{\n  Print(1);\n}\n"
        "class B { }\n"
        "const int LAST = 1;\n"
    )
    chunks = index._block_chunks(_write(tmp_path, "g.c", src), "c")
    assert [c["parent_context"] for c in chunks] == ["", "A", "", "B", ""]
    assert "enum EColor" in chunks[0]["content"]
    assert chunks[2]["content"].startswith("typedef array<int>")
    assert chunks[2]["line_start"] == 10
    assert "void GlobalHelper()" in chunks[2]["content"]
    assert chunks[4]["content"].strip() == "const int LAST = 1;"
    # Every non-blank line of the file lands in some chunk.
    joined = "".join(c["content"] for c in chunks)
    assert all(line in joined for line in src.splitlines() if line.strip())


def test_comment_only_gap_is_not_a_chunk(tmp_path):
    src = "class A { }\n// just a note\n/* and a block */\nclass B { }\n"
    chunks = index._block_chunks(_write(tmp_path, "n.c", src), "c")
    assert [c["parent_context"] for c in chunks] == ["A", "B"]


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


def test_file_hash_is_the_content_sha256(tmp_path):
    """The server compares this hash to tell a changed file from a re-extracted one."""
    import hashlib

    p = tmp_path / "a.c"
    p.write_bytes(b"class A {};")
    assert index.file_sha256(p) == hashlib.sha256(b"class A {};").hexdigest()
    assert index.file_sha256(tmp_path / "gone.c") is None


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
    assert all(c["parent_context"] == "" for c in chunks)
    # Whole-file windows: nothing cut, every window within the embed limit.
    assert "".join(c["content"] for c in chunks) == text
    assert all(len(c["content"]) <= index.EMBED_MAX_CHARS for c in chunks)
    assert chunks[0]["line_start"] == 1 and chunks[-1]["line_end"] == len(text.splitlines())


def test_20k_xml_loses_no_text_and_batches_by_size(tmp_path):
    items = "\n".join(
        f'  <type name="Item{i:03d}"><nominal>{i}</nominal>' + "<usage name=\"Military\"/>" * 8 + "</type>"
        for i in range(90)
    )
    text = f"<types>\n{items}\n</types>\n"
    assert len(text) >= 20_000
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", text))
    assert all(len(c["content"]) <= index.EMBED_MAX_CHARS for c in chunks)
    joined = "\n".join(c["content"] for c in chunks)
    assert all(f'name="Item{i:03d}"' in joined for i in range(90))
    assert sum(len(c["content"]) for c in chunks) >= len(items) - 90 * 3  # only the joins between items differ
    # Batches stop at the size limit, not at a fixed 50 elements.
    assert all("(50 items)" not in c["parent_context"] for c in chunks)


def test_xml_element_larger_than_embed_limit_is_windowed(tmp_path):
    import xml.etree.ElementTree as ET

    big = "<event name=\"Big\">\n" + "".join(f"  <pos x=\"{i}\" z=\"{i}\"/>\n" for i in range(900)) + "</event>"
    small = "\n".join(f'<event name="E{i}"><nominal>1</nominal></event>' for i in range(5))
    text = f"<events>\n{small}\n{big}\n</events>\n"
    chunks = index.chunk_xml(_write(tmp_path, "events.xml", text))
    big_chunks = [c for c in chunks if c["parent_context"] == "events > Big"]
    assert len(big_chunks) > 1
    assert all(len(c["content"]) <= index.EMBED_MAX_CHARS for c in big_chunks)
    ET.fromstring(text)  # the fixture is well-formed, so this is the parsed path
    # The windows are the element's own source lines, exactly as written.
    assert "".join(c["content"] for c in big_chunks) == big + "\n"
    assert big_chunks[0]["line_start"] == 7 and big_chunks[-1]["line_end"] == 7 + 901
    lines = text.split("\n")
    for c in big_chunks:
        assert c["content"].rstrip("\n") == "\n".join(lines[c["line_start"] - 1 : c["line_end"]])


def _commented_types_xml() -> str:
    """A >4 KB types.xml with comments before the root, between, inside and after the elements."""
    items = []
    for i in range(80):
        if i == 10:
            items.append('  <!-- <type name="DisabledItem"><nominal>0</nominal></type> -->')
        items.append(f'  <type name="Item{i:03d}">\n    <nominal>{i}</nominal> <!-- tuned {i} -->\n  </type>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<!-- vanilla economy -->\n<types>\n'
        + "\n".join(items)
        + "\n  <!-- trailing note -->\n</types>\n"
    )


def test_large_xml_keeps_comments_and_source_text(tmp_path):
    text = _commented_types_xml()
    assert len(text) >= 4000
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", text))
    assert len(chunks) > 1
    joined = "".join(c["content"] for c in chunks)
    # Leading and trailing comments pull in the whole file; nothing is lost or reformatted.
    assert joined == text
    for note in ('<!-- <type name="DisabledItem">', "<!-- tuned 42 -->", "<!-- vanilla economy -->", "<!-- trailing note -->"):
        assert note in joined
    lines = index._split_lines(text)
    for c in chunks:  # every chunk is the file's own lines for its range
        assert c["content"] == "".join(lines[c["line_start"] - 1 : c["line_end"]])
    assert all(len(c["content"]) <= index.EMBED_MAX_CHARS for c in chunks)
    # A commented-out entry travels with the element that follows it.
    disabled = next(c for c in chunks if "DisabledItem" in c["content"])
    assert "Item010" in disabled["content"]


def test_xml_without_outer_comments_leaves_out_only_the_root_tags(tmp_path):
    text = _commented_types_xml().replace("<!-- vanilla economy -->\n", "").replace("  <!-- trailing note -->\n", "")
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", text))
    joined = "".join(c["content"] for c in chunks)
    head = '<?xml version="1.0" encoding="UTF-8"?>\n<types>\n'
    assert joined == text[len(head) : -len("</types>\n")]
    assert chunks[0]["line_start"] == 3


def test_xml_elements_sharing_a_line_stay_in_one_chunk(tmp_path):
    row = "".join(f'<type name="T{i}"><nominal>{i}</nominal></type>' for i in range(5))
    text = "<types>\n" + "\n".join(row for _ in range(30)) + "\n</types>\n"
    assert len(text) >= 4000
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", text))
    lines = index._split_lines(text)
    assert all(c["content"] == "".join(lines[c["line_start"] - 1 : c["line_end"]]) for c in chunks)
    assert "".join(c["content"] for c in chunks) == text[len("<types>\n") : -len("</types>\n")]
    assert all(c["parent_context"].endswith("items)") for c in chunks)


def test_xml_with_non_utf8_encoding_declaration_is_parsed(tmp_path):
    text = _types_xml(120).replace("<types>", '<?xml version="1.0" encoding="windows-1252"?>\n<types>', 1)
    text = text.replace("Item005", "Itém005")
    chunks = index.chunk_xml(_write(tmp_path, "types.xml", text))
    assert chunks[0]["parent_context"].startswith("types > Item000..")
    assert any('name="Itém005"' in c["content"] for c in chunks)


def test_20k_csv_loses_no_rows_and_repeats_the_header(tmp_path):
    header = "Language,original,english,czech\n"
    rows = "".join(f"STR_ITEM_{i:04d},Item {i},Item {i},Predmet {i}\n" for i in range(500))
    text = header + rows
    assert len(text) >= 20_000
    chunks = index.chunk_whole_file(_write(tmp_path, "stringtable.csv", text), "csv")
    assert len(chunks) > 1
    assert all(c["content"].startswith(header) for c in chunks)
    assert all(len(c["content"]) <= index.EMBED_MAX_CHARS for c in chunks)
    assert "".join(c["content"][len(header):] for c in chunks) == rows
    lines = text.splitlines(keepends=True)
    for c in chunks:  # each chunk's line range is the rows it holds
        assert "".join(lines[c["line_start"] - 1 : c["line_end"]]) == c["content"][len(header):]


def test_csv_header_over_half_the_window_is_not_repeated(tmp_path):
    """SKILL.md documents this limit: a header over EMBED_MAX_CHARS // 2 is only in the first window."""
    header = ",".join(f"lang{i:04d}" for i in range(index.EMBED_MAX_CHARS // 2 // 9 + 1)) + "\n"
    assert len(header) > index.EMBED_MAX_CHARS // 2
    rows = "".join(f"STR_{i:04d},x\n" for i in range(800))
    chunks = index.chunk_whole_file(_write(tmp_path, "wide.csv", header + rows), "csv")
    assert chunks[0]["content"].startswith(header)
    assert not any(c["content"].startswith(header) for c in chunks[1:])
    assert "".join(c["content"] for c in chunks) == header + rows


def test_line_numbers_count_only_newlines(tmp_path):
    """str.splitlines also breaks at \\f and \\u2028; chunk line ranges must follow real lines."""
    method = "    void M{n}() {{ int a = 1; }}\n"
    body = "".join(method.format(n=i) for i in range(400))
    text = "// header\x0c\nclass Big {\n" + body.replace("M5()", "M5() /*   */") + "};\n"
    chunks = index._block_chunks(_write(tmp_path, "big.c", text), "c")
    lines = text.split("\n")
    big = [c for c in chunks if c["parent_context"] == "Big"]
    assert len(big) > 1
    for c in big:
        expected = "\n".join(lines[c["line_start"] - 1 : c["line_end"]])
        content = c["content"].rstrip("\n")
        # The class block ends at its "}", before the closing ";" on the last line.
        assert expected.startswith(content) and expected[len(content):] in ("", ";")


def test_large_json_is_windowed_not_cut(tmp_path):
    import json

    text = json.dumps({f"key{i}": {"value": i, "note": "x" * 40} for i in range(400)}, indent=2)
    assert len(text) > index.EMBED_MAX_CHARS
    chunks = index.chunk_whole_file(_write(tmp_path, "big.json", text), "json")
    assert len(chunks) > 1
    assert "".join(c["content"] for c in chunks) == text
    assert all(len(c["content"]) <= index.EMBED_MAX_CHARS for c in chunks)


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


def _over_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    monkeypatch.setenv("VOYAGE_FREE_TIER_TOKENS", "1000000")


def test_non_interactive_tier_refusal_is_one_stderr_line_naming_the_flag(tmp_path, monkeypatch, capsys):
    _over_budget(tmp_path, monkeypatch)

    def eof(_prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    assert index._check_voyage_tier(2_000_000, False) is False
    captured = capsys.readouterr()
    assert index.FAIL not in captured.out
    fails = _fail_lines(captured.err)
    assert len(fails) == 1 and "--ignore-tier-warning" in fails[0]
    assert "Cancelled" not in captured.err


def test_declined_tier_prompt_says_cancelled(tmp_path, monkeypatch, capsys):
    _over_budget(tmp_path, monkeypatch)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "n")
    assert index._check_voyage_tier(2_000_000, False) is False
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "Cancelled at the free-tier prompt" in fails[0]


def test_accepted_tier_prompt_proceeds(tmp_path, monkeypatch, capsys):
    _over_budget(tmp_path, monkeypatch)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "y")
    assert index._check_voyage_tier(2_000_000, False) is True
    assert _fail_lines(capsys.readouterr().err) == []


def test_non_interactive_build_refusal_prints_only_the_flag_line(tmp_path, monkeypatch, capsys):
    _stub_build(tmp_path, monkeypatch)
    monkeypatch.setenv("VOYAGE_FREE_TIER_TOKENS", "1")

    def eof(_prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    assert index.main(["--full"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "--ignore-tier-warning" in fails[0]


@pytest.mark.parametrize("value", ["abc", "1.5", "0", "-5"])
def test_bad_free_tier_budget_is_a_clear_fail_not_a_traceback(tmp_path, monkeypatch, capsys, value):
    _stub_build(tmp_path, monkeypatch)
    monkeypatch.setenv("VOYAGE_FREE_TIER_TOKENS", value)
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "VOYAGE_FREE_TIER_TOKENS" in fails[0] and repr(value) in fails[0]
    assert not (tmp_path / "idx" / "manifest.json").exists()


def test_free_tier_budget_accepts_separators_and_defaults_when_unset(monkeypatch):
    monkeypatch.setenv("VOYAGE_FREE_TIER_TOKENS", "50_000,000")
    assert index._free_tier_budget() == 50_000_000
    monkeypatch.setenv("VOYAGE_FREE_TIER_TOKENS", "  ")
    assert index._free_tier_budget() == index.VOYAGE_FREE_TIER_BUDGET
    monkeypatch.delenv("VOYAGE_FREE_TIER_TOKENS")
    assert index._free_tier_budget() == index.VOYAGE_FREE_TIER_BUDGET


def test_startup_line_shows_only_the_last_4_key_characters(tmp_path, monkeypatch, capsys):
    _stub_build(tmp_path, monkeypatch)
    assert index.main(["--full", "--ignore-tier-warning"]) == 0
    out = capsys.readouterr().out
    assert "VOYAGE_API_KEY loaded (ending ...1234)" in out
    assert "pa-tes" not in out
    assert index._key_hint("short") == "set"


def test_usage_counts_every_logged_build_not_only_this_month(tmp_path, monkeypatch):
    # Voyage's free tokens are per account with no monthly reset, so an old build still counts.
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    old = int(time.time()) - 90 * 86400
    (tmp_path / index.USAGE_LOG_NAME).write_text(
        json.dumps({"timestamp_unix": old, "tokens": 150_000_000}) + "\n"
        + json.dumps({"timestamp_unix": int(time.time()), "tokens": 1_000}) + "\n"
        + "not json\n",
        encoding="utf-8",
    )
    assert index._read_logged_usage_tokens() == 150_001_000


# --------------- staged table write ---------------


class _FakeTable:
    """A LanceDB table stand-in that keeps every version, as an overwrite does."""

    def __init__(self, rows):
        self.history = [list(rows)]
        self._checked_out = None

    @property
    def rows(self):
        return self.history[-1]

    @property
    def version(self):
        return len(self.history)

    def to_arrow(self):
        return list(self.rows)

    def checkout(self, version):
        self._checked_out = version

    def restore(self):
        self.history.append(list(self.history[self._checked_out - 1]))


class _FakeDb:
    def __init__(self, tables=None, fail_on=None):
        self.tables = {k: _FakeTable(v) for k, v in (tables or {}).items()}
        self.fail_on = fail_on
        self.log = []

    def table_names(self):
        return list(self.tables)

    def open_table(self, name):
        return self.tables[name]

    def drop_table(self, name):
        self.log.append(("drop", name))
        del self.tables[name]

    def create_table(self, name, data, mode="create"):
        self.log.append(("create", name, mode))
        if name == self.fail_on:
            raise OSError("disk full")
        if name in self.tables and mode != "overwrite":
            raise ValueError(f"table {name} exists")
        if name in self.tables:
            self.tables[name].history.append(list(data))
        else:
            self.tables[name] = _FakeTable(data)
        return self.tables[name]


def test_write_table_swaps_new_rows_in_and_drops_staging():
    db = _FakeDb({index.TABLE_NAME: [{"v": "old"}]})
    assert index.write_table(db, [{"v": "new"}]) == 1  # the version to roll back to
    assert db.tables[index.TABLE_NAME].rows == [{"v": "new"}]
    assert index.STAGING_TABLE_NAME not in db.tables


def test_rollback_table_restores_previous_version_or_drops_new_table():
    db = _FakeDb({index.TABLE_NAME: [{"v": "old"}]})
    index.rollback_table(db, index.write_table(db, [{"v": "new"}]))
    assert db.tables[index.TABLE_NAME].rows == [{"v": "old"}]

    empty = _FakeDb()
    index.rollback_table(empty, index.write_table(empty, [{"v": "new"}]))
    assert empty.tables == {}


def test_write_table_failed_staging_leaves_live_table():
    db = _FakeDb({index.TABLE_NAME: [{"v": "old"}]}, fail_on=index.STAGING_TABLE_NAME)
    with pytest.raises(OSError):
        index.write_table(db, [{"v": "new"}])
    assert db.tables[index.TABLE_NAME].rows == [{"v": "old"}]
    assert ("drop", index.TABLE_NAME) not in db.log


def test_failed_staging_cleanup_after_swap_still_commits_the_sidecars(tmp_path, monkeypatch):
    """The swap already happened, so a failed staging drop must not leave the new table beside the old config."""
    db, _old = _old_index(tmp_path / "idx")
    real_drop = db.drop_table

    def drop(name):
        if name == index.STAGING_TABLE_NAME and index.TABLE_NAME in db.tables and db.tables[index.TABLE_NAME].version > 1:
            raise OSError("staging locked")
        real_drop(name)

    db.drop_table = drop
    idx = _stub_build(tmp_path, monkeypatch, db)
    monkeypatch.setenv("VOYAGE_MODEL", "voyage-3.5")
    assert index.main(["--full", "--ignore-tier-warning"]) == 0
    assert [r["content"] for r in db.tables[index.TABLE_NAME].rows] == ["class A { int x; }"]
    assert json.loads((idx / "config.json").read_text(encoding="utf-8"))["embed_model"] == "voyage-3.5"


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
        self._items = args[0] if args else []

    def __iter__(self):
        return iter(self._items)

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
            return SimpleNamespace(embeddings=[[0.0] * index.EMBED_DIM for _ in texts], total_tokens=len(texts))

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
    with pytest.raises(index.EmbedError) as exc:
        index.embed_all(["a"], "voyage-code-3", "pa-test")
    assert isinstance(exc.value.cause, errors.AuthenticationError)
    assert exc.value.transient is False
    assert len(calls) == 1


def test_embed_all_gives_up_after_last_attempt(fake_voyage):
    errors, failures, calls = fake_voyage
    failures += [errors.Timeout("slow")] * index.EMBED_ATTEMPTS
    with pytest.raises(index.EmbedError) as exc:
        index.embed_all(["a"], "voyage-code-3", "pa-test")
    assert isinstance(exc.value.cause, errors.Timeout)
    assert exc.value.transient is True
    assert len(calls) == index.EMBED_ATTEMPTS


def _usage_entries(path):
    import json

    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_bad_key_is_one_fail_line_and_logs_tokens_already_spent(fake_voyage, tmp_path, monkeypatch, capsys):
    errors, _failures, _calls = fake_voyage
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(index, "TEXT_LIMIT_PER_BATCH", 2)

    # First batch (2 texts, 2 tokens) succeeds; the key is revoked before the second.
    class FailingSecondBatch:
        def __init__(self, **_kwargs):
            self.n = 0

        def embed(self, texts, **_kwargs):
            self.n += 1
            if self.n == 2:
                raise errors.AuthenticationError("Provided API key is invalid.\nSee docs.")
            return SimpleNamespace(embeddings=[[0.0] * index.EMBED_DIM for _ in texts], total_tokens=len(texts))

    monkeypatch.setattr(sys.modules["voyageai"], "Client", FailingSecondBatch)

    assert index.embed_or_fail(["a", "b", "c"], "voyage-code-3", "pa-test") is None

    err_lines = [l for l in capsys.readouterr().err.splitlines() if l.strip()]
    assert len(err_lines) == 1
    assert err_lines[0].startswith(index.FAIL)
    assert "AuthenticationError: Provided API key is invalid. See docs." in err_lines[0]
    assert "VOYAGE_API_KEY" in err_lines[0]
    entries = _usage_entries(tmp_path / index.USAGE_LOG_NAME)
    assert [e["tokens"] for e in entries] == [2]
    assert entries[0]["skill"] == "dayz-search-index"


def test_failure_before_any_tokens_writes_no_usage_entry(fake_voyage, tmp_path, monkeypatch, capsys):
    errors, failures, _calls = fake_voyage
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    failures.append(errors.AuthenticationError("bad key"))
    assert index.embed_or_fail(["a"], "voyage-code-3", "pa-test") is None
    assert "No tokens were used" in capsys.readouterr().err
    assert _usage_entries(tmp_path / index.USAGE_LOG_NAME) == []


def test_transient_failure_after_retries_names_attempts(fake_voyage, tmp_path, monkeypatch, capsys):
    errors, failures, _calls = fake_voyage
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    failures += [errors.Timeout("slow")] * index.EMBED_ATTEMPTS
    assert index.embed_or_fail(["a"], "voyage-code-3", "pa-test") is None
    err = capsys.readouterr().err
    assert f"after {index.EMBED_ATTEMPTS} attempts" in err
    assert "Timeout: slow" in err


def test_embed_or_fail_returns_vectors_on_success(fake_voyage):
    vectors, tokens = index.embed_or_fail(["a", "b"], "voyage-code-3", "pa-test")
    assert len(vectors) == 2 and tokens == 2


# --------------- API key ---------------


def test_missing_key_exits_1_with_fail_line(monkeypatch, capsys):
    monkeypatch.setattr(index.voyage_common, "dotenv_paths", lambda: [])
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        index._load_env_and_key()
    assert exc.value.code == 1
    assert "VOYAGE_API_KEY not set" in capsys.readouterr().err


def _stub_build(tmp_path, monkeypatch, db=None):
    """Run main() against a one-file fake P drive with the embed stubbed and LanceDB
    replaced by db (a _FakeDb, empty by default). Returns the index root."""
    p_root = tmp_path / "P"
    (p_root / "scripts").mkdir(parents=True)
    _write(p_root / "scripts", "a.c", "class A { int x; };\n")
    idx = tmp_path / "idx"
    db = _FakeDb() if db is None else db
    monkeypatch.setattr(index, "P_ROOT", p_root)
    monkeypatch.setattr(index, "INDEX_ROOT", idx)
    monkeypatch.setattr(index.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr(index.h.preflight, "find_vanilla_data", lambda: None)
    monkeypatch.setattr(index, "_require_deps", lambda: None)
    monkeypatch.setattr(index, "_load_env_and_key", lambda: "pa-test-key-1234")
    monkeypatch.setitem(sys.modules, "lancedb", SimpleNamespace(connect=lambda _p: db))
    monkeypatch.setitem(sys.modules, "tqdm", SimpleNamespace(tqdm=lambda it=None, **_k: it))
    monkeypatch.setattr(index, "embed_or_fail", lambda texts, model, key, *_a: ([[0.0]] * len(texts), 1234))
    return idx


def _old_index(idx: Path) -> tuple[_FakeDb, dict[str, str]]:
    """An existing voyage-code-3 index: a one-row table plus its three sidecar files."""
    idx.mkdir()
    files = {
        "file_hashes.json": json.dumps({"P:\\old.c": "abc"}),
        "config.json": json.dumps({"embed_model": "voyage-code-3", "embed_provider": "voyage"}),
        "manifest.json": json.dumps({"embed_model": "voyage-code-3", "total_chunks": 1}),
    }
    for name, body in files.items():
        (idx / name).write_text(body, encoding="utf-8")
    return _FakeDb({index.TABLE_NAME: [{"content": "old", "vector": [1.0]}]}), files


def _fail_replace_of(monkeypatch, target: str) -> None:
    real_replace = index.os.replace

    def replace(src, dst):
        if Path(dst).name == target:
            raise PermissionError(f"{target} locked")
        return real_replace(src, dst)

    monkeypatch.setattr(index.os, "replace", replace)


def test_config_write_failure_after_model_change_keeps_old_table_and_config(tmp_path, monkeypatch, capsys):
    """A new-model table must never go live next to the old config.json: queries would use the wrong model."""
    db, old_files = _old_index(tmp_path / "idx")
    idx = _stub_build(tmp_path, monkeypatch, db)
    monkeypatch.setenv("VOYAGE_MODEL", "voyage-3.5")
    _fail_replace_of(monkeypatch, "config.json")

    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "PermissionError: config.json locked" in fails[0]
    assert "previous index is unchanged" in fails[0]
    assert db.tables[index.TABLE_NAME].rows == [{"content": "old", "vector": [1.0]}]
    # file_hashes.json was replaced before config.json failed; it is back to the old one too.
    assert {name: (idx / name).read_text(encoding="utf-8") for name in old_files} == old_files
    assert not list(idx.glob("*.tmp"))
    assert [e["tokens"] for e in _usage_entries(idx / index.USAGE_LOG_NAME)] == [1234]


def test_manifest_replace_failure_on_first_build_leaves_no_index(tmp_path, monkeypatch, capsys):
    idx = _stub_build(tmp_path, monkeypatch)
    db = sys.modules["lancedb"].connect("")
    _fail_replace_of(monkeypatch, "manifest.json")
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    assert db.tables == {}
    assert sorted(p.name for p in idx.iterdir()) == [index.USAGE_LOG_NAME]


def test_failed_rollback_says_the_index_may_be_inconsistent(tmp_path, monkeypatch, capsys):
    db, _files = _old_index(tmp_path / "idx")
    _stub_build(tmp_path, monkeypatch, db)
    _fail_replace_of(monkeypatch, "manifest.json")

    def broken_rollback(_db, _previous):
        raise OSError("lancedb gone")

    monkeypatch.setattr(index, "rollback_table", broken_rollback)
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1
    assert "PermissionError: manifest.json locked" in fails[0] and "OSError: lancedb gone" in fails[0]
    assert "may be inconsistent" in fails[0] and "unchanged" not in fails[0]


def test_full_build_replaces_table_and_all_sidecars(tmp_path, monkeypatch):
    db, old_files = _old_index(tmp_path / "idx")
    idx = _stub_build(tmp_path, monkeypatch, db)
    monkeypatch.setenv("VOYAGE_MODEL", "voyage-3.5")
    assert index.main(["--full", "--ignore-tier-warning"]) == 0
    assert [r["content"] for r in db.tables[index.TABLE_NAME].rows] == ["class A { int x; }"]
    assert json.loads((idx / "config.json").read_text(encoding="utf-8"))["embed_model"] == "voyage-3.5"
    manifest = json.loads((idx / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["embed_model"] == "voyage-3.5" and manifest["total_chunks"] == 1
    assert list(json.loads((idx / "file_hashes.json").read_text(encoding="utf-8"))) == [
        str(tmp_path / "P" / "scripts" / "a.c")
    ]
    assert not list(idx.glob("*.tmp"))


def _fail_lines(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith(index.FAIL)]


def test_table_write_failure_is_one_fail_line_and_keeps_usage(tmp_path, monkeypatch, capsys):
    """Tokens are billed once the embed returns, so a LanceDB failure after it must not lose them."""
    idx = _stub_build(tmp_path, monkeypatch)

    def broken_write(_db, _rows):
        raise OSError("disk full")

    monkeypatch.setattr(index, "write_table", broken_write)
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "OSError: disk full" in fails[0]
    assert [e["tokens"] for e in _usage_entries(idx / index.USAGE_LOG_NAME)] == [1234]
    assert not (idx / "manifest.json").exists()


def test_manifest_write_failure_is_one_fail_line(tmp_path, monkeypatch, capsys):
    db, old_files = _old_index(tmp_path / "idx")
    idx = _stub_build(tmp_path, monkeypatch, db)
    real_write_text = Path.write_text

    def write_text(self, *args, **kwargs):
        if self.name.startswith("manifest.json"):
            raise PermissionError("manifest locked")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", write_text)
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "PermissionError: manifest locked" in fails[0]
    # The sidecars are written before the swap, so a full disk never reaches the live table.
    assert ("create", index.TABLE_NAME, "overwrite") not in db.log
    assert db.tables[index.TABLE_NAME].rows == [{"content": "old", "vector": [1.0]}]
    assert {name: (idx / name).read_text(encoding="utf-8") for name in old_files} == old_files
    assert not list(idx.glob("*.tmp"))


def test_full_build_removes_downloaded_release_tag(tmp_path, monkeypatch):
    """A local build replaces the downloaded index, so /dayz-search-download must not see its old tag."""
    idx = _stub_build(tmp_path, monkeypatch)
    idx.mkdir()
    (idx / index.RELEASE_TAG_FILE).write_text("v1.4.0\n", encoding="utf-8")
    assert index.main(["--full", "--ignore-tier-warning"]) == 0
    assert (idx / "manifest.json").exists()
    assert not (idx / index.RELEASE_TAG_FILE).exists()


def test_failed_build_keeps_release_tag(tmp_path, monkeypatch):
    """The downloaded index is still the one in place when the write fails, so its tag stays."""
    idx = _stub_build(tmp_path, monkeypatch)
    idx.mkdir()
    (idx / index.RELEASE_TAG_FILE).write_text("v1.4.0\n", encoding="utf-8")

    def broken_write(_db, _rows):
        raise OSError("disk full")

    monkeypatch.setattr(index, "write_table", broken_write)
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    assert (idx / index.RELEASE_TAG_FILE).exists()


def test_release_tag_name_matches_download_skill():
    download = (Path(__file__).parent.parent / "dayz-search-download" / "download.py").read_text(encoding="utf-8")
    assert f'INSTALLED_TAG_FILE = "{index.RELEASE_TAG_FILE}"' in download


# --------------- Ctrl+C, vector dimension, checkpoint ---------------

_REAL_EMBED_OR_FAIL = index.embed_or_fail


def _vec(x: float) -> list[float]:
    return [x] * index.EMBED_DIM


def _scripted_client(monkeypatch, on_call):
    """Install a voyageai.Client whose embed(texts) is on_call(call_number, texts)."""

    class Client:
        def __init__(self, **_kwargs):
            self.n = 0

        def embed(self, texts, **_kwargs):
            self.n += 1
            return on_call(self.n, texts)

    monkeypatch.setattr(sys.modules["voyageai"], "Client", Client)


def _ok(texts, dim=None):
    dim = dim or index.EMBED_DIM
    return SimpleNamespace(embeddings=[[float(len(t))] * dim for t in texts], total_tokens=len(texts))


def test_ctrl_c_mid_embed_logs_tokens_already_spent(fake_voyage, tmp_path, monkeypatch, capsys):
    """Tokens billed before Ctrl+C must reach usage.log, or later free-tier checks under-count."""
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(index, "TEXT_LIMIT_PER_BATCH", 2)

    def on_call(n, texts):
        if n == 2:
            raise KeyboardInterrupt
        return _ok(texts)

    _scripted_client(monkeypatch, on_call)
    assert index.embed_or_fail(["a", "b", "c"], "voyage-code-3", "pa-test") is None
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "interrupted (Ctrl+C)" in fails[0]
    assert [e["tokens"] for e in _usage_entries(tmp_path / index.USAGE_LOG_NAME)] == [2]


def test_ctrl_c_during_retry_backoff_is_also_caught(fake_voyage, tmp_path, monkeypatch, capsys):
    errors, failures, _calls = fake_voyage
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    failures.append(errors.RateLimitError("429"))

    def sleep(_s):
        raise KeyboardInterrupt

    monkeypatch.setattr(index.time, "sleep", sleep)
    with pytest.raises(index.EmbedError) as exc:
        index.embed_all(["a"], "voyage-code-3", "pa-test")
    assert exc.value.kind == "interrupted"


def test_wrong_dimension_vectors_stop_before_anything_is_saved(fake_voyage, tmp_path, monkeypatch, capsys):
    """A VOYAGE_MODEL with 512-dim output must not build a table the 1024-dim manifest misdescribes."""
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    _scripted_client(monkeypatch, lambda _n, texts: _ok(texts, dim=512))
    checkpoint = tmp_path / index.CHECKPOINT_NAME
    assert index.embed_or_fail(["a", "b"], "voyage-3-lite", "pa-test", {}, checkpoint) is None
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1
    assert "voyage-3-lite returned 512-dim vectors but the index needs 1024" in fails[0]
    assert "VOYAGE_MODEL" in fails[0]
    assert checkpoint.read_bytes() == b""  # nothing of the wrong size was kept for reuse
    assert [e["tokens"] for e in _usage_entries(tmp_path / index.USAGE_LOG_NAME)] == [2]


def test_wrong_vector_count_is_a_response_error(fake_voyage, monkeypatch):
    _scripted_client(monkeypatch, lambda _n, _t: SimpleNamespace(embeddings=[_vec(0.0)], total_tokens=2))
    with pytest.raises(index.EmbedError) as exc:
        index.embed_all(["a", "b"], "voyage-code-3", "pa-test")
    assert exc.value.kind == "response" and "got 1 vectors for a batch of 2" in str(exc.value)


def test_wrong_dimension_build_never_touches_the_table(fake_voyage, tmp_path, monkeypatch, capsys):
    db, old_files = _old_index(tmp_path / "idx")
    idx = _stub_build(tmp_path, monkeypatch, db)
    monkeypatch.setitem(sys.modules, "tqdm", SimpleNamespace(tqdm=_FakeBar))
    monkeypatch.setattr(index, "embed_or_fail", _REAL_EMBED_OR_FAIL)
    _scripted_client(monkeypatch, lambda _n, texts: _ok(texts, dim=1536))
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    assert "1536-dim" in _fail_lines(capsys.readouterr().err)[0]
    assert db.log == []
    assert {name: (idx / name).read_text(encoding="utf-8") for name in old_files} == old_files


def test_checkpoint_resumes_a_failed_build_without_re_embedding(fake_voyage, tmp_path, monkeypatch, capsys):
    """A late failure must not make the next --full pay for the finished batches again."""
    errors, _failures, _calls = fake_voyage
    monkeypatch.setattr(index, "TEXT_LIMIT_PER_BATCH", 2)
    checkpoint = tmp_path / index.CHECKPOINT_NAME
    texts = ["a", "bb", "ccc", "dddd", "eeeee"]
    sent: list[list[str]] = []

    def failing_third(n, batch):
        sent.append(batch)
        if n == 3:
            raise errors.AuthenticationError("revoked")
        return _ok(batch)

    _scripted_client(monkeypatch, failing_third)
    with pytest.raises(index.EmbedError):
        index.embed_all(texts, "voyage-code-3", "pa-test", {}, checkpoint)
    assert checkpoint.stat().st_size == 4 * index._RECORD_BYTES

    sent.clear()
    _scripted_client(monkeypatch, lambda _n, batch: (sent.append(batch), _ok(batch))[1])
    saved = index._load_checkpoint(checkpoint)
    vectors, tokens = index.embed_all(texts, "voyage-code-3", "pa-test", saved, checkpoint)
    assert sent == [["eeeee"]] and tokens == 1
    assert [v[0] for v in vectors] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert all(len(v) == index.EMBED_DIM for v in vectors)

    # Another model's vectors are never reused.
    sent.clear()
    index.embed_all(["a"], "voyage-3.5", "pa-test", index._load_checkpoint(checkpoint), None)
    assert sent == [["a"]]


def test_checkpoint_drops_a_half_written_record_and_truncates(tmp_path):
    checkpoint = tmp_path / index.CHECKPOINT_NAME
    whole = index._checkpoint_key("m", "a") + index.array("f", _vec(0.5)).tobytes()
    checkpoint.write_bytes(whole + whole[:100])  # Ctrl+C mid-write
    saved = index._load_checkpoint(checkpoint)
    assert list(saved) == [index._checkpoint_key("m", "a")] and saved[index._checkpoint_key("m", "a")][0] == 0.5
    assert checkpoint.stat().st_size == index._RECORD_BYTES
    assert index._load_checkpoint(tmp_path / "missing.bin") == {}


def test_failed_embed_message_says_the_batches_are_saved(fake_voyage, tmp_path, monkeypatch, capsys):
    errors, _f, _c = fake_voyage
    monkeypatch.setattr(index, "INDEX_ROOT", tmp_path)
    monkeypatch.setattr(index, "TEXT_LIMIT_PER_BATCH", 1)

    def on_call(n, texts):
        if n == 2:
            raise errors.Timeout("slow")
        return _ok(texts)

    _scripted_client(monkeypatch, on_call)
    monkeypatch.setattr(index, "EMBED_ATTEMPTS", 1)
    assert index.embed_or_fail(["a", "b"], "voyage-code-3", "pa-test", {}, tmp_path / index.CHECKPOINT_NAME) is None
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and index.CHECKPOINT_NAME in fails[0] and "embeds only the rest" in fails[0]


def test_build_resumes_from_checkpoint_and_deletes_it_on_success(fake_voyage, tmp_path, monkeypatch, capsys):
    idx = _stub_build(tmp_path, monkeypatch)
    monkeypatch.setitem(sys.modules, "tqdm", SimpleNamespace(tqdm=_FakeBar))
    monkeypatch.setattr(index, "embed_or_fail", _REAL_EMBED_OR_FAIL)
    idx.mkdir()
    text = "class A { int x; }"
    (idx / index.CHECKPOINT_NAME).write_bytes(
        index._checkpoint_key(index.DEFAULT_EMBED_MODEL, text) + index.array("f", _vec(0.25)).tobytes()
    )
    _scripted_client(monkeypatch, lambda _n, _t: pytest.fail("a saved chunk was embedded again"))
    assert index.main(["--full", "--ignore-tier-warning"]) == 0
    assert "Resuming: 1 of 1 chunks" in capsys.readouterr().out
    assert not (idx / index.CHECKPOINT_NAME).exists()
    manifest = json.loads((idx / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["chunks_reused_from_checkpoint"] == 1 and manifest["total_tokens"] == 0


def test_failed_write_keeps_the_checkpoint_and_says_so(fake_voyage, tmp_path, monkeypatch, capsys):
    idx = _stub_build(tmp_path, monkeypatch)
    monkeypatch.setitem(sys.modules, "tqdm", SimpleNamespace(tqdm=_FakeBar))
    monkeypatch.setattr(index, "embed_or_fail", _REAL_EMBED_OR_FAIL)
    _scripted_client(monkeypatch, lambda _n, texts: _ok(texts))

    def broken_write(_db, _rows):
        raise OSError("disk full")

    monkeypatch.setattr(index, "write_table", broken_write)
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "spends no tokens" in fails[0]
    assert (idx / index.CHECKPOINT_NAME).stat().st_size == index._RECORD_BYTES


def test_ctrl_c_during_sidecar_replace_rolls_back(tmp_path, monkeypatch, capsys):
    db, old_files = _old_index(tmp_path / "idx")
    idx = _stub_build(tmp_path, monkeypatch, db)
    real_replace = index.os.replace

    def replace(src, dst):
        if Path(dst).name == "config.json":
            raise KeyboardInterrupt
        return real_replace(src, dst)

    monkeypatch.setattr(index.os, "replace", replace)
    assert index.main(["--full", "--ignore-tier-warning"]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "Interrupted (Ctrl+C) while writing the index" in fails[0]
    assert db.tables[index.TABLE_NAME].rows == [{"content": "old", "vector": [1.0]}]
    assert {name: (idx / name).read_text(encoding="utf-8") for name in old_files} == old_files


@pytest.mark.parametrize("leftover", ["manifest.json", "lancedb/chunks.lance"])
def test_existing_index_is_refused_before_preflight(tmp_path, monkeypatch, capsys, leftover):
    idx = tmp_path / "idx"
    (idx / leftover).parent.mkdir(parents=True, exist_ok=True)
    if leftover.endswith(".lance"):
        (idx / leftover).mkdir()
    else:
        (idx / leftover).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(index, "INDEX_ROOT", idx)
    monkeypatch.setattr(index.h, "gate_on_preflight", lambda: pytest.fail("preflight ran before the refusal"))
    monkeypatch.setattr(index, "_require_deps", lambda: pytest.fail("deps checked before the refusal"))
    assert index.main([]) == 1
    fails = _fail_lines(capsys.readouterr().err)
    assert len(fails) == 1 and "--full" in fails[0]
