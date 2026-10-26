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


def test_terms_keep_short_dayz_terms():
    # Two-letter terms used to be dropped: "what is the AI" was an ERROR and
    # "how does HP regen" searched for "regen" alone.
    assert ask.search_terms("what is the AI") == ["ai"]
    assert ask.search_terms("how does HP regen") == ["hp", "regen"]
    assert ask.search_terms("how is the ui id set") == ["ui", "id"]
    assert ask.search_terms("what does NV do in an OK way") == ["nv", "ok"]
    # Other two-letter words still go, in capitals too when they are stop words.
    assert ask.search_terms("is it on by me") == []
    assert ask.search_terms("HOW DOES IT WORK") == []


def test_short_term_matches_its_own_word_not_inside_words():
    # Shapes taken from vanilla names in P:\scripts (EntityAI, DayZCreatureAI, zoneHP,
    # HPTypes, FAIL, MAIN_MENU, STANCEIDX_RAISEDERECT, UAInput, LIQUID_THROUGHPUT_WELL).
    for text in ("class EntityAI", "DayZCreatureAI m_Bear", "float zoneHP", "HPTypes t", "ai = 1"):
        assert ask._has_term("ai", text) or ask._has_term("hp", text), text
    for text in ("FAIL", "MAIN_MENU", "STANCEIDX_RAISEDERECT", "UAInput", "void Main()", "contain"):
        assert not ask._has_term("ai", text), text
    assert not ask._has_term("hp", "LIQUID_THROUGHPUT_WELL")
    assert ask._has_term("spoil", "m_SpoilTime")  # long terms stay substring matches
    assert ask._name_holds("ai", "entityai") and ask._name_holds("ui", "uiscriptedmenu")
    assert not ask._name_holds("ai", "mainmenu") and not ask._name_holds("ai", "onfail")


def test_grep_finds_a_short_term(p_drive):
    d = p_drive / "scripts" / "3_game" / "entities"
    d.mkdir(parents=True)
    (d / "entityai.c").write_text("class EntityAI\n{\n\tfloat GetHP() { return 0; }\n};\n", encoding="utf-8")
    (d / "menu.c").write_text("class MainMenu\n{\n\tvoid OnFail() {}\n};\n", encoding="utf-8")
    paths = [Path(c["path"]).name for c in ask.grep_vanilla(["ai"], ["scripts"], None, 5, root=p_drive)]
    assert paths == ["entityai.c"]
    report = ask.ask("how does HP regen", force_grep=True)
    assert report["citations"] and Path(report["citations"][0]["path"]).name == "entityai.c"


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


def test_far_hit_is_dropped_as_off_topic(p_drive, fake_index):
    fake_index.rows = [_row(p_drive / "scripts" / "4_world" / "foodstage.c", 1, 9,
                            SPOIL_C.rstrip("\n").rstrip(";"), distance=ask.RAG_MAX_DISTANCE + 0.01)]
    report = ask.ask("food spoilage", server=fake_index.server)
    assert report["dropped"][0]["reason"].startswith("off topic: distance")
    assert report["mode"] == "rag+grep" and {c["source"] for c in report["citations"]} == {"grep"}


def test_hit_without_a_search_term_is_dropped_as_off_topic(p_drive, fake_index):
    # Close by meaning but about something else, like a cooking class for a spoilage question.
    fake_index.rows = [_row(p_drive / "scripts" / "4_world" / "bleedingsource.c", 1, 7,
                            BLEED_C.rstrip("\n").rstrip(";"), distance=0.7, context="BleedingSource")]
    report = ask.ask("food spoilage", server=fake_index.server)
    assert report["dropped"] == [{"cite": f"{p_drive / 'scripts' / '4_world' / 'bleedingsource.c'}:1-7",
                                  "reason": "off topic: holds no search term from the question"}]
    assert any("off topic" in n for n in report["notes"])
    assert report["citations"][0]["path"].endswith("foodstage.c")


def test_search_term_in_class_context_keeps_the_hit():
    cite = {"distance": ask.RAG_MAX_DISTANCE, "excerpt": "{\n\tint m_X;\n}", "context": "FoodStage"}
    assert ask.off_topic(cite, ["food"]) is None
    assert ask.off_topic({**cite, "distance": None}, ["food"]) is None
    assert ask.off_topic(cite, ["bleed"]) is not None


