"""Tests for server_kit.py against the release pack's fixture mod and mission. No P: drive, no DayZ."""
import importlib.util
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent / "dayz-release-pack" / "fixtures"
_SPEC = importlib.util.spec_from_file_location("dayz_server_kit_under_test", HERE / "server_kit.py")
kit = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(kit)


@pytest.fixture
def mod(tmp_path):
    dest = tmp_path / "MyVest"
    shutil.copytree(FIXTURES / "MyVest", dest)
    return dest


def build(mod, tmp_path, mission=None, deps=None):
    report = kit.server_kit("MyVest", mod, tmp_path / "out", mission, deps, p_mods=None)
    with zipfile.ZipFile(report["zip"]) as z:
        members = {name: z.read(name) for name in z.namelist()}
    return report, members


def type_names(members):
    root = ET.fromstring(members["MyVest_ce/types.xml"])
    return [t.get("name") for t in root.findall("type")]


def test_kit_holds_the_five_parts(mod, tmp_path):
    report, members = build(mod, tmp_path, FIXTURES / "mission", ["CF"])
    assert sorted(members) == ["MyVest_ce/types.xml", "README.txt", "cfgeconomycore-lines.xml",
                               "keys/MyVest.bikey", "load-order.txt"]
    assert Path(report["zip"]).name == "MyVest-server-kit.zip"


def test_types_come_from_mod_then_mission_then_placeholder(mod, tmp_path):
    report, members = build(mod, tmp_path, FIXTURES / "mission")
    # Black from the mod's own types file, Green from db/types.xml, Pouch from a cfgeconomycore file.
    assert report["types"] == {"mod": ["MyVest_Black"], "mission": ["MyVest_Green", "MyVest_Pouch"], "placeholder": []}
    assert type_names(members) == ["MyVest_Black", "MyVest_Green", "MyVest_Pouch"]
    root = ET.fromstring(members["MyVest_ce/types.xml"])
    green = next(t for t in root.findall("type") if t.get("name") == "MyVest_Green")
    assert green.findtext("nominal") == "6" and green.find("usage").get("name") == "Hunting"
    assert "AKM" not in members["MyVest_ce/types.xml"].decode()  # vanilla entries stay out


def test_without_a_mission_missing_entries_are_placeholders_that_do_not_spawn(mod, tmp_path):
    report, members = build(mod, tmp_path)
    assert report["types"]["placeholder"] == ["MyVest_Green", "MyVest_Pouch"]
    root = ET.fromstring(members["MyVest_ce/types.xml"])
    for t in root.findall("type"):
        if t.get("name") in report["types"]["placeholder"]:
            assert t.findtext("nominal") == "0" and t.findtext("min") == "0"
    assert b"placeholder values" in members["MyVest_ce/types.xml"]
    assert any(w.startswith("placeholder-types") and "--mission" in w for w in report["warnings"])
    assert b"MyVest_Green" in members["README.txt"]


def test_economycore_block_loads_the_types_file(mod, tmp_path):
    _, members = build(mod, tmp_path)
    text = members["cfgeconomycore-lines.xml"].decode()
    ce = ET.fromstring(text[text.index("<ce"):])
    assert ce.get("folder") == "MyVest_ce"
    assert [(f.get("name"), f.get("type")) for f in ce.findall("file")] == [("types.xml", "types")]


def test_load_order_puts_dependencies_first(mod, tmp_path):
    report, members = build(mod, tmp_path, deps=["@CF"])
    assert report["load_order"] == ["@CF", "@MyVest"]
    assert "-mod=@CF;@MyVest" in members["load-order.txt"].decode()
    report, members = build(mod, tmp_path)
    assert "JM_CF_Scripts" in members["load-order.txt"].decode()
    assert any(w.startswith("deps-unmapped") for w in report["warnings"])


def test_private_key_is_never_zipped(mod, tmp_path):
    (mod / "Keys" / "MyVest.biprivatekey").write_bytes(b"secret")
    (mod / "MyVest.biprivatekey").write_bytes(b"secret")
    report, members = build(mod, tmp_path)
    assert not any(name.lower().endswith(".biprivatekey") for name in members)
    assert all(b"secret" not in data for data in members.values())
    assert members["keys/MyVest.bikey"] == (mod / "Keys" / "MyVest.bikey").read_bytes()
    assert any(w.startswith("private-key-in-mod") for w in report["warnings"])


