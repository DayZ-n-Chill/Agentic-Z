"""Round-trip tests for types_edit.py (no P:\\ or DayZ install needed)."""
import argparse
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "types_edit", Path(__file__).with_name("types_edit.py")
)
te = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(te)

SAMPLE = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<types>
    <!-- Vanilla weapons -->
    <type name="AKM">
        <nominal>10</nominal>
        <lifetime>14400</lifetime>
        <restock>0</restock>
        <min>5</min>
        <cost>100</cost>
        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>
        <category name="weapons"/>
        <usage name="Military"/>
        <value name="Tier3"/>
    </type>
</types>
"""


def _args(**kw):
    base = dict(nominal=None, min=None, lifetime=None, restock=None, cost=None,
                category=None, usage=None, value=None, tag=None)
    base.update(kw)
    return argparse.Namespace(**base)


@pytest.fixture
def types_file(tmp_path):
    path = tmp_path / "types.xml"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def _roundtrip(path):
    tree = te.parse_types(path)
    return tree, tree.getroot()


def _find(root, name):
    return next((t for t in root.findall("type") if t.get("name") == name), None)


def _backups(path):
    """Every <name>.<stamp>.bak backup beside path."""
    return sorted(path.parent.glob(f"{path.name}.*.bak"))


def test_upsert_new_entry_gets_defaults_and_survives_write(types_file):
    tree, root = _roundtrip(types_file)
    changed, msg = te.upsert(root, "MyMod_Vest", _args(nominal=3, usage=["Police", "Military"]))
    assert changed
    assert msg == 'Added <type name="MyMod_Vest"> nominal=3, min=0, lifetime=14400, cost=100'
    te.write_types(tree, types_file)

    _, root = _roundtrip(types_file)
    vest = _find(root, "MyMod_Vest")
    assert vest.findtext("nominal") == "3"
    assert vest.findtext("restock") == "0"
    assert vest.find("flags").get("count_in_cargo") == "0"
    assert vest.findtext("lifetime") == "14400"
    assert dict(vest.find("flags").attrib) == {
        "count_in_cargo": "0", "count_in_hoarder": "0", "count_in_map": "1",
        "count_in_player": "0", "crafted": "0", "deloot": "0",
    }
    assert sorted(u.get("name") for u in vest.findall("usage")) == ["Military", "Police"]


def test_new_entry_has_quant_tags_and_passes_its_own_merge_check(types_file):
    _, root = _roundtrip(types_file)
    te.upsert(root, "MyMod_Vest", _args(nominal=3))
    vest = _find(root, "MyMod_Vest")
    assert vest.findtext("quantmin") == "-1" and vest.findtext("quantmax") == "-1"
    assert te.validate_type(vest) == ([], [])


def test_update_leaves_quant_tags_alone(types_file):
    _, root = _roundtrip(types_file)
    te.upsert(root, "AKM", _args(nominal=20))
    akm = _find(root, "AKM")
    assert akm.find("quantmin") is None and akm.find("quantmax") is None


def test_new_entry_zero_values_are_not_replaced_by_defaults(types_file):
    _, root = _roundtrip(types_file)
    changed, msg = te.upsert(root, "Zero", _args(nominal=0, cost=0))
    assert changed
    assert "nominal=0" in msg and "cost=0" in msg
    assert _find(root, "Zero").findtext("cost") == "0"


def test_update_existing_only_touches_passed_fields(types_file):
    tree, root = _roundtrip(types_file)
    changed, msg = te.upsert(root, "AKM", _args(nominal=20, value=["Tier4"]))
    assert changed
    assert "nominal 10 -> 20" in msg
    te.write_types(tree, types_file)

    _, root = _roundtrip(types_file)
    akm = _find(root, "AKM")
    assert akm.findtext("nominal") == "20"
    assert akm.findtext("lifetime") == "14400"
    assert [v.get("name") for v in akm.findall("value")] == ["Tier4"]
    assert [u.get("name") for u in akm.findall("usage")] == ["Military"]


def test_update_with_matching_values_reports_no_change(types_file):
    _, root = _roundtrip(types_file)
    changed, msg = te.upsert(root, "AKM", _args(nominal=10, category="weapons"))
    assert not changed
    assert "no change" in msg


def test_remove_existing_and_missing(types_file):
    tree, root = _roundtrip(types_file)
    assert te.remove(root, "AKM")[0] is True
    assert te.remove(root, "AKM")[0] is False
    te.write_types(tree, types_file)
    _, root = _roundtrip(types_file)
    assert _find(root, "AKM") is None


def test_comments_survive_round_trip(types_file):
    tree, root = _roundtrip(types_file)
    te.upsert(root, "AKM", _args(nominal=11))
    te.write_types(tree, types_file)
    assert "<!-- Vanilla weapons -->" in types_file.read_text(encoding="utf-8")


def test_comments_outside_the_root_survive_round_trip(tmp_path):
    path = tmp_path / "types.xml"
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
        "<!-- MyMod types -->\n<!-- second\n     header line -->\n"
        + SAMPLE.split("?>\n", 1)[1].rstrip("\n")
        + "\n<!-- end of MyMod types -->\n",
        encoding="utf-8",
    )
    tree, root = _roundtrip(path)
    te.upsert(root, "AKM", _args(nominal=11))
    te.write_types(tree, path)
    text = path.read_text(encoding="utf-8")
    assert text.index("<!-- MyMod types -->") < text.index("<!-- second\n     header line -->") < text.index("<types>")
    assert text.index("</types>") < text.index("<!-- end of MyMod types -->")
    assert "<!-- Vanilla weapons -->" in text
    # The written file parses, and a second round trip keeps the comments once.
    tree, root = _roundtrip(path)
    te.write_types(tree, path)
    again = path.read_text(encoding="utf-8")
    assert again == text
    assert again.count("MyMod types") == 2


def test_header_comment_survives_a_bom(tmp_path):
    path = tmp_path / "types.xml"
    path.write_bytes(("﻿<!-- MyMod types -->\n" + SAMPLE.split("?>\n", 1)[1]).encode("utf-8"))
    tree, _ = _roundtrip(path)
    te.write_types(tree, path)
    assert "<!-- MyMod types -->\n<types>" in path.read_text(encoding="utf-8")


def test_unchanged_tree_writes_the_file_back_byte_for_byte(types_file):
    # The original XML declaration is kept, not replaced by ElementTree's own.
    before = types_file.read_bytes()
    tree, _ = _roundtrip(types_file)
    te.write_types(tree, types_file)
    assert types_file.read_bytes() == before


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(te.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr("sys.argv", ["types_edit.py", *argv])
    return te.main()


def test_main_no_change_skips_backup_and_write(types_file, monkeypatch):
    before = types_file.read_bytes()
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--nominal", "10"]) == 0
    assert types_file.read_bytes() == before
    assert not _backups(types_file)


def test_main_change_writes_backup_of_original(types_file, monkeypatch):
    before = types_file.read_bytes()
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--remove"]) == 0
    assert [b.read_bytes() for b in _backups(types_file)] == [before]
    ET.parse(types_file)  # still valid XML
    assert "AKM" not in types_file.read_text(encoding="utf-8")


def test_main_remove_ignores_field_flags(types_file, monkeypatch):
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--remove", "--nominal", "99"]) == 0
    assert "AKM" not in types_file.read_text(encoding="utf-8")


def test_main_gates_on_shared_preflight(types_file, monkeypatch):
    def fail_gate():
        raise SystemExit(1)

    monkeypatch.setattr(te.h, "gate_on_preflight", fail_gate)
    monkeypatch.setattr("sys.argv", ["types_edit.py", str(types_file), "AKM", "--nominal", "3"])
    before = types_file.read_bytes()
    with pytest.raises(SystemExit):
        te.main()
    assert types_file.read_bytes() == before


@pytest.mark.parametrize("flag", ["--nominal", "--min", "--lifetime", "--restock", "--cost"])
def test_main_rejects_negative_numbers(types_file, monkeypatch, flag):
    before = types_file.read_bytes()
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), "AKM", flag, "-1"])
    assert exc.value.code == 2  # argparse usage error
    assert types_file.read_bytes() == before


@pytest.mark.parametrize("argv", [
    ["AKM", "--min", "11"],                      # existing nominal is 10
    ["AKM", "--nominal", "4"],                   # existing min is 5
    ["NewItem", "--min", "3", "--nominal", "2"],
    ["NewItem", "--min", "2"],                   # default nominal is 1
])
def test_main_rejects_min_above_nominal(types_file, monkeypatch, argv):
    before = types_file.read_bytes()
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), *argv])
    assert "greater than nominal" in str(exc.value.code)
    assert types_file.read_bytes() == before
    assert not _backups(types_file)


def test_main_accepts_min_equal_to_nominal(types_file, monkeypatch):
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--min", "10"]) == 0
    assert _find(_roundtrip(types_file)[1], "AKM").findtext("min") == "10"


def test_main_refuses_file_without_types_root(tmp_path, monkeypatch):
    events = tmp_path / "events.xml"
    events.write_text('<?xml version="1.0"?>\n<events>\n    <event name="x"/>\n</events>\n', encoding="utf-8")
    before = events.read_bytes()
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(events), "AKM", "--nominal", "3"])
    assert "root element <events>, not <types>" in str(exc.value.code)
    assert events.read_bytes() == before
    assert not _backups(events)


def _with_duplicate(types_file, name):
    text = types_file.read_text(encoding="utf-8")
    types_file.write_text(text.replace("</types>", f'    <type name="{name}"><nominal>1</nominal></type>\n</types>'),
                          encoding="utf-8")


def test_main_refuses_to_edit_a_duplicated_entry(types_file, monkeypatch):
    _with_duplicate(types_file, "AKM")
    before = types_file.read_bytes()
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), "AKM", "--nominal", "3"])
    assert 'more than one <type name="AKM">' in str(exc.value.code)
    assert types_file.read_bytes() == before


def test_main_warns_on_other_duplicates_and_still_edits(types_file, monkeypatch, capsys):
    _with_duplicate(types_file, "Apple")
    _with_duplicate(types_file, "Apple")
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--nominal", "12"]) == 0
    assert "lists these types more than once: Apple" in capsys.readouterr().out
    assert _find(_roundtrip(types_file)[1], "AKM").findtext("nominal") == "12"


# --- --merge: a pasted chunk of many <type> blocks ----------------------------------

def _entry(name, nominal=5, min_=2, extra=""):
    return (f'<type name="{name}"><nominal>{nominal}</nominal><lifetime>7200</lifetime><restock>0</restock>'
            f'<min>{min_}</min><quantmin>-1</quantmin><quantmax>-1</quantmax><cost>100</cost>'
            f'<flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>'
            f'<category name="clothes"/><usage name="Military"/>{extra}</type>')


CHUNK = _entry("MyMod_Vest") + "\n" + _entry("AKM", nominal=12, min_=6)


def _chunk_file(tmp_path, text):
    path = tmp_path / "chunk.xml"
    path.write_text(text, encoding="utf-8")
    return str(path)


@pytest.mark.parametrize("wrap", [
    lambda c: c,
    lambda c: f"<types>\n{c}\n</types>",
    lambda c: f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n<types>{c}</types>',
])
def test_parse_chunk_accepts_bare_blocks_or_a_whole_file(wrap):
    assert [t.get("name") for t in te.parse_chunk(wrap(CHUNK))] == ["MyMod_Vest", "AKM"]


def test_parse_chunk_refuses_other_elements():
    with pytest.raises(ET.ParseError):
        te.parse_chunk('<event name="x"/>')


def test_vanilla_shaped_entry_is_clean():
    assert te.validate_type(te.parse_chunk(_entry("X"))[0]) == ([], [])


@pytest.mark.parametrize("entry, problem", [
    ('<type><nominal>1</nominal></type>', "no name attribute"),
    (_entry("X", nominal=1, min_=3), "min (3) is greater than nominal (1)"),
    (_entry("X").replace("<cost>100", "<cost>-5"), "<cost> is negative"),
    (_entry("X").replace("<lifetime>7200", "<lifetime>soon"), "not a whole number"),
    (_entry("X").replace("<quantmin>-1", "<quantmin>150"), "-1 or 0 to 100"),
    (_entry("X").replace("<quantmin>-1</quantmin><quantmax>-1", "<quantmin>80</quantmin><quantmax>20"),
     "quantmin (80) is greater than quantmax (20)"),
    (_entry("X").replace('crafted="0"', 'crafted="yes"'), "flag crafted must be 0 or 1"),
    (_entry("X", extra="<usage/>"), "<usage> has no name"),
])
def test_validate_type_errors(entry, problem):
    errors, _ = te.validate_type(te.parse_chunk(entry)[0])
    assert any(problem in e for e in errors), errors


def test_validate_type_warns_on_missing_and_unknown_children():
    _, warnings = te.validate_type(te.parse_chunk('<type name="X"><nominal>1</nominal><colour>red</colour></type>')[0])
    assert "no <lifetime>" in warnings and "unknown element <colour>" in warnings


def test_main_merge_adds_replaces_and_backs_up_once(types_file, tmp_path, monkeypatch, capsys):
    before = types_file.read_bytes()
    assert _run_main(monkeypatch, [str(types_file), "--merge", _chunk_file(tmp_path, CHUNK)]) == 0
    out = capsys.readouterr().out
    assert "Checked 2 <type> entries" in out
    assert 'Added <type name="MyMod_Vest">' in out
    assert 'Replaced <type name="AKM">: nominal 10 -> 12' in out
    assert [b.read_bytes() for b in _backups(types_file)] == [before]
    tree, root = _roundtrip(types_file)
    assert [t.get("name") for t in root.findall("type")] == ["AKM", "MyMod_Vest"]  # AKM replaced in place
    assert _find(root, "AKM").findtext("nominal") == "12"
    assert "<!-- Vanilla weapons -->" in types_file.read_text(encoding="utf-8")


def test_main_merge_same_chunk_twice_changes_nothing(types_file, tmp_path, monkeypatch, capsys):
    chunk = _chunk_file(tmp_path, CHUNK)
    assert _run_main(monkeypatch, [str(types_file), "--merge", chunk]) == 0
    after_first = types_file.read_bytes()
    [b.unlink() for b in _backups(types_file)]
    capsys.readouterr()
    assert _run_main(monkeypatch, [str(types_file), "--merge", chunk]) == 0
    assert "already matches" in capsys.readouterr().out
    assert types_file.read_bytes() == after_first
    assert not _backups(types_file)


def test_main_merge_refuses_whole_chunk_when_one_entry_is_bad(types_file, tmp_path, monkeypatch):
    before = types_file.read_bytes()
    bad = CHUNK + _entry("Broken", nominal=1, min_=4) + _entry("MyMod_Vest")
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), "--merge", _chunk_file(tmp_path, bad)])
    message = str(exc.value.code)
    assert "Broken: min (4) is greater than nominal (1)" in message
    assert "MyMod_Vest: listed 2 times in the chunk" in message
    assert types_file.read_bytes() == before
    assert not _backups(types_file)


def test_main_merge_reads_stdin_and_dry_run_writes_nothing(types_file, monkeypatch, capsys):
    import io
    before = types_file.read_bytes()
    monkeypatch.setattr("sys.stdin", io.StringIO(CHUNK))
    assert _run_main(monkeypatch, [str(types_file), "--merge", "-", "--dry-run"]) == 0
    assert "Dry run" in capsys.readouterr().out
    assert types_file.read_bytes() == before


def test_main_merge_refuses_unparseable_chunk(types_file, tmp_path, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), "--merge", _chunk_file(tmp_path, "<type name='x'>")])
    assert "Could not parse the chunk" in str(exc.value.code)


@pytest.mark.parametrize("argv", [[], ["AKM", "--merge", "-"], ["--dry-run"]])
def test_main_needs_exactly_one_of_classname_or_merge(types_file, monkeypatch, argv):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), *argv])
    assert exc.value.code == 2


@pytest.mark.parametrize("argv", [["AKM", "--nominal", "12"], ["MyMod_Vest", "--nominal", "2"], ["AKM", "--remove"]])
def test_main_dry_run_reports_upsert_or_remove_and_writes_nothing(types_file, monkeypatch, capsys, argv):
    before = types_file.read_bytes()
    assert _run_main(monkeypatch, [str(types_file), *argv, "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Dry run" in out
    assert any(word in out for word in ("Added", "Updated", "Removed"))
    assert types_file.read_bytes() == before
    assert not _backups(types_file)


def test_main_dry_run_still_refuses_min_above_nominal(types_file, monkeypatch):
    before = types_file.read_bytes()
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), "AKM", "--min", "99", "--dry-run"])
    assert "min (99)" in str(exc.value.code)
    assert types_file.read_bytes() == before


def test_new_entry_children_follow_vanilla_order(types_file):
    _, root = _roundtrip(types_file)
    te.upsert(root, "MyMod_Rifle", _args(category="weapons", usage=["Military"], value=["Tier4"]))
    # Child order of the AKM block in vanilla chernarusplus db/types.xml.
    vanilla = ["nominal", "lifetime", "restock", "min", "quantmin", "quantmax", "cost",
               "flags", "category", "usage", "value"]
    assert [c.tag for c in _find(root, "MyMod_Rifle")] == vanilla


# --- names checked against the mission's cfglimitsdefinition.xml --------------------

FIXTURE_MISSION = Path(__file__).with_name("fixtures") / "mission"


@pytest.fixture
def mission_types(tmp_path):
    """<mission>/db/types.xml with the fixture limits files next to db/."""
    import shutil
    mission = tmp_path / "mission"
    shutil.copytree(FIXTURE_MISSION, mission)
    (mission / "db").mkdir()
    path = mission / "db" / "types.xml"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_load_limits_reads_both_files(mission_types):
    limits = te.load_limits(mission_types)
    assert "Military" in limits["name"]["usage"] and "Tier3" in limits["name"]["value"]
    assert limits["name"]["category"] == {"clothes", "weapons"}
    assert limits["user"]["usage"] == {"TownVillage"} and limits["user"]["value"] == {"Tier12"}


def test_load_limits_skips_with_a_note_when_absent(types_file, capsys):
    assert te.load_limits(types_file) is None
    assert "names not checked" in capsys.readouterr().out


def test_undefined_limit_names_flags_each_unknown_name(mission_types):
    limits = te.load_limits(mission_types)
    el = te.parse_chunk(_entry("X", extra='<usage name="Militar"/><value name="Tier9"/><tag name="roof"/>'
                                          '<usage user="TownVillage"/><value user="Tier99"/>'))[0]
    assert te.undefined_limit_names(el, limits) == [
        'usage name "Militar" is not defined in cfglimitsdefinition.xml',
        'value name "Tier9" is not defined in cfglimitsdefinition.xml',
        'tag name "roof" is not defined in cfglimitsdefinition.xml',
        'value user "Tier99" is not defined in cfglimitsdefinitionuser.xml',
    ]


def test_main_upsert_warns_on_undefined_usage_and_still_writes(mission_types, monkeypatch, capsys):
    assert _run_main(monkeypatch, [str(mission_types), "AKM", "--usage", "Militar", "--category", "weapon"]) == 0
    out = capsys.readouterr().out
    assert f"{te.WARN} " + 'usage name "Militar" is not defined in cfglimitsdefinition.xml' in out
    assert f"{te.WARN} " + 'category name "weapon" is not defined in cfglimitsdefinition.xml' in out
    assert 'name="Militar"' in mission_types.read_text(encoding="utf-8")


def test_main_upsert_with_known_names_has_no_limits_warning(mission_types, monkeypatch, capsys):
    assert _run_main(monkeypatch, [str(mission_types), "AKM", "--usage", "Police", "--value", "Tier2"]) == 0
    assert "not defined in" not in capsys.readouterr().out


def test_main_merge_warns_on_undefined_names(mission_types, tmp_path, monkeypatch, capsys):
    chunk = _entry("MyMod_Vest", extra='<value name="Tier7"/>')
    assert _run_main(monkeypatch, [str(mission_types), "--merge", _chunk_file(tmp_path, chunk)]) == 0
    out = capsys.readouterr().out
    assert f"{te.WARN} " + 'MyMod_Vest: value name "Tier7" is not defined in cfglimitsdefinition.xml' in out
    assert 'Added <type name="MyMod_Vest">' in out


def test_main_skips_the_limits_check_outside_a_mission(types_file, monkeypatch, capsys):
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--usage", "Militar"]) == 0
    out = capsys.readouterr().out
    assert "names not checked" in out and "not defined in" not in out


def test_new_and_updated_entries_put_tag_between_category_and_usage(types_file):
    _, root = _roundtrip(types_file)
    te.upsert(root, "MyMod_Crate", _args(category="tools", usage=["Industrial"], value=["Tier1"], tag=["shelves"]))
    named = [c.tag for c in _find(root, "MyMod_Crate") if c.tag in te.NAMED_CHILDREN]
    assert named == ["category", "tag", "usage", "value"]
    te.upsert(root, "AKM", _args(tag=["floor"]))
    named = [c.tag for c in _find(root, "AKM") if c.tag in te.NAMED_CHILDREN]
    assert named == ["category", "tag", "usage", "value"]


def test_user_groups_not_checked_without_the_user_file(mission_types):
    (mission_types.parent.parent / te.LIMITS_USER_FILE).unlink()
    limits = te.load_limits(mission_types)
    assert "user" not in limits
    el = te.ET.fromstring('<type name="X"><usage user="AnyGroup"/><usage name="Militar"/></type>')
    problems = te.undefined_limit_names(el, limits)
    assert problems == ['usage name "Militar" is not defined in cfglimitsdefinition.xml']


# Three blocks copied verbatim from vanilla P:\DZ\worlds\chernarusplus\ce\db\types.xml
# (declaration at line 1, AK74_WoodBttstck at line 112, AKM at 124, AKM_Gold at 137):
# 4-space indent, LF line endings, and self-closing tags with no space before "/>".
VANILLA = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<types>
    <type name="AK74_WoodBttstck">
        <nominal>5</nominal>
        <lifetime>14400</lifetime>
        <restock>0</restock>
        <min>2</min>
        <quantmin>-1</quantmin>
        <quantmax>-1</quantmax>
        <cost>100</cost>
        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>
        <category name="weapons"/>
        <usage name="Military"/>
    </type>
    <type name="AKM">
        <nominal>3</nominal>
        <lifetime>7200</lifetime>
        <restock>3600</restock>
        <min>2</min>
        <quantmin>30</quantmin>
        <quantmax>80</quantmax>
        <cost>100</cost>
        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>
        <category name="weapons"/>
        <usage name="Military"/>
        <value name="Tier4"/>
    </type>
    <type name="AKM_Gold">
        <nominal>0</nominal>
        <lifetime>14400</lifetime>
        <restock>2700</restock>
        <min>0</min>
        <quantmin>-1</quantmin>
        <quantmax>-1</quantmax>
        <cost>100</cost>
        <flags count_in_cargo="0" count_in_hoarder="0" count_in_map="1" count_in_player="0" crafted="0" deloot="0"/>
        <category name="weapons"/>
        <usage name="Military"/>
        <value name="Unique"/>
    </type>
</types>
"""