def _big_config(p_drive, deep_line):
    """A 1,000-line config class whose only search-term line is deep_line (None: no term line)."""
    lines = ["class CfgVehicles", "{", "\tclass BoxCereal: Edible_Base", "\t{",
             '\t\tmodel="\\dz\\gear\\food\\BoxCereal.p3d";']  # "food" only in a model path
    lines += [f"\t\tvarFiller{i}=1;" for i in range(len(lines) + 1, 1000)]
    if deep_line:
        lines[deep_line - 1] = "\t\tspoilTime=7200;"
    lines.append("};")
    path = p_drive / "dz" / "gear" / "food_config.cpp"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path, "\n".join(lines[:3])


def test_whole_class_hit_is_recited_at_its_deep_term_line(p_drive, fake_index):
    path, head = _big_config(p_drive, deep_line=812)
    fake_index.rows = [_row(path, 1, 1000, head, distance=0.9, context="CfgVehicles")]
    report = ask.ask("food spoil time", server=fake_index.server)
    assert report["mode"] == "rag"
    (c,) = report["citations"]
    assert (c["line_start"], c["line_end"]) == (810, 814)
    assert c["within"] == f"{path}:1-1000" and "spoilTime=7200;" in c["excerpt"]
    assert any("re-cited" in n for n in report["notes"])


def test_whole_class_hit_with_term_only_in_an_asset_path_is_dropped(p_drive, fake_index):
    path, head = _big_config(p_drive, deep_line=None)
    fake_index.rows = [_row(path, 1, 1000, head, distance=0.9, context="CfgVehicles")]
    report = ask.ask("food spoil time", server=fake_index.server)
    assert report["dropped"] == [{"cite": f"{path}:1-1000",
                                  "reason": "off topic: none of its 1000 lines holds a search term from the question"}]
    assert all(c["source"] == "grep" for c in report["citations"])


def test_far_whole_class_hit_is_dropped_once_whole(p_drive, fake_index):
    # Term lines far apart would give three windows; a far hit must count as one drop.
    path, head = _big_config(p_drive, deep_line=300)
    text = path.read_text(encoding="utf-8").splitlines()
    text[599] = text[899] = "\t\tspoilTime=3600;"
    path.write_text("\n".join(text) + "\n", encoding="utf-8")
    fake_index.rows = [_row(path, 1, 1000, head, distance=ask.RAG_MAX_DISTANCE + 0.05, context="CfgVehicles")]
    report = ask.ask("food spoil time", server=fake_index.server)
    assert report["dropped"] == [{"cite": f"{path}:1-1000",
                                  "reason": f"off topic: distance {ask.RAG_MAX_DISTANCE + 0.05:.3f} "
                                            f"is above {ask.RAG_MAX_DISTANCE}"}]
    assert any(n.startswith("1 hit(s) dropped as off topic") for n in report["notes"])
    assert not any("re-cited" in n for n in report["notes"])


def test_short_hit_is_not_narrowed():
    cite = {"path": "x", "line_start": 1, "line_end": ask.EXCERPT_LINES}
    assert ask.narrow_hit(cite, ["food"]) == [cite]


def test_term_in_quoted_asset_path_is_off_topic():
    cite = {"distance": 0.5, "excerpt": 'model="\\dz\\gear\\food\\BoxCereal.p3d";', "context": "CfgVehicles"}
    assert ask.off_topic(cite, ["food"]) is not None
    assert ask.off_topic({**cite, "excerpt": "class Food_Base"}, ["food"]) is None


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


# Shaped like P:\scripts\5_mission\gui\scriptshuddebug\huddebugwinhorticulture.c, which a
# live "how does food spoilage work" run ranked first: gameplay words in widget names only.
HUD_DEBUG_C = """class HudDebugWinHorticulture : HudDebugWinBase
{
	protected EditBoxWidget m_FoodSpoilEditBox;
	protected EditBoxWidget m_SpoilRemoveEditBox;

	void HudDebugWinHorticulture(Widget widget_root)
	{
		m_FoodSpoilEditBox = EditBoxWidget.Cast(m_WgtRoot.FindAnyWidget("FoodSpoilEBox"));
		m_SpoilRemoveEditBox = EditBoxWidget.Cast(m_WgtRoot.FindAnyWidget("SpoilRemoveEBox"));
	}
};
"""


def _add_hud_debug(p_drive, folder=("5_mission", "gui", "scriptshuddebug")):
    d = p_drive.joinpath("scripts", *folder)
    d.mkdir(parents=True)
    (d / "huddebugwinhorticulture.c").write_text(HUD_DEBUG_C, encoding="utf-8")


def test_grep_ranks_gameplay_class_above_debug_hud(p_drive):
    _add_hud_debug(p_drive)
    report = ask.ask("how does food spoilage work", force_grep=True)
    assert Path(report["citations"][0]["path"]).name == "foodstage.c"


