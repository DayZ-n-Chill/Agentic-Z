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
    assert msg == 'Added <type name="MyMod_Vest"> nominal=3, min=0, lifetime=3888000, cost=100'
    te.write_types(tree, types_file)

    _, root = _roundtrip(types_file)
    vest = _find(root, "MyMod_Vest")
    assert vest.findtext("nominal") == "3"
    assert vest.findtext("restock") == "0"
    assert vest.find("flags").get("count_in_cargo") == "1"
    assert sorted(u.get("name") for u in vest.findall("usage")) == ["Military", "Police"]


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