@pytest.fixture
def vanilla_file(tmp_path):
    path = tmp_path / "types.xml"
    path.write_bytes(VANILLA.encode("utf-8"))
    return path


def _block_lines(text: str, name: str):
    """The lines of the <type name=name> block in text."""
    lines = text.splitlines()
    start = lines.index(f'    <type name="{name}">')
    return lines[start:lines.index("    </type>", start) + 1]


def _changed_lines(before: str, after: str):
    """(removed, added) lines of a line diff."""
    import difflib
    diff = list(difflib.ndiff(before.splitlines(), after.splitlines()))
    return ([l[2:] for l in diff if l.startswith("- ")], [l[2:] for l in diff if l.startswith("+ ")])


def test_one_field_edit_of_a_vanilla_file_changes_only_that_line(vanilla_file, monkeypatch):
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--nominal", "12"]) == 0
    after = vanilla_file.read_text(encoding="utf-8")
    assert _changed_lines(VANILLA, after) == (["        <nominal>3</nominal>"], ["        <nominal>12</nominal>"])
    assert after == VANILLA.replace("<nominal>3</nominal>", "<nominal>12</nominal>")


def test_list_edit_of_a_vanilla_file_changes_only_that_block(vanilla_file, monkeypatch):
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--usage", "Police"]) == 0
    removed, added = _changed_lines(VANILLA, vanilla_file.read_text(encoding="utf-8"))
    assert removed == ['        <usage name="Military"/>'] and added == ['        <usage name="Police"/>']
    # The other blocks still hold their own <usage name="Military"/>.
    assert vanilla_file.read_text(encoding="utf-8").count('<usage name="Military"/>') == 2