def test_deployed_keys_are_found(mod, tmp_path):
    shutil.rmtree(mod / "Keys")
    p_mods = tmp_path / "Mods"
    (p_mods / "@MyVest" / "Keys").mkdir(parents=True)
    (p_mods / "@MyVest" / "Keys" / "Deployed.bikey").write_bytes(b"k")
    (p_mods / "@MyVest" / "Keys" / "Deployed.biprivatekey").write_bytes(b"secret")
    report = kit.server_kit("MyVest", mod, tmp_path / "out", p_mods=p_mods)
    assert report["keys"] == ["Deployed.bikey"]
    assert "keys/Deployed.biprivatekey" not in zipfile.ZipFile(report["zip"]).namelist()


def test_no_key_is_reported(mod, tmp_path):
    shutil.rmtree(mod / "Keys")
    report, members = build(mod, tmp_path)
    assert report["keys"] == []
    assert b"No .bikey" in members["README.txt"]
    assert any(w.startswith("no-bikey") for w in report["warnings"])


def test_mission_by_instance_name(tmp_path):
    project = tmp_path / "proj"
    shutil.copytree(FIXTURES / "mission", project / ".server" / "chernarus" / "mission")
    assert kit.resolve_mission("chernarus", [project]) == project / ".server" / "chernarus" / "mission"
    with pytest.raises(kit.ReleaseError):
        kit.resolve_mission("nowhere", [project])


