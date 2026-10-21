"""Tests for conflict_check.py: fixture mods built in tmp_path with planted collisions. No DayZ, no real P:\\."""
from __future__ import annotations

import importlib.util
import json
import struct
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dayz_conflict_check_under_test", HERE / "conflict_check.py")
cc = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cc  # its dataclass looks the module up by name
_spec.loader.exec_module(cc)

OUR_CONFIG = """class CfgPatches
{
    class MyVest
    {
        units[] = {"MyVest_Plate"};
        weapons[] = {};
        requiredAddons[] = {"DZ_Data"};
    };
};
class CfgVehicles
{
    class Clothing;
    class MyVest_Plate: Clothing
    {
        scope = 2;
    };
};
"""

OUR_SCRIPT = """modded class PlayerBase
{
};
class MyVest_Helper
{
};
"""


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_mod(root: Path, prefix: str = "MyVest", config: str = OUR_CONFIG, script: str = OUR_SCRIPT) -> Path:
    write(root / "$PBOPREFIX$", prefix + "\n")
    write(root / "config.cpp", config)
    write(root / "scripts" / "4_World" / "MyVest.c", script)
    write(root / "data" / "plate_co.paa", "x")
    return root


def make_pbo(path: Path, prefix: str, files: dict[str, bytes]) -> Path:
    """A real PBO: a Vers entry with the prefix, one entry per file, the end entry, then the data."""
    head = b"\0" + struct.pack("<5I", cc.VERS, 0, 0, 0, 0) + b"prefix\0" + prefix.encode() + b"\0\0"
    for name, data in files.items():
        head += name.encode() + b"\0" + struct.pack("<5I", 0, len(data), 0, 0, len(data))
    head += b"\0" + struct.pack("<5I", 0, 0, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(head + b"".join(files.values()) + b"\0" * 21)
    return path


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A mods folder with CF and COT as PBOs and an Expansion part with an unpacked addon; an empty vanilla P:."""
    mods = tmp_path / "Mods"
    make_pbo(mods / "@CF" / "Addons" / "scripts.pbo", "JM\\CF\\Scripts",
             {"config.bin": b"raP", "4_World\\Entities\\PlayerBase.c": b"modded class PlayerBase {};"})
    make_pbo(mods / "@Community-Online-Tools" / "Addons" / "gui.pbo", "JM\\COT\\GUI",
             {"config.bin": b"raP", "layouts\\menu.layout": b"FrameWidgetClass x {}"})
    exp = mods / "@DayZ-Expansion-Core" / "Addons" / "core"
    write(exp / "$PBOPREFIX$", "DayZExpansion\\Core\n")
    write(exp / "config.cpp", """class CfgPatches { class DayZExpansion_Core { units[] = {}; weapons[] = {}; requiredAddons[] = {}; }; };
class CfgVehicles { class Inventory_Base; class ExpansionBox: Inventory_Base { scope = 2; }; };
""")
    write(exp / "scripts" / "Expansion.c", "class ExpansionHelper\n{\n};\n")
    p_drive = tmp_path / "P"
    (p_drive / "DZ").mkdir(parents=True)
    monkeypatch.setattr(cc, "P_DRIVE", p_drive)
    return tmp_path


def check(world: Path, mod_dir: Path, against=None) -> dict:
    targets = cc.resolve_targets(against or [], False, world / "Mods", mod_dir.name)
    return cc.check_mod(mod_dir.name, mod_dir, targets, world, world / "P")


def rules(report: dict) -> list[str]:
    return [f["rule"] for f in report["findings"]]


# --- clean -------------------------------------------------------------------

def test_clean_mod_passes(world):
    report = check(world, make_mod(world / "workspace" / "MyVest", script="class MyVest_Helper\n{\n};\n"))
    assert report["verdict"] == "PASS"
    assert report["findings"] == []
    assert [s["mod"] for s in report["scanned"]] == ["@CF", "@Community-Online-Tools", "@DayZ-Expansion-Core"]
    assert "PBO headers only" in report["note"]


# --- planted collisions -------------------------------------------------------

def test_same_prefix_is_an_error(world):
    report = check(world, make_mod(world / "workspace" / "MyVest", prefix="JM\\CF\\Scripts"))
    f = next(f for f in report["findings"] if f["rule"] == "prefix-same")
    assert f["severity"] == "error" and f["mod"] == "@CF"
    assert f["other"] == "@CF/Addons/scripts.pbo"
    assert report["verdict"] == "FAIL"


def test_nested_prefix_warns_and_shared_path_fails(world):
    mod = make_mod(world / "workspace" / "MyVest", prefix="JM\\CF", script="class MyVest_Helper\n{\n};\n")
    write(mod / "Scripts" / "4_World" / "Entities" / "PlayerBase.c", "class MyVest_Other\n{\n};\n")
    report = check(world, mod)
    assert "prefix-nested" in rules(report)
    path = next(f for f in report["findings"] if f["rule"] == "path-collision")
    assert path["severity"] == "error"
    assert "jm\\cf\\scripts\\4_world\\entities\\playerbase.c" in path["message"]
    assert path["other"].endswith("scripts.pbo > 4_World\\Entities\\PlayerBase.c")


def test_cfgpatches_collision(world):
    config = OUR_CONFIG.replace("class MyVest\n", "class DayZExpansion_Core\n")
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config))
    f = next(f for f in report["findings"] if f["rule"] == "cfgpatches-collision")
    assert f["severity"] == "error" and f["where"] == "workspace/MyVest/config.cpp:3"
    assert f["other"] == "@DayZ-Expansion-Core/Addons/core/config.cpp:1"


def test_config_class_collision_and_override(world):
    config = OUR_CONFIG.replace("MyVest_Plate: Clothing", "ExpansionBox: Clothing")
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config))
    assert "class-collision" in rules(report)
    required = config.replace('{"DZ_Data"}', '{"DZ_Data", "DayZExpansion_Core"}')
    report = check(world, make_mod(world / "workspace" / "MyVest", config=required))
    assert "class-override" in rules(report) and "class-collision" not in rules(report)
    assert report["verdict"] == "PASS"


def test_vanilla_class_both_change_is_a_warning(world):
    write(world / "P" / "DZ" / "gear" / "config.cpp", "class CfgVehicles { class Inventory_Base; class ExpansionBox: Inventory_Base {}; };")
    config = OUR_CONFIG.replace("MyVest_Plate: Clothing", "ExpansionBox: Clothing")
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config, script="class MyVest_Helper\n{\n};\n"))
    assert rules(report) == ["vanilla-class-overlap"]
    assert report["findings"][0]["severity"] == "warning"


def test_script_class_collision(world):
    report = check(world, make_mod(world / "workspace" / "MyVest", script="class ExpansionHelper\n{\n};\n"))
    f = next(f for f in report["findings"] if f["rule"] == "script-class-collision")
    assert f["where"] == "workspace/MyVest/scripts/4_World/MyVest.c:1"
    assert f["other"] == "@DayZ-Expansion-Core/Addons/core/scripts/Expansion.c:1"


def test_modded_class_overlap_in_unpacked_mod(world):
    write(world / "Mods" / "@DayZ-Expansion-Core" / "Addons" / "core" / "scripts" / "Player.c", "modded class PlayerBase\n{\n};\n")
    report = check(world, make_mod(world / "workspace" / "MyVest"))
    f = next(f for f in report["findings"] if f["rule"] == "modded-class-overlap")
    assert f["severity"] == "warning" and f["mod"] == "@DayZ-Expansion-Core"


def test_script_file_name_in_pbo_header_is_a_likely_overlap(world):
    report = check(world, make_mod(world / "workspace" / "MyVest"))
    f = next(f for f in report["findings"] if f["rule"] == "script-name-match")
    assert f["mod"] == "@CF" and "4_World\\Entities\\PlayerBase.c" in f["message"]
    assert report["verdict"] == "PASS"


def test_comments_and_strings_are_not_declarations(world):
    script = '// class ExpansionHelper\n/* modded class PlayerBase */\nstring s = "class ExpansionHelper";\n'
    config = OUR_CONFIG + '// class CfgPatches { class DayZExpansion_Core {}; };\n'
    report = check(world, make_mod(world / "workspace" / "MyVest", config=config, script=script))
    assert report["findings"] == []


# --- reading only headers -----------------------------------------------------

def test_header_reader_stops_at_the_data(tmp_path):
    pbo = make_pbo(tmp_path / "a.pbo", "Some\\Prefix", {"config.bin": b"\xff" * 64, "x\\y.c": b"class Hidden {};"})
    props, names = cc.read_pbo_header(pbo)
    assert props["prefix"] == "Some\\Prefix"
    assert names == ["config.bin", "x\\y.c"]


def test_truncated_pbo_is_reported_not_fatal(world):
    (world / "Mods" / "@CF" / "Addons" / "broken.pbo").write_bytes(b"abc")
    report = check(world, make_mod(world / "workspace" / "MyVest"))
    cf = next(s for s in report["scanned"] if s["mod"] == "@CF")
    assert cf["pbo_headers"] == 1 and len(cf["unreadable"]) == 1


def test_scan_never_writes_to_other_mods(world):
    mods = world / "Mods"
    before = {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in mods.rglob("*")}
    check(world, make_mod(world / "workspace" / "MyVest", prefix="JM\\CF\\Scripts"))
    assert {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in mods.rglob("*")} == before


# --- which mods ---------------------------------------------------------------

def test_expansion_bundle_replaces_its_parts(tmp_path):
    for name in ("@CF", "@DayZ-Expansion-Vehicles", "@DayZ-Expansion-Core", "@DayZ-Expansion-Bundle", "@Other"):
        (tmp_path / name).mkdir()
    assert [p.name for p in cc.default_targets(tmp_path)] == ["@CF", "@DayZ-Expansion-Bundle"]
    (tmp_path / "@DayZ-Expansion-Bundle").rmdir()
    assert [p.name for p in cc.default_targets(tmp_path)] == ["@CF", "@DayZ-Expansion-Core", "@DayZ-Expansion-Vehicles"]


def test_against_names_and_own_mod(tmp_path):
    for name in ("@CF", "@MyVest", "@Other"):
        (tmp_path / name).mkdir()
    assert [p.name for p in cc.resolve_targets(["CF", "@Other", "MyVest"], False, tmp_path, "MyVest")] == ["@CF", "@Other"]
    assert [p.name for p in cc.resolve_targets([], True, tmp_path, "MyVest")] == ["@CF", "@Other"]
    with pytest.raises(cc.ConflictError):
        cc.resolve_targets(["Missing"], False, tmp_path, "MyVest")


# --- CLI ----------------------------------------------------------------------

def test_cli_json_fail(world, capsys):
    mod = make_mod(world / "workspace" / "MyVest", prefix="JM\\COT\\GUI")
    rc = cc.main(["--mod-dir", str(mod), "--mods-root", str(world / "Mods"), "--json"])
    out = capsys.readouterr().out
    verdict, _, body = out.partition("\n")
    assert rc == 1 and verdict == "FAIL"
    assert json.loads(body)["findings"][0]["rule"] == "prefix-same"


def test_cli_text_lists_owner_and_fix(world, capsys):
    rc = cc.main(["--mod-dir", str(make_mod(world / "workspace" / "MyVest")), "--mods-root", str(world / "Mods")])
    out = capsys.readouterr().out
    assert rc == 0 and out.startswith("PASS\n")
    assert "-> dayz-script-specialist:" in out and "scanned @CF: 1 PBO header(s)" in out


def test_cli_error_when_nothing_to_compare(world, capsys):
    rc = cc.main(["--mod-dir", str(make_mod(world / "workspace" / "MyVest")), "--mods-root", str(world / "Empty")])
    assert rc == 2 and capsys.readouterr().out.startswith("ERROR\n")


def test_cli_error_on_missing_mod(world, capsys):
    rc = cc.main(["--mod-dir", str(world / "nope"), "--mods-root", str(world / "Mods")])
    assert rc == 2


# --- the in-game option (the gate is never really run here) ------------------

@pytest.mark.parametrize("gate_verdict, rc_expected", [("PASS", 0), ("FAIL", 1)])
def test_ingame_runs_the_gate_with_the_compared_mods(world, monkeypatch, capsys, gate_verdict, rc_expected):
    make_mod(world / "workspace" / "MyVest")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    calls = []

    def fake_run(cmd):
        calls.append(cmd)
        gate = {"verdict": gate_verdict, "failures": [{"category": "script", "file": "script.log", "line": 4, "text": "SCRIPT (E): boom"}] if gate_verdict == "FAIL" else []}
        return (0 if gate_verdict == "PASS" else 1), gate_verdict + "\n" + json.dumps(gate)

    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--ingame", "--server", "chernarus-hc"], run=fake_run)
    out = capsys.readouterr().out
    assert rc == rc_expected
    cmd = calls[0]
    assert cmd[0] == sys.executable and Path(cmd[1]).name == "gate.py"
    assert cmd[2:] == ["ingame", "MyVest", "--deps", "@CF", "@Community-Online-Tools", "@DayZ-Expansion-Core",
                       "--server", "chernarus-hc", "--port", "2302", "--json"]
    assert f"in-game gate on chernarus-hc with @CF @Community-Online-Tools @DayZ-Expansion-Core: {gate_verdict}" in out
    if gate_verdict == "FAIL":
        assert "SCRIPT (E): boom" in out


def test_ingame_unreadable_gate_output_fails(world, monkeypatch, capsys):
    make_mod(world / "workspace" / "MyVest")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--ingame", "--json"], run=lambda cmd: (2, "ERROR\n  no instance"))
    report = json.loads(capsys.readouterr().out.partition("\n")[2])
    assert rc == 1 and report["ingame"]["verdict"] == "ERROR"


def test_ingame_needs_a_project_mod(world, capsys):
    assert cc.main(["--mod-dir", str(world), "--ingame"]) == 2


def test_ingame_refuses_a_source_folder_in_against(world, monkeypatch, capsys):
    make_mod(world / "workspace" / "MyVest")
    source = make_mod(world / "OtherSource", prefix="OtherSource")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--against", str(source), "--ingame"],
                 run=lambda cmd: pytest.fail("the gate must not run"))
    out = capsys.readouterr().out
    assert rc == 2 and out.startswith("ERROR")
    assert "OtherSource" in out and "@mod" in out


def test_ingame_accepts_named_mods_in_against(world, monkeypatch, capsys):
    make_mod(world / "workspace" / "MyVest")
    monkeypatch.setattr(cc.h, "resolve_project_dir", lambda: world)
    calls = []
    rc = cc.main(["MyVest", "--mods-root", str(world / "Mods"), "--against", "CF", "--ingame"],
                 run=lambda cmd: calls.append(cmd) or (0, "PASS\n{}"))
    assert rc == 0 and calls[0][4:6] == ["--deps", "@CF"]