def test_remove_from_a_vanilla_file_drops_only_that_blocks_lines(vanilla_file, monkeypatch):
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--remove"]) == 0
    akm = "\n".join(_block_lines(VANILLA, "AKM")) + "\n"
    assert vanilla_file.read_text(encoding="utf-8") == VANILLA.replace(akm, "", 1)


def test_new_entry_in_a_vanilla_file_adds_only_its_lines_in_vanilla_style(vanilla_file, monkeypatch):
    assert _run_main(monkeypatch, [str(vanilla_file), "MyMod_Vest", "--category", "clothes"]) == 0
    after = vanilla_file.read_text(encoding="utf-8")
    removed, added = _changed_lines(VANILLA, after)
    assert removed == []
    assert added[0] == '    <type name="MyMod_Vest">' and added[-1] == "    </type>"
    assert '        <category name="clothes"/>' in added
    assert not any(" />" in line for line in added)
    assert after.endswith("    </type>\n</types>\n")
    assert _find(ET.parse(vanilla_file).getroot(), "MyMod_Vest") is not None


def test_merge_into_a_vanilla_file_changes_only_the_replaced_and_added_blocks(vanilla_file, tmp_path, monkeypatch):
    chunk = _entry("AKM", nominal=12, min_=6) + "\n" + _entry("MyMod_Vest")
    assert _run_main(monkeypatch, [str(vanilla_file), "--merge", _chunk_file(tmp_path, chunk)]) == 0
    after = vanilla_file.read_text(encoding="utf-8")
    # The declaration and the untouched blocks are line for line the same, and
    # every removed line comes from the replaced AKM block.
    assert after.startswith(VANILLA.split('    <type name="AKM">')[0])
    assert _block_lines(after, "AKM_Gold") == _block_lines(VANILLA, "AKM_Gold")
    removed, _ = _changed_lines(VANILLA, after)
    assert removed and set(removed) <= set(_block_lines(VANILLA, "AKM"))
    root = ET.parse(vanilla_file).getroot()
    assert [t.get("name") for t in root.findall("type")] == ["AK74_WoodBttstck", "AKM", "AKM_Gold", "MyMod_Vest"]
    assert _find(root, "AKM").findtext("nominal") == "12"
    assert " />" not in after


