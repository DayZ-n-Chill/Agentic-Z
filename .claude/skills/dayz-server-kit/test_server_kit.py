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
