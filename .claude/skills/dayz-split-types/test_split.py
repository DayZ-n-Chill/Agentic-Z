"""Fixture test: split a small types.xml with the vendored splitter."""
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("split", Path(__file__).with_name("split.py"))
split = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(split)

TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<types>
    <type name="Ammo_762x39"><nominal>10</nominal><category name="weapons"/></type>
    <type name="AKM"><nominal>5</nominal><category name="weapons"/></type>
    <type name="Apple"><nominal>20</nominal><category name="food"/></type>
    <type name="MysteryThing"><nominal>1</nominal></type>
</types>
"""

CFGECONOMYCORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<economycore>
    <classes>
        <rootclass name="DefaultWeapon"/>
    </classes>
    <defaults>
        <default name="dyn_radius" value="40"/>
    </defaults>
</economycore>
"""


@pytest.fixture
def mission(tmp_path, monkeypatch):
    db = tmp_path / "db"
    db.mkdir()
    (db / "types.xml").write_text(TYPES, encoding="utf-8")
    (tmp_path / "cfgeconomycore.xml").write_text(CFGECONOMYCORE, encoding="utf-8")
    monkeypatch.setattr(split, "gate_on_preflight", lambda: None)
    monkeypatch.setattr("sys.argv", ["split.py", str(db / "types.xml")])
    return tmp_path


def test_split_writes_categories_and_updates_cfgeconomycore(mission):
    assert split.main() == 0

    types_dir = mission / "db" / "types"
    assert split.non_empty_category_files(types_dir) == [
        "ammo.xml", "food.xml", "uncategorized.xml", "weapons.xml",
    ]
    weapons = ET.parse(types_dir / "weapons.xml").getroot()
    assert [t.get("name") for t in weapons.findall("type")] == ["AKM"]

    listed = split.cfgeconomycore_type_files(mission / "cfgeconomycore.xml")
    assert listed == {"ammo.xml", "food.xml", "uncategorized.xml", "weapons.xml"}
    assert not (mission / "db" / "_typeSplitter_runtime.py").exists()


def test_backups_are_written_once_and_not_overwritten(mission):
    assert split.main() == 0
    core_bak = mission / "cfgeconomycore.xml.bak"
    types_bak = mission / "db" / "types.xml.bak"
    assert core_bak.read_text(encoding="utf-8") == CFGECONOMYCORE
    assert types_bak.read_text(encoding="utf-8") == TYPES

    assert split.main() == 0  # rerun: cfgeconomycore is now the split version
    assert core_bak.read_text(encoding="utf-8") == CFGECONOMYCORE


def test_fails_when_cfgeconomycore_is_not_updated(mission, monkeypatch):
    # Upstream only logs errors; a cfgeconomycore without <classes> makes its
    # formatter fail after the ce entries were written. Simulate a splitter
    # that leaves cfgeconomycore untouched to check the wrapper's verification.
    monkeypatch.setattr(split, "cfgeconomycore_type_files", lambda _p: set())
    assert split.main() == 1


def test_refuses_without_cfgeconomycore(mission):
    (mission / "cfgeconomycore.xml").unlink()
    with pytest.raises(SystemExit) as exc:
        split.main()
    assert "cfgeconomycore.xml not found" in str(exc.value)