def test_crlf_file_keeps_crlf_and_its_other_lines(tmp_path, monkeypatch):
    path = tmp_path / "types.xml"
    original = VANILLA.replace("\n", "\r\n").encode("utf-8")
    path.write_bytes(original)
    assert _run_main(monkeypatch, [str(path), "AKM", "--nominal", "12"]) == 0
    assert path.read_bytes() == original.replace(b"<nominal>3</nominal>", b"<nominal>12</nominal>")


def test_commented_out_block_is_left_alone(tmp_path, monkeypatch):
    path = tmp_path / "types.xml"
    text = VANILLA.replace("<types>\n", '<types>\n    <!-- <type name="Old"><nominal>1</nominal></type> -->\n')
    path.write_text(text, encoding="utf-8")
    assert _run_main(monkeypatch, [str(path), "AKM", "--nominal", "12"]) == 0
    assert path.read_text(encoding="utf-8") == text.replace("<nominal>3</nominal>", "<nominal>12</nominal>")


def test_empty_self_closing_root_is_written_whole_with_its_declaration(tmp_path, monkeypatch):
    path = tmp_path / "types.xml"
    path.write_text('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<types/>\n', encoding="utf-8")
    assert _run_main(monkeypatch, [str(path), "MyMod_Vest"]) == 0
    text = path.read_text(encoding="utf-8")
    assert text.startswith('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<types>\n    <type name="MyMod_Vest">')
    assert " />" not in text
    assert _find(ET.parse(path).getroot(), "MyMod_Vest") is not None


