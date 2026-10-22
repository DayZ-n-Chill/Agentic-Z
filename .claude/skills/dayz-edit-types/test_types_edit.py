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


def _run_main(monkeypatch, argv):
    monkeypatch.setattr(te.h, "gate_on_preflight", lambda: None)
    monkeypatch.setattr("sys.argv", ["types_edit.py", *argv])
    return te.main()


def test_main_no_change_skips_backup_and_write(types_file, monkeypatch):
    before = types_file.read_bytes()
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--nominal", "10"]) == 0
    assert types_file.read_bytes() == before
    assert not types_file.with_suffix(".xml.bak").exists()


def test_main_change_writes_backup_of_original(types_file, monkeypatch):
    before = types_file.read_bytes()
    assert _run_main(monkeypatch, [str(types_file), "AKM", "--remove"]) == 0
    assert types_file.with_suffix(".xml.bak").read_bytes() == before
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
    assert not types_file.with_suffix(".xml.bak").exists()


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
    assert not events.with_suffix(".xml.bak").exists()


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
    assert types_file.with_suffix(".xml.bak").read_bytes() == before
    tree, root = _roundtrip(types_file)
    assert [t.get("name") for t in root.findall("type")] == ["AKM", "MyMod_Vest"]  # AKM replaced in place
    assert _find(root, "AKM").findtext("nominal") == "12"
    assert "<!-- Vanilla weapons -->" in types_file.read_text(encoding="utf-8")


def test_main_merge_same_chunk_twice_changes_nothing(types_file, tmp_path, monkeypatch, capsys):
    chunk = _chunk_file(tmp_path, CHUNK)
    assert _run_main(monkeypatch, [str(types_file), "--merge", chunk]) == 0
    after_first = types_file.read_bytes()
    types_file.with_suffix(".xml.bak").unlink()
    capsys.readouterr()
    assert _run_main(monkeypatch, [str(types_file), "--merge", chunk]) == 0
    assert "already matches" in capsys.readouterr().out
    assert types_file.read_bytes() == after_first
    assert not types_file.with_suffix(".xml.bak").exists()


def test_main_merge_refuses_whole_chunk_when_one_entry_is_bad(types_file, tmp_path, monkeypatch):
    before = types_file.read_bytes()
    bad = CHUNK + _entry("Broken", nominal=1, min_=4) + _entry("MyMod_Vest")
    with pytest.raises(SystemExit) as exc:
        _run_main(monkeypatch, [str(types_file), "--merge", _chunk_file(tmp_path, bad)])
    message = str(exc.value.code)
    assert "Broken: min (4) is greater than nominal (1)" in message
    assert "MyMod_Vest: listed 2 times in the chunk" in message
    assert types_file.read_bytes() == before
    assert not types_file.with_suffix(".xml.bak").exists()


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
    assert not types_file.with_suffix(".xml.bak").exists()


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
