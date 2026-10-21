"""Tests for ask.py. A fake index (the real dayz-rag server with a stub table and
embedder) and a fake P:\\ folder under tmp_path, so no Voyage key, index or
mounted drive is needed."""
from __future__ import annotations

import importlib.util
import json
from collections import OrderedDict
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_ask_under_test", HERE / "ask.py")
ask = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ask)

SPOIL_C = """class FoodStage
{
	float m_SpoilTime;

	void UpdateSpoilage(float delta)
	{
		m_SpoilTime += delta;
	}
};
"""

BLEED_C = """class BleedingSource
{
	void OnBleedingStart()
	{
		Print("bleeding");
	}
};
"""


@pytest.fixture
def p_drive(tmp_path, monkeypatch):
    root = tmp_path / "P"
    (root / "scripts" / "4_world").mkdir(parents=True)
    (root / "dz" / "gear").mkdir(parents=True)
    (root / "scripts" / "4_world" / "foodstage.c").write_text(SPOIL_C, encoding="utf-8")
    (root / "scripts" / "4_world" / "bleedingsource.c").write_text(BLEED_C, encoding="utf-8")
    (root / "dz" / "gear" / "config.cpp").write_text("class CfgVehicles\n{\n};\n", encoding="utf-8")
    monkeypatch.setattr(ask, "P_DRIVE", root)
    return root


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def where(self, _clause, prefilter=None):
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    def to_list(self):
        return self.rows


class _FakeTable:
    def __init__(self, rows):
        self.rows = rows
        self.searches = 0

    def search(self, _vec):
        self.searches += 1
        return _FakeQuery(list(self.rows))


def _row(path, start, end, content, distance=0.5, context="FoodStage"):
    return {"path": str(path), "file_type": "c", "parent_context": context, "line_start": start,
            "line_end": end, "content": content, "_distance": distance}


@pytest.fixture
def fake_index(tmp_path, monkeypatch):
    """The real dayz-rag server over a stub table. Set .rows on the result to fill it."""
    server = ask._load_server()
    index_root = tmp_path / "index"
    (index_root / "lancedb").mkdir(parents=True)
    table = _FakeTable([])
    monkeypatch.setattr(server, "INDEX_ROOT", index_root)
    monkeypatch.setattr(server, "DEFAULT_MAX_DISTANCE", None)
    monkeypatch.setattr(server, "_search_cache", OrderedDict())
    monkeypatch.setattr(server, "_manifest_stamp", None)
    monkeypatch.setattr(server, "_get_table", lambda: table)
    monkeypatch.setattr(server, "_embed_query", lambda _q: [0.0])
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-test")
    monkeypatch.setattr(ask.voyage_common, "dotenv_paths", lambda: [])  # never read a real .env
    table.server = server
    return table


def _spoil_row(p_drive, start=1, end=9):
    return _row(p_drive / "scripts" / "4_world" / "foodstage.c", start, end, SPOIL_C.rstrip("\n").rstrip(";"))


# --------------- search terms ---------------


def test_terms_drop_stop_words_and_stem():
    assert ask.search_terms("How does vanilla handle food spoilage timing?") == ["handle", "food", "spoil", "timing"]


def test_terms_keep_identifiers_and_dedupe():
    assert ask.search_terms("What calls PlayerBase.OnBleedingStart and PlayerBase?") == [
        "call", "playerbase", "onbleedingstart"]


# --------------- RAG path ---------------


def test_rag_hits_are_verified_against_the_file(p_drive, fake_index):
    fake_index.rows = [_spoil_row(p_drive)]
    report = ask.ask("food spoilage", server=fake_index.server)
    assert report["verdict"] == "EVIDENCE" and report["mode"] == "rag"
    (c,) = report["citations"]
    assert c["status"] == "verified"
    assert c["cite"] == f"{p_drive / 'scripts' / '4_world' / 'foodstage.c'}:1-9"
    assert "m_SpoilTime += delta;" in c["excerpt"]
    assert c["distance"] == 0.5 and c["context"] == "FoodStage"


def test_moved_hit_is_recited_at_its_new_line(p_drive, fake_index):
    path = p_drive / "scripts" / "4_world" / "foodstage.c"
    path.write_text("// header line\n" * 10 + SPOIL_C, encoding="utf-8")
    fake_index.rows = [_spoil_row(p_drive)]
    (c,) = ask.ask("food spoilage", server=fake_index.server)["citations"]
    assert (c["status"], c["line_start"], c["line_end"]) == ("moved", 11, 19)
    assert "--full" in c["reason"]


def test_changed_hit_is_dropped_and_grep_takes_over(p_drive, fake_index):
    fake_index.rows = [_row(p_drive / "scripts" / "4_world" / "foodstage.c", 1, 3, "class Gone\n{\n\tint m_Old;")]
    report = ask.ask("food spoilage", server=fake_index.server)
    assert report["dropped"][0]["reason"] == "cited lines no longer match the index"
    assert report["mode"] == "rag+grep"
    assert {c["source"] for c in report["citations"]} == {"grep"}