def test_empty_root_with_close_tag_gets_the_new_block_inside(tmp_path, monkeypatch):
    path = tmp_path / "types.xml"
    path.write_text('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<types>\n</types>\n', encoding="utf-8")
    assert _run_main(monkeypatch, [str(path), "MyMod_Vest"]) == 0
    text = path.read_text(encoding="utf-8")
    assert text.startswith('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<types>\n    <type name="MyMod_Vest">\n        <nominal>1</nominal>')
    assert text.endswith("    </type>\n</types>\n")


def test_each_changing_run_keeps_its_own_backup(vanilla_file, monkeypatch):
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--nominal", "12"]) == 0
    first = vanilla_file.read_bytes()
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--nominal", "13"]) == 0
    backups = _backups(vanilla_file)
    assert sorted(b.read_bytes() for b in backups) == sorted([VANILLA.encode("utf-8"), first])
    assert all(b.name.startswith("types.xml.") and b.suffix == ".bak" for b in backups)


# --- --quantmin / --quantmax and the "set, not add" list flags --------------
# Vanilla AKM (P:\DZ\worlds\chernarusplus\ce\db\types.xml:129-130) has
# quantmin 30, quantmax 80; every vanilla value is -1 or 0 to 100.

def test_quant_flags_edit_a_vanilla_entry_in_one_line(vanilla_file, monkeypatch, capsys):
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--quantmax", "90"]) == 0
    assert "quantmax 80 -> 90" in capsys.readouterr().out
    after = vanilla_file.read_text(encoding="utf-8")
    assert _changed_lines(VANILLA, after) == (["        <quantmax>80</quantmax>"], ["        <quantmax>90</quantmax>"])


