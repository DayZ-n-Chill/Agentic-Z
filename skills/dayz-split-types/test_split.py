"""Fixture test: split a small types.xml with the vendored splitter."""
import importlib.util
import io
import os
import re
import stat
import sys
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


def test_failed_check_restores_files_from_backups(mission, monkeypatch, capsys):
    monkeypatch.setattr(split, "cfgeconomycore_type_files", lambda _p, _f: set())
    assert split.main() == 1
    assert (mission / "cfgeconomycore.xml").read_text(encoding="utf-8") == CFGECONOMYCORE
    assert (mission / "db" / "types.xml").read_text(encoding="utf-8") == TYPES
    assert not (mission / "db" / "types").exists()  # no types/ folder before the run
    assert "Restored cfgeconomycore.xml" in capsys.readouterr().err
    (core_bak,) = _backups(mission, "cfgeconomycore.xml")  # backups are kept
    assert core_bak.read_text(encoding="utf-8") == CFGECONOMYCORE


def test_failed_check_restores_previous_types_folder(mission, monkeypatch):
    hand_edited = mission / "db" / "types" / "custom.xml"
    hand_edited.parent.mkdir()
    hand_edited.write_text("<types/>", encoding="utf-8")
    monkeypatch.setattr(split, "cfgeconomycore_type_files", lambda _p, _f: set())
    assert split.main() == 1
    assert sorted(p.name for p in hand_edited.parent.iterdir()) == ["custom.xml"]
    assert hand_edited.read_text(encoding="utf-8") == "<types/>"


def test_splitter_crash_restores_files(mission, monkeypatch):
    class Failed:
        returncode = 3

    def fake_run(*_a, **_k):
        # Mimic a splitter that rewrote cfgeconomycore and wrote types/ before dying.
        (mission / "cfgeconomycore.xml").write_text("<economycore/>", encoding="utf-8")
        (mission / "db" / "types").mkdir()
        (mission / "db" / "types" / "ammo.xml").write_text("<types/>", encoding="utf-8")
        return Failed()

    monkeypatch.setattr(split.subprocess, "run", fake_run)
    assert split.main() == 1
    assert (mission / "cfgeconomycore.xml").read_text(encoding="utf-8") == CFGECONOMYCORE
    assert not (mission / "db" / "types").exists()
    assert not (mission / "db" / "_typeSplitter_runtime.py").exists()


def test_unexpected_error_restores_files_and_reraises(mission, monkeypatch):
    def boom(*_a, **_k):
        (mission / "cfgeconomycore.xml").write_text("<economycore/>", encoding="utf-8")
        raise OSError("disk full")

    monkeypatch.setattr(split, "fix_cfgeconomycore", boom)
    with pytest.raises(OSError):
        split.main()
    assert (mission / "cfgeconomycore.xml").read_text(encoding="utf-8") == CFGECONOMYCORE
    assert not (mission / "db" / "types").exists()


def test_main_gates_on_preflight_before_touching_files(mission, monkeypatch):
    def fail_gate():
        raise SystemExit(1)

    monkeypatch.setattr(split.h, "gate_on_preflight", fail_gate)
    with pytest.raises(SystemExit):
        split.main()
    assert _backups(mission, "cfgeconomycore.xml") == []
    assert not (mission / "db" / "types").exists()


def test_refuses_without_cfgeconomycore(mission):
    (mission / "cfgeconomycore.xml").unlink()
    with pytest.raises(SystemExit) as exc:
        split.main()
    assert "cfgeconomycore.xml not found" in str(exc.value)


def test_backup_lines_are_flushed_before_the_splitter_starts(mission, monkeypatch):
    # With stdout piped, Python buffers it; unflushed backup lines would appear
    # after the splitter's own log in a captured transcript.
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="utf-8"))
    real_run = split.subprocess.run
    seen = {}

    def checking_run(*a, **k):
        seen["before_splitter"] = raw.getvalue().decode("utf-8")
        return real_run(*a, **k)

    monkeypatch.setattr(split.subprocess, "run", checking_run)
    assert split.main() == 0
    assert seen["before_splitter"].count("Backup:") == 2


