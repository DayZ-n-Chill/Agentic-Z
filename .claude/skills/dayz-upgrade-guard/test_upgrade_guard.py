"""Tests for upgrade_guard.py: the two fixture snapshots and the fixture mod, plus fake P:\\ roots in tmp_path. No DayZ, no real P:\\."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
_spec = importlib.util.spec_from_file_location("dayz_upgrade_guard_under_test", HERE / "upgrade_guard.py")
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

OLD = json.loads((FIXTURES / "snapshot_old.json").read_text(encoding="utf-8"))
NEW = json.loads((FIXTURES / "snapshot_new.json").read_text(encoding="utf-8"))
MOD = FIXTURES / "MyVest"


def _reasons(report: dict) -> dict[str, list[str]]:
    return {f["class"]: [r["reason"] for r in f["reasons"]] for f in report["findings"]}


# --- diff of the two fixture snapshots -------------------------------------------

def test_diff_finds_each_vanilla_change():
    diff = guard.diff_snapshots(OLD, NEW)
    assert diff["script"]["removed"] == ["Hologram"]
    assert diff["script"]["added"] == ["Fence"]
    assert diff["script"]["parent"] == [{"class": "Clothing", "old": "Clothing_Base", "new": "ItemBase"}]
    assert diff["script"]["methods"] == [{"class": "ItemBase", "removed": ["GetQuickBarBonus"], "changed": ["OnWasAttached"]}]
    assert diff["config"]["members"] == [{"class": "CfgVehicles/PlateCarrierVest", "removed": ["hiddenSelections"]}]
    assert diff["config"]["parent"] == [] and diff["config"]["removed"] == []


def test_same_snapshot_has_an_empty_diff():
    assert guard.diff_is_empty(guard.diff_snapshots(OLD, OLD))
    assert guard.same_classes(OLD, json.loads(json.dumps(OLD)))


# --- the fixture mod against the two snapshots ------------------------------------

def test_mod_classes_whose_vanilla_parents_changed_are_listed():
    report = guard.check_mod("MyVest", MOD, OLD, NEW, display_root=FIXTURES)
    reasons = _reasons(report)
    assert reasons == {
        "MyVest_Base": ["parent-changed"],
        "ItemBase": ["override-removed", "override-changed"],
        "MyVest_Hologram": ["parent-removed"],
        "CfgVehicles/MyVest_PlateCarrier": ["members-removed"],
    }
    # Built on vanilla: 5 script classes (the CF one is skipped) and 2 config items.
    assert report["classes_checked"] == 7


def test_findings_carry_file_line_and_a_readable_reason():
    report = guard.check_mod("MyVest", MOD, OLD, NEW, display_root=FIXTURES)
    by_class = {f["class"]: f for f in report["findings"]}
    assert by_class["MyVest_Base"]["where"] == "MyVest/scripts/4_World/MyVest.c:3"
    assert by_class["CfgVehicles/MyVest_PlateCarrier"]["where"] == "MyVest/config.cpp:15"
    assert by_class["MyVest_Base"]["reasons"][0]["message"] == "vanilla Clothing now extends ItemBase (was Clothing_Base)"
    changed = next(r for r in by_class["ItemBase"]["reasons"] if r["reason"] == "override-changed")
    assert changed["method"] == "OnWasAttached"
    assert "from_cargo" in changed["message"]
    assert by_class["CfgVehicles/MyVest_PlateCarrier"]["reasons"][0]["members"] == ["hiddenSelections"]


def test_unchanged_vanilla_affects_nothing():
    report = guard.check_mod("MyVest", MOD, OLD, OLD)
    assert report["findings"] == []


def test_config_redeclared_with_an_old_parent(tmp_path):
    (tmp_path / "config.cpp").write_text(
        "class CfgVehicles\n{\n    class Clothing_Base;\n    class Clothing: Clothing_Base\n    {\n        itemSize[] = {2,2};\n    };\n};\n",
        encoding="utf-8")
    new = json.loads(json.dumps(NEW))
    new["config"]["cfgvehicles/clothing"]["parent"] = "Inventory_Base"
    report = guard.check_mod("Redeclare", tmp_path, OLD, new)
    assert _reasons(report)["CfgVehicles/Clothing"][0] == "redeclared-parent"


def test_override_in_a_class_two_steps_below_vanilla(tmp_path):
    # MyVest extends MyVest_Base extends Clothing: the override is checked against Clothing's chain.
    (tmp_path / "MyVest.c").write_text(
        "class MyVest_Base extends Clothing {}\n"
        "class MyVest extends MyVest_Base { override void OnWear(int a) {} }\n",
        encoding="utf-8")
    old = {"script": {"Clothing": {"parent": None, "file": "c.c", "line": 1,
                                   "methods": {"OnWear": "void OnWear(int a)"}}}, "config": {}}
    new = json.loads(json.dumps(old))
    new["script"]["Clothing"]["methods"]["OnWear"] = "void OnWear(float a)"
    report = guard.check_mod("MyVest", tmp_path, old, new)
    assert _reasons(report) == {"MyVest": ["override-changed"]}
    assert report["findings"][0]["vanilla"] == "Clothing"
    assert report["classes_checked"] == 2


def test_missing_mod_folder_is_an_error(tmp_path, capsys):
    args = ["diff", "--old", str(FIXTURES / "snapshot_old.json"), "--new", str(FIXTURES / "snapshot_new.json"),
            "--mod-dir", str(tmp_path / "Gone")]
    assert guard.main(args) == 2
    assert capsys.readouterr().out.startswith("ERROR")


def test_config_class_names_ignore_case(tmp_path):
    # Vanilla writes CfgVehicles in one config.cpp and cfgVehicles in another; both are one class.
    def p_root(root: Path, second: str) -> Path:
        (root / "scripts").mkdir(parents=True)
        for addon, body in (("a", "class CfgVehicles { class Clothing { a = 1; }; };\n"), ("b", second)):
            (root / "DZ" / addon).mkdir(parents=True)
            (root / "DZ" / addon / "config.cpp").write_text(body, encoding="utf-8")
        return root

    old = guard.take_snapshot(p_root(tmp_path / "old", "class cfgVehicles { class Clothing { b = 1; }; };\n"))
    new = guard.take_snapshot(p_root(tmp_path / "new", "class cfgVehicles { class Clothing {}; };\n"))
    assert list(old["config"]) == ["cfgvehicles/clothing"]
    assert old["config"]["cfgvehicles/clothing"]["name"] == "CfgVehicles/Clothing"
    assert old["config"]["cfgvehicles/clothing"]["members"] == ["a", "b"]
    mod = tmp_path / "MyBag"
    mod.mkdir()
    (mod / "config.cpp").write_text("class CfgVehicles { class MyBag: clothing {}; };\n", encoding="utf-8")
    report = guard.check_mod("MyBag", mod, old, new)
    assert _reasons(report) == {"CfgVehicles/MyBag": ["members-removed"]}
    assert report["findings"][0]["reasons"][0]["members"] == ["b"]
    assert report["findings"][0]["reasons"][0]["message"] == "vanilla Clothing no longer sets b"


def _config_chain(clothing_base: list[str], clothing: list[str]) -> dict:
    def entry(name: str, parent, members: list[str]) -> dict:
        return {"name": f"CfgVehicles/{name}", "parent": parent, "members": members}
    return {"script": {}, "config": {
        "cfgvehicles/clothing_base": entry("Clothing_Base", None, clothing_base),
        "cfgvehicles/clothing": entry("Clothing", "Clothing_Base", clothing)}}


def _bag(tmp_path: Path, body: str = "") -> Path:
    (tmp_path / "config.cpp").write_text(
        "class CfgVehicles { class Clothing; class MyBag: Clothing { " + body + " }; };" + chr(10),
        encoding="utf-8")
    return tmp_path


def test_a_property_that_moves_up_the_chain_is_not_removed(tmp_path):
    old = _config_chain(["scope"], ["itemSize", "weight"])
    new = _config_chain(["scope", "itemSize", "weight"], [])
    report = guard.check_mod("MyBag", _bag(tmp_path), old, new)
    assert report["findings"] == []


def test_a_property_the_mod_sets_itself_is_not_removed(tmp_path):
    old = _config_chain(["scope"], ["itemSize", "weight"])
    new = _config_chain(["scope"], ["weight"])
    report = guard.check_mod("MyBag", _bag(tmp_path, "itemSize[] = {2,2};"), old, new)
    assert report["findings"] == []


def test_a_property_gone_from_the_whole_chain_is_removed(tmp_path):
    old = _config_chain(["scope", "quickBarBonus"], ["itemSize", "weight"])
    new = _config_chain(["scope"], ["itemSize"])
    report = guard.check_mod("MyBag", _bag(tmp_path), old, new)
    assert _reasons(report) == {"CfgVehicles/MyBag": ["members-removed", "members-removed"]}
    messages = [r["message"] for r in report["findings"][0]["reasons"]]
    assert messages == ["vanilla Clothing no longer sets weight", "vanilla Clothing_Base no longer sets quickBarBonus"]


def test_a_config_class_built_on_a_mod_base_is_not_followed(tmp_path):
    # Config classes are checked against their direct parent only: the mod base is
    # checked, its child (MyBag_Black : MyBag_ColorBase) is skipped, as SKILL.md says.
    (tmp_path / "config.cpp").write_text(
        "class CfgVehicles { class Clothing; class MyBag_ColorBase: Clothing {}; "
        "class MyBag_Black: MyBag_ColorBase {}; };" + chr(10), encoding="utf-8")
    old = _config_chain(["scope"], ["itemSize", "weight"])
    new = _config_chain(["scope"], ["itemSize"])
    report = guard.check_mod("MyBag", tmp_path, old, new)
    assert _reasons(report) == {"CfgVehicles/MyBag_ColorBase": ["members-removed"]}
    assert report["classes_checked"] == 1


def test_a_snapshot_from_before_the_case_fix_is_refused(tmp_path):
    old = json.loads(json.dumps(OLD))
    old["format"] = 1
    path = tmp_path / "old.json"
    path.write_text(json.dumps(old), encoding="utf-8")
    with pytest.raises(guard.GuardError, match="Take a new snapshot"):
        guard.load_snapshot(str(path), tmp_path)


# --- parsing ----------------------------------------------------------------------

def test_script_parser_reads_classes_and_methods():
    text = """
    // class InComment extends Nope {}
    /* class InBlock extends Nope {} */
    class Fwd;
    class Param1<Class T1> extends Param { T1 param1; void Param1(T1 p1) { param1 = p1; } }
    sealed class Sealed {}
    class Plain : Managed
    {
        [NonSerialized()]
        int m_Count = Count("x;{");
        ref array<string> m_List = new array<string>();
        void Plain() {}
        void ~Plain() {}
        override protected bool Do(int a, float b = 0.5, string s = "a,b")
        {
            if (a) { return true; }
            return false;
        }
        proto native int Native(out vector pos);
    }
    modded class Plain { override void Extra() {} }
    """
    decls = {(d["name"], d["modded"]): d for d in guard.parse_script(text)}
    assert set(decls) == {("Param1", False), ("Sealed", False), ("Plain", False), ("Plain", True)}
    assert decls[("Param1", False)]["parent"] == "Param"
    plain = decls[("Plain", False)]
    assert plain["parent"] == "Managed"
    assert plain["line"] == 7
    methods = {name: sig for name, (sig, _) in plain["methods"].items()}
    assert methods == {
        "Plain": "void Plain()",
        "~Plain": "void ~Plain()",
        "Do": "protected bool Do(int a, float b, string s)",
        "Native": "proto native int Native(out vector pos)",
    }
    assert plain["methods"]["Do"][1] is True
    assert decls[("Plain", True)]["methods"]["Extra"] == ("void Extra()", True)


def test_config_parser_keeps_parents_and_member_names():
    text = """
    class CfgPatches { class A { units[] = {}; weapons[] = {}; requiredAddons[] = {}; }; };
    class CfgVehicles
    {
        class Clothing;
        class Vest: Clothing
        {
            scope = 2;
            hiddenSelections[] = {"camo"};
            itemInfo[] += {"Vest"};
            class DamageSystem { class GlobalHealth { hitpoints = 100; }; };
        };
    };
    """
    decls = {f"{d['container']}/{d['name']}": d for d in guard.parse_config(text)}
    assert set(decls) == {"CfgPatches/A", "CfgVehicles/Vest"}
    vest = decls["CfgVehicles/Vest"]
    assert vest["parent"] == "Clothing"
    assert vest["members"] == ["DamageSystem", "hiddenSelections", "itemInfo", "scope"]


# --- snapshot and check from fake P:\ roots ------------------------------------------

def _fake_p(root: Path, clothing_parent: str, quickbar: bool) -> Path:
    scripts = root / "scripts" / "4_world"
    scripts.mkdir(parents=True)
    quick = "int GetQuickBarBonus() { return 0; }" if quickbar else ""
    (scripts / "itembase.c").write_text(
        f"class ItemBase extends InventoryItem {{ void SetActions() {{}} {quick} }}\n"
        "class InventoryItem extends EntityAI {}\n"
        f"class Clothing extends {clothing_parent} {{}}\n"
        "class Clothing_Base extends ItemBase {}\n",
        encoding="utf-8")
    (scripts / "modded_part.c").write_text("modded class ItemBase { void Extra() {} }\n", encoding="utf-8")
    cfg = root / "DZ" / "characters"
    cfg.mkdir(parents=True)
    (cfg / "config.cpp").write_text(
        "class CfgVehicles { class Clothing_Base; class Clothing: Clothing_Base { itemSize[] = {1,1}; }; };\n",
        encoding="utf-8")
    (root / "DZ" / "characters" / "broken").mkdir()
    (root / "DZ" / "characters" / "broken" / "config.cpp").write_text('class X { a = "unclosed; };\n', encoding="utf-8")
    return root


def test_snapshot_reads_a_fake_p_root(tmp_path):
    snap = guard.take_snapshot(_fake_p(tmp_path / "p", "Clothing_Base", True))
    assert snap["script"]["ItemBase"]["parent"] == "InventoryItem"
    assert set(snap["script"]["ItemBase"]["methods"]) == {"SetActions", "GetQuickBarBonus", "Extra"}
    assert snap["script"]["ItemBase"]["file"] == "scripts/4_world/itembase.c"
    assert snap["config"]["cfgvehicles/clothing"] == {
        "name": "CfgVehicles/Clothing", "parent": "Clothing_Base", "file": "DZ/characters/config.cpp", "line": 1,
        "members": ["itemSize"]}
    assert snap["skipped"] == ["DZ/characters/broken/config.cpp"]


def test_snapshot_command_saves_and_prints_counts(tmp_path, capsys):
    store = tmp_path / "store"
    p_root = _fake_p(tmp_path / "p", "Clothing_Base", True)
    assert guard.main(["snapshot", "--p-root", str(p_root), "--store", str(store), "--label", "1.28"]) == 0
    out = capsys.readouterr().out.splitlines()
    saved = guard.stored_snapshots(store)
    assert len(saved) == 1 and saved[0].name.endswith("-1.28.json")
    snap = json.loads(saved[0].read_text(encoding="utf-8"))
    assert out[0] == f"Snapshot saved: {saved[0]}"
    assert out[1] == (f"  {len(snap['script'])} script classes, {len(snap['config'])} config classes, "
                      f"{len(snap['skipped'])} file(s) skipped")


def test_snapshot_without_game_data_is_an_error(tmp_path, capsys):
    assert guard.main(["snapshot", "--p-root", str(tmp_path), "--store", str(tmp_path / "store")]) == 2
    assert capsys.readouterr().out.startswith("ERROR")


def test_check_before_and_after_an_update(tmp_path, capsys, monkeypatch):
    store = tmp_path / "store"
    mod = tmp_path / "MyVest"
    shutil.copytree(MOD, mod)
    reindexed = []
    monkeypatch.setattr(guard, "run_reindex", lambda out=None: reindexed.append(True) or 0)
    before = _fake_p(tmp_path / "before", "Clothing_Base", True)
    after = _fake_p(tmp_path / "after", "ItemBase", False)
    common = ["--store", str(store), "--mod-dir", str(mod)]

    # First run: nothing to compare with, so it saves the baseline.
    assert guard.main(["check", "--p-root", str(before), *common]) == 0
    assert "baseline" in capsys.readouterr().out
    assert len(guard.stored_snapshots(store)) == 1

    # Same game data again: PASS, and no second copy is saved.
    assert guard.main(["check", "--p-root", str(before), "--reindex", *common]) == 0
    assert capsys.readouterr().out.startswith("PASS")
    assert len(guard.stored_snapshots(store)) == 1 and not reindexed

    # After the update: FAIL with the affected classes, a new snapshot and a re index.
    assert guard.main(["check", "--p-root", str(after), "--reindex", "--json", *common]) == 1
    out = capsys.readouterr().out
    assert out.startswith("FAIL")
    report = json.loads(out.split("\n", 1)[1])  # stdout is the verdict line plus one JSON document
    assert _reasons(report["mods"][0]) == {"MyVest_Base": ["parent-changed"], "ItemBase": ["override-removed"]}
    assert len(guard.stored_snapshots(store)) == 2 and reindexed == [True]

    # diff shows the same report again from the two saved snapshots.
    assert guard.main(["diff", *common]) == 1
    assert "MyVest_Base" in capsys.readouterr().out


def test_a_mistyped_mod_name_saves_no_snapshot(tmp_path, capsys):
    store = tmp_path / "store"
    before = _fake_p(tmp_path / "before", "Clothing_Base", True)
    after = _fake_p(tmp_path / "after", "ItemBase", False)
    assert guard.main(["check", "--p-root", str(before), "--store", str(store), "--mod-dir", str(MOD)]) == 0
    baseline = guard.stored_snapshots(store)
    capsys.readouterr()

    args = ["check", "--p-root", str(after), "--store", str(store), "--mod-dir", str(tmp_path / "MyVst")]
    assert guard.main(args) == 2
    assert capsys.readouterr().out.startswith("ERROR")
    assert guard.stored_snapshots(store) == baseline

    # The corrected run still sees the update.
    assert guard.main(["check", "--p-root", str(after), "--store", str(store), "--mod-dir", str(MOD)]) == 1
    assert "Vanilla classes did not change" not in capsys.readouterr().out


def test_snapshots_from_the_same_second_sort_in_order(tmp_path, monkeypatch):
    fixed = guard.datetime(2026, 10, 21, 5, 22, 57)
    monkeypatch.setattr(guard, "datetime", type("FixedClock", (), {"now": staticmethod(lambda: fixed)}))
    store = tmp_path / "store"
    saved = [guard.save_snapshot({"label": label}, store) for label in ("b", "", "a", "")]
    assert len(set(saved)) == 4
    assert guard.stored_snapshots(store) == saved
    assert [p.name for p in saved] == [
        "20261021-052257-b.json", "20261021-052257_02.json", "20261021-052257_03-a.json", "20261021-052257_04.json"]


def test_check_json_on_the_first_run_prints_the_baseline(tmp_path, capsys):
    store = tmp_path / "store"
    args = ["check", "--p-root", str(_fake_p(tmp_path / "p", "Clothing_Base", True)), "--store", str(store),
            "--mod-dir", str(MOD), "--json"]
    assert guard.main(args) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "PASS"
    data = json.loads(out[out.index("{"):])
    assert data == {"verdict": "PASS", "baseline": str(guard.stored_snapshots(store)[0])}


class _FakeRun:
    """Stands in for subprocess.run so --reindex never starts the real indexer."""

    def __init__(self, returncode: int):
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def __call__(self, cmd, *args, **kwargs):
        self.calls.append([str(c) for c in cmd])
        return type("Done", (), {"returncode": self.returncode})()


def test_reindex_runs_the_indexer_only_when_vanilla_changed(tmp_path, capsys, monkeypatch):
    fake = _FakeRun(0)
    monkeypatch.setattr(guard.subprocess, "run", fake)
    store = tmp_path / "store"
    before = _fake_p(tmp_path / "before", "Clothing_Base", True)
    after = _fake_p(tmp_path / "after", "ItemBase", False)
    common = ["--store", str(store), "--mod-dir", str(MOD), "--reindex"]

    assert guard.main(["check", "--p-root", str(before), *common]) == 0  # baseline
    assert guard.main(["check", "--p-root", str(before), *common]) == 0  # nothing changed
    assert fake.calls == []
    capsys.readouterr()

    guard.main(["check", "--p-root", str(after), *common])
    assert len(fake.calls) == 1
    assert fake.calls[0][1] == str(guard.INDEXER) and fake.calls[0][2:] == ["--full"]
    assert "old index is still in place" not in capsys.readouterr().out


def test_a_failed_reindex_keeps_the_verdict_exit_code(tmp_path, capsys, monkeypatch):
    fake = _FakeRun(3)
    monkeypatch.setattr(guard.subprocess, "run", fake)
    store = tmp_path / "store"
    mod = tmp_path / "MyVest"
    shutil.copytree(MOD, mod)
    common = ["--store", str(store), "--mod-dir", str(mod), "--reindex"]

    assert guard.main(["check", "--p-root", str(_fake_p(tmp_path / "before", "Clothing_Base", True)), *common]) == 0
    capsys.readouterr()
    assert guard.main(["check", "--p-root", str(_fake_p(tmp_path / "after", "ItemBase", False)), *common]) == 1
    out = capsys.readouterr().out
    assert out.startswith("FAIL")
    assert "The search index rebuild exited with 3; the old index is still in place." in out
    assert len(fake.calls) == 1


@pytest.mark.parametrize("reindex", [False, True])
def test_json_stdout_is_only_the_verdict_and_the_report(tmp_path, capsys, monkeypatch, reindex):
    fake = _FakeRun(3)
    monkeypatch.setattr(guard.subprocess, "run", fake)
    store = tmp_path / "store"
    common = ["--store", str(store), "--mod-dir", str(MOD), "--json"] + (["--reindex"] if reindex else [])

    guard.main(["check", "--p-root", str(_fake_p(tmp_path / "before", "Clothing_Base", True)), *common])
    capsys.readouterr()
    guard.main(["check", "--p-root", str(_fake_p(tmp_path / "after", "ItemBase", False)), *common])
    captured = capsys.readouterr()
    verdict, body = captured.out.split("\n", 1)
    assert verdict == "FAIL"
    assert json.loads(body)["vanilla_changed"] is True
    note = "old index is still in place" if reindex else "Vanilla changed: rebuild the search index"
    assert note in captured.err
    if reindex:
        assert "Rebuilding the search index" in captured.err


def test_diff_with_the_fixture_snapshots_from_the_cli(capsys):
    args = ["diff", "--old", str(FIXTURES / "snapshot_old.json"), "--new", str(FIXTURES / "snapshot_new.json"),
            "--mod-dir", str(MOD)]
    assert guard.main(args) == 1
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "FAIL"
    assert "script Clothing now extends ItemBase (was Clothing_Base)" in out
    assert "script Hologram removed" in out
    assert "MyVest: 7 class(es) built on vanilla, 4 affected" in out


def test_diff_needs_two_snapshots(tmp_path, capsys):
    assert guard.main(["diff", "--store", str(tmp_path), "--mod-dir", str(MOD)]) == 2
    assert capsys.readouterr().out.startswith("ERROR")


def test_no_mods_named_and_no_project_checks_vanilla_only(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(guard, "_cached_project", lambda: None)
    args = ["diff", "--old", str(FIXTURES / "snapshot_old.json"), "--new", str(FIXTURES / "snapshot_new.json")]
    assert guard.main(args) == 0
    assert "No mods checked" in capsys.readouterr().out


def test_check_with_no_mod_and_no_project_is_an_error_and_saves_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(guard, "_cached_project", lambda: None)
    store = tmp_path / "store"
    args = ["check", "--p-root", str(_fake_p(tmp_path / "p", "Clothing_Base", True)), "--store", str(store)]
    assert guard.main(args) == 2
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "ERROR"
    assert "Name the mod" in out and "Nothing was saved" in out
    assert guard.stored_snapshots(store) == []


def test_reindex_command_rebuilds_after_a_check_that_saved_the_new_baseline(tmp_path, capsys, monkeypatch):
    fake = _FakeRun(0)
    monkeypatch.setattr(guard.subprocess, "run", fake)
    store = tmp_path / "store"
    common = ["--store", str(store), "--mod-dir", str(MOD)]
    guard.main(["check", "--p-root", str(_fake_p(tmp_path / "before", "Clothing_Base", True)), *common])
    after = _fake_p(tmp_path / "after", "ItemBase", False)
    assert guard.main(["check", "--p-root", str(after), *common]) == 1
    out = capsys.readouterr().out
    assert "upgrade_guard.py reindex" in out and "check --reindex again would see no change" in out
    # The second check sees the saved baseline, so --reindex there does nothing...
    guard.main(["check", "--p-root", str(after), "--reindex", *common])
    assert fake.calls == []
    # ...and the reindex command rebuilds the index on its own.
    assert guard.main(["reindex"]) == 0
    assert len(fake.calls) == 1 and fake.calls[0][1:] == [str(guard.INDEXER), "--full"]


def test_reindex_command_passes_on_a_failed_rebuild(capsys, monkeypatch):
    monkeypatch.setattr(guard.subprocess, "run", _FakeRun(3))
    assert guard.main(["reindex"]) == 3
    assert "old index is still in place" in capsys.readouterr().out


def test_every_mod_in_the_workspace_is_checked_by_default(tmp_path, capsys, monkeypatch):
    shutil.copytree(MOD, tmp_path / "workspace" / "MyVest")
    (tmp_path / "workspace" / "Empty").mkdir()
    monkeypatch.setattr(guard, "_cached_project", lambda: tmp_path)
    args = ["diff", "--old", str(FIXTURES / "snapshot_old.json"), "--new", str(FIXTURES / "snapshot_new.json")]
    assert guard.main(args) == 1
    out = capsys.readouterr().out
    assert "Empty: 0 class(es)" in out
    assert "workspace/MyVest/scripts/4_World/MyVest.c:3" in out


def test_scan_mod_skips_config_copies_in_dot_folders(tmp_path):
    mod = tmp_path / "MyVest"
    shutil.copytree(MOD, mod)
    real = guard.scan_mod(mod)["config"]
    backup = mod / ".history" / "config.cpp"
    backup.parent.mkdir()
    backup.write_text("class CfgVehicles { class Clothing; class Stale_Vest : Clothing { scope = 2; }; };", encoding="utf-8")
    configs = guard.scan_mod(mod)["config"]
    assert configs == real
    assert not any(d["name"] == "Stale_Vest" for d in configs)


def test_parse_config_records_classes_in_any_top_level_container():
    text = "class BillboardPresets { class Default { a = 1; }; }; class CfgVehicles { class V { b = 1; }; };"
    assert [(d["container"], d["name"]) for d in guard.parse_config(text)] == [
        ("BillboardPresets", "Default"), ("CfgVehicles", "V")]


@pytest.mark.parametrize("argv", [["check", "--bogus"], [], ["diff", "--json", "--bogus"]])
def test_argparse_errors_still_print_error_first_line(argv, capsys):
    assert guard.main(argv) == 2
    out = capsys.readouterr().out.splitlines()
    assert out[0] == "ERROR"
    if "--json" in argv:
        assert json.loads("\n".join(out[1:]))["verdict"] == "ERROR"