def test_quant_flags_add_missing_tags_in_vanilla_order(types_file, monkeypatch):
    # SAMPLE's AKM has no quant tags; they go after <min>, before <cost>.
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--quantmin", "30", "--quantmax", "80"]) == 0
    akm = _find(_roundtrip(types_file)[1], "AKM")
    assert [c.tag for c in akm][:7] == ["nominal", "lifetime", "restock", "min", "quantmin", "quantmax", "cost"]
    assert akm.findtext("quantmin") == "30" and akm.findtext("quantmax") == "80"


def test_new_entry_takes_quant_flags_and_passes_its_own_merge_check(types_file, monkeypatch):
    assert _run_main(monkeypatch, [str(types_file), "Mag_New", "--quantmin", "20", "--quantmax", "100"]) == 0
    mag = _find(_roundtrip(types_file)[1], "Mag_New")
    assert mag.findtext("quantmin") == "20" and mag.findtext("quantmax") == "100"
    assert te.validate_type(mag)[0] == []


@pytest.mark.parametrize("argv", [
    ["--quantmin", "101"], ["--quantmax", "150"], ["--quantmin", "-2"], ["--quantmax", "x"],
])
def test_main_rejects_quant_values_outside_minus_one_or_0_to_100(vanilla_file, monkeypatch, argv):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(vanilla_file), "AKM", *argv])
    assert exc.value.code == 2  # argparse usage error, same range as the merge check
    assert vanilla_file.read_text(encoding="utf-8") == VANILLA