def test_lost_type_entries_fail_and_restore(mission, monkeypatch, capsys):
    real_run = split.subprocess.run

    def lossy_run(*a, **k):
        result = real_run(*a, **k)
        (mission / "db" / "types" / "food.xml").write_text("<types/>", encoding="utf-8")
        return result

    monkeypatch.setattr(split.subprocess, "run", lossy_run)
    assert split.main() == 1
    assert "hold 3 <type> entries, but types.xml had 4" in capsys.readouterr().err
    assert (mission / "db" / "types.xml").read_text(encoding="utf-8") == TYPES
    assert (mission / "cfgeconomycore.xml").read_text(encoding="utf-8") == CFGECONOMYCORE
    assert not (mission / "db" / "types").exists()


def test_failure_transcript_keeps_ok_lines_before_fail_and_restore(mission, monkeypatch):
    # stdout and stderr piped into one transcript: stdout block-buffered,
    # stderr line-buffered (as Python sets them up for a pipe). The [OK] split
    # lines must come before [FAIL] and the Restored line must be last.
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding="utf-8"))
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(raw, encoding="utf-8", line_buffering=True))
    monkeypatch.setattr(split, "cfgeconomycore_type_files", lambda _p, _f: set())
    assert split.main() == 1
    sys.stderr.flush()
    out = raw.getvalue().decode("utf-8")
    assert "Split into" in out
    assert out.index("Split into") < out.index("[FAIL]") < out.index("Restored")
    assert out.rstrip().splitlines()[-1].lstrip().startswith("[OK]    Restored")


@pytest.mark.parametrize("which", ["db/types.xml", "cfgeconomycore.xml"])
def test_refuses_read_only_files_before_touching_anything(mission, which):
    # Files copied from a server install are often read-only; the run must stop
    # before any backup or split rather than fail halfway.
    target = mission / which
    os.chmod(target, stat.S_IREAD)
    try:
        with pytest.raises(SystemExit) as exc:
            split.main()
    finally:
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)
    assert "Not writable" in str(exc.value) and str(target) in str(exc.value)
    assert _backups(mission, "cfgeconomycore.xml") == []
    assert not (mission / "db" / "types").exists()
    assert (mission / "db" / "types.xml").read_text(encoding="utf-8") == TYPES


def test_failed_stub_write_restores_instead_of_double_loading(mission, monkeypatch, capsys):
    # A locked types.xml passes the writability check but the final stub write
    # fails. Without the restore, cfgeconomycore would list db/types while the
    # full types.xml stays, and the server would load every type twice.
    real_write_text = Path.write_text

    def locked_write_text(self, *a, **k):
        if self.name == "types.xml":
            raise PermissionError(13, "locked by another process", str(self))
        return real_write_text(self, *a, **k)

    monkeypatch.setattr(split.Path, "write_text", locked_write_text)
    assert split.main() == 1
    err = capsys.readouterr().err
    assert "Could not empty" in err and "Restored cfgeconomycore.xml" in err
    assert (mission / "cfgeconomycore.xml").read_text(encoding="utf-8") == CFGECONOMYCORE
    assert (mission / "db" / "types.xml").read_text(encoding="utf-8") == TYPES
    assert not (mission / "db" / "types").exists()


def test_failed_restore_prints_backup_paths_and_manual_steps(mission, monkeypatch, capsys):
    monkeypatch.setattr(split, "cfgeconomycore_type_files", lambda _p, _f: set())

    def locked_rmtree(path, *a, **k):
        raise PermissionError(13, "in use", str(path))

    monkeypatch.setattr(split.shutil, "rmtree", locked_rmtree)
    assert split.main() == 1
    err = capsys.readouterr().err
    (core_bak,) = _backups(mission, "cfgeconomycore.xml")
    (types_bak,) = _backups(mission / "db", "types.xml")
    assert "Automatic restore failed" in err
    assert f"copy {core_bak} over {mission / 'cfgeconomycore.xml'}" in err
    assert f"copy {types_bak} over {mission / 'db' / 'types.xml'}" in err
    assert f"delete the folder {mission / 'db' / 'types'}" in err
    assert "Restored cfgeconomycore.xml" not in err
