"""Fixture test: split a small types.xml with the vendored splitter."""
import importlib.util
import re
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
    <ce folder="custom">
        <file name="mymod_types.xml" type="types"/>
    </ce>
</economycore>
"""


@pytest.fixture
def mission(tmp_path, monkeypatch):
    db = tmp_path / "db"
    db.mkdir()
    (db / "types.xml").write_text(TYPES, encoding="utf-8")
    (tmp_path / "cfgeconomycore.xml").write_text(CFGECONOMYCORE, encoding="utf-8")
    (tmp_path / "custom").mkdir()
    (tmp_path / "custom" / "mymod_types.xml").write_text("<types/>", encoding="utf-8")
    monkeypatch.setattr(split.h, "gate_on_preflight", lambda: None)
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

    core = mission / "cfgeconomycore.xml"
    listed = split.cfgeconomycore_type_files(core, "db/types")
    assert listed == {"ammo.xml", "food.xml", "uncategorized.xml", "weapons.xml"}
    # The CE resolves folder= relative to the mission root, so no bare "types".
    folders = [ce.get("folder") for ce in ET.parse(core).getroot().findall("ce")]
    assert "types" not in folders
    assert split.missing_listed_files(core, mission) == []
    assert not (mission / "db" / "_typeSplitter_runtime.py").exists()


def test_preserves_other_ce_blocks_and_core_sections(mission):
    assert split.main() == 0
    root = ET.parse(mission / "cfgeconomycore.xml").getroot()
    custom = [ce for ce in root.findall("ce") if ce.get("folder") == "custom"]
    assert [f.get("name") for f in custom[0].findall("file")] == ["mymod_types.xml"]
    assert root.find("classes/rootclass").get("name") == "DefaultWeapon"
    assert root.find("defaults/default").get("value") == "40"


def test_original_types_xml_is_emptied_to_avoid_double_loading(mission):
    assert split.main() == 0
    assert split.type_count(mission / "db" / "types.xml") == 0
    (types_bak,) = _backups(mission / "db", "types.xml")
    assert split.type_count(types_bak) == 4


def test_refuses_to_split_an_already_split_types_xml(mission):
    assert split.main() == 0
    with pytest.raises(SystemExit) as exc:
        split.main()
    assert "already split" in str(exc.value)


def test_warns_about_listed_files_that_do_not_exist(mission, capsys):
    (mission / "custom" / "mymod_types.xml").unlink()
    assert split.main() == 0
    assert "custom/mymod_types.xml, which does not exist" in capsys.readouterr().out


def _backups(folder: Path, name: str) -> list[Path]:
    stamp = re.compile(re.escape(name) + r"\.\d{8}-\d{6}(-\d+)?\.bak")
    return sorted(p for p in folder.iterdir() if stamp.fullmatch(p.name))


def test_every_run_gets_its_own_timestamped_backups(mission):
    assert split.main() == 0
    (core_bak,) = _backups(mission, "cfgeconomycore.xml")
    (types_bak,) = _backups(mission / "db", "types.xml")
    assert core_bak.read_text(encoding="utf-8") == CFGECONOMYCORE
    assert types_bak.read_text(encoding="utf-8") == TYPES
    assert _backups(mission / "db", "types") == []  # no types/ folder before the first run

    split_core = (mission / "cfgeconomycore.xml").read_text(encoding="utf-8")
    (mission / "db" / "types.xml").write_text(TYPES, encoding="utf-8")  # restore to split again
    assert split.main() == 0  # rerun, possibly within the same second
    core_baks = _backups(mission, "cfgeconomycore.xml")
    assert len(core_baks) == 2
    assert {p.read_text(encoding="utf-8") for p in core_baks} == {CFGECONOMYCORE, split_core}


def test_existing_types_folder_is_backed_up_before_regeneration(mission):
    hand_edited = mission / "db" / "types" / "custom.xml"
    hand_edited.parent.mkdir()
    hand_edited.write_text("<types/>", encoding="utf-8")
    assert split.main() == 0
    assert not hand_edited.exists()  # upstream deletes and regenerates types/
    (types_dir_bak,) = _backups(mission / "db", "types")
    assert (types_dir_bak / "custom.xml").read_text(encoding="utf-8") == "<types/>"


def test_backup_adds_counter_when_name_taken(tmp_path):
    src = tmp_path / "a.xml"
    src.write_text("x", encoding="utf-8")
    first = split.backup(src, "20260101-000000")
    second = split.backup(src, "20260101-000000")
    assert first.name == "a.xml.20260101-000000.bak"
    assert second.name == "a.xml.20260101-000000-2.bak"


def test_fails_when_cfgeconomycore_is_not_updated(mission, monkeypatch):
    # Upstream only logs errors; a cfgeconomycore without <classes> makes its
    # formatter fail after the ce entries were written. Simulate a splitter
    # that leaves cfgeconomycore untouched to check the wrapper's verification.
    monkeypatch.setattr(split, "cfgeconomycore_type_files", lambda _p, _f: set())
    assert split.main() == 1


def test_refuses_without_cfgeconomycore(mission):
    (mission / "cfgeconomycore.xml").unlink()
    with pytest.raises(SystemExit) as exc:
        split.main()
    assert "cfgeconomycore.xml not found" in str(exc.value)