def test_grep_down_weights_debug_and_gui_paths(p_drive, monkeypatch):
    monkeypatch.setattr(ask, "_declared_names", lambda _lines: [])  # path weight alone
    _add_hud_debug(p_drive)
    paths = [c["path"] for c in ask.grep_vanilla(["food", "spoil"], ["scripts"], None, 5, root=p_drive)]
    assert Path(paths[0]).name == "foodstage.c" and "scriptshuddebug" in paths[-1]


def test_grep_boosts_files_declaring_the_terms(p_drive, monkeypatch):
    monkeypatch.setattr(ask, "DEBUG_GUI_WEIGHT", 1.0)  # name boost alone
    _add_hud_debug(p_drive, folder=("4_world", "plants"))
    paths = [c["path"] for c in ask.grep_vanilla(["food", "spoil"], ["scripts"], None, 5, root=p_drive)]
    assert Path(paths[0]).name == "foodstage.c"


def test_declared_names_and_debug_gui_paths(p_drive):
    assert ask._declared_names(SPOIL_C.splitlines()) == ["foodstage", "updatespoilage"]
    assert ask._declared_names(["\treturn Foo(x);", "\tm_A = Bar(1);", "\toverride void ProcessDecay(float d)"]) == [
        "processdecay"]
    is_dg = ask._is_debug_or_gui
    assert is_dg(p_drive / "scripts" / "5_mission" / "gui" / "scriptshuddebug" / "x.c", p_drive)
    assert is_dg(p_drive / "scripts" / "1_core" / "debug" / "x.c", p_drive)
    assert not is_dg(p_drive / "scripts" / "4_world" / "classes" / "foodstage" / "foodstage.c", p_drive)
    assert not is_dg(p_drive / "gui" / "layouts" / "x.layout", p_drive)  # --folder gui is not penalized


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


def test_cli_excerpt_lines_sets_the_excerpt_length_for_that_run_only(p_drive, monkeypatch, capsys):
    monkeypatch.setattr(ask, "EXCERPT_LINES", ask.DEFAULT_EXCERPT_LINES)
    assert ask.main(["--grep", "--excerpt-lines", "2", "food spoilage"]) == 0
    out = capsys.readouterr().out
    assert "    | {" in out and "m_SpoilTime;" not in out
    assert ask.main(["--grep", "food spoilage"]) == 0
    assert "    | \tfloat m_SpoilTime;" in capsys.readouterr().out


def test_cli_none_exits_1(p_drive, capsys):
    assert ask.main(["--grep", "zzqx"]) == 1
    assert capsys.readouterr().out.startswith("NONE")


@pytest.mark.parametrize("argv", [["  "], ["--top-k", "0", "q"], ["--top-k", "99", "q"],
                                  ["--file-type", "bogus", "q"], ["--top-k", "x", "q"], [],
                                  ["--excerpt-lines", "0", "q"], ["--excerpt-lines", "301", "q"]])
def test_cli_bad_arguments(p_drive, argv, capsys):
    assert ask.main(argv) == 2
    assert capsys.readouterr().out.startswith("ERROR")


def test_cli_bad_top_k_is_reported_before_missing_search_terms(p_drive, capsys):
    assert ask.main(["--top-k", "0", "how does it work"]) == 2
    assert capsys.readouterr().out.startswith("ERROR\n  --top-k must be")


def test_cli_short_term_question_is_not_an_error(p_drive, capsys):
    assert ask.main(["--grep", "what is the AI"]) in (0, 1)
    assert not capsys.readouterr().out.startswith("ERROR")


def test_cli_stop_words_only_is_an_error(p_drive, capsys):
    assert ask.main(["--grep", "how does it work"]) == 2
    assert capsys.readouterr().out.startswith("ERROR\n  no search terms")


def test_cli_server_load_failure_is_an_error_not_none(p_drive, monkeypatch, capsys):
    def broken():
        raise ImportError("server.py is broken")

    monkeypatch.setattr(ask, "_load_server", broken)
    assert ask.main(["food spoilage"]) == 2
    assert capsys.readouterr().out.startswith("ERROR\n  ImportError: server.py is broken")


def test_cli_helper_import_failure_is_an_error(p_drive, monkeypatch, capsys):
    monkeypatch.setattr(ask, "IMPORT_ERROR", "ModuleNotFoundError: No module named 'voyage_common'")
    assert ask.main(["--grep", "food"]) == 2
    assert "could not load the script's helpers" in capsys.readouterr().out


def test_cli_needs_p_drive(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(ask, "P_DRIVE", tmp_path / "not-mounted")
    assert ask.main(["food"]) == 2
    assert "/dayz-workdrive" in capsys.readouterr().out