@pytest.mark.parametrize("argv", [
    ["AKM", "--quantmin", "90"],                          # existing quantmax is 80
    ["AKM", "--quantmax", "20"],                          # existing quantmin is 30
    ["NewMag", "--quantmin", "60", "--quantmax", "50"],
])
def test_main_rejects_quantmin_above_quantmax(vanilla_file, monkeypatch, argv):
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(vanilla_file), *argv])
    assert "greater than quantmax" in str(exc.value.code)
    assert vanilla_file.read_text(encoding="utf-8") == VANILLA
    assert not _backups(vanilla_file)


def test_main_accepts_minus_one_beside_a_set_quant(vanilla_file, monkeypatch):
    # -1 means "not a quantity item" and is never compared.
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--quantmin", "-1"]) == 0
    assert _find(_roundtrip(vanilla_file)[1], "AKM").findtext("quantmin") == "-1"


def test_usage_change_line_names_the_removed_usages(vanilla_file, monkeypatch, capsys):
    assert _run_main(monkeypatch, [str(vanilla_file), "AKM", "--usage", "Police"]) == 0
    assert "usage [Military] -> [Police] (removed Military)" in capsys.readouterr().out


def test_list_change_line_has_no_removed_note_when_nothing_is_dropped(vanilla_file, monkeypatch, capsys):
    argv = [str(vanilla_file), "AKM", "--usage", "Military", "--usage", "Police", "--value", "Tier3", "--value", "Tier4"]
    assert _run_main(monkeypatch, argv) == 0
    out = capsys.readouterr().out
    assert "usage [Military] -> [Military, Police]," in out
    assert "value [Tier4] -> [Tier3, Tier4]" in out
    assert "removed" not in out


def test_tag_change_line_names_the_removed_tags(types_file):
    _, root = _roundtrip(types_file)
    te.upsert(root, "AKM", _args(tag=["floor", "shelves"]))
    changed, msg = te.upsert(root, "AKM", _args(tag=["floor"]))
    assert changed and msg.endswith("tag [floor, shelves] -> [floor] (removed shelves)")