def test_cli_json_and_errors(mod, tmp_path):
    out = tmp_path / "cli"
    r = subprocess.run([sys.executable, str(HERE / "server_kit.py"), "--mod-dir", str(mod), "--out", str(out),
                        "--mission", str(FIXTURES / "mission"), "--deps", "CF", "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["types"]["placeholder"] == []
    assert (out / "MyVest-server-kit.zip").is_file()
    r = subprocess.run([sys.executable, str(HERE / "server_kit.py"), "--mod-dir", str(mod), "--mission", str(tmp_path / "x")],
                       capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("[FAIL]") and r.stdout == ""


def test_cli_repeated_deps_add_to_the_load_order(mod, tmp_path):
    """A second --deps adds to the list instead of replacing it, as /dayz-release-pack does."""
    r = subprocess.run([sys.executable, str(HERE / "server_kit.py"), "--mod-dir", str(mod), "--out", str(tmp_path / "cli"),
                        "--deps", "CF", "--deps", "COT", "--json"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["load_order"] == ["@CF", "@COT", "@MyVest"]


def test_cli_mod_dir_with_instance_name(mod, tmp_path):
    """--mod-dir plus an instance name resolves .server/<instance>/mission/ under the current folder."""
    project = tmp_path / "proj"
    shutil.copytree(FIXTURES / "mission", project / ".server" / "chernarus" / "mission")
    r = subprocess.run([sys.executable, str(HERE / "server_kit.py"), "--mod-dir", str(mod), "--out", str(tmp_path / "cli"),
                        "--mission", "chernarus", "--json"], capture_output=True, text=True, cwd=project)
    assert r.returncode == 0, r.stdout + r.stderr
    report = json.loads(r.stdout)
    assert Path(report["mission"]) == project / ".server" / "chernarus" / "mission"
    assert report["types"]["mission"] == ["MyVest_Green", "MyVest_Pouch"]


def test_item_in_a_sub_folder_config_gets_a_types_entry(mod, tmp_path):
    """Imported mods keep CfgPatches at the root and the items in data/config.cpp."""
    (mod / "data").mkdir()
    (mod / "data" / "config.cpp").write_text(
        "class CfgPatches\n{\n\tclass MyVest_Data\n\t{\n\t\tunits[] = {};\n\t\tweapons[] = {};\n"
        "\t\trequiredVersion = 0.1;\n\t\trequiredAddons[] = {\"MyVest\"};\n\t};\n};\n"
        "class CfgVehicles\n{\n\tclass Inventory_Base;\n\tclass MyVest_SubItem: Inventory_Base\n\t{\n"
        "\t\tscope = 2;\n\t};\n};\n", encoding="utf-8")
    report, members = build(mod, tmp_path)
    assert "MyVest_SubItem" in type_names(members)
    assert "MyVest_SubItem" in report["types"]["placeholder"]


def test_broken_mission_economycore_exits_2(mod, tmp_path):
    mission = tmp_path / "mission"
    shutil.copytree(FIXTURES / "mission", mission)
    (mission / "cfgeconomycore.xml").write_text("<economycore><ce folder=\"custom\">", encoding="utf-8")
    with pytest.raises(kit.ReleaseError, match="does not parse"):
        build(mod, tmp_path, mission)
    r = subprocess.run([sys.executable, str(HERE / "server_kit.py"), "--mod-dir", str(mod), "--out", str(tmp_path / "cli"),
                        "--mission", str(mission)], capture_output=True, text=True)
    assert r.returncode == 2 and "does not parse" in r.stderr
    assert not (tmp_path / "cli" / "MyVest-server-kit.zip").exists()


@pytest.mark.parametrize("folder", ["Addons", "ADDONS", "Keys", "keys", "output", ".vscode"])
def test_types_files_under_skipped_folders_are_ignored(mod, tmp_path, folder):
    (mod / folder).mkdir(exist_ok=True)
    (mod / folder / "types.xml").write_text(
        '<types><type name="MyVest_Green"><nominal>99</nominal></type></types>', encoding="utf-8")
    assert all(folder not in p.relative_to(mod).parts for p in kit.mod_types_files(mod))
    report, members = build(mod, tmp_path)
    assert report["types"]["mod"] == ["MyVest_Black"]
    assert b"<nominal>99</nominal>" not in members["MyVest_ce/types.xml"]


def test_mod_dir_instance_roots_include_the_cached_project(mod, tmp_path, monkeypatch):
    cached = tmp_path / "cached"
    cached.mkdir()

    class FakeState:
        @staticmethod
        def cached_project_root():
            return cached

    monkeypatch.setattr(kit.h, "load_module", lambda name, path: FakeState)
    monkeypatch.chdir(tmp_path)
    assert kit.instance_roots(True, mod) == [tmp_path, cached.resolve()]


def test_malformed_mod_types_file_exits_2_and_names_the_file(mod, tmp_path):
    """A typo in the mod's own types.xml must not silently swap its real entry for a placeholder."""
    bad = mod / "server" / "types.xml"
    bad.write_text(bad.read_text(encoding="utf-8")[:200], encoding="utf-8")
    with pytest.raises(kit.ReleaseError, match="does not parse") as e:
        build(mod, tmp_path)
    assert str(bad) in str(e.value)
    r = subprocess.run([sys.executable, str(HERE / "server_kit.py"), "--mod-dir", str(mod), "--out", str(tmp_path / "cli")],
                       capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("[FAIL]") and "types.xml" in r.stderr
    assert not (tmp_path / "cli" / "MyVest-server-kit.zip").exists()


def test_malformed_non_types_xml_in_mod_is_ignored(mod, tmp_path):
    (mod / "notes.xml").write_text("<notes><unclosed>", encoding="utf-8")
    report, _ = build(mod, tmp_path)
    assert report["types"]["mod"] == ["MyVest_Black"]


@pytest.mark.parametrize("rel", ["db/types.xml", "custom/extra.xml"])
def test_malformed_mission_types_file_exits_2(mod, tmp_path, rel):
    """db/types.xml and a type="types" file from cfgeconomycore.xml are both declared types files."""
    mission = tmp_path / "mission"
    shutil.copytree(FIXTURES / "mission", mission)
    (mission / rel).write_text("<types><type name=\"MyVest_Green\">", encoding="utf-8")
    with pytest.raises(kit.ReleaseError, match="does not parse") as e:
        build(mod, tmp_path, mission)
    assert str(mission / rel) in str(e.value)
    assert not (tmp_path / "out" / "MyVest-server-kit.zip").exists()


def test_mod_types_entry_with_unknown_class_is_warned(mod, tmp_path):
    (mod / "server" / "extra.xml").write_text(
        '<types><type name="MyVest_Blak"><nominal>3</nominal></type></types>', encoding="utf-8")
    report, members = build(mod, tmp_path)
    assert "MyVest_Blak" in report["types"]["mod"]
    warn = [w for w in report["warnings"] if w.startswith("types-unknown-class")]
    assert len(warn) == 1 and "MyVest_Blak" in warn[0] and "MyVest_Black" not in warn[0]


def test_placeholder_warning_names_the_mission_when_one_was_searched(mod, tmp_path):
    mission = tmp_path / "mission"
    shutil.copytree(FIXTURES / "mission", mission)
    (mission / "custom" / "extra.xml").write_text("<types></types>", encoding="utf-8")
    report, _ = build(mod, tmp_path, mission)
    assert report["types"]["placeholder"] == ["MyVest_Pouch"]
    warn = next(w for w in report["warnings"] if w.startswith("placeholder-types"))
    assert "the mod or the mission" in warn and "--mission" not in warn


def test_existing_kit_is_replaced_with_notice(mod, tmp_path):
    report, _ = build(mod, tmp_path)
    assert report["replaced"] is False and "(replaced the previous kit)" not in kit.render_text(report)
    report, _ = build(mod, tmp_path)
    assert report["replaced"] is True and "(replaced the previous kit)" in kit.render_text(report)
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["MyVest-server-kit.zip"]


def test_mission_types_file_with_wrong_root_exits_2(mod, tmp_path):
    """A cfgeconomycore type="types" file whose root is not <types> must not be dropped silently."""
    mission = tmp_path / "mission"
    shutil.copytree(FIXTURES / "mission", mission)
    (mission / "custom" / "extra.xml").write_text('<type name="MyVest_Pouch"><nominal>2</nominal></type>', encoding="utf-8")
    with pytest.raises(kit.ReleaseError, match="not <types>") as e:
        build(mod, tmp_path, mission)
    assert str(mission / "custom" / "extra.xml") in str(e.value)


def test_failed_zip_write_keeps_the_old_kit_and_leaves_no_temp_file(mod, tmp_path, monkeypatch):
    report, _ = build(mod, tmp_path)
    old = Path(report["zip"]).read_bytes()

    def boom(self, name, data, *a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(kit.zipfile.ZipFile, "writestr", boom)
    with pytest.raises(OSError, match="disk full"):
        kit.server_kit("MyVest", mod, tmp_path / "out", p_mods=None)
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["MyVest-server-kit.zip"]
    assert Path(report["zip"]).read_bytes() == old


def test_mission_folder_that_is_not_a_mission_exits_2_and_names_the_subfolder(mod, tmp_path):
    """An instance folder passed instead of its mission subfolder must not run as if the mission had been searched."""
    instance = tmp_path / "project" / ".server" / "chernarus"
    shutil.copytree(FIXTURES / "mission", instance / "mission")
    with pytest.raises(kit.ReleaseError, match="not a mission folder") as e:
        build(mod, tmp_path, instance)
    assert str(instance / "mission") in str(e.value)
    out = tmp_path / "cli"
    r = subprocess.run([sys.executable, str(HERE / "server_kit.py"), "--mod-dir", str(mod), "--out", str(out),
                        "--mission", str(instance)], capture_output=True, text=True)
    assert r.returncode == 2 and r.stderr.startswith("[FAIL]") and str(instance / "mission") in r.stderr
    assert not out.exists()


def test_empty_folder_as_mission_exits_2(mod, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(kit.ReleaseError, match="no db.types.xml and no cfgeconomycore.xml"):
        build(mod, tmp_path, empty)


def test_missing_listed_mission_types_file_exits_2(mod, tmp_path):
    """A type="types" file cfgeconomycore.xml lists but that is not on disk must not turn its classes into placeholders."""
    mission = tmp_path / "mission"
    shutil.copytree(FIXTURES / "mission", mission)
    (mission / "custom" / "extra.xml").unlink()
    with pytest.raises(kit.ReleaseError, match="does not exist") as e:
        build(mod, tmp_path, mission)
    assert str(mission / "custom" / "extra.xml") in str(e.value)
    assert not (tmp_path / "out").exists()


def test_mission_with_only_cfgeconomycore_is_accepted(mod, tmp_path):
    mission = tmp_path / "mission"
    shutil.copytree(FIXTURES / "mission", mission)
    (mission / "db" / "types.xml").unlink()
    report, _ = build(mod, tmp_path, mission)
    assert report["types"]["mission"] == ["MyVest_Pouch"]
    assert report["types"]["placeholder"] == ["MyVest_Green"]


def test_workshop_summary_warning_is_not_passed_on(mod, tmp_path):
    # The kit writes no Workshop text, so the release pack's summary-missing warning does not apply.
    (mod / "mod.cpp").unlink()
    report, _ = build(mod, tmp_path, FIXTURES / "mission", ["CF"])
    assert not any(w.startswith("summary-missing") for w in report["warnings"])