def test_hit_off_the_p_drive_is_dropped(p_drive, fake_index, tmp_path):
    elsewhere = tmp_path / "elsewhere.c"
    elsewhere.write_text(SPOIL_C, encoding="utf-8")
    fake_index.rows = [_row(elsewhere, 1, 9, SPOIL_C)]
    report = ask.ask("food spoilage", server=fake_index.server)
    assert report["dropped"] and all(c["source"] == "grep" for c in report["citations"])


def test_repeated_question_uses_the_server_cache(p_drive, fake_index):
    fake_index.rows = [_spoil_row(p_drive)]
    ask.ask("food spoilage", server=fake_index.server)
    ask.ask("food  spoilage", server=fake_index.server)
    assert fake_index.searches == 1


def test_search_error_falls_back_to_grep(p_drive, fake_index, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("Voyage is down")

    monkeypatch.setattr(fake_index.server, "search_dayz_source_impl", boom)
    report = ask.ask("food spoilage", server=fake_index.server)
    assert report["mode"] == "grep"
    assert any("Voyage is down" in n for n in report["notes"])
    assert report["citations"][0]["path"].endswith("foodstage.c")


# --------------- Grep fallback ---------------


def test_no_key_falls_back_to_grep(p_drive, fake_index, monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY")
    report = ask.ask("where does bleeding start", server=fake_index.server)
    assert fake_index.searches == 0
    assert any("VOYAGE_API_KEY not set" in n for n in report["notes"])
    (c,) = report["citations"]
    assert c["source"] == "grep" and c["path"].endswith("bleedingsource.c")
    assert c["match_line"] == 3 and "OnBleedingStart" in c["excerpt"]


def test_no_index_falls_back_to_grep(p_drive, fake_index):
    (fake_index.server.INDEX_ROOT / "lancedb").rmdir()
    report = ask.ask("food spoilage", server=fake_index.server)
    assert report["mode"] == "grep" and fake_index.searches == 0
    assert any("no search index" in n for n in report["notes"])


def test_grep_ranks_the_file_holding_more_terms_first(p_drive):
    cites = ask.grep_vanilla(["spoil", "delta", "bleed"], ["scripts"], None, 5, root=p_drive)
    assert cites[0]["path"].endswith("foodstage.c")
    assert {Path(c["path"]).name for c in cites} == {"foodstage.c", "bleedingsource.c"}


def test_grep_merges_overlapping_windows(p_drive):
    cites = ask.grep_vanilla(["spoil"], ["scripts"], None, 5, root=p_drive)
    assert [(c["line_start"], c["line_end"]) for c in cites] == [(1, 9)]


def test_grep_file_type_and_folder_scope(p_drive):
    assert ask.grep_vanilla(["cfgvehicles"], ["scripts"], None, 5, root=p_drive) == []
    (c,) = ask.grep_vanilla(["cfgvehicles"], ["dz"], "cpp", 5, root=p_drive)
    assert c["path"].endswith("config.cpp")
    assert ask.grep_vanilla(["cfgvehicles"], ["dz"], "c", 5, root=p_drive) == []


def test_nothing_found_is_none(p_drive):
    report = ask.ask("zzqx wobble", force_grep=True)
    assert report["verdict"] == "NONE" and report["citations"] == []


# --------------- CLI ---------------


def test_cli_json(p_drive, capsys):
    assert ask.main(["--grep", "--json", "food", "spoilage"]) == 0
    first, rest = capsys.readouterr().out.split("\n", 1)
    assert first == "EVIDENCE"
    report = json.loads(rest)
    assert report["question"] == "food spoilage" and report["citations"][0]["cite"].endswith(":1-7")


def test_cli_text(p_drive, capsys):
    assert ask.main(["--grep", "food spoilage"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("EVIDENCE 1 citation(s) via grep")
    assert "foodstage.c:1-7  verified" in out and "    | \tfloat m_SpoilTime;" in out


def test_cli_none_exits_1(p_drive, capsys):
    assert ask.main(["--grep", "zzqx"]) == 1
    assert capsys.readouterr().out.startswith("NONE")


@pytest.mark.parametrize("argv", [["  "], ["--top-k", "0", "q"], ["--top-k", "99", "q"]])
def test_cli_bad_arguments(p_drive, argv, capsys):
    assert ask.main(argv) == 2
    assert capsys.readouterr().out.startswith("ERROR")


def test_cli_needs_p_drive(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ask, "P_DRIVE", tmp_path / "not-mounted")
    assert ask.main(["food"]) == 2
    assert "/dayz-workdrive" in capsys.readouterr().out
