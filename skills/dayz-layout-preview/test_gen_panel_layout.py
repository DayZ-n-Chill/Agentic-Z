"""Tests for gen_panel_layout.py and the files that ship next to it.

Offline: needs only pytest. The generator is loaded by file path so its module
name cannot clash with a script of the same name in another skill.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "_shared" / "ui" / "templates"


def _load():
    spec = importlib.util.spec_from_file_location("dayz_ui_gen_panel_layout", HERE / "gen_panel_layout.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load()


@pytest.mark.parametrize("kind,rows,title,filename", gen.SELFTEST_SPECS, ids=lambda v: str(v))
def test_shipped_example_is_what_the_generator_writes(kind, rows, title, filename):
    # A checkout with autocrlf turns LF into CRLF; the content is what is compared.
    shipped = (TEMPLATES / filename).read_bytes().replace(b"\r\n", b"\n")
    assert shipped == gen.generate_layout(kind, rows, title=title).encode(gen.ENCODING)
    titled = gen.has_title_widget(kind, title)
    assert gen.verify_layout_text(shipped.decode(gen.ENCODING), kind, rows, titled) == []


def test_self_test_passes_in_a_scratch_folder(tmp_path, capsys):
    assert gen.run_selftest(tmp_path) == 0
    assert "SELFTEST PASS" in capsys.readouterr().out
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(spec[3] for spec in gen.SELFTEST_SPECS)


def test_cli_writes_the_contract_names(tmp_path):
    out = tmp_path / "panel.layout"
    assert gen.main(["info", "--rows", "3", "--title", "STATUS", "--out", str(out)]) == 0
    names = gen.NAME_RE.findall(out.read_text(encoding=gen.ENCODING))
    assert names == ["InfoRoot", "InfoPanel", "TitleText", "Label0", "Value0", "Label1", "Value1", "Label2", "Value2"]


def test_hud_has_a_title_widget_only_when_a_title_is_passed():
    assert "TitleText" not in gen.generate_layout("hud", 2)
    titled = gen.generate_layout("hud", 2, title="Fuel")
    assert 'name "TitleText"' in titled
    assert 'text "Fuel"' not in titled  # the title goes into the file comment, the widget stays empty


def test_verify_reports_a_stringtable_key_and_a_duplicate_name():
    text = gen.generate_layout("feed", 2, title="CHAT")
    assert any("#STR_" in e for e in gen.verify_layout_text(text.replace('text ""', 'text "#STR_X"', 1), "feed", 2, True))
    doubled = text.replace('name "FeedLine1"', 'name "FeedLine0"')
    assert any("duplicate name" in e for e in gen.verify_layout_text(doubled, "feed", 2, True))


def test_rows_below_one_are_refused():
    with pytest.raises(ValueError):
        gen.generate_layout("feed", 0)


TEMPLATE_NAMES = ("form_row", "hud_overlay", "modal_panel", "scroll_list")


@pytest.mark.parametrize("name", TEMPLATE_NAMES)
def test_template_braces_balance_and_rect_files_name_its_widgets(name):
    text = (TEMPLATES / f"{name}.layout").read_text(encoding="utf-8")
    assert text.count("{") == text.count("}")
    names = set(gen.NAME_RE.findall(text))
    for res in ("1920", "1280"):
        rects = json.loads((TEMPLATES / f"{name}.rects.{res}.json").read_text(encoding="utf-8"))
        assert rects["layout"] == f"skills/_shared/ui/templates/{name}.layout"
        assert {node["name"] for node in rects["nodes"]} == names


def test_stringtable_defines_every_key_the_templates_use():
    import csv
    import re

    with (TEMPLATES / "stringtable.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["Language", "original", "english", "spanish", "german", "russian", "chinesesimp"]
    keys = {row[0] for row in rows[1:]}
    used = set()
    for name in TEMPLATE_NAMES:
        used |= set(re.findall(r'"#(STR_\w+)"', (TEMPLATES / f"{name}.layout").read_text(encoding="utf-8")))
    assert used and used <= keys
